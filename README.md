# backlog-cli

A Git-aware, branch-specific backlog for people and coding agents by
[SmoothSDLC Systems Inc](https://SmoothSDLC.com), licensed under [Apache 2.0](LICENSE).

Requires **Node.js 24+**, npm, and Git. Supports Linux, macOS, and Windows.
The npm package is **`@smoothsdlc/smooth-backlog-cli`**; its command is **`backlog`**.

## Install and use

Install **1.0.1** directly from this public repository's release asset. No GitHub
login or package-registry token is required:

```sh
npm install --global https://github.com/SmoothSDLC/backlog-cli/releases/download/v1.0.1/smoothsdlc-smooth-backlog-cli-1.0.1.tgz
backlog --version
```

The release asset is the exact tarball downloaded from GitHub Packages after
publication, with its SHA-512 integrity verified. See the
[latest release](https://github.com/SmoothSDLC/backlog-cli/releases/latest) for
downloads and release notes.

From a Git working tree:

```sh
backlog init
backlog new "Fix login" --description "Expired cookies prevent sign-in" --ac "An expired cookie permits a fresh sign-in"
backlog 0 add tasks "Reproduce,Failing test captures the regression"
backlog list
backlog 0 done
backlog list done --json
```

A numeric selector means the current active priority, starting at 0. Every item
also has a permanent GUID for durable references, including completed work.
Task/list-entry positions start at 1. Both `backlog set 0 ...` and
`backlog 0 set ...` work. States are `new`, `open`, `done`, and `archived`.

`init` installs backlog skills into detected `.agents`, `.claude`, `.github`, and
`.qwen` vendor folders. It always creates the base skill under `.backlog/skills`.
Data and skills are intended for Git; initialization reminds you to commit.
Repeated init requires `init backup` to retain data or **`init clean` to erase the
entire backlog, including every branch and contained backups**. Generated skill
edits are replaceable; preserve them through Git.

Read the [full command reference](docs/commands.md) for list operations, priorities,
branch isolation/transfers, archive ordering, interactive input, JSON output,
transaction recovery, and update policies. `--force` is only a whole-list `set`
replacement option. Archive and init do not accept it.

Weekly update notices default on; automatic installs default off. Use
`backlog update auto` for daily compatible updates, `backlog update off` to stop
auto installs, and `backlog update disable` to disable weekly notices. Settings
are user-scoped. Automatic updates require a writable global/user-prefix install;
repository-local dependencies receive normal npm update instructions.

### GitHub Packages and updates

The repository and release download are public. GitHub's npm registry requires
authentication even for public packages. To install by package name or use the
built-in update checks and automatic updates, configure the registry:

```sh
npm config set @smoothsdlc:registry https://npm.pkg.github.com
npm login --scope=@smoothsdlc --auth-type=legacy --registry=https://npm.pkg.github.com
npm install --global @smoothsdlc/smooth-backlog-cli
```

When npm login asks for a password, use a GitHub personal access token (classic)
with `read:packages`. To keep installing updates from public release assets
instead, use `backlog update disable` to turn off weekly registry checks.

## Development and releases

No product dependencies or build step are needed:

```sh
npm test
npm run check
node bin/backlog.js --help
npm pack --dry-run
```

Tests create temporary Git repositories and use controlled registry fixtures.
CI runs Node 24/26 across Linux, macOS, and Windows, plus generated-skill checks.
Updater-compatible releases retain the package.json schema/bootstrap markers
and stable bin launcher; see the release contract in the command reference.
The release workflow runs the reusable CI matrix before publishing the exact
packed tarball to GitHub Packages. It then installs that exact version using a
fresh npm cache on Linux, macOS, and Windows with Node 24/26, checks the registry
integrity against the published artifact, and exercises the downloaded CLI and
its four generated integrations. It also upgrades the published 1.0.0 baseline
through the real feed and verifies permanent item identity and skill refresh.
Each platform uploads its verification result.
The [1.0.1 release evidence](docs/releases/1.0.1-verification.json) records the
successful registry installations, upgrades, artifact integrity, and job links.
The actual published tarball was also downloaded through the public release and
installed in the local agent workspace: **all 51 tests passed with zero failures
or skips**, plus 27 installed-CLI checks and generated-skill validation. All 24
original installed files retained their hashes. See the
[local verification evidence](docs/releases/1.0.1-local-verification.json) and
[full test output](docs/releases/1.0.1-local-tests.log).
Version tags and manual dispatch trigger releases using the repository token.
The `Export published package to public release` workflow downloads an existing
published version, verifies its registry integrity, and attaches the tarball to
its GitHub release without rebuilding it.
To independently verify an accessible published version, configure package-read
authentication and run `node scripts/verify-published-package.mjs 1.0.1`.

[initial-prompt.md](initial-prompt.md) preserves the initial requirements;
[the revised specification](docs/superpowers/specs/2026-10-16-backlog-cli-design.md)
records subsequent product decisions. See [AGENTS.md](AGENTS.md) and
[cloud setup](docs/codex-cloud-setup.md) for the repository development skills and
code graph tooling. Third-party development tools retain MIT licenses; see [NOTICE](NOTICE).
