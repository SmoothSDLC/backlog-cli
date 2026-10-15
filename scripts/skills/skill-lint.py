#!/usr/bin/env python3
"""
skill-lint.py — comprehensive, STRICT validator for Agent Skills.
Requires: Python 3.8+, PyYAML (pip install pyyaml). Purpose: strict YAML/structure
pre-check for skills. Idempotent: yes (read-only).

DETECTION ONLY. This tool never modifies skills; it reports ERROR/WARN findings
against the agentskills.io specification, best practices, and the repo guidance
(docs/agent-skills-specification-guidance.md). Fixes are applied by hand, per file.

Ships INSIDE the skill-creator skill (scripts/skill-lint.py). Use skill-audit.py for
the full rule set; this is the fast strict gate.

Usage:
  python3 scripts/skill-lint.py <skill-dir> [<skill-dir> ...]
  python3 scripts/skill-lint.py --portable      # all skills in the portable bundle
Exit 0 = no ERRORs (WARN allowed), 1 = at least one ERROR, 2 = usage error.
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
# <root>/.claude/skills/skill-creator/scripts/) to the nearest dir with portable/, or
# both .agent and .claude, or a .git. Else cwd. Never hardcode an absolute checkout path.
def _default_root() -> Path:
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


def canonical_dir(name: str) -> Path:
    a = ROOT / ".agent/skills" / name
    return a if a.is_dir() else ROOT / ".claude/skills" / name


def lint(skill_dir: Path) -> tuple[list[str], list[str]]:
    E: list[str] = []  # errors
    W: list[str] = []  # warnings
    name = skill_dir.name
    md = skill_dir / "SKILL.md"
    if not md.exists():
        return (["SKILL.md missing"], [])
    text = md.read_text(encoding="utf-8")

    # --- frontmatter: must be a real YAML mapping delimited by --- / --- ---
    m = re.match(r"^---[ \t]*\n(.*?)\n---[ \t]*\n?", text, re.S)
    if not m:
        E.append("no valid --- frontmatter --- block")
        return (E, W)
    raw_fm = m.group(1)
    try:
        fm = yaml.safe_load(raw_fm)
    except yaml.YAMLError as e:
        E.append(f"frontmatter is not valid YAML: {str(e).splitlines()[0]}")
        return (E, W)
    if not isinstance(fm, dict):
        E.append("frontmatter is not a YAML mapping")
        return (E, W)

    # --- allowed keys ---
    extra = set(fm) - ALLOWED_KEYS
    if extra:
        E.append(f"non-spec top-level frontmatter keys: {sorted(extra)} (move under metadata)")

    # --- name ---
    nm = fm.get("name")
    if not isinstance(nm, str) or not nm:
        E.append("name missing or not a string")
    else:
        if nm != name:
            E.append(f"name '{nm}' != directory '{name}'")
        if not NAME_RE.match(nm):
            E.append(f"name '{nm}' violates charset (lowercase/digits/hyphen, no leading/trailing/double hyphen)")
        if len(nm) > 64:
            E.append(f"name length {len(nm)} > 64")

    # --- description ---
    desc = fm.get("description")
    if not isinstance(desc, str) or not desc.strip():
        E.append("description missing or empty")
    else:
        flat = re.sub(r"\s+", " ", desc).strip()
        if len(flat) > 1024:
            E.append(f"description length {len(flat)} > 1024")
        if not flat.startswith("Use this skill when"):
            E.append("description does not start with 'Use this skill when'")
        # duplication: any 45-char window occurring twice
        low = flat.lower()
        dup = next((low[i:i+45] for i in range(0, max(0, len(low) - 45), 5)
                    if low.count(low[i:i+45]) > 1), None)
        if dup:
            E.append(f"description contains duplicated text: '...{dup.strip()}...'")
        # best-practice: state what it does NOT do
        if not re.search(r"\b(does not|doesn't|not for|rather than|not the|it does not)\b", flat, re.I):
            W.append("description has no exclusion clause ('does not …') — best practice for trigger precision")
        # awkward 'you need to: <verb>s' grammar
        if re.search(r"you need to:\s+(runs|parses|derives|reports|identifies|commits|measures)\b", flat, re.I):
            W.append("description grammar is awkward ('you need to: runs …') — reword imperatively")

    # --- compatibility / metadata ---
    comp = fm.get("compatibility")
    if comp is not None and (not isinstance(comp, str) or len(comp) > 500):
        E.append("compatibility must be a string <= 500 chars")
    meta = fm.get("metadata")
    if meta is not None:
        if not isinstance(meta, dict):
            E.append("metadata must be a mapping")
        else:
            badv = [k for k, v in meta.items() if not isinstance(v, str)]
            if badv:
                E.append(f"metadata values must be strings; non-string: {badv}")

    # --- body ---
    body = text[m.end():]
    if len(text.splitlines()) > 500:
        E.append(f"SKILL.md {len(text.splitlines())} lines > 500")
    if not re.search(r"^##+\s*Gotchas", body, re.M | re.I):
        E.append("missing '## Gotchas' section")
    # referenced files must exist. The prefix must sit at a token boundary so the tail of a
    # longer path (another skill's ".agent/skills/{name}/scripts/run.py", or a page name like
    # "using-scripts/best-practices") is not misread as a reference to a file in THIS skill.
    for ref in sorted(set(re.findall(r"(?<![\w./\-])(references/[\w\-./]+|scripts/[\w\-./]+|assets/[\w\-./]+)", text))):
        if not (skill_dir / ref).exists():
            E.append(f"referenced file missing: {ref}")

    # --- scripts ---
    sc = skill_dir / "scripts"
    if not (sc / "validate-skill.py").exists():
        E.append("scripts/validate-skill.py missing")
    funcs = [p for p in list(skill_dir.glob("*.py")) + list(skill_dir.glob("*.sh"))]
    funcs += [p for p in (list(sc.glob("*.py")) + list(sc.glob("*.sh"))) if p.name != "validate-skill.py"] if sc.exists() else []
    procedural = "<!-- procedural -->" in text
    if not funcs and not procedural:
        E.append("no functional script and not marked '<!-- procedural -->'")

    # --- eval_queries.json ---
    eqp = sc / "eval_queries.json"
    if not eqp.exists():
        E.append("scripts/eval_queries.json missing")
    else:
        try:
            q = json.loads(eqp.read_text(encoding="utf-8"))
            if not isinstance(q, list):
                E.append("eval_queries.json is not a list")
            else:
                if any(not isinstance(x, dict) or "query" not in x or "should_trigger" not in x for x in q):
                    E.append("eval_queries entries must have 'query' and 'should_trigger'")
                tr = sum(1 for x in q if isinstance(x, dict) and x.get("should_trigger"))
                no = sum(1 for x in q if isinstance(x, dict) and not x.get("should_trigger"))
                if tr < 10:
                    E.append(f"eval_queries should-trigger {tr} < 10")
                if no < 8:
                    E.append(f"eval_queries should-not-trigger {no} < 8")
                qs = [x.get("query") for x in q if isinstance(x, dict)]
                if len(qs) != len(set(qs)):
                    E.append("eval_queries has duplicate queries")
        except ValueError as e:
            E.append(f"eval_queries.json invalid JSON: {e}")

    # --- evals/evals.json ---
    evp = skill_dir / "evals/evals.json"
    if not evp.exists():
        E.append("evals/evals.json missing")
    else:
        try:
            e = json.loads(evp.read_text(encoding="utf-8"))
            cases = e.get("evals") if isinstance(e, dict) else None
            if not cases:
                E.append("evals.json has no 'evals' cases")
            else:
                for c in cases:
                    if not c.get("assertions"):
                        E.append(f"evals case {c.get('id')} has no assertions")
                    if not c.get("prompt") or not c.get("expected_output"):
                        E.append(f"evals case {c.get('id')} missing prompt/expected_output")
        except ValueError as ex:
            E.append(f"evals.json invalid JSON: {ex}")

    # --- analyzer (rubric) skills ---
    rub = skill_dir / "assets/rubric.json"
    if rub.exists():
        if not (sc / "analyze.py").exists():
            E.append("rubric present but scripts/analyze.py missing")
        try:
            r = json.loads(rub.read_text(encoding="utf-8"))
            ctrls = r.get("controls")
            if not ctrls:
                E.append("rubric has no controls")
            else:
                for c in ctrls:
                    if not all(k in c for k in ("id", "title", "evidence_any", "remediation")):
                        E.append(f"rubric control missing fields: {c.get('id')}")
            for ap in r.get("antipatterns", []):
                try:
                    re.compile(ap["pattern"])
                except re.error as ex:
                    E.append(f"rubric antipattern '{ap.get('id')}' bad regex: {ex}")
        except ValueError as ex:
            E.append(f"rubric.json invalid JSON: {ex}")
        # fixtures + runtime gates
        good = skill_dir / "evals/files/good-plan.md"
        weak = skill_dir / "evals/files/weak-plan.md"
        if not good.exists() or not weak.exists():
            E.append("analyzer missing good-plan.md / weak-plan.md fixtures")
        else:
            ap = sc / "analyze.py"
            g = subprocess.run([sys.executable, str(ap), "--plan", str(good)], capture_output=True).returncode
            wv = subprocess.run([sys.executable, str(ap), "--plan", str(weak)], capture_output=True).returncode
            if g != 0:
                E.append(f"analyze.py on good-plan exited {g} (want 0)")
            if wv != 1:
                E.append(f"analyze.py on weak-plan exited {wv} (want 1)")

    return (E, W)


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print("usage: skill-lint.py <skill-dir>... | --portable", file=sys.stderr)
        return 2
    if args == ["--portable"]:
        # Validate the ACTUAL bundle copies (both tiers). Works whether ROOT is the repo
        # (skills under ROOT/portable/) or ROOT is itself a bundle/destination root.
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
    else:
        dirs = [Path(a) for a in args]
    total_err = 0
    err_skills = 0
    for d in dirs:
        E, W = lint(d)
        if E or W:
            print(f"\n{d.name}")
            for e in E:
                print(f"  ERROR  {e}")
            for w in W:
                print(f"  warn   {w}")
        if E:
            err_skills += 1
            total_err += len(E)
    print(f"\n{'='*50}\nskills checked: {len(dirs)}  |  skills with ERRORs: {err_skills}  |  total ERRORs: {total_err}")
    return 0 if total_err == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
