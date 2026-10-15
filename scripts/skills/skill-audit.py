#!/usr/bin/env python3
"""
skill-audit.py — EXHAUSTIVE, DETECTION-ONLY auditor for Agent Skills.
Requires: Python 3.8+, PyYAML (pip install pyyaml). Purpose: audit skills against the
agentskills.io spec/best-practice/guidance rules. Idempotent: yes (read-only).

Ships INSIDE the skill-creator skill (scripts/skill-audit.py) so any environment that
has the bundle can audit existing skills. Encodes a rule for every claim on the
agentskills.io specification, using-scripts, and best-practices pages (plus the
evaluating-skills / optimizing-descriptions guides and the repo house rules). The
full claim→rule map lives in references/spec-claim-coverage.md. It NEVER edits skills.
Per skill it emits, per rule, one of:
  PASS  — rule satisfied
  FAIL  — rule violated (mechanical)
  NA    — rule does not apply to this skill
  REVIEW— judgment rule; a human must evaluate applicability/quality

Outputs a Markdown compliance matrix (--md) and prints a summary. Remediation and
exemption-justification are done by hand, per file.

Usage:
  python3 scripts/skill-audit.py <skill-dir>...        # audit existing skill(s)
  python3 scripts/skill-audit.py --portable [--md out] # the whole portable bundle
  SKILL_REPO_ROOT=/path python3 .../skill-audit.py --portable
Exit 0 if no FAILs, 1 otherwise.
"""
# /// script
# requires-python = ">=3.8"
# dependencies = ["pyyaml>=6,<7"]
# ///
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

# Repo/bundle root: $SKILL_REPO_ROOT, else walk up from this script (it lives at
# <root>/.claude/skills/skill-creator/scripts/) to the nearest dir that has portable/,
# or both .agent and .claude, or a .git. Else cwd. Only --portable needs the root;
# per-directory auditing takes explicit paths and needs none. Never hardcode.
def _default_root():
    try:
        here = Path(__file__).resolve()
        for p in (here, *here.parents):
            if (p / "portable").is_dir() or ((p / ".agent").is_dir() and (p / ".claude").is_dir()) or (p / ".git").is_dir():
                return p
    except OSError:
        pass
    return Path.cwd()
ROOT = Path(os.environ.get("SKILL_REPO_ROOT") or _default_root())
ALLOWED_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
STDLIB_HINT = {"os", "sys", "re", "json", "glob", "argparse", "subprocess", "pathlib",
               "datetime", "shutil", "stat", "math", "collections", "itertools",
               "functools", "typing", "hashlib", "base64", "tempfile", "io", "time",
               "random", "string", "textwrap", "csv", "sqlite3", "urllib", "http"}
THIRD_PARTY_HINT = {"requests", "yaml", "bs4", "beautifulsoup4", "numpy", "pandas",
                    "pydantic", "click", "rich", "httpx", "aiohttp"}
GENERIC_GOTCHA = [r"handle errors? (appropriately|properly)", r"follow best practices",
                  r"use good (judgment|practices)", r"be careful", r"make sure to test"]


def build_ctx(d: Path) -> dict:
    c: dict = {"dir": d, "name": d.name}
    md = d / "SKILL.md"
    c["md_exists"] = md.exists()
    text = md.read_text(encoding="utf-8") if md.exists() else ""
    c["text"] = text
    m = re.match(r"^---[ \t]*\n(.*?)\n---[ \t]*\n?", text, re.S)
    c["fm_block"] = m.group(1) if m else None
    c["body"] = text[m.end():] if m else ""
    c["fm"] = None
    c["fm_error"] = None
    if m:
        try:
            fm = yaml.safe_load(m.group(1))
            c["fm"] = fm if isinstance(fm, dict) else None
            if not isinstance(fm, dict):
                c["fm_error"] = "not a mapping"
        except yaml.YAMLError as e:
            c["fm_error"] = str(e).splitlines()[0]
    fm = c["fm"] or {}
    c["desc"] = re.sub(r"\s+", " ", str(fm.get("description", ""))).strip()
    sc = d / "scripts"
    c["scripts_dir"] = sc
    root_scripts = [p for p in list(d.glob("*.py")) + list(d.glob("*.sh"))]
    sub_scripts = [p for p in (list(sc.glob("*.py")) + list(sc.glob("*.sh")))
                   if p.name != "validate-skill.py"] if sc.exists() else []
    c["functional"] = root_scripts + sub_scripts
    c["procedural"] = "<!-- procedural -->" in text
    # Files (not dirs) directly at the skill root. Spec layout puts executable
    # code in scripts/, docs in references/, data in assets/ — only SKILL.md (and
    # a spec-sanctioned bundled LICENSE) belong loose at the root.
    c["root_extra"] = sorted(
        p.name for p in d.iterdir()
        if p.is_file() and p.name != "SKILL.md" and not p.name.upper().startswith("LICENSE")
    )
    # Skill-root-relative references only. The references/|scripts/|assets/ prefix must sit
    # at a token boundary — otherwise the tail of a longer path (e.g. another skill's
    # ".agent/skills/{name}/scripts/run.py", or the page name "using-scripts/best-practices")
    # would be misread as a reference to a file in THIS skill.
    c["refs"] = sorted(set(re.findall(r"(?<![\w./\-])(references/[\w\-./]+|scripts/[\w\-./]+|assets/[\w\-./]+)", text)))
    # Absolute (filesystem-root) reference paths only. The leading "/" must sit at
    # a token boundary — otherwise a *relative* path like ".agent/skills/x/scripts/y"
    # would be misread as absolute because it contains "/scripts/" mid-string.
    c["abs_refs"] = re.findall(r"(?<![\w./\-])(/[\w\-./]+/(?:references|scripts|assets)/[\w\-./]+)", text)
    c["rubric"] = (d / "assets/rubric.json")
    return c


