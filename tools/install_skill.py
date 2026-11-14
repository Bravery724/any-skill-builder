#!/usr/bin/env python3
"""Install the allowlisted runtime into an explicitly selected host skills directory."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

from package_release import ROOT, ReleaseError, load_release

NAME = "any-skill-builder"


def install(destination: Path, root: Path = ROOT) -> dict:
    root = root.resolve()
    version, runtime, _ = load_release(root)
    parent = destination.expanduser().absolute()
    for part in (parent, *parent.parents):
        if part.is_symlink():
            raise ReleaseError("The destination must not pass through a symbolic link.")
    parent = parent.resolve()
    if parent.is_relative_to(root):
        raise ReleaseError("Choose a host skills directory outside the source repository.")
    target = parent / NAME
    expected = {str(Path(name).relative_to(NAME)).replace("\\", "/"): (root / name).read_bytes() for name in runtime}
    expected["VERSION"] = (root / "VERSION").read_bytes()
    if target.is_symlink():
        raise ReleaseError("The target is a symbolic link; use your host's update workflow.")
    if target.exists():
        actual = {}
        for path in target.rglob("*"):
            if path.is_symlink():
                raise ReleaseError("The existing installation contains a symbolic link.")
            if path.is_file():
                actual[path.relative_to(target).as_posix()] = path.read_bytes()
        if target.is_dir() and actual == expected:
            return {"installed": True, "changed": False, "version": version, "path": str(target)}
        raise ReleaseError("A different installation already exists. Preserve it and use your host's update workflow; this installer does not overwrite it.")
    parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".any-skill-builder-", dir=parent))
    try:
        for relative, content in expected.items():
            path = stage / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            if hashlib.sha256(path.read_bytes()).digest() != hashlib.sha256(content).digest():
                raise ReleaseError(f"Installed file verification failed: {relative}")
        if target.exists():
            raise ReleaseError("The installation target appeared while preparing the copy.")
        stage.rename(target)
    finally:
        if stage.exists():
            # Only the unique staging directory created by this call is removed.
            if stage.parent.resolve() == parent and stage.name.startswith(".any-skill-builder-"):
                shutil.rmtree(stage)
    return {"installed": True, "changed": True, "version": version, "path": str(target), "files": len(expected)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", required=True, type=Path, help="Explicit host skills directory (the skill name is appended)")
    args = parser.parse_args()
    try:
        print(json.dumps(install(args.dest), indent=2))
        return 0
    except (OSError, ReleaseError) as error:
        print(f"Installation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
