# Package development

Use Node.js 24+, npm, Git, and Python 3.8+ for the bundled skill helper tests.
No development framework or code-indexing service is required.

From the repository root:

```sh
npm ci --ignore-scripts
npm test
npm run check
npm pack --dry-run
```

The CLI sources are under `src/`, its executable is `bin/backlog.js`, and its
public integration templates are under `templates/`. Tests are in `.agents/test/`;
the release verifier is `.agents/scripts/verify-published-package.mjs`. Development-only documents
are kept in `.agents/docs/`; public usage documentation stays at the root.

GitHub Actions validates the supported operating systems and Node.js versions
before publishing tagged releases. The first-party release verifier downloads
published packages and exercises the installed CLI independently of source code.

CI runs on branch pushes except `master`, and on pull requests except those targeting
`master`. Tag pushes do not start a separate CI run. Publishing starts only on a
push to `main`, after the pull request is merged, and reruns the reusable CI gate.
Release workflows run one at a time with `queue: max`, so new pushes do not replace
pending releases. GitHub allows up to 100 pending runs in this queue; additional
runs are canceled when that limit is reached.

Release PRs bump package.json and package-lock.json together. The main workflow
publishes that exact stable version, verifies registry installations and upgrades,
then creates and pushes its annotated version tag at the validated main commit.
Already-released versions from earlier commits are skipped for documentation-only
merges. Reruns never overwrite npm versions or move existing tags; they can resume
verification and tagging of an identical artifact after partial release failure.
Registry authentication or network failures stop publication rather than being
treated as a version that does not exist.
