# Product skill validation coverage

The repository validates its product skill using the bundled first-party
validator and tests under `.agents/test/`. It does not depend on a vendored
linter, auditor, or agent development framework.

| Check | Current validation |
| --- | --- |
| Frontmatter block and matching directory name | Bundled validator |
| SKILL.md below 500 lines | Bundled validator |
| Referenced skill resources exist | Bundled validator |
| Bundled Python files parse | Bundled validator using Python AST parsing |
| Snapshot helper exists | Bundled validator |
| At least 10 positive and 8 negative trigger fixtures, with unique queries | Bundled validator |
| Output fixtures contain prompts, expected outputs, and assertions | Bundled validator |
| Full Agent Skills reference validation | Optional `skills-ref` invocation when installed |
| All four installed agent integrations and snapshot behavior | `.agents/test/integrations.test.js` |
| Public documentation and integration resources are included in the npm artifact | `.agents/test/package.test.js` |
| Development-only files are excluded from the npm artifact | `.agents/test/package.test.js` |

The built-in frontmatter checks do not replace a complete YAML/specification
parser. Fixture checks validate structure; they do not measure model activation
or response quality. Review instruction quality and real trigger behavior when
changing the product skill.

Run the documented commands in `skill-authoring-for-codex.md` from the repository
root. The installed skill's resource paths resolve relative to its own directory.
