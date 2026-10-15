# Agent Skills — Specification & Best-Practices Knowledge Base

Authoritative reference for **creating, structuring, scripting, evaluating, and
validating skills** in this repository. Distilled from the complete
[agentskills.io](https://agentskills.io) documentation set:

- [Specification](https://agentskills.io/specification)
- [Best practices for skill creators](https://agentskills.io/skill-creation/best-practices)
- [Using scripts in skills](https://agentskills.io/skill-creation/using-scripts)
- [Evaluating skill output quality](https://agentskills.io/skill-creation/evaluating-skills)
- [Optimizing skill descriptions](https://agentskills.io/skill-creation/optimizing-descriptions)

…reconciled with this repo's `.agent/skills.instructions.md`. Where the two
differ, the conflict is called out explicitly (see §9).

> **No exemptions.** Every skill in this repository — newly authored or
> pre-existing, in `.agent/skills/`, `.claude/skills/`, `.github/skills/`, or the
> `portable/` bundle — MUST conform to this standard in full. There are no
> grandfathered or exempt skills. A skill that cannot meet a requirement must be
> brought into compliance, not excepted.

> **The single most important rule, stated up front:** *Scripts do the
> deterministic work; `SKILL.md` carries only what the agent wouldn't already
> know.* A skill whose script merely keyword-matches while the markdown does all
> the reasoning is an anti-pattern. If the same deterministic logic would be
> re-derived on every run, **bundle a tested script for it.**

---

## 1. Directory structure

```
skill-name/
├── SKILL.md          # Required: frontmatter + lean instructions
├── scripts/          # Executable code that does the real work
├── references/       # Detailed docs, loaded on demand
├── assets/           # Templates, schemas, rubric data
└── evals/            # Output-quality evals (evals.json + files/)
```

Spec minimum is just `SKILL.md`. **House rules require** `scripts/validate-skill.py`,
≥1 functional script, and `scripts/eval_queries.json`. **Best practice adds**
`evals/evals.json` for output-quality testing. Directory name **MUST** equal `name`.

---

## 2. Frontmatter (spec)

| Field | Required | Constraint |
|-------|----------|-----------|
| `name` | Yes | 1–64 chars; lowercase `a-z`,`0-9`,`-`; no leading/trailing hyphen; **no `--`**; matches directory |
| `description` | Yes | 1–1024 chars; **what it does AND when to use it**; imperative; keyword-rich (see §7) |
| `license` | No | Name or bundled-file reference; `Proprietary` here |
| `compatibility` | No | ≤500 chars; only if environment-specific (product/packages/network) |
| `metadata` | No | Map of **string→string**; quote `version: "1.0"` |
| `allowed-tools` | No | Space-separated pre-approved tools (experimental) |

---

## 3. Body & progressive disclosure

Three load tiers: **metadata** (`name`+`description`, ~100 tok, all skills at startup)
→ **instructions** (full `SKILL.md`, **≤500 lines / <5000 tok**, on activation) →
**resources** (`scripts/`,`references/`,`assets/`, on demand).

- **Add what the agent lacks; omit what it knows.** Don't explain what a PDF is.
  Ask of every line: *"Would the agent get this wrong without it?"* If no, cut it.
- **Aim for moderate detail.** Concise stepwise guidance + one working example beats
  exhaustive documentation. Over-comprehensive skills make the agent chase
  irrelevant instructions.
- **Design coherent units** — one composable unit of work (like a function), not too
  narrow (forces many loads) or too broad (won't activate precisely).
- **Progressive disclosure:** move depth to `references/<topic>.md` and say *when* to
  load it ("Read `references/api-errors.md` if the API returns non-200"), never a bare
  "see references/".

---

## 4. Calibrating control (match specificity to fragility)

- **Give freedom** when many approaches work — explain *why*, not rigid steps.
- **Be prescriptive** when operations are fragile/order-dependent ("Run exactly this
  sequence … do not add flags").
- **Provide defaults, not menus.** Pick one tool; mention alternatives as a guarded
  escape hatch ("for scanned PDFs, use X instead"). Never "use X or Y or Z" equally.
- **Favor procedures over declarations** — teach *how to approach the class of problem*
  (reusable), not the answer to one instance.

---

## 5. Patterns for effective instructions

- **Gotchas** — the highest-value content: concrete, environment-specific facts that
  defy reasonable assumptions ("`users` uses soft deletes; add `WHERE deleted_at IS
  NULL`"). Not general advice. Keep in `SKILL.md`. *Add a gotcha every time you correct
  the agent.*
- **Templates** for required output formats (inline if short; `assets/` if long).
- **Checklists** for multi-step workflows, each step naming the script it runs.
- **Validation loops** — do work → run validator → fix → repeat until it passes.
- **Plan→Validate→Execute** for batch/destructive ops: emit a structured plan, validate
  it against a source of truth with a script, then execute. The validator's specific
  errors ("Field 'x' not found — available: a,b,c") are what let the agent self-correct.
- **Bundle reusable scripts** — if traces show the agent re-deriving the same logic each
  run, write it once and bundle it.

---

## 6. Using scripts (this is where the work lives)

### When to script vs instruct
- **One-off command** (existing tool, few flags): reference it inline with a **pinned
  version** via `uvx ruff@0.8.0` / `npx eslint@9` / `pipx run`. State prerequisites.
- **Bundle a script** when logic is complex, repeated, fragile, or must be deterministic.
  Move "complex enough to be hard to get right first try" commands into `scripts/`.

### Self-contained scripts (preferred)
Declare deps inline so one command runs it with no install step. **Python: PEP 723**:

```python
# /// script
# requires-python = ">=3.9"
# dependencies = ["beautifulsoup4>=4.12,<5"]
# ///
```
Run with `uv run scripts/extract.py`. (Repo scripts that need no deps stay pure-stdlib.)

### Design scripts for agentic use (hard requirements)
- **No interactive prompts** — agents run non-interactive shells; blocking input hangs
  forever. Take input via flags / env / stdin; on missing input, error with usage.
- **`--help`** documenting description, flags, examples, and **exit-code meanings** — this
  is how the agent learns the interface. Keep it concise.
- **Structured output**: JSON/CSV/TSV to **stdout**; progress/warnings/diagnostics to
  **stderr** (separate data from diagnostics so the agent can parse cleanly).
- **Helpful errors**: say what went wrong, what was expected, what to try.
- **Meaningful, documented exit codes** for distinct failure classes (not-found, bad-args,
  auth) — agents branch on them.
- **Idempotency** ("create if not exists"), **`--dry-run`** for stateful ops, **safe
  defaults** (`--confirm`/`--force` for destructive), **predictable output size**
  (summarize/limit; support `--offset` or `--output` for large output).

---

## 7. Optimizing descriptions (triggering)

The `description` carries the entire triggering burden (only `name`+`description` load
at startup). Agents typically consult a skill only for tasks beyond what they handle
alone.

- **Imperative**: "Use this skill when…" not "This skill does…".
- **User intent, not mechanics.** Match what the user asked for.
- **Be pushy**: list contexts including ones where the domain isn't named ("even if they
  don't mention 'CSV' or 'analysis'").
- **Concise**, ≤1024 chars (descriptions grow during optimization — recheck).

**Test triggering with `scripts/eval_queries.json`** — ~20 queries, 8–10 should-trigger,
8–10 should-not. Should-trigger: vary phrasing/explicitness/detail/complexity; best ones
are where the skill helps but the link isn't obvious. Should-not: **near-misses** sharing
keywords but needing something else (a Postgres-ETL prompt for a CSV-analysis skill).
Use realistic paths/names/typos. Run each query ≥3× → **trigger rate**; pass if >0.5
(should-trigger) / <0.5 (should-not). Use a **60/40 train/validation split** to avoid
overfitting; don't paste failed-query keywords in (that's overfitting) — generalize the
category. ~5 iterations; pick the iteration with the best *validation* pass rate.

---

## 8. Evaluating output quality (`evals/evals.json`)

Separate from trigger testing — this checks whether the skill produces **good outputs**.

A test case = **prompt** (realistic) + **expected_output** (prose) + optional **files** +
**assertions** (objective, verifiable statements). Run each case **with vs without** the
skill for a baseline.

```json
{ "skill_name": "<name>", "evals": [
  { "id": 1, "prompt": "<realistic user message>",
    "expected_output": "<what success looks like>",
    "files": ["evals/files/..."],
    "assertions": ["The output is valid JSON", "Lists every missing control with a remediation"] } ]}
```

- **Good assertions**: programmatically verifiable / specific / countable. **Weak**: "is
  good" (vague) or exact-phrase (brittle).
- **Grade** each assertion PASS/FAIL **with evidence** quoting the output; require concrete
  evidence for PASS. Prefer **code-based checks** for mechanical assertions; LLM-judge for
  semantic ones.
- **Iterate**: failed assertions → gaps; transcripts → *why*; feed all signals + current
  `SKILL.md` to an LLM for proposed changes. Keep it lean; explain the why; **bundle
  repeated work into scripts**. Stop when feedback is consistently empty.
- `skill-creator` automates much of this loop.

---

## 8a. Authoritative validation: skill-creator's bundled validators

The per-skill `scripts/validate-skill.py` is a lightweight self-check and is **not**
sufficient on its own — a regex that only finds a `name:` line will pass a skill whose
frontmatter is invalid YAML (this happened and shipped). The **authoritative** validators
ship inside the **skill-creator** skill (so they travel with the bundle): the strict linter
`scripts/skill-lint.py` (zero ERRORs) and the exhaustive auditor `scripts/skill-audit.py`
(one rule per agentskills.io spec claim; zero FAILs). The auditor's full claim→rule map is
in `.claude/skills/skill-creator/references/spec-claim-coverage.md`.

```bash
python3 .claude/skills/skill-creator/scripts/skill-lint.py --portable           # whole bundle
python3 .claude/skills/skill-creator/scripts/skill-audit.py .agent/skills/<name> # one skill
```

It **parses frontmatter as real YAML** and asserts the actual properties (not proxies),
including: valid YAML mapping; only the spec-allowed top-level keys; `name` charset/length and
directory match; `description` length, trigger phrase, **no duplicated text**, and (best
practice) an exclusion clause; `metadata` values are strings; SKILL.md ≤ 500 lines; Gotchas
present; every referenced `references/`/`scripts/`/`assets/` file exists; `eval_queries.json`
is valid JSON with **≥10 should-trigger / ≥8 should-not-trigger and no duplicates**;
`evals/evals.json` cases carry prompt + expected_output + assertions; and for analyzer skills,
the rubric controls/anti-patterns are well-formed and `analyze.py` actually exits 0 on the
good fixture and 1 on the weak fixture. **Detection only — it never edits skills; fixes are
made by hand, per file.**

---

## 9. Reconciliation with house rules (`.agent/skills.instructions.md`)

House rules are mostly a **superset** (they add `validate-skill.py`, eval-query counts,
convergence). Two tensions to resolve in favor of the spec's richer guidance:

1. **Exit codes.** House rule says "exit 0/1 only." The spec/best-practice says use
   **distinct, documented exit codes** for failure classes. **Resolution:** keep `0`=clean
   / `1`=findings as the gate/convergence contract, but a script MAY use additional codes
   (e.g. `2`=usage error) **as long as `--help` documents them**. Put detailed findings in
   structured stdout, not the exit code.
2. **Script substance.** House rule requires "≥1 functional script"; the spec demands that
   script **do the deterministic work**. A keyword-presence stub does not satisfy the
   intent — the functional script must perform real analysis/transformation/validation and
   emit structured, actionable output.

---

## 10. Compliance checklist

**Structure & frontmatter**
- [ ] dir name == `name`; lowercase/hyphen; ≤64; no `--`; no edge hyphen
- [ ] `description` 1–1024, imperative, what+when, keyword-rich, "even if not named"
- [ ] `metadata` values all strings; `compatibility` ≤500 (only if needed)
- [ ] `SKILL.md` ≤500 lines / <5000 tok; depth in `references/` with load-when cues

**Scripts (the work)**
- [ ] Functional script does **real deterministic work**, not keyword presence
- [ ] `--help` with flags, examples, **exit-code meanings**
- [ ] Structured output to stdout; diagnostics to stderr; helpful error messages
- [ ] Idempotent; `--dry-run` for stateful ops; pinned deps (PEP 723 / `tool@version`)
- [ ] `scripts/validate-skill.py` present and exits 0

**Evals**
- [ ] `scripts/eval_queries.json` ≥10 (≥5 trigger / ≥5 non-trigger, incl. near-misses)
- [ ] `evals/evals.json` with prompt + expected_output + objective assertions
- [ ] `skills-ref validate <skill>` exits 0 (when available)

**Body**
- [ ] Lists available scripts; workflow names the script per step
- [ ] Gotchas section (concrete, non-obvious) present where applicable
- [ ] Defaults not menus; procedures not one-off answers

---

## 11. Sources

agentskills.io: /specification · /skill-creation/best-practices · /using-scripts ·
/evaluating-skills · /optimizing-descriptions · /llms.txt (index).
Validator: `skills-ref validate ./skill`. Repo: `.agent/skills.instructions.md`.