def jload(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return e


# ---- rule registry: id -> (source, kind, fn(ctx)->(status, detail)) ----
RULES: list[tuple[str, str, str, object]] = []


def rule(rid, source, kind):
    def deco(fn):
        RULES.append((rid, source, kind, fn))
        return fn
    return deco


def ok(): return ("PASS", "")
def na(why=""): return ("NA", why)
def review(why): return ("REVIEW", why)
def fail(why): return ("FAIL", why)


def load_exemptions(skill_dir):
    """Per-skill written justifications for non-PASS rules: {rule_id: reason}.

    A skill records why a rule legitimately does not apply (NA) or why a REVIEW is
    accepted in <skill>/audit-exemptions.json. The auditor treats such cells as
    accounted; any non-PASS cell with neither a rule-supplied reason nor an exemption
    is UNACCOUNTED (a silent skipped rule) and blocks the audit.
    """
    p = Path(skill_dir) / "audit-exemptions.json"
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if isinstance(data, dict) and isinstance(data.get("exemptions"), dict):
        data = data["exemptions"]
    return {k: v for k, v in data.items() if isinstance(v, str) and v.strip()} \
        if isinstance(data, dict) else {}


# ===== SPECIFICATION — structure & frontmatter =====
@rule("SPEC-01-skillmd-exists", "spec", "mech")
def _(c): return ok() if c["md_exists"] else fail("SKILL.md missing")

@rule("SPEC-02-frontmatter-present", "spec", "mech")
def _(c): return ok() if c["fm_block"] is not None else fail("no --- frontmatter --- block")

@rule("SPEC-03-frontmatter-valid-yaml", "spec", "mech")
def _(c):
    if c["fm_block"] is None: return na("no frontmatter")
    return fail(f"invalid YAML: {c['fm_error']}") if c["fm_error"] else ok()

@rule("SPEC-04-name-present", "spec", "mech")
def _(c): return ok() if (c["fm"] or {}).get("name") is not None else fail("name missing")

@rule("SPEC-05-name-string", "spec", "mech")
def _(c):
    n = (c["fm"] or {}).get("name")
    return ok() if isinstance(n, str) else fail("name not a string")

@rule("SPEC-06-name-len-1-64", "spec", "mech")
def _(c):
    n = (c["fm"] or {}).get("name")
    if not isinstance(n, str): return na("name field absent or not a string (see SPEC-04/05)")
    return ok() if 1 <= len(n) <= 64 else fail(f"len {len(n)}")

@rule("SPEC-07-name-charset", "spec", "mech")
def _(c):
    n = (c["fm"] or {}).get("name")
    if not isinstance(n, str): return na("name field absent or not a string (see SPEC-04/05)")
    return ok() if NAME_RE.match(n) else fail("not lowercase-alnum-hyphen")

@rule("SPEC-08-name-no-leading-hyphen", "spec", "mech")
def _(c):
    n = (c["fm"] or {}).get("name")
    if not isinstance(n, str): return na("name field absent or not a string (see SPEC-04/05)")
    return ok() if not n.startswith("-") else fail("leading hyphen")

@rule("SPEC-09-name-no-trailing-hyphen", "spec", "mech")
def _(c):
    n = (c["fm"] or {}).get("name")
    if not isinstance(n, str): return na("name field absent or not a string (see SPEC-04/05)")
    return ok() if not n.endswith("-") else fail("trailing hyphen")

@rule("SPEC-10-name-no-double-hyphen", "spec", "mech")
def _(c):
    n = (c["fm"] or {}).get("name")
    if not isinstance(n, str): return na("name field absent or not a string (see SPEC-04/05)")
    return ok() if "--" not in n else fail("consecutive hyphens")

@rule("SPEC-11-name-matches-dir", "spec", "mech")
def _(c):
    n = (c["fm"] or {}).get("name")
    return ok() if n == c["name"] else fail(f"name '{n}' != dir '{c['name']}'")

@rule("SPEC-12-description-present", "spec", "mech")
def _(c): return ok() if (c["fm"] or {}).get("description") is not None else fail("description missing")

@rule("SPEC-13-description-string", "spec", "mech")
def _(c):
    de = (c["fm"] or {}).get("description")
    return ok() if isinstance(de, str) else fail("description not a string")

@rule("SPEC-14-description-nonempty", "spec", "mech")
def _(c): return ok() if c["desc"] else fail("description empty")

@rule("SPEC-15-description-max-1024", "spec", "mech")
def _(c):
    return ok() if len(c["desc"]) <= 1024 else fail(f"len {len(c['desc'])} > 1024")

@rule("SPEC-16-description-what-and-when", "spec", "judge")
def _(c):
    if not c["desc"]: return na("no description present (see SPEC-12/14)")
    has_when = "use this skill when" in c["desc"].lower() or " when " in c["desc"].lower()
    return ok() if has_when else review("does it say WHAT and WHEN?")

@rule("SPEC-17-only-allowed-top-keys", "spec", "mech")
def _(c):
    if not c["fm"]: return na("no parseable frontmatter (see SPEC-02/03)")
    extra = set(c["fm"]) - ALLOWED_KEYS
    return ok() if not extra else fail(f"non-spec keys {sorted(extra)}")

@rule("SPEC-18-license-string", "spec", "mech")
def _(c):
    lic = (c["fm"] or {}).get("license")
    if lic is None: return na("optional")
    return ok() if isinstance(lic, str) else fail("license not a string")

@rule("SPEC-19-compatibility-string", "spec", "mech")
def _(c):
    co = (c["fm"] or {}).get("compatibility")
    if co is None: return na("optional")
    return ok() if isinstance(co, str) else fail("compatibility not a string")

@rule("SPEC-20-compatibility-max-500", "spec", "mech")
def _(c):
    co = (c["fm"] or {}).get("compatibility")
    if not isinstance(co, str): return na("no compatibility field (optional)")
    return ok() if len(co) <= 500 else fail(f"len {len(co)} > 500")

@rule("SPEC-21-metadata-mapping", "spec", "mech")
def _(c):
    me = (c["fm"] or {}).get("metadata")
    if me is None: return na("optional")
    return ok() if isinstance(me, dict) else fail("metadata not a mapping")

@rule("SPEC-22-metadata-keys-string", "spec", "mech")
def _(c):
    me = (c["fm"] or {}).get("metadata")
    if not isinstance(me, dict): return na("no metadata mapping (optional, see SPEC-21)")
    bad = [k for k in me if not isinstance(k, str)]
    return ok() if not bad else fail(f"non-string keys {bad}")

@rule("SPEC-23-metadata-values-string", "spec", "mech")
def _(c):
    me = (c["fm"] or {}).get("metadata")
    if not isinstance(me, dict): return na("no metadata mapping (optional, see SPEC-21)")
    bad = [k for k, v in me.items() if not isinstance(v, str)]
    return ok() if not bad else fail(f"non-string values {bad}")

@rule("SPEC-24-allowed-tools-string", "spec", "mech")
def _(c):
    at = (c["fm"] or {}).get("allowed-tools")
    if at is None: return na("optional")
    return ok() if isinstance(at, str) else fail("allowed-tools not a string")

@rule("SPEC-25-body-present", "spec", "mech")
def _(c): return ok() if c["body"].strip() else fail("no markdown body after frontmatter")

@rule("SPEC-26-skillmd-max-500-lines", "spec", "mech")
def _(c):
    n = len(c["text"].splitlines())
    return ok() if n <= 500 else fail(f"{n} lines > 500")

@rule("SPEC-27-skillmd-under-5000-tokens", "spec", "mech")
def _(c):
    approx = len(c["text"]) // 4
    return ok() if approx < 5000 else fail(f"~{approx} tokens >= 5000")

@rule("SPEC-28-refs-relative", "spec", "mech")
def _(c):
    return fail(f"absolute ref paths {c['abs_refs'][:2]}") if c["abs_refs"] else ok()

@rule("SPEC-29-refs-one-level-deep", "spec", "mech")
def _(c):
    deep = [r for r in c["refs"] if r.count("/") > 1]
    return fail(f"refs nested >1 level: {deep[:2]}") if deep else ok()

@rule("SPEC-30-refs-exist", "spec", "mech")
def _(c):
    miss = [r for r in c["refs"] if not (c["dir"] / r).exists()]
    return fail(f"missing refs {miss[:3]}") if miss else ok()

@rule("SPEC-31-root-only-skillmd", "spec", "mech")
def _(c):
    # Spec directory structure: SKILL.md at the root; executable code in
    # scripts/, docs in references/, data/schemas in assets/. A loose file at
    # the skill root (run.py, schema.json, README.md, ...) is misplaced.
    # Only applies to actual skills — a dir without SKILL.md is not a skill
    # (SPEC-01 already flags that), so the layout rule does not apply.
    if not c["md_exists"]: return na("not a skill (no SKILL.md)")
    return fail(f"non-SKILL.md files at skill root: {c['root_extra']}") if c["root_extra"] else ok()

@rule("SPEC-32-description-keyword-rich", "spec", "judge")
def _(c):
    # Spec: description "Should include specific keywords that help agents identify
    # relevant tasks." A very short description cannot carry those keywords.
    if not c["desc"]: return na("no description present (see SPEC-12/14)")
    words = len(re.findall(r"\w+", c["desc"]))
    return ok() if words >= 12 else review(f"only {words} words — too sparse for trigger keywords")

@rule("SPEC-33-allowed-tools-space-separated", "spec", "mech")
def _(c):
    # Spec: allowed-tools is a "Space-separated string of pre-approved tools."
    at = (c["fm"] or {}).get("allowed-tools")
    if not isinstance(at, str): return na("no allowed-tools field (optional)")
    if "\n" in at: return fail("allowed-tools spans multiple lines (must be space-separated)")
    if "," in at: return fail("allowed-tools comma-separated (spec: space-separated)")
    return ok()

@rule("SPEC-34-license-concise", "spec", "judge")
def _(c):
    # Spec: "We recommend keeping it short (either the name of a license or the name
    # of a bundled license file)."
    lic = (c["fm"] or {}).get("license")
    if not isinstance(lic, str): return na("no license field (optional)")
    return ok() if len(lic) <= 120 else review(f"license is {len(lic)} chars — spec recommends keeping it short")

@rule("SPEC-35-body-recommends-examples", "spec", "judge")
def _(c):
    # Spec recommended body sections include "Examples of inputs and outputs". A
    # functional/procedural skill with no example block likely omits them.
    if not c["body"].strip(): return na("empty body (see SPEC-25)")
    if "```" in c["body"] or re.search(r"^##+\s*Examples?\b", c["body"], re.M | re.I):
        return ok()
    return review("no example/code block (spec recommends input/output examples)")

# ===== OPTIMIZING DESCRIPTIONS =====
@rule("DESC-01-starts-use-this-skill-when", "optimizing-descriptions", "mech")
def _(c):
    if not c["desc"]: return na("no description present (see SPEC-12/14)")
    return ok() if c["desc"].startswith("Use this skill when") else fail("does not start with 'Use this skill when'")

@rule("DESC-02-imperative-not-this-skill-does", "optimizing-descriptions", "mech")
def _(c):
    return fail("'This skill does …' phrasing") if re.match(r"this skill (does|is|will|helps)", c["desc"], re.I) else ok()

@rule("DESC-03-pushy-even-if-not-named", "optimizing-descriptions", "judge")
def _(c):
    if not c["desc"]: return na("no description present (see SPEC-12/14)")
    if re.search(r"even if|not named|without (naming|mentioning)|don'?t (mention|say)", c["desc"], re.I):
        return ok()
    return review("no 'even if not named' pushiness clause")

@rule("DESC-04-concise-max-6-sentences", "optimizing-descriptions", "mech")
def _(c):
    s = len(re.findall(r"[.!?](\s|$)", c["desc"]))
    return ok() if s <= 6 else fail(f"{s} sentences > 6")

@rule("DESC-05-no-duplicated-text", "optimizing-descriptions", "mech")
def _(c):
    low = c["desc"].lower()
    dup = next((low[i:i+45] for i in range(0, max(0, len(low) - 45), 5) if low.count(low[i:i+45]) > 1), None)
    return fail(f"duplicated '…{dup.strip()}…'") if dup else ok()

@rule("DESC-06-states-exclusion", "best-practices", "judge")
def _(c):
    if not c["desc"]: return na("no description present (see SPEC-12/14)")
    return ok() if re.search(r"does not|doesn'?t|not for|rather than|not the\b", c["desc"], re.I) else review("no exclusion ('does not …')")

# ===== EVAL QUERIES (optimizing-descriptions + house) =====
@rule("EVAL-01-eval-queries-exist", "house", "mech")
def _(c): return ok() if (c["scripts_dir"] / "eval_queries.json").exists() else fail("scripts/eval_queries.json missing")

@rule("EVAL-02-eval-queries-valid-json", "house", "mech")
def _(c):
    p = c["scripts_dir"] / "eval_queries.json"
    if not p.exists(): return na("no eval_queries.json (see EVAL-01)")
    q = jload(p)
    return fail(f"invalid JSON: {q}") if isinstance(q, Exception) else (ok() if isinstance(q, list) else fail("not a list"))

@rule("EVAL-03-entries-well-formed", "optimizing-descriptions", "mech")
def _(c):
    p = c["scripts_dir"] / "eval_queries.json"; q = jload(p) if p.exists() else None
    if not isinstance(q, list): return na("no/invalid eval_queries.json (see EVAL-02)")
    bad = [x for x in q if not isinstance(x, dict) or "query" not in x or "should_trigger" not in x]
    return fail("entries missing query/should_trigger") if bad else ok()

@rule("EVAL-04-min-10-should-trigger", "optimizing-descriptions", "mech")
def _(c):
    p = c["scripts_dir"] / "eval_queries.json"; q = jload(p) if p.exists() else None
    if not isinstance(q, list): return na("no/invalid eval_queries.json (see EVAL-02)")
    t = sum(1 for x in q if isinstance(x, dict) and x.get("should_trigger"))
    return ok() if t >= 10 else fail(f"{t} should-trigger < 10")

@rule("EVAL-05-min-8-should-not-trigger", "optimizing-descriptions", "mech")
def _(c):
    p = c["scripts_dir"] / "eval_queries.json"; q = jload(p) if p.exists() else None
    if not isinstance(q, list): return na("no/invalid eval_queries.json (see EVAL-02)")
    n = sum(1 for x in q if isinstance(x, dict) and not x.get("should_trigger"))
    return ok() if n >= 8 else fail(f"{n} should-not-trigger < 8")

@rule("EVAL-06-no-duplicate-queries", "optimizing-descriptions", "mech")
def _(c):
    p = c["scripts_dir"] / "eval_queries.json"; q = jload(p) if p.exists() else None
    if not isinstance(q, list): return na("no/invalid eval_queries.json (see EVAL-02)")
    qs = [x.get("query") for x in q if isinstance(x, dict)]
    return fail("duplicate queries") if len(qs) != len(set(qs)) else ok()

@rule("EVAL-07-negatives-are-near-misses", "optimizing-descriptions", "judge")
def _(c):
    p = c["scripts_dir"] / "eval_queries.json"; q = jload(p) if p.exists() else None
    if not isinstance(q, list): return na("no/invalid eval_queries.json (see EVAL-02)")
    toks = set(re.split(r"[-_ ]", c["name"]))
    negs = [x.get("query", "") for x in q if isinstance(x, dict) and not x.get("should_trigger")]
    nearmiss = sum(1 for n in negs if toks & set(re.split(r"\W+", n.lower())))
    return ok() if nearmiss >= 1 else review("no near-miss negatives (share a keyword)")

@rule("EVAL-08-evals-json-exists", "evaluating-skills", "mech")
def _(c): return ok() if (c["dir"] / "evals/evals.json").exists() else fail("evals/evals.json missing")

@rule("EVAL-09-evals-has-cases", "evaluating-skills", "mech")
def _(c):
    p = c["dir"] / "evals/evals.json"; e = jload(p) if p.exists() else None
    if e is None: return na("no evals.json (see EVAL-08)")
    if isinstance(e, Exception): return fail(f"invalid JSON: {e}")
    return ok() if (isinstance(e, dict) and e.get("evals")) else fail("no evals cases")

@rule("EVAL-10-cases-have-prompt", "evaluating-skills", "mech")
def _(c):
    p = c["dir"] / "evals/evals.json"; e = jload(p) if p.exists() else None
    if not isinstance(e, dict) or not e.get("evals"): return na("no evals.json cases (see EVAL-08/09)")
    return ok() if all(x.get("prompt") for x in e["evals"]) else fail("a case lacks prompt")

@rule("EVAL-11-cases-have-expected-output", "evaluating-skills", "mech")
def _(c):
    p = c["dir"] / "evals/evals.json"; e = jload(p) if p.exists() else None
    if not isinstance(e, dict) or not e.get("evals"): return na("no evals.json cases (see EVAL-08/09)")
    return ok() if all(x.get("expected_output") for x in e["evals"]) else fail("a case lacks expected_output")

@rule("EVAL-12-cases-have-assertions", "evaluating-skills", "mech")
def _(c):
    p = c["dir"] / "evals/evals.json"; e = jload(p) if p.exists() else None
    if not isinstance(e, dict) or not e.get("evals"): return na("no evals.json cases (see EVAL-08/09)")
    return ok() if all(x.get("assertions") for x in e["evals"]) else fail("a case lacks assertions")

@rule("EVAL-13-assertions-verifiable", "evaluating-skills", "judge")
def _(c):
    p = c["dir"] / "evals/evals.json"; e = jload(p) if p.exists() else None
    if not isinstance(e, dict) or not e.get("evals"): return na("no evals.json cases (see EVAL-08/09)")
    vague = [a for x in e["evals"] for a in x.get("assertions", []) if re.search(r"\b(is good|looks? (good|right)|works? well)\b", a, re.I)]
    return review(f"vague assertions: {vague[:1]}") if vague else ok()

# ===== USING SCRIPTS + HOUSE =====
@rule("SCR-01-validate-skill-present", "house", "mech")
def _(c): return ok() if (c["scripts_dir"] / "validate-skill.py").exists() else fail("scripts/validate-skill.py missing")

@rule("SCR-02-functional-script-or-procedural", "house", "mech")
def _(c):
    return ok() if (c["functional"] or c["procedural"]) else fail("no functional script and not marked procedural")

@rule("SCR-03-script-language-py-or-sh", "house", "mech")
def _(c):
    bad = [p.name for p in c["functional"] if p.suffix not in (".py", ".sh")]
    return fail(f"non py/sh scripts {bad}") if bad else ok()

@rule("SCR-04-functional-script-not-thin", "best-practices", "judge")
def _(c):
    if not c["functional"]: return na("procedural")
    for f in c["functional"]:
        b = f.read_text(encoding="utf-8", errors="ignore")
        loc = len([l for l in b.splitlines() if l.strip() and not l.strip().startswith("#")])
        if loc < 12 or ("for t in TERMS" in b and "rubric" not in b):
            return review(f"{f.name} may be thin ({loc} loc)")
    return ok()

@rule("SCR-05-dependency-header", "using-scripts", "mech")
def _(c):
    if not c["functional"]: return na("procedural skill (no functional script to check)")
    miss = []
    for f in c["functional"]:
        head = "\n".join(f.read_text(encoding="utf-8", errors="ignore").splitlines()[:12]).lower()
        if not re.search(r"requires|dependenc|purpose|/// script", head):
            miss.append(f.name)
    return fail(f"no dep/purpose header in {miss}") if miss else ok()

@rule("SCR-06-pep723-if-thirdparty", "using-scripts", "mech")
def _(c):
    for f in c["functional"]:
        if f.suffix != ".py": continue
        b = f.read_text(encoding="utf-8", errors="ignore")
        imps = set(re.findall(r"^\s*(?:import|from)\s+([a-zA-Z0-9_]+)", b, re.M))
        tp = (imps & THIRD_PARTY_HINT) - STDLIB_HINT
        if tp and "/// script" not in b:
            return fail(f"{f.name} imports {sorted(tp)} without PEP 723 block")
    return ok() if c["functional"] else na("procedural skill (no functional script to check)")

@rule("SCR-07-supports-help", "using-scripts", "mech")
def _(c):
    if not c["functional"]: return na("procedural skill (no functional script to check)")
    for f in c["functional"]:
        b = f.read_text(encoding="utf-8", errors="ignore")
        if f.suffix == ".py" and "argparse" not in b and "--help" not in b and "sys.argv" in b:
            return review(f"{f.name} parses argv without argparse/--help")
    return ok()

@rule("SCR-08-documents-exit-codes", "using-scripts", "judge")
def _(c):
    if not c["functional"]: return na("procedural skill (no functional script to check)")
    for f in c["functional"]:
        b = f.read_text(encoding="utf-8", errors="ignore")
        if "sys.exit" in b and not re.search(r"exit code|epilog|exit\s*0|exit 0", b, re.I):
            return review(f"{f.name} exits without documenting codes")
    return ok()

@rule("SCR-09-structured-output", "using-scripts", "judge")
def _(c):
    if not c["functional"]: return na("procedural skill (no functional script to check)")
    if any("json." in f.read_text(encoding="utf-8", errors="ignore") for f in c["functional"]):
        return ok()
    return review("functional script may not emit structured output")

@rule("SCR-10-no-interactive-prompts", "using-scripts", "mech")
def _(c):
    for f in c["functional"]:
        b = f.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"\binput\s*\(|\braw_input\s*\(", b):
            return fail(f"{f.name} reads interactive stdin prompts")
    return ok() if c["functional"] else na("procedural skill (no functional script to check)")

