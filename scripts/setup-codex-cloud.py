#!/usr/bin/env python3
"""Install pinned development tooling into this checkout.

Requires Python 3.11+, venv/pip, Linux x86_64 or aarch64, and HTTPS access
to GitHub release assets and PyPI. Idempotent; no global configuration changes.
Usage: python3 scripts/setup-codex-cloud.py [--dry-run]
Exit codes: 0 success, 1 installation failure, 2 invalid usage.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import venv


ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def setup(dry_run):
    if sys.version_info < (3, 11):
        raise RuntimeError("Python 3.11 or newer is required for skills-ref.")
    arch = {"x86_64": "amd64", "aarch64": "arm64"}.get(platform.machine())
    if platform.system() != "Linux" or arch is None:
        raise RuntimeError("Cloud setup supports Linux x86_64 and aarch64.")
    pin = json.loads((ROOT / ".codex/tool-versions.json").read_text())["codebase-memory-mcp"]
    target = f"linux-{arch}-portable"
    name = f"codebase-memory-mcp-{target}.tar.gz"
    url = f"{pin['repository']}/releases/download/v{pin['version']}/{name}"
    directory = ROOT / ".codex/tools" / f"v{pin['version']}"
    archive = directory / name
    unpacked = directory / target
    binary = unpacked / "codebase-memory-mcp"
    launcher = ROOT / ".codex/tools/bin/codebase-memory-mcp"
    python_dir = ROOT / ".codex/tools/skill-python"
    print(f"Install codebase-memory-mcp {pin['version']} ({target}) into {directory}", flush=True)
    print(f"Install pinned skill validators into {python_dir}", flush=True)
    if dry_run:
        print(f"Download if absent: {url}")
        return

    directory.mkdir(parents=True, exist_ok=True)
    if not archive.exists():
        partial = archive.with_suffix(".download")
        print(f"Downloading {url}", flush=True)
        with urllib.request.urlopen(url, timeout=120) as response, partial.open("wb") as output:
            shutil.copyfileobj(response, output)
        if sha256(partial) != pin["archives"][target]:
            raise RuntimeError(f"SHA-256 mismatch; retained download at {partial}")
        partial.replace(archive)
    if sha256(archive) != pin["archives"][target]:
        raise RuntimeError(f"SHA-256 mismatch: {archive}. Move it aside before retrying.")

    unpacked.mkdir(exist_ok=True)
    with tarfile.open(archive, "r:gz") as bundle:
        # Extract only named regular files; never trust archive paths or links.
        for filename in ("codebase-memory-mcp", "LICENSE", "THIRD_PARTY_NOTICES.md"):
            member = bundle.getmember(filename)
            if not member.isfile():
                raise RuntimeError(f"Not a regular archive member: {filename}")
            destination = unpacked / filename
            with bundle.extractfile(member) as source:
                digest = hashlib.sha256()
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
            if destination.exists() and sha256(destination) == digest.hexdigest():
                continue
            if destination.exists():
                raise RuntimeError(f"Existing runtime file differs: {destination}. Move it aside before retrying.")
            with bundle.extractfile(member) as source, destination.open("xb") as output:
                shutil.copyfileobj(source, output)
    binary.chmod(0o755)
    expected = f"codebase-memory-mcp {pin['version']}"
    version = subprocess.check_output([str(binary), "--version"], text=True).strip()
    if version != expected:
        raise RuntimeError(f"Expected {expected!r}, got {version!r}")
    launcher.parent.mkdir(parents=True, exist_ok=True)
    relative_binary = os.path.relpath(binary, launcher.parent)
    if os.path.lexists(launcher):
        if not launcher.is_symlink() or os.readlink(launcher) != relative_binary:
            raise RuntimeError(f"Existing launcher differs: {launcher}. Move it aside before retrying.")
    else:
        launcher.symlink_to(relative_binary)

    if not (python_dir / "bin/python").exists():
        venv.create(python_dir, with_pip=True)
    subprocess.run([
        str(python_dir / "bin/python"), "-m", "pip", "install",
        "--disable-pip-version-check", "-r", str(ROOT / ".codex/skill-requirements.txt"),
    ], check=True)
    # The copied guidance uses the old command name; 0.1.1 ships 'agentskills'.
    legacy_command = python_dir / "bin/skills-ref"
    if not os.path.lexists(legacy_command):
        legacy_command.symlink_to("agentskills")
    elif not legacy_command.is_symlink() or os.readlink(legacy_command) != "agentskills":
        raise RuntimeError(f"Existing command differs: {legacy_command}. Move it aside before retrying.")
    print("Ready: 21 repository skills, codebase-memory-mcp, and skill validators.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print the plan without writing or downloading")
    args = parser.parse_args()
    try:
        setup(args.dry_run)
    except (OSError, RuntimeError, ValueError, KeyError, tarfile.TarError, subprocess.SubprocessError) as error:
        print(f"Setup failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
