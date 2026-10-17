> Historical authoring reference. Current repository validation commands are
> documented in `skill-authoring-for-codex.md`; external tool paths below are
> examples from the source guidance, not an installed repository toolchain.

# Spec claim → audit-rule coverage map

Load this when you need to confirm that `scripts/skill-audit.py` tests a given
claim from the Agent Skills documentation, or when adding a new rule. Every
normative claim on the three authoritative pages is listed here and mapped to
the rule that tests it. Claims that are pure *process* guidance (things you do
while authoring, not properties of a finished skill on disk) cannot be checked
by a static auditor; those are marked **process — not statically auditable**
with a one-line rationale rather than a silent omission.

Authoritative sources (treated as canonical, each claim = a testable assertion):
- Specification — https://agentskills.io/specification
- Using scripts in skills — https://agentskills.io/skill-creation/using-scripts
- Best practices for skill creators — https://agentskills.io/skill-creation/best-practices
- (supporting) Evaluating skill output quality, Optimizing skill descriptions

---

## 1. Specification — https://agentskills.io/specification

| # | Claim (quoted/paraphrased) | Rule |
|---|---|---|
| 1 | A skill is a directory containing, at minimum, a `SKILL.md` file | `SPEC-01` |
| 2 | `scripts/` holds executable code; `references/` docs; `assets/` resources — only `SKILL.md` (+ optional bundled LICENSE) belongs at the root | `SPEC-31` |
| 3 | `SKILL.md` must contain YAML frontmatter | `SPEC-02`, `SPEC-03` |
| 4 | …followed by Markdown body content | `SPEC-25` |
| 5 | `name` required | `SPEC-04` |
| 6 | `name` is a string | `SPEC-05` |
| 7 | `name` 1–64 characters | `SPEC-06` |
| 8 | `name` lowercase letters, numbers, hyphens only | `SPEC-07` |
| 9 | `name` must not start with a hyphen | `SPEC-08` |
| 10 | `name` must not end with a hyphen | `SPEC-09` |
| 11 | `name` must not contain consecutive hyphens (`--`) | `SPEC-10` |
| 12 | `name` must match the parent directory name | `SPEC-11` |
| 13 | `description` required | `SPEC-12` |
| 14 | `description` is a string | `SPEC-13` |
| 15 | `description` non-empty | `SPEC-14` |
| 16 | `description` max 1024 characters | `SPEC-15` |
| 17 | `description` describes what the skill does **and** when to use it | `SPEC-16` |
| 18 | `description` should include specific keywords | `SPEC-32` |
| 19 | `license` optional, string | `SPEC-18` |
| 20 | `license` recommended to be short | `SPEC-34` |
| 21 | `compatibility` optional, string | `SPEC-19` |
| 22 | `compatibility` max 500 characters | `SPEC-20` |
| 23 | `compatibility` only if the skill has specific env requirements | `SPEC-19`/`SPEC-20` (presence+length); applicability is **judge — not mechanically decidable**, surfaced via REVIEW when present |
| 24 | `metadata` optional, a mapping | `SPEC-21` |
| 25 | `metadata` keys are strings | `SPEC-22` |
| 26 | `metadata` values are strings | `SPEC-23` |
| 27 | `metadata` keys should be reasonably unique | **process — not statically auditable** (uniqueness is across clients, not within one file) |
| 28 | `allowed-tools` optional, a string | `SPEC-24` |
| 29 | `allowed-tools` is space-separated | `SPEC-33` |
| 30 | Body has no format restrictions; recommended sections: steps, examples, edge cases | `BP-02` (workflow/steps), `SPEC-35` (examples) |
| 31 | Consider splitting long `SKILL.md` into referenced files | `SPEC-26`, `SPEC-27` |
| 32 | `scripts/` scripts self-contained or clearly document dependencies | `SCR-05`, `SCR-06` |
| 33 | scripts include helpful error messages | `SCR-15` |
| 34 | scripts handle edge cases gracefully | `SCR-15`/`SCR-10` (defensive paths); depth is **judge** via REVIEW |
| 35 | `references/` files kept focused/small, loaded on demand | `SPEC-29`, `BP-06` |
| 36 | Progressive disclosure: metadata ~100 tok / instructions <5000 tok / resources on demand | `SPEC-27` |
| 37 | Keep `SKILL.md` under 500 lines | `SPEC-26` |
| 38 | File references use relative paths from the skill root (no absolute) | `SPEC-28` |
| 39 | Keep file references one level deep | `SPEC-29` |
| 40 | Referenced files must exist (house extension of "file references") | `SPEC-30` |