@rule("SCR-11-dry-run-flag", "using-scripts", "judge")
def _(c):
    if not c["functional"]: return na("procedural skill (no functional script to check)")
    writes = any(re.search(r"\.write_text|open\([^)]*['\"][wa]", f.read_text(encoding="utf-8", errors="ignore")) for f in c["functional"])
    has_dry = any("--dry-run" in f.read_text(encoding="utf-8", errors="ignore") for f in c["functional"])
    if writes and not has_dry:
        return review("script writes files but has no --dry-run")
    return ok()

@rule("SCR-12-idempotent-documented", "using-scripts", "judge")
def _(c):
    if not c["functional"]: return na("procedural skill (no functional script to check)")
    if any("idempotent" in f.read_text(encoding="utf-8", errors="ignore").lower() for f in c["functional"]):
        return ok()
    return review("idempotency not documented in script header")

@rule("SCR-13-pinned-tool-versions", "using-scripts", "judge")
def _(c):
    if re.search(r"pip install \w+(?!\S*[=<>])", c["text"]) and not re.search(r"pip install \S+[=<>]", c["text"]):
        return review("install command without a pinned version")
    return ok()

@rule("SCR-14-procedural-marker-when-no-script", "house", "mech")
def _(c):
    if c["functional"]: return ok()
    return ok() if c["procedural"] else fail("no functional script and no <!-- procedural --> marker")

