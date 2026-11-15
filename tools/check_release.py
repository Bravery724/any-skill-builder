#!/usr/bin/env python3
"""Check portable release inputs, local documentation links, and skill structure."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

from package_release import ROOT, ReleaseError, load_release

sys.path.insert(0, str(ROOT / "any-skill-builder" / "scripts"))
from builder_core import markdown_prose


PERSONAL_HOME = re.compile(r"(?:[A-Za-z]:[/\\]Users[/\\][^\s/\\]+|/(?:Users|home)/[^\s/]+)")
MARKDOWN_LINK = re.compile(r"!?\[[^\]\n]+\]\((?:<([^>]+)>|([^\s)]+))(?:\s+\"[^\"]*\")?\)")
IMAGE_SIGNATURES = {
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".gif": (b"GIF87a", b"GIF89a"),
}


def check_files(root: Path, paths: list[str]) -> list[str]:
    errors = []
    for relative in paths:
        path = root / relative
        if path.suffix.lower() == ".mp4":
            if path.read_bytes()[4:8] != b"ftyp":
                errors.append(f"{relative}: invalid MP4 signature")
            continue
        signatures = IMAGE_SIGNATURES.get(path.suffix.lower())
        if signatures is not None:
            if not path.read_bytes().startswith(signatures):
                errors.append(f"{relative}: invalid image signature")
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            errors.append(f"{relative}: expected readable UTF-8 source ({error})")
            continue
        if PERSONAL_HOME.search(content):
            errors.append(f"{relative}: contains a personal absolute home path")
        if path.suffix == ".md":
            prose = markdown_prose(content)
            for match in MARKDOWN_LINK.finditer(prose):
                target = match.group(1) or match.group(2)
                parsed = urlsplit(target)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                destination = (path.parent / unquote(parsed.path)).resolve()
                if not destination.is_relative_to(root) or not destination.exists():
                    errors.append(f"{relative}: broken or external local link: {target}")
    return errors


def main() -> int:
    try:
        version, runtime, source = load_release()
        errors = check_files(ROOT, source)
        sys.path.insert(0, str(ROOT / "any-skill-builder" / "scripts"))
        import builder_core as core
        try:
            result = core.check_skill(ROOT / "any-skill-builder")
            if not result.get("valid"):
                errors.append("Skill structural validation failed.")
            if core.resolve_locale()["language"] != "en":
                errors.append("The default locale must be English.")
        except core.BuilderError as error:
            errors.append(f"Skill validation failed: {error}")
        if errors:
            print(json.dumps({"valid": False, "errors": errors}, indent=2))
            return 1
        print(json.dumps({"valid": True, "version": version, "runtime_files": len(runtime), "source_files": len(source),
                          "checks": ["explicit file allowlist", "portable paths", "UTF-8 source", "local Markdown links", "skill structure", "English locale default"],
                          "note": "These checks are not a secret scanner, semantic review, or GitHub-hosted CI execution."}, indent=2))
        return 0
    except (OSError, UnicodeError, ReleaseError, ValueError) as error:
        print(f"Release check failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
