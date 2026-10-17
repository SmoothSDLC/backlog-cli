# Codex cloud setup

## Environment setup

Select this repository in the Codex cloud environment and set the setup script to:

```bash
python3 scripts/setup-codex-cloud.py
```

Use the same command as the maintenance script so a cached container installs
the versions pinned by the branch it checks out. Reset the environment cache
when changing tool versions. Setup and maintenance run from the repository root.
This checkout must be committed and pushed before a cloud environment can use it.

Requirements: Linux x86_64 or aarch64, Python 3.11+ with venv/pip, Bash, Git,
and HTTPS access to GitHub releases (including release asset redirects) and
PyPI. No credentials are needed for these public downloads.

Setup installs codebase-memory-mcp 0.11.0 from its official portable release
archive, verifying a SHA-256 value pinned in `.codex/tool-versions.json` before
extracting the executable and license notices. Archives, executables, and the
Python virtual environment stay in ignored `.codex/tools/`. Setup can run again
without replacing a matching runtime. A changed existing file or checksum
mismatch fails explicitly; retain it for inspection and move it aside before
retrying. Inspect the plan with `--dry-run`.

The Python environment contains the pinned dependencies in
`.codex/skill-requirements.txt`. Nothing is added to the user's Codex/Claude
configuration or shell startup files. Agent-phase network access is unnecessary
for the installed skills or local code graph.

## Skills

Codex discovers the 21 checked-in skills in `.agents/skills/`. The files and
supporting references were copied from BIGFAN's installed Claude plugins:

| Package | Version | Provenance |
| --- | --- | --- |
| Superpowers | 6.4.2 | `.agent/third_party/superpowers/source.json` |
| Ponytail | 5.2.0 | `.agent/third_party/ponytail/source.json` |

The source manifests record original locations for provenance only. No runtime
file depends on `/home/smooth` or `~/.claude`. The manifests contain SHA-256
digests for every skill file. Keep these updated when deliberately refreshing
a vendor copy. Copied skills retain their upstream wording and MIT terms.

`AGENTS.md` loads the Superpowers bootstrap and Ponytail's full-mode instructions
at session start. Skills can also be invoked as `$brainstorming`, `$ponytail`,
or `$ponytail-review`. Claude lifecycle hooks, statusline installation, and
home-directory mode files are not part of this skill installation. Ponytail's
published benchmark references are preserved under `.agent/third_party/ponytail/`.
Skills become available to a new Codex session/turn after the repo is loaded.

## Codebase memory

`.codex/config.toml` defines the local stdio MCP server for Codex clients that
load trusted project configuration. The launcher resolves the checkout from Git,
so it works from nested working directories. Project configuration alone does
not guarantee that a particular hosted cloud harness exposes stdio MCP tools.

Every cloud session can use the same tools through the CLI launcher:

```bash
scripts/codebase-memory.sh --version
scripts/codebase-memory.sh cli index_repository --repo-path "$PWD" --name smooth-backlog-cli
scripts/codebase-memory.sh cli list_projects
# Use the project name returned by list_projects in subsequent graph queries.
scripts/codebase-memory.sh cli get_architecture --project smooth-backlog-cli
scripts/codebase-memory.sh cli search_graph --project smooth-backlog-cli --query init
```

Use `search_graph` for symbols, `trace_path` for relationships,
`get_code_snippet` for source, `query_graph` for multi-hop questions, and
`get_architecture` for the overview. Use `rg` for literals and coverage gaps.
Index again after edits in CLI mode: it does not run the MCP daemon's automatic
watcher. The graph becomes more useful after the CLI source is implemented.

CBM stores its normal indexes in the environment user's cache; its generated
`.codebase-memory/` repository artifacts are ignored. It coordinates all active
processes for an account and requires matching executable builds. On a shared
server with an existing CBM installation, use that installation if the pinned
release reports a build conflict; do not stop other sessions to force it.
Cloud containers get their own downloaded runtime.

## Authoring project skills

Read [the Codex adaptation](skill-authoring-for-codex.md), the copied instruction
file, and the specification guidance before creating product skills. Use the
installed Python environment for the corporate validators:

```bash
.codex/tools/skill-python/bin/python scripts/skills/skill-lint.py .agents/skills/<new-skill>
.codex/tools/skill-python/bin/python scripts/skills/skill-audit.py .agents/skills/<new-skill>
export PATH="$PWD/.codex/tools/skill-python/bin:$PATH"
python .agents/skills/<new-skill>/scripts/validate-skill.py
```

Pass project skill directories explicitly. The copied validators' `--portable`
mode uses the source repository's layout. Setup provides a `skills-ref` alias
for the package's `agentskills` command, preserving the copied guidance's
validation commands. No product skill exists yet.

## Sources

- [Official Codex skill discovery](https://learn.chatgpt.com/docs/build-skills)
- [Official project MCP configuration](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)
- [Official cloud setup and maintenance scripts](https://learn.chatgpt.com/docs/environments/cloud-environment)
- [Superpowers](https://github.com/obra/superpowers)
- [Ponytail](https://github.com/DietrichGebert/ponytail)
- [codebase-memory-mcp 0.11.0](https://github.com/DeusData/codebase-memory-mcp/releases/tag/v0.11.0)