@rule("SCR-15-helpful-error-messages", "using-scripts", "judge")
def _(c):
    # using-scripts: "Write helpful error messages" — say what went wrong and what to try.
    if not c["functional"]: return na("procedural skill (no functional script to check)")
    for f in c["functional"]:
        b = f.read_text(encoding="utf-8", errors="ignore")
        emits = re.search(r"file\s*=\s*sys\.stderr|sys\.stderr\.write|logging\.(error|warning)"
                          r"|raise \w*Error\(|\bError:|usage:|parser\.error", b, re.I)
        if not emits:
            return review(f"{f.name}: no visible error-message path (stderr/raise/'Error:')")
    return ok()

@rule("SCR-16-diagnostics-to-stderr", "using-scripts", "judge")
def _(c):
    # using-scripts: "Separate data from diagnostics" — structured data to stdout,
    # progress/warnings/diagnostics to stderr.
    if not c["functional"]: return na("procedural skill (no functional script to check)")
    for f in c["functional"]:
        b = f.read_text(encoding="utf-8", errors="ignore")
        prints = len(re.findall(r"\bprint\s*\(", b))
        uses_stderr = "sys.stderr" in b or "file=sys.stderr" in b
        # many plain prints and no stderr at all → diagnostics likely mixed into stdout
        if prints >= 3 and not uses_stderr:
            return review(f"{f.name}: {prints} prints, none to stderr — diagnostics may pollute stdout")
    return ok()

