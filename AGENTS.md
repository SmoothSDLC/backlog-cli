# backlog-cli

backlog-cli is an npm CLI project by SmoothSDLC Systems Inc
(https://SmoothSDLC.com), licensed under Apache-2.0. Read `initial-prompt.md`
for the product requirements before implementation. Environment setup does not
authorize implementing the CLI or generating its product skills.

## Installed development skills

At the beginning of a session, read
`.agents/skills/using-superpowers/SKILL.md` and
`.agents/skills/using-superpowers/references/codex-tools.md`, then use the
relevant Superpowers skills. Read `.agents/skills/ponytail/SKILL.md` and apply
its default full mode to coding work unless the user requests another mode.
All 21 skills live directly in `.agents/skills/` for Codex discovery. Read their
supporting files from the same skill directory.

In Codex, invoke skills with `$<name>` or read the named `SKILL.md` when the
harness has no skill invocation tool. A `superpowers:<name>` reference resolves
to `.agents/skills/<name>/SKILL.md`; a `ponytail:<name>` reference resolves the
same way. These are repository skills, so no plugin namespace is required.

Honor the actual tools, available models, and higher-priority instructions in
the current session. Do not enable features, install user-level plugins, or
trust lifecycle hooks merely because an upstream skill describes that workflow.
The repository installs skills without Claude hooks or home-directory state.
Ponytail's plugin statusline, automatic mode persistence, and lifecycle hooks
are outside this installation; session instructions provide its default mode.
Its benchmark references are in `third_party/ponytail/benchmarks/results/`.

## Code navigation

Use codebase-memory-mcp for graph-based navigation when available:
`index_repository`, `search_graph`, `trace_path`, `get_code_snippet`,
`query_graph`, and `get_architecture`. Use `list_projects` to find the project
name rather than assuming it. Use `rg` for literals or missing graph coverage.
Index this checkout by passing its absolute path as `repo_path`.

The repository includes a Codex MCP configuration and a CLI launcher for cloud
hosts that do not expose local stdio MCP servers. See `docs/codex-cloud-setup.md`
for setup and CLI examples. If setup is incomplete, report the problem and use
ordinary file navigation until the runtime is available.

## Creating or changing project skills

Before authoring a skill, read all three:

1. `.agent/skills.instructions.md`
2. `docs/agent-skills-specification-guidance.md`
3. `docs/skill-authoring-for-codex.md`

The third file maps the copied guidance to this repository's Codex paths,
license, and validators. New project skills belong in `.agents/skills/` and
use `license: Apache-2.0`. Keep imported third-party skills and their MIT
licenses intact; record deliberate vendor updates in their source manifests.
Apply the authoring standards to project-authored skills, including any edits
made to imported skills. Do not claim the imported skills already pass the
stricter corporate authoring gates.
