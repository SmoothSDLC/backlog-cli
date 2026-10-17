---
applyTo: ".github/skills/**,.agent/skills/**,.claude/skills/**,**/SKILL.md"
---

> Historical authoring reference. Current repository validation commands are
> documented in `skill-authoring-for-codex.md`; external tool paths below are
> examples from the source guidance, not an installed repository toolchain.

# Skill Creation & Structure Standards

These rules govern **all skills** created or modified in this repository. They are derived from the [Agent Skills specification](https://agentskills.io/specification), [best practices](https://agentskills.io/skill-creation/best-practices), [using scripts](https://agentskills.io/skill-creation/using-scripts), [evaluating skills](https://agentskills.io/skill-creation/evaluating-skills), and [optimizing descriptions](https://agentskills.io/skill-creation/optimizing-descriptions). Every skill MUST conform completely.

> **No exemptions.** No skill — new or pre-existing — is exempt from the agentskills.io specification, best practices, or these guidance standards. See `.agents/docs/agent-skills-specification-guidance.md` for the full knowledge base.

> **Authoritative validation:** the auditor and linter ship inside the **skill-creator** skill. `python3 .claude/skills/skill-creator/scripts/skill-lint.py --portable` must pass with **zero ERRORs**, and `python3 .claude/skills/skill-creator/scripts/skill-audit.py --portable` (one rule per agentskills.io spec claim) must report **zero FAILs**. They parse frontmatter as real YAML and check the actual spec/best-practice properties (the per-skill `scripts/validate-skill.py` is only a lightweight self-check and is not sufficient alone). Both are detection-only — fixes are made by hand, per file.

---

## 1. Required Directory Structure

```
.github/skills/<skill-name>/
├── SKILL.md                        # Required — frontmatter + instructions
├── scripts/
│   ├── validate-skill.py           # Required — self-validation script
│   └── <step-name>.py or .sh       # Required — at least one functional script
├── references/                     # Optional — detailed docs loaded on demand
└── assets/                         # Optional — templates, schemas, static data
```

The skill directory name MUST match the `name` field in `SKILL.md` frontmatter exactly.

---

## 2. SKILL.md Frontmatter Requirements

```yaml
---
name: <skill-name>                  # Required. Max 64 chars. Lowercase, hyphens only. No leading/trailing/consecutive hyphens.
description: >                      # Required. Max 1024 chars. Imperative. Start with "Use this skill when…"
  Use this skill when <specific trigger scenario>. Covers <scope>. Also
  applies when <non-obvious case where domain knowledge helps>.
license: Proprietary                # Required for repo skills.
compatibility: >                    # Required if environment-specific.
  Requires Python 3.8+, bash. <Any additional tool/env requirements>.
metadata:
  team: <team-name>
  version: "1.0"
---
```

**Description rules** (from [optimizing-descriptions](https://agentskills.io/skill-creation/optimizing-descriptions)):
- Use imperative phrasing: "Use this skill when…" not "This skill does…"
- Name specific scenarios where the skill is useful — including cases where users don't use domain terminology
- Include "even if they don't explicitly mention X" for non-obvious triggers
- Hard limit: **1024 characters**
- Test with ~20 trigger eval queries (10 should-trigger, 10 should-not) stored in `scripts/eval_queries.json`

---

## 3. scripts/ Folder Requirements

### Language
Scripts MUST be written in **Python 3.8+** (`*.py`) or **bash** (`*.sh`). No other script languages.
- Python is preferred for data processing, API calls, validation logic, and anything requiring structured output
- Bash is acceptable for simple orchestration, file manipulation, and CLI command sequences

### Required script: `validate-skill.py`
Every skill MUST include `scripts/validate-skill.py`. This script:
1. Runs `skills-ref validate .github/skills/<skill-name>` and asserts exit code 0
2. Checks all required files exist (SKILL.md, scripts/validate-skill.py, at least one functional script)
3. Asserts `SKILL.md` is under 500 lines
4. Verifies the `name` field matches the directory name
5. Checks all referenced files in SKILL.md actually exist
6. Runs any trigger eval queries in `scripts/eval_queries.json` if present
7. Exits 0 (all pass) or 1 (any failure) with a human-readable summary

### Script quality requirements
All scripts in `scripts/` MUST:
- **Be idempotent** — safe to run multiple times without side effects
- **Exit 0 on success, 1 on failure** — no other exit codes
- **Print human-readable status** — prefix lines with `✅`, `❌`, or `ℹ️` for clarity
- **Handle errors explicitly** — no silent failures; every external call should check return codes
- **Accept `--dry-run`** flag for destructive operations (deletes, writes, API mutations)
- **Be self-contained** — document all dependencies in a comment block at the top of the file

### Dependency declaration (top of every script)
```python
#!/usr/bin/env python3
"""
Script: <name>.py
Requires: python 3.8+, pip install requests (or: no external deps)
Purpose: <one-line description>
Idempotent: yes/no — <explanation if no>
"""
```

---

## 4. Deterministic and Convergent Behavior

Skills exist to produce **consistent, predictable outcomes**. Every skill must be designed for convergence:

### Validation loops
Multi-step skills MUST include explicit validation gates between phases:
```
Phase N → Validate state → (only proceed if valid) → Phase N+1
```
Never advance to the next step if the previous step's output cannot be verified.

### Plan-validate-execute pattern
For any operation that mutates external state (APIs, files, databases, repos):
1. **Plan** — generate a structured plan (JSON or checklist) describing what will change
2. **Validate** — check the plan against a source of truth (schema, API, filesystem)
3. **Execute** — only execute after the plan passes validation in step 2

### Idempotency
Every script outcome MUST be a stable fixed point: running the same script a second time with the same inputs produces the same result and no errors. Document any script that cannot be made fully idempotent and explain why.

### No ambiguous control flow
Skills MUST NOT present equal-weight alternatives ("you can use X or Y or Z"). Instead:
- Pick one default, implement it
- Note alternatives only as fallbacks with explicit conditions: "If X fails, fall back to Y"

### Pinned dependencies
Scripts that install packages MUST pin versions:
```python
# requirements.txt entries or inline:
# requests==2.31.0
# not: requests>=2
```

---

## 5. SKILL.md Body Quality Standards

From the [best practices guide](https://agentskills.io/skill-creation/best-practices):

### Size limits
- `SKILL.md` MUST be **under 500 lines / 5,000 tokens**
- Move detailed reference material to `references/<topic>.md`
- Instruct the skill when to load each reference file, not just "see references/"

### Required sections for operational skills
- **Purpose** — one paragraph: what problem this solves, when to use it
- **Prerequisites** — tools, credentials, environment setup required before running
- **Workflow** — numbered steps or checklist with explicit validation gates
- **Gotchas** — concrete, non-obvious facts that will cause failures without warning (not generic advice)

### Checklist format for multi-step workflow
```markdown
Progress:
- [ ] Step 1: <description> — run `scripts/<step1>.py`
- [ ] Step 2: <description> — validate with `scripts/<step2>.py --verify`
- [ ] Step 3: <description>
```

### Gotchas section (required if any non-obvious constraints exist)
```markdown
## Gotchas

- <Specific, concrete failure case>: <exactly what to do instead>
- <Environment quirk>: <precise workaround>
```

Do NOT include general advice in Gotchas ("handle errors properly"). Only include surprises that defy reasonable assumptions — facts the agent cannot know from general training.

---

## 6. Self-Validation: `scripts/validate-skill.py` Template

Every new skill MUST include this file, adapted to its actual structure:

```python
#!/usr/bin/env python3
"""
Script: validate-skill.py
Requires: python 3.8+, git (for skills-ref clone if not installed)
Purpose: Validates that this skill conforms to .github/skills.instructions.md
Idempotent: yes
"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]   # adjust depth for skill location
SKILL_DIR = Path(__file__).resolve().parents[1]
SKILL_NAME = SKILL_DIR.name
SKILL_MD = SKILL_DIR / "SKILL.md"
MAX_SKILL_LINES = 500

failures = []

def check(condition: bool, label: str) -> None:
    if condition:
        print(f"  ✅ {label}")
    else:
        print(f"  ❌ {label}")
        failures.append(label)

print(f"\n{'='*60}")
print(f"  Skill Self-Validation: {SKILL_NAME}")
print(f"{'='*60}\n")

# 1. Required files exist
check(SKILL_MD.exists(), "SKILL.md exists")
check((SKILL_DIR / "scripts" / "validate-skill.py").exists(), "scripts/validate-skill.py exists")

# 2. SKILL.md line count
if SKILL_MD.exists():
    lines = SKILL_MD.read_text(encoding="utf-8").splitlines()
    check(len(lines) <= MAX_SKILL_LINES, f"SKILL.md under {MAX_SKILL_LINES} lines (actual: {len(lines)})")

    # 3. name matches directory
    for line in lines:
        if line.startswith("name:"):
            declared = line.split(":", 1)[1].strip()
            check(declared == SKILL_NAME, f"SKILL.md name '{declared}' matches directory '{SKILL_NAME}'")
            break

    # 4. Referenced files exist
    import re
    refs = re.findall(r'`?(scripts/[\w\-\.]+|references/[\w\-\.]+|assets/[\w\-\.]+)`?', "\n".join(lines))
    for ref in set(refs):
        check((SKILL_DIR / ref).exists(), f"Referenced file exists: {ref}")

# 5. At least one non-validate script exists
scripts = [f for f in (SKILL_DIR / "scripts").glob("*.py") if f.name != "validate-skill.py"]
scripts += list((SKILL_DIR / "scripts").glob("*.sh"))
check(len(scripts) >= 1, f"At least one functional script in scripts/ (found: {len(scripts)})")

# 6. skills-ref validate (install if needed)
try:
    result = subprocess.run(
        ["skills-ref", "validate", str(SKILL_DIR)],
        capture_output=True, text=True
    )
    check(result.returncode == 0, f"skills-ref validate passes (output: {result.stdout.strip() or result.stderr.strip()})")
except FileNotFoundError:
    print("  ℹ️  skills-ref not in PATH — skipping spec validation (install: pip install skills-ref)")

# Results
print(f"\n{'='*60}")
if failures:
    print(f"  RESULT: FAILED ({len(failures)} issue(s))")
    for f in failures:
        print(f"    • {f}")
    print(f"{'='*60}\n")
    sys.exit(1)
else:
    print(f"  RESULT: PASSED")
    print(f"{'='*60}\n")
    sys.exit(0)
```

---

## 7. Trigger Eval Queries (for description validation)

Store in `scripts/eval_queries.json`. Minimum 10 entries (5 should-trigger, 5 should-not):

```json
[
  { "query": "<realistic user prompt that should use this skill>", "should_trigger": true },
  { "query": "<realistic prompt that should NOT use this skill>", "should_trigger": false }
]
```

Guidelines:
- Should-trigger: vary phrasing, explicitness, length; include cases where the domain isn't named explicitly
- Should-not-trigger: use near-miss queries that share keywords but need something different
- Include real context (file paths, names, specifics) to mirror actual user prompts

---

## 8. New Skill Checklist

Before declaring a new skill complete, verify all of the following:

- [ ] Directory name matches `name` in frontmatter (lowercase, hyphens, max 64 chars)
- [ ] `description` field ≤ 1024 chars, imperative, starts with "Use this skill when"
- [ ] `SKILL.md` body ≤ 500 lines
- [ ] `scripts/validate-skill.py` exists and exits 0 when run
- [ ] At least one functional script (`.py` or `.sh`) exists in `scripts/`
- [ ] All scripts are idempotent and exit 0/1 only
- [ ] Destructive operations support `--dry-run`
- [ ] All `scripts/` dependencies declared in each file's header comment
- [ ] `scripts/eval_queries.json` contains ≥ 10 entries (≥5 should-trigger, ≥5 should-not)
- [ ] `skills-ref validate .github/skills/<skill-name>` exits 0
- [ ] Gotchas section present if any non-obvious constraints exist

Run the full checklist via: `python .github/skills/<skill-name>/scripts/validate-skill.py`