@rule("SCR-17-safe-defaults-confirm", "using-scripts", "judge")
def _(c):
    # using-scripts: destructive operations should require explicit confirmation flags.
    if not c["functional"]: return na("procedural skill (no functional script to check)")
    for f in c["functional"]:
        b = f.read_text(encoding="utf-8", errors="ignore")
        destructive = re.search(r"shutil\.rmtree|os\.(remove|unlink|rmdir)|Path[^\n]*\.unlink\("
                                r"|\brm\s+-rf\b|DROP\s+TABLE|DELETE\s+FROM", b, re.I)
        guarded = re.search(r"--confirm|--force|--yes|--apply|dry[_-]?run", b, re.I)
        if destructive and not guarded:
            return review(f"{f.name}: destructive op without --confirm/--force/--dry-run guard")
    return ok()

@rule("SCR-18-predictable-output-size", "using-scripts", "judge")
def _(c):
    # using-scripts: large output should be paginated/limited (--offset/--limit/--output)
    # or summarized; harnesses truncate beyond ~10-30K chars.
    if not c["functional"]: return na("procedural skill (no functional script to check)")
    for f in c["functional"]:
        b = f.read_text(encoding="utf-8", errors="ignore")
        loops_print = re.search(r"for\b[^\n]*:\s*\n(?:[^\n]*\n)?\s*print\s*\(", b)
        paginated = re.search(r"--offset|--limit|--max|--output|\[:\s*\d|head|truncat", b, re.I)
        if loops_print and not paginated:
            return review(f"{f.name}: prints in a loop with no --limit/--offset/--output bound")
    return ok()

