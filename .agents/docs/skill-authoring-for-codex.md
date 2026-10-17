# Maintaining the product agent integration

The public skill is under `templates/skills/backlog/`. Its instructions, snapshot
helper, validation script, and evaluation fixtures ship with the npm package and
are installed by `backlog init`. Keep them independent of development-only tools.

Use `license: Apache-2.0` for project-authored skills. Keep the skill description
specific, preserve working relative links, and use scripts for deterministic work.
The authoring standards and validation coverage in this directory describe the
current product integration and supported maintenance commands.

Validate from the repository root:

```sh
python3 templates/skills/backlog/scripts/validate-skill.py
npm test
npm run check
npm pack --dry-run
```

The bundled validator uses Python's standard library. If `skills-ref` is installed,
it also runs reference validation. Product integration tests exercise the installed
snapshot helper and all four supported agent destinations.
