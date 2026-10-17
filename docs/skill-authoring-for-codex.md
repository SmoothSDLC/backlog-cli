# Skill authoring in smooth-backlog-cli

The original `.agent/skills.instructions.md` and
`docs/agent-skills-specification-guidance.md` were copied without changes from
`corp_smoothsdlc_ai_coding_model` at commit
`bbd807863a77a8f3a5cb37f6cd42309b6132810d`.

Read them before building project skills. Apply these explicit adaptations:

| Source convention | smooth-backlog-cli convention |
| --- | --- |
| `.github/skills/<name>`, `.agent/skills/<name>`, `.claude/skills/<name>` | `.agents/skills/<name>` for Codex |
| `license: Proprietary` | `license: Apache-2.0` for original SmoothSDLC project skills |
| `.claude/skills/skill-creator/scripts/skill-lint.py` | `scripts/skills/skill-lint.py` |
| `.claude/skills/skill-creator/scripts/skill-audit.py` | `scripts/skills/skill-audit.py` |
| `skill-creator/references/spec-claim-coverage.md` | `docs/skill-spec-claim-coverage.md` |
| Validator `--portable` discovery | Pass each project skill directory explicitly |

For example, after the future backlog skill exists:

```bash
.codex/tools/skill-python/bin/python scripts/skills/skill-lint.py .agents/skills/backlog
.codex/tools/skill-python/bin/python scripts/skills/skill-audit.py .agents/skills/backlog
export PATH="$PWD/.codex/tools/skill-python/bin:$PATH"
python .agents/skills/backlog/scripts/validate-skill.py
```

The linter and auditor require PyYAML. The cloud setup installs a pinned copy.
Both scripts are copied unchanged and retain their original usage behavior:
`--portable` scans the source repository's directory conventions and does not
discover `.agents/skills`. Passing explicit directories avoids a false claim
that a new skill was checked. Require zero linter ERRORs and zero auditor FAILs;
also inspect REVIEW findings. The per-skill self-check is an additional gate.

The 15 Superpowers and six Ponytail skills are imported development tools,
with byte-for-byte skill copies recorded in `.agent/third_party/*/source.json`.
They retain their MIT licenses and upstream conventions. Their installation
does not certify conformance to SmoothSDLC's stricter authoring standards.
When modifying one or creating a new project skill, apply the standards and
record the modification and validation results. Never relabel upstream content
as solely owned by SmoothSDLC.

No backlog product skills are created during this environment setup.