# ===== BEST PRACTICES — body =====
@rule("BP-01-has-purpose", "house", "mech")
def _(c):
    return ok() if re.search(r"^##+\s*Purpose", c["body"], re.M | re.I) else review("no Purpose section")

@rule("BP-02-has-workflow", "best-practices", "judge")
def _(c):
    return ok() if re.search(r"^##+\s*(Workflow|Pipeline|Steps|Invocation|Available scripts)", c["body"], re.M | re.I) else review("no Workflow/Invocation section")

@rule("BP-03-has-gotchas", "best-practices", "mech")
def _(c):
    return ok() if re.search(r"^##+\s*Gotchas", c["body"], re.M | re.I) else fail("no Gotchas section")

@rule("BP-04-gotchas-concrete", "best-practices", "judge")
def _(c):
    g = re.search(r"(?ms)^##+\s*Gotchas\s*\n(.*?)(?=\n##|\Z)", c["body"], re.I)
    if not g: return na("no Gotchas section to evaluate (see BP-03)")
    hits = [p for p in GENERIC_GOTCHA if re.search(p, g.group(1), re.I)]
    return review(f"generic gotcha advice: {hits}") if hits else ok()

@rule("BP-05-no-equal-weight-menus", "best-practices", "judge")
def _(c):
    if re.search(r"\b(use|choose|pick) \w+,? (\w+,? )?or \w+", c["body"], re.I):
        return review("possible equal-weight 'use X or Y or Z' menu")
    return ok()

@rule("BP-06-load-when-for-references", "best-practices", "judge")
def _(c):
    refmd = [r for r in c["refs"] if r.startswith("references/")]
    if not refmd: return na("no references/ files to load")
    # require a 'load/read … when/before' instruction near a reference mention
    if re.search(r"(load|read|consult)[^.\n]*references/[^.\n]*\b(when|before|if)\b", c["body"], re.I) or \
       re.search(r"\b(when|before)\b[^.\n]*references/", c["body"], re.I):
        return ok()
    return review("references present but no explicit 'load when' instruction")

@rule("BP-07-lists-available-scripts", "using-scripts", "judge")
def _(c):
    if not c["functional"]: return na("procedural skill (no functional script to check)")
    named = any(f.name in c["body"] or f"scripts/{f.name}" in c["body"] for f in c["functional"])
    return ok() if named else review("functional script not referenced in SKILL.md body")

# ===== HOUSE frontmatter =====
@rule("HOUSE-01-metadata-team", "house", "judge")
def _(c):
    me = (c["fm"] or {}).get("metadata") or {}
    return ok() if me.get("team") else review("metadata.team missing")

@rule("HOUSE-02-metadata-version", "house", "judge")
def _(c):
    me = (c["fm"] or {}).get("metadata") or {}
    return ok() if me.get("version") else review("metadata.version missing")

@rule("HOUSE-03-license-present", "house", "judge")
def _(c):
    return ok() if (c["fm"] or {}).get("license") else review("license missing (house: recommended)")

@rule("HOUSE-04-source-provenance", "house", "judge")
def _(c):
    # Every extracted/imported/derived skill MUST record where it came from, so its design
    # intent (the what/why) is traceable to the source and not mistaken for a defect later.
    # Accept metadata.source/origin/extracted_from/derived_from, or a references/provenance.md.
    me = (c["fm"] or {}).get("metadata") or {}
    if any(me.get(k) for k in ("source", "origin", "extracted_from", "derived_from", "provenance")):
        return ok()
    if (c["dir"] / "references" / "provenance.md").exists():
        return ok()
    return review("no recorded source/provenance — where was this skill extracted/derived from? "
                  "(record metadata.source or references/provenance.md)")

@rule("HOUSE-05-output-contract", "house", "mech")
def _(c):
    # New standard (founder 2026-06-20): an atomic skill must declare a typed OUTPUT CONTRACT
    # in frontmatter so composed skills can combine its structured output deterministically;
    # composed skills likewise declare their outcome contract. Record metadata.output_contract.
    me = (c["fm"] or {}).get("metadata") or {}
    typ = str(me.get("type", "")).lower()
    if typ not in ("atomic", "composed"):
        return na("no metadata.type=atomic|composed (output-contract requirement applies to those)")
    oc = me.get("output_contract")
    return ok() if (isinstance(oc, str) and oc.strip()) \
        else fail("metadata.output_contract missing — atomic/composed skills must declare a "
                  "typed output contract in frontmatter")

def _contract_top_keys(oc: str):
    """Top-level JSON object keys named in an output_contract's first {...} group."""
    i = oc.find("{")
    if i < 0:
        return []
    depth = 0
    end = i
    for end in range(i, len(oc)):
        if oc[end] == "{":
            depth += 1
        elif oc[end] == "}":
            depth -= 1
            if depth == 0:
                break
    inner = oc[i + 1:end]
    parts, d, cur = [], 0, ""
    for ch in inner:
        if ch in "[{(":
            d += 1; cur += ch
        elif ch in "]})":
            d -= 1; cur += ch
        elif ch == "," and d == 0:
            parts.append(cur); cur = ""
        else:
            cur += ch
    parts.append(cur)
    keys = []
    for p in parts:
        m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)", p)
        if m:
            keys.append(m.group(1))
    return keys

@rule("HOUSE-06-output-contract-honored", "house", "mech")
def _(c):
    # An output_contract the script does not emit is just another unverified claim. Statically
    # enforce that every top-level key the contract declares is actually referenced as a string
    # literal in the functional script(s) — catches a declared key the run.py never produces.
    me = (c["fm"] or {}).get("metadata") or {}
    oc = me.get("output_contract")
    if not (isinstance(oc, str) and oc.strip()):
        return na("no output_contract (see HOUSE-05)")
    keys = _contract_top_keys(oc)
    if not keys:
        return na("output_contract declares no JSON object keys (non-JSON contract)")
    funcs = [f for f in c["functional"] if f.suffix == ".py"]
    if not funcs:
        return na("no python functional script to check the contract against")
    src = "\n".join(f.read_text(encoding="utf-8", errors="ignore") for f in funcs)
    missing = [k for k in keys if (f'"{k}"' not in src and f"'{k}'" not in src)]
    return fail(f"output_contract declares keys the script never emits: {missing} "
                f"(the contract must match run.py's actual output)") if missing else ok()

