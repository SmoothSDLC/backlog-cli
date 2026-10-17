#!/usr/bin/env python3
"""Script: validate-skill.py
Requires: Python 3.8+ stdlib; skills-ref/agentskills optional for full spec validation.
Purpose: Validate bundled skill resources, Python syntax, and evaluation fixture structure.
Idempotent: yes — read-only checks. Exit codes: 0 passes, 1 findings, 2 usage.
"""
import argparse
import ast
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    root = Path(__file__).resolve().parents[1]
    failures = []
    def check(condition, message):
        print(("✅ " if condition else "❌ ") + message, file=sys.stderr)
        if not condition:
            failures.append(message)
    try:
        text = (root / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"---\n(.*?)\n---\n", text, re.S)
        check(bool(match), "Frontmatter block exists")
        check(bool(re.search(r"^name: " + re.escape(root.name) + r"$", text, re.M)), "Directory matches skill name")
        check(len(text.splitlines()) < 500, "SKILL.md is under 500 lines")
        refs = set(re.findall(r"(?<![\w./-])(?:scripts|references|assets|evals)/[\w./-]+", text))
        for ref in refs:
            check((root / ref).is_file(), "Referenced resource exists: " + ref)
        for path in (root / "scripts").glob("*.py"):
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        check((root / "scripts/snapshot.py").exists(), "Functional snapshot helper exists")
        queries = json.loads((root / "scripts/eval_queries.json").read_text(encoding="utf-8"))
        check(sum(x["should_trigger"] is True for x in queries) >= 10, "At least 10 trigger fixtures")
        check(sum(x["should_trigger"] is False for x in queries) >= 8, "At least 8 negative fixtures")
        check(len({x["query"] for x in queries}) == len(queries), "Trigger fixtures are unique")
        cases = json.loads((root / "evals/evals.json").read_text(encoding="utf-8"))["evals"]
        check(bool(cases) and all(x.get("prompt") and x.get("expected_output") and x.get("assertions") for x in cases), "Output evaluation cases are complete")
        reference = shutil.which("skills-ref") or shutil.which("agentskills")
        if reference:
            result = subprocess.run([reference, "validate", str(root)], capture_output=True, text=True, timeout=30, check=False)
            check(result.returncode == 0, "Agent Skills reference validation: " + (result.stdout or result.stderr).strip())
        else:
            print("ℹ️ skills-ref is unavailable; run the repository authoritative linter/auditor separately", file=sys.stderr)
    except (OSError, ValueError, SyntaxError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        check(False, str(exc))
    print(json.dumps({"ok": not failures, "failures": failures}))
    return int(bool(failures))


if __name__ == "__main__":
    sys.exit(main())