## 2. Using scripts in skills — https://agentskills.io/skill-creation/using-scripts

| # | Claim | Rule |
|---|---|---|
| 1 | Pin versions of one-off commands (`npx eslint@9.0.0`) | `SCR-13` |
| 2 | State prerequisites in `SKILL.md` / use `compatibility` | `SCR-05` (script header), `SPEC-19` (compatibility) |
| 3 | Move complex commands into `scripts/` | **process — authoring judgment**; thin/over-inline detection via `SCR-04` |
| 4 | Reference scripts with relative paths from the skill root | `SPEC-28` |
| 5 | List available scripts in `SKILL.md` | `BP-07` |
| 6 | Self-contained scripts declare dependencies inline (PEP 723 etc.) | `SCR-06` |
| 7 | Pin dependency versions inside the inline metadata | `SCR-06` (block present) + `SCR-13` (pinning); exact PEP 508 pinning is **judge** |
| 8 | **Avoid interactive prompts** (hard requirement) | `SCR-10` |
| 9 | Document usage with `--help` | `SCR-07` |
| 10 | Write helpful error messages | `SCR-15` |
| 11 | Use structured output (JSON/CSV/TSV) | `SCR-09` |
| 12 | Separate data (stdout) from diagnostics (stderr) | `SCR-16` |
| 13 | Idempotency — retries are safe | `SCR-12` |
| 14 | Input constraints — reject ambiguous input with a clear error | `SCR-15` (error path) + `SCR-10` (no silent prompt) |
| 15 | Dry-run support for destructive/stateful ops | `SCR-11` |
| 16 | Meaningful exit codes, documented in `--help` | `SCR-08` |
| 17 | Safe defaults — destructive ops require `--confirm`/`--force` | `SCR-17` |
| 18 | Predictable output size — paginate/limit/`--output` large output | `SCR-18` |
| 19 | Functional script language is runnable (py/sh here) | `SCR-03` |

## 3. Best practices — https://agentskills.io/skill-creation/best-practices

| # | Claim | Rule |
|---|---|---|
| 1 | Start from real expertise / don't generate generic skills | **process — authoring method**, not a property of the file |
| 2 | Synthesize from existing project artifacts | **process — authoring method** |
| 3 | Refine with real execution (execute-then-revise) | **process**; supported by `evals/` (`EVAL-08…13`) |
| 4 | Add what the agent lacks, omit what it knows (no bloat) | `SPEC-26`/`SPEC-27` (size); generic filler via `BP-04` |
| 5 | Design coherent units (right scope) | **judge — authoring decision**; not mechanically decidable |
| 6 | Aim for moderate detail | `SPEC-26`, `SPEC-27` |
| 7 | Structure large skills with progressive disclosure | `SPEC-26`, `SPEC-27`, `BP-06` |
| 8 | Tell the agent *when* to load each reference file | `BP-06` |
| 9 | Match specificity to fragility | **judge — authoring decision** |
| 10 | Provide defaults, not equal-weight option menus | `BP-05` |
| 11 | Favor procedures over one-off declarations | **judge**; partly surfaced by `BP-02` (has a procedure/workflow) |
| 12 | Gotchas section of concrete, environment-specific facts | `BP-03` (present) |
| 13 | Gotchas are concrete, not generic advice | `BP-04` |
| 14 | Keep gotchas in `SKILL.md` | `BP-03` |
| 15 | Templates for output format (inline if short, `assets/` if long) | `SPEC-35` (example/template block); placement is **judge** |
| 16 | Checklists for multi-step workflows | `BP-02` (workflow/steps); optional pattern |
| 17 | Validation loops (do → validate → fix → repeat) | optional pattern; analyzers enforced by `AN-01…08` |
| 18 | Plan-validate-execute for batch/destructive ops | optional pattern; destructive guard via `SCR-17` |
| 19 | Bundle reusable scripts when logic is reinvented | `BP-07`, `SCR-02` |
| 20 | Has a clear purpose | `BP-01` |

## 4. Supporting guides (already enforced)

- **Optimizing descriptions** → `DESC-01…06`, `EVAL-01…07`
- **Evaluating skill output quality** → `EVAL-08…13`
- **House rules** (repo) → `SCR-01`, `SCR-14`, `HOUSE-01…04`, `AN-01…08`

---

## Maintenance

When agentskills.io changes, re-fetch the three pages, diff their claims against
this table, and add a rule (or a documented rationale) for any new claim. A claim
must never be dropped silently — every row maps to a rule id or carries a
**process / judge — not statically auditable** rationale.