@rule("HOUSE-07-input-contract", "house", "mech")
def _(c):
    # New standard (founder 2026-06-20): an atomic/composed skill must declare a typed INPUT
    # CONTRACT in frontmatter — what it consumes AND who produces it (the human: a code repo
    # or an undefined-structure document; and/or named upstream skill(s)) — so an orchestrator
    # can chain producer→consumer skills back to a human-useful result. Without it the
    # producer→consumer map is unknowable. Record metadata.input_contract.
    me = (c["fm"] or {}).get("metadata") or {}
    typ = str(me.get("type", "")).lower()
    if typ not in ("atomic", "composed"):
        return na("no metadata.type=atomic|composed (input-contract requirement applies to those)")
    ic = me.get("input_contract")
    return ok() if (isinstance(ic, str) and ic.strip()) \
        else fail("metadata.input_contract missing — atomic/composed skills must declare a "
                  "typed input contract (what it consumes + its producer) in frontmatter")

# ===== ANALYZER skills (rubric present) =====
def _is_analyzer(c): return c["rubric"].exists()

@rule("AN-01-analyze-present", "house", "mech")
def _(c):
    if not _is_analyzer(c): return na("not an analyzer skill (no assets/rubric.json)")
    return ok() if (c["scripts_dir"] / "analyze.py").exists() else fail("rubric present but analyze.py missing")

@rule("AN-02-rubric-valid-json", "house", "mech")
def _(c):
    if not _is_analyzer(c): return na("not an analyzer skill (no assets/rubric.json)")
    r = jload(c["rubric"])
    return fail(f"invalid JSON: {r}") if isinstance(r, Exception) else ok()

@rule("AN-03-rubric-controls-wellformed", "house", "mech")
def _(c):
    if not _is_analyzer(c): return na("not an analyzer skill (no assets/rubric.json)")
    r = jload(c["rubric"])
    if isinstance(r, Exception): return na("rubric.json not valid JSON (see AN-02)")
    ctrls = r.get("controls") or []
    if not ctrls: return fail("no controls")
    bad = [x.get("id") for x in ctrls if not all(k in x for k in ("id", "title", "evidence_any", "remediation"))]
    return fail(f"controls missing fields {bad[:2]}") if bad else ok()

@rule("AN-04-antipatterns-valid-regex", "house", "mech")
def _(c):
    if not _is_analyzer(c): return na("not an analyzer skill (no assets/rubric.json)")
    r = jload(c["rubric"])
    if isinstance(r, Exception): return na("rubric.json not valid JSON (see AN-02)")
    for ap in r.get("antipatterns", []):
        try: re.compile(ap["pattern"])
        except re.error as e: return fail(f"bad regex {ap.get('id')}: {e}")
    return ok()

@rule("AN-05-fixtures-present", "house", "mech")
def _(c):
    if not _is_analyzer(c): return na("not an analyzer skill (no assets/rubric.json)")
    g = (c["dir"] / "evals/files/good-plan.md").exists()
    w = (c["dir"] / "evals/files/weak-plan.md").exists()
    return ok() if g and w else fail("missing good-plan/weak-plan fixtures")

@rule("AN-06-good-fixture-converges", "house", "mech")
def _(c):
    if not _is_analyzer(c): return na("not an analyzer skill (no assets/rubric.json)")
    ap = c["scripts_dir"] / "analyze.py"; good = c["dir"] / "evals/files/good-plan.md"
    if not ap.exists() or not good.exists(): return na("analyze.py or good-plan fixture missing (see AN-01/05)")
    rc = subprocess.run([sys.executable, str(ap), "--plan", str(good)], capture_output=True).returncode
    return ok() if rc == 0 else fail(f"good-plan exit {rc} (want 0)")

@rule("AN-07-weak-fixture-fails", "house", "mech")
def _(c):
    if not _is_analyzer(c): return na("not an analyzer skill (no assets/rubric.json)")
    ap = c["scripts_dir"] / "analyze.py"; weak = c["dir"] / "evals/files/weak-plan.md"
    if not ap.exists() or not weak.exists(): return na("analyze.py or weak-plan fixture missing (see AN-01/05)")
    rc = subprocess.run([sys.executable, str(ap), "--plan", str(weak)], capture_output=True).returncode
    return ok() if rc == 1 else fail(f"weak-plan exit {rc} (want 1)")

@rule("AN-08-rubric-not-name-bingo", "house", "judge")
def _(c):
    # Early extracts produced "keyword-bingo" rubrics: controls whose evidence is just the
    # skill-NAME tokens (e.g. secure-coding -> controls secure/coding/practices), so a plan
    # passes by echoing the title, not by real domain coverage. A real rubric's controls
    # must be derived from the CLAIMS in the source material, with evidence independent of
    # the skill name. Flag rubrics that are mostly name-bingo (convergence gap).
    if not _is_analyzer(c): return na("not an analyzer skill (no assets/rubric.json)")
    r = jload(c["rubric"])
    if isinstance(r, Exception): return na("rubric.json not valid JSON (see AN-02)")
    ctrls = r.get("controls") or []
    if not ctrls: return na("rubric has no controls (see AN-03)")
    name_tokens = {t for t in re.split(r"[-_]", c["name"]) if t}
    bingo = 0
    for ct in ctrls:
        toks = set()
        for e in (ct.get("evidence_any") or []):
            toks |= {t for t in re.split(r"[\s\-_]+", str(e).lower()) if t}
        if toks and toks <= name_tokens:
            bingo += 1
    if bingo and bingo >= (len(ctrls) + 1) // 2:
        return review(f"rubric is keyword-bingo on the skill name ({bingo}/{len(ctrls)} controls' "
                      f"evidence is only name tokens) — derive real domain controls from the "
                      f"source claims (convergence)")
    return ok()


def canonical(name):
    a = ROOT / ".agent/skills" / name
    return a if a.is_dir() else ROOT / ".claude/skills" / name


