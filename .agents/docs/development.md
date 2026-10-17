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
