#!/usr/bin/env bash
# Requires bash; the runtime is installed by setup-codex-cloud.py.
set -euo pipefail
repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
runtime="$repo_root/.codex/tools/bin/codebase-memory-mcp"
if [[ ! -x "$runtime" ]]; then
  printf '%s\n' 'Run python3 scripts/setup-codex-cloud.py from the repo first.' >&2
  exit 1
fi
cd -- "$repo_root"
exec "$runtime" "$@"