def main():
    args = sys.argv[1:]
    out_md = None
    if "--md" in args:
        i = args.index("--md"); out_md = args[i + 1]; args = args[:i] + args[i + 2:]
    if args == ["--portable"]:
        # Validate the ACTUAL bundle copies (both tiers). Works whether ROOT is the repo
        # (skills under ROOT/portable/) or ROOT is itself a bundle/destination root
        # (skills directly under ROOT/.agent and ROOT/.claude).
        dirs = []
        layouts = (("portable/.agent/skills", "portable/.claude/skills"),
                   (".agent/skills", ".claude/skills"))
        for layout in layouts:
            for tier in layout:
                base = ROOT / tier
                if base.is_dir():
                    dirs += sorted((d for d in base.iterdir() if d.is_dir()), key=lambda p: p.name)
            if dirs:
                break
        if not dirs:
            print(f"error: no skills found under {ROOT}/portable/ or {ROOT}/.agent|.claude "
                  f"(set $SKILL_REPO_ROOT or run from the repo/bundle root)", file=sys.stderr)
            return 2
    elif args:
        dirs = [Path(a) for a in args]
    else:
        print("usage: skill-audit.py --portable | <dir>... [--md out.md]", file=sys.stderr); return 2

    results = {}  # skill -> {rule: (status, detail)}
    exemptions = {}  # skill -> {rule_id: justification}
    for d in dirs:
        c = build_ctx(d)
        exemptions[d.name] = load_exemptions(d)
        rr = {}
        for rid, src, kind, fn in RULES:
            try:
                rr[rid] = fn(c)
            except Exception as e:
                rr[rid] = ("FAIL", f"checker error: {e}")
        results[d.name] = rr

    # summary + ACCOUNTING ENFORCEMENT.
    # Hard boundary: every rule must PASS, FAIL, or be fully explained. A non-PASS cell
    # is "accounted" only if it carries a written reason —
    #   NA     -> accounted if the rule states a reason OR a per-skill exemption exists;
    #   REVIEW -> accounted only if a per-skill exemption (a recorded decision) exists
    #             (the rule's note is the open question, not its resolution);
    #   FAIL   -> never accounted here; it is a blocker that must be remediated.
    # An unaccounted NA/REVIEW is a silent skipped rule and is a BLOCKER (non-zero exit).
    counts = {s: 0 for s in ("PASS", "FAIL", "NA", "REVIEW")}
    rule_fail = {}
    skill_fail = {}
    skill_review = {}
    unaccounted = {}  # skill -> [(rid, status, detail)]
    for sk, rr in results.items():
        exempt = exemptions.get(sk, {})
        for rid, (st, det) in rr.items():
            counts[st] += 1
            if st == "FAIL":
                rule_fail[rid] = rule_fail.get(rid, 0) + 1
                skill_fail.setdefault(sk, []).append((rid, det))
            elif st == "REVIEW":
                skill_review.setdefault(sk, []).append((rid, det))
                if rid not in exempt:
                    unaccounted.setdefault(sk, []).append((rid, st, det))
            elif st == "NA":
                if not det and rid not in exempt:
                    unaccounted.setdefault(sk, []).append((rid, st, det))

    accounted_cells = counts["PASS"] + counts["NA"] + counts["REVIEW"] - sum(len(v) for v in unaccounted.values())
    print(f"rules: {len(RULES)}  skills: {len(dirs)}")
    print(f"cells PASS={counts['PASS']} FAIL={counts['FAIL']} NA={counts['NA']} REVIEW={counts['REVIEW']}")
    print(f"accounted: {accounted_cells + counts['FAIL']}/{len(RULES) * len(dirs)} "
          f"(FAIL counts as accounted-but-blocking)  UNACCOUNTED={sum(len(v) for v in unaccounted.values())}")
    print(f"skills with >=1 FAIL: {len(skill_fail)}   skills with >=1 REVIEW: {len(skill_review)}   "
          f"skills with >=1 UNACCOUNTED: {len(unaccounted)}")
    if rule_fail:
        print("\nFAIL counts by rule:")
        for rid, n in sorted(rule_fail.items(), key=lambda x: -x[1]):
            print(f"  {n:4d}  {rid}")
    if unaccounted:
        print("\nUNACCOUNTED (non-PASS rules with no reason — FAIL them or justify in "
              "audit-exemptions.json):")
        for sk in sorted(unaccounted):
            for rid, st, det in unaccounted[sk]:
                print(f"  {sk}: {rid} [{st}] {det or '(rule gave no reason)'}")

    if out_md:
        write_md(out_md, dirs, results, rule_fail, skill_fail, skill_review, counts)
        print(f"\nwrote matrix: {out_md}")
    return 1 if (counts["FAIL"] or unaccounted) else 0


def write_md(path, dirs, results, rule_fail, skill_fail, skill_review, counts):
    L = ["# Skill Compliance Audit Matrix\n",
         f"Generated by the skill-creator `scripts/skill-audit.py`. **Detection only** — remediation and "
         f"exemption justifications are added by hand.\n",
         f"\n**{len(RULES)} rules × {len(dirs)} skills.** "
         f"Cells: PASS={counts['PASS']} · FAIL={counts['FAIL']} · NA={counts['NA']} · REVIEW={counts['REVIEW']}.\n",
         f"\nSkills with ≥1 FAIL: **{len(skill_fail)}** · with ≥1 REVIEW: **{len(skill_review)}**.\n"]
    L.append("\n## Rule catalog\n\n| Rule | Source | Kind | FAILs |\n|---|---|---|---|")
    for rid, src, kind, fn in RULES:
        L.append(f"| `{rid}` | {src} | {kind} | {rule_fail.get(rid, 0)} |")
    L.append("\n## FAILs (must remediate by hand or justify an exemption)\n\n| Skill | Rule | Detail | Resolution |\n|---|---|---|---|")
    for sk in sorted(skill_fail):
        for rid, det in skill_fail[sk]:
            L.append(f"| `{sk}` | `{rid}` | {det} | _pending_ |")
    if not skill_fail:
        L.append("| — | — | none | — |")
    L.append("\n## REVIEW items (manual judgment of applicability/quality)\n\n| Skill | Rule | Note | Decision |\n|---|---|---|---|")
    for sk in sorted(skill_review):
        for rid, det in skill_review[sk]:
            L.append(f"| `{sk}` | `{rid}` | {det} | _pending_ |")
    Path(path).write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
