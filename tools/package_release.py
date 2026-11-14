#!/usr/bin/env python3
"""Build deterministic, allowlisted skill and source archives without dependencies."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST = "tools/release-files.json"
VERSION_PATTERN = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9]+(?:[.-][A-Za-z0-9]+)*)?")
FORBIDDEN_PARTS = {".git", ".agents", ".codex", ".venv", "__pycache__", "node_modules", "dist", "runs", "demo-runs", "verification", "test-results", ".pending-state.json", "ai-request.json", "submission-history.json", "submission.json", "handoff.json", "progress.json", "imports.json", "questionnaire-export.json", "answers.json", "questions.json"}


class ReleaseError(ValueError):
    """A release input is missing or is unsafe to package."""


def relative_file(root: Path, value: object, *, required: bool = True) -> Path | None:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ReleaseError(f"Use a nonempty portable relative path: {value!r}")
    parts = value.split("/")
    if value.startswith("/") or any(part in {"", ".", ".."} for part in parts):
        raise ReleaseError(f"Invalid relative path: {value}")
    if any(part in FORBIDDEN_PARTS or part == ".env" or part.startswith(".env.") for part in parts):
        raise ReleaseError(f"Generated or private files cannot enter a release: {value}")
    if PurePosixPath(value).suffix.lower() in {".pyc", ".pyo", ".key", ".pem", ".zip"}:
        raise ReleaseError(f"Unsupported release file type: {value}")
    candidate = root
    for part in parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise ReleaseError(f"Release inputs cannot be symbolic links: {value}")
    if not candidate.exists():
        if required:
            raise ReleaseError(f"Missing allowlisted file: {value}")
        return None
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ReleaseError(f"Release input is not a file inside the repository: {value}")
    return candidate


def load_release(root: Path = ROOT) -> tuple[str, list[str], list[str]]:
    root = root.resolve()
    try:
        data = json.loads((root / ALLOWLIST).read_text(encoding="utf-8"))
        version = (root / "VERSION").read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ReleaseError(f"Cannot read release metadata: {error}") from error
    if not VERSION_PATTERN.fullmatch(version):
        raise ReleaseError("VERSION must contain one version such as 0.1.0 or 0.2.0-rc.1.")
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ReleaseError("The release allowlist must use schema_version 1.")
    if set(data) != {"schema_version", "runtime", "source", "optional"}:
        raise ReleaseError("Unknown or missing release allowlist fields.")
    seen: set[str] = set()
    groups: dict[str, list[str]] = {}
    for group in ("runtime", "source", "optional"):
        paths = data[group]
        if not isinstance(paths, list) or (group != "optional" and not paths):
            raise ReleaseError(f"Allowlist {group} must be an array of file paths.")
        groups[group] = []
        for value in paths:
            path = relative_file(root, value, required=group != "optional")
            folded = value.casefold()
            if folded in seen:
                raise ReleaseError(f"Duplicate or case-colliding allowlist entry: {value}")
            seen.add(folded)
            if path is not None:
                groups[group].append(value)
    if any(not path.startswith("any-skill-builder/") for path in groups["runtime"]):
        raise ReleaseError("Every runtime file must be inside any-skill-builder/.")
    if "any-skill-builder/SKILL.md" not in groups["runtime"] or ALLOWLIST not in groups["source"] or "VERSION" not in groups["source"]:
        raise ReleaseError("SKILL.md, VERSION, and the release allowlist must be included.")
    runtime = sorted(groups["runtime"])
    source = sorted(runtime + groups["source"] + groups["optional"])
    return version, runtime, source


def archive_bytes(entries: list[tuple[str, bytes]]) -> bytes:
    """Use fixed metadata and stored bytes for reproducibility across zlib versions."""
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, content in sorted(entries):
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            entry.compress_type = zipfile.ZIP_STORED
            archive.writestr(entry, content)
    result = stream.getvalue()
    with zipfile.ZipFile(io.BytesIO(result)) as archive:
        if archive.testzip() is not None:
            raise ReleaseError("Archive integrity verification failed.")
    return result


def build_artifacts(root: Path = ROOT) -> dict[str, bytes]:
    root = root.resolve()
    version, runtime, source = load_release(root)
    contents = {path: (root / path).read_bytes() for path in source}
    runtime_entries = [(path, contents[path]) for path in runtime]
    if "any-skill-builder/VERSION" in contents:
        if contents["any-skill-builder/VERSION"] != contents["VERSION"]:
            raise ReleaseError("Root and runtime VERSION files differ.")
    else:
        runtime_entries.append(("any-skill-builder/VERSION", contents["VERSION"]))
    if "LICENSE" in contents:
        if "any-skill-builder/LICENSE" in contents:
            if contents["any-skill-builder/LICENSE"] != contents["LICENSE"]:
                raise ReleaseError("Root and runtime LICENSE files differ.")
        else:
            runtime_entries.append(("any-skill-builder/LICENSE", contents["LICENSE"]))
    source_prefix = f"any-skill-builder-{version}-source/"
    archives = {
        f"any-skill-builder-{version}.zip": archive_bytes(runtime_entries),
        f"any-skill-builder-{version}-source.zip": archive_bytes([(source_prefix + path, contents[path]) for path in source]),
    }
    manifest = {
        "schema_version": 1,
        "name": "any-skill-builder",
        "version": version,
        "license_file_included": "LICENSE" in contents,
        "archives": [{"path": name, "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest()} for name, blob in sorted(archives.items())],
        "source_files": [{"path": path, "bytes": len(contents[path]), "sha256": hashlib.sha256(contents[path]).hexdigest()} for path in source],
        "runtime_files": sorted(name for name, _ in runtime_entries),
    }
    artifacts = dict(archives)
    artifacts[f"any-skill-builder-{version}-manifest.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    return artifacts


def write_artifacts(artifacts: dict[str, bytes], output: Path, *, overwrite: bool = False) -> None:
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    for name, blob in artifacts.items():
        path = output / name
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise ReleaseError(f"Output is not a regular file: {path}")
        if path.exists() and path.read_bytes() != blob and not overwrite:
            raise ReleaseError(f"Different output already exists: {path}. Choose another directory or pass --overwrite.")
    for name, blob in artifacts.items():
        path = output / name
        if not path.exists():
            with path.open("xb") as stream:
                stream.write(blob)
        elif path.read_bytes() != blob:
            path.write_bytes(blob)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "dist", help="Artifact directory (default: repository dist/)")
    parser.add_argument("--overwrite", action="store_true", help="Replace only conflicting generated artifact files in the selected directory")
    args = parser.parse_args(argv)
    try:
        artifacts = build_artifacts()
        write_artifacts(artifacts, args.out, overwrite=args.overwrite)
        print(json.dumps({"artifacts": [{"path": str(args.out / name), "bytes": len(blob)} for name, blob in artifacts.items()]}, indent=2))
        return 0
    except (OSError, UnicodeError, ReleaseError) as error:
        print(f"Release failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
