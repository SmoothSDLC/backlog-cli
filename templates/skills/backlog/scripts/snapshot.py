#!/usr/bin/env python3
"""Script: snapshot.py
Requires: Python 3.8+ stdlib, Node.js 24+, installed backlog-cli; no pip packages.
Purpose: Produce a validated, branch-specific snapshot and deterministic task counts.
Idempotent: yes — read-only CLI inspection; never changes project backlog data.
Exit codes: 0 success, 1 operational/validation failure, 2 invalid arguments.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__, epilog="Example: python snapshot.py --state done --branch main")
    parser.add_argument("--cli", help="Path to the installed bin/backlog.js (default: resolve backlog from PATH)")
    parser.add_argument("--branch", help="Read another stored branch without changing Git checkout")
    parser.add_argument("--state", choices=["active", "done", "archive"], default="active")
    args = parser.parse_args()
    try:
        cli = args.cli or shutil.which("backlog")
        if not cli:
            raise ValueError("backlog is not on PATH; install it or provide --cli /path/to/bin/backlog.js")
        path = Path(cli).resolve()
        if os.name == "nt" and path.suffix.lower() == ".cmd":
            candidates = [path.parent / "node_modules/@smoothsdlc/smooth-backlog-cli/bin/backlog.js", path.parent.parent / "@smoothsdlc/smooth-backlog-cli/bin/backlog.js"]
            path = next((p for p in candidates if p.exists()), path)
        if path.suffix.lower() == ".cmd":
            raise ValueError("Cannot resolve the Windows npm shim; provide --cli with the bin/backlog.js path")
        command = ["node", str(path), "list", "--json"]
        if args.state != "active":
            command.append(args.state)
        if args.branch:
            command.extend(["--branch", args.branch])
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=45, check=False)
        try:
            envelope = json.loads(result.stdout)
        except ValueError as exc:
            raise ValueError("CLI did not emit one JSON object; check the executable path and version") from exc
        if result.returncode or envelope.get("ok") is not True:
            raise ValueError(envelope.get("error", {}).get("message", "CLI snapshot failed"))
        items = envelope.get("data")
        if not isinstance(items, list):
            raise ValueError("CLI list output must contain an item array")
        identities = [str(uuid.UUID(item["id"])) for item in items]
        if len(set(identities)) != len(identities):
            raise ValueError("Snapshot contains duplicate GUIDs; resolve the backlog conflict")
        if args.state == "active" and [item["priority"] for item in items] != list(range(len(items))):
            raise ValueError("Active priorities are not contiguous from zero; resolve the backlog conflict")
        task_count = sum(len(item["tasks"]) for item in items)
        branches = sorted({item["branch"] for item in items})
        print(json.dumps({"ok": True, "data": {"branch": args.branch or (branches[0] if len(branches) == 1 else None), "items": items, "summary": {"items": len(items), "tasks": task_count}}}))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        print("❌ " + str(exc), file=sys.stderr)
        print(json.dumps({"ok": False, "error": {"code": "SNAPSHOT_FAILED", "message": str(exc)}}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
