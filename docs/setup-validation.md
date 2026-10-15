# Setup validation on BIGFAN

The repository integration was checked on October 15, 2026:

- Setup completed, then completed again with the same runtime and dependencies.
- The downloaded Linux amd64 portable archive matched the pinned SHA-256.
- The extracted runtime reported `codebase-memory-mcp 0.11.0`.
- All 21 skill frontmatter headers parsed as YAML, matched their directory names,
  and contained nonempty descriptions within the 1024-character limit.
- Every imported skill file matched its source manifest SHA-256.
- Both requested guidance files matched their source files byte for byte.
- The project MCP configuration parsed as TOML, and the launcher passed Bash's
  syntax check.
- The validator Python environment passed `pip check`.

The downloaded portable build could not execute a graph query on BIGFAN because
the account already had active sessions using a different executable build of
the same version. CBM correctly rejected the concurrent build. Those sessions
were left running. The existing native installation successfully answered
`cli list_projects`, establishing local availability independently of the
downloaded build. The launcher also successfully ran the pinned build's
`--version`, which does not enter session coordination.

A fresh hosted cloud run and MCP handshake have not been performed. They
require publishing the checkout and configuring its cloud environment. The
CLI path is provided because hosted harness support for project stdio MCP
configuration varies.

The imported development skills were not changed to satisfy the corporate
authoring gates. No product skill was created or certified by those gates.
