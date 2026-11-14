"""Release checks exercise reproducibility, boundaries, and archive fidelity."""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import package_release as release
from check_release import check_files


class PackagingTests(unittest.TestCase):
    def setUp(self):
        cache = os.environ.get("SKILL_BUILDER_TEST_TMPDIR")
        if cache:
            Path(cache).mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="release-", dir=cache)
        self.root = Path(self.temp.name)
        self.allowlist = {
            "schema_version": 1,
            "runtime": ["any-skill-builder/SKILL.md", "any-skill-builder/LICENSE"],
            "source": ["README.md", "VERSION", "LICENSE", "tools/release-files.json"],
            "optional": [],
        }
        self.write("any-skill-builder/SKILL.md", "---\nname: any-skill-builder\ndescription: Test fixture\n---\nInstructions.\n")
        self.write("VERSION", "0.1.0\n")
        self.write("README.md", "# Test fixture\n[Skill](any-skill-builder/SKILL.md)\n")
        self.write("LICENSE", "Synthetic license fixture.\n")
        self.write("any-skill-builder/LICENSE", "Synthetic license fixture.\n")
        self.save_allowlist()

    def tearDown(self):
        self.temp.cleanup()

    def write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")

    def save_allowlist(self):
        self.write("tools/release-files.json", json.dumps(self.allowlist, indent=2) + "\n")

    def test_reproducible_despite_file_mtimes(self):
        first = release.build_artifacts(self.root)
        for path in self.root.rglob("*"):
            if path.is_file():
                os.utime(path, (1234567890, 1234567890))
        self.assertEqual(first, release.build_artifacts(self.root))

    def test_only_explicit_files_are_packaged(self):
        self.write(".env", "DO_NOT_PACKAGE=private-fixture\n")
        self.write("runs/user/answers.json", '{"private": true}\n')
        self.write("any-skill-builder/forgotten-notes.md", "Not selected for release.\n")
        files = release.build_artifacts(self.root)
        for name, blob in files.items():
            self.assertNotIn(b"private-fixture", blob)
            self.assertNotIn(b"forgotten-notes", blob)
            if name.endswith(".zip"):
                with zipfile.ZipFile(io.BytesIO(blob)) as archive:
                    self.assertTrue(all(not item.startswith("/") and ".." not in item.split("/") and "\\" not in item for item in archive.namelist()))
        with zipfile.ZipFile(io.BytesIO(files["any-skill-builder-0.1.0.zip"])) as archive:
            self.assertEqual(set(archive.namelist()), {"any-skill-builder/SKILL.md", "any-skill-builder/LICENSE", "any-skill-builder/VERSION"})

    def test_manifest_hashes_match_exact_bytes(self):
        files = release.build_artifacts(self.root)
        manifest = json.loads(files["any-skill-builder-0.1.0-manifest.json"])
        self.assertTrue(manifest["license_file_included"])
        self.assertNotIn(str(self.root), json.dumps(manifest))
        for item in manifest["archives"]:
            self.assertEqual(item["bytes"], len(files[item["path"]]))
            self.assertEqual(item["sha256"], hashlib.sha256(files[item["path"]]).hexdigest())
        for item in manifest["source_files"]:
            blob = (self.root / item["path"]).read_bytes()
            self.assertEqual(item["sha256"], hashlib.sha256(blob).hexdigest())

    def test_missing_required_input_fails(self):
        self.allowlist["source"].append("missing.md")
        self.save_allowlist()
        with self.assertRaisesRegex(release.ReleaseError, "Missing allowlisted"):
            release.build_artifacts(self.root)

    def test_unsafe_and_private_paths_fail(self):
        for path in ("../outside.md", "/absolute.md", "assets\\file.md", "D:/file.md", ".env", ".agents/session.json", ".codex/auth.json", "nested/.agents/local.json", "runs/answers.json", "ai-request.json", "submission-history.json", "handoff.json", "progress.json", "nested/handoff.json", "nested/progress.json", ".pending-state.json", "key.pem", "dist/archive.zip"):
            with self.subTest(path=path), self.assertRaises(release.ReleaseError):
                release.relative_file(self.root, path, required=False)

    def test_case_colliding_names_fail(self):
        self.allowlist["optional"].append("readme.md")
        self.save_allowlist()
        with self.assertRaisesRegex(release.ReleaseError, "case-colliding"):
            release.load_release(self.root)

    def test_conflicting_outputs_require_explicit_overwrite(self):
        output = self.root / "dist"
        initial = release.build_artifacts(self.root)
        release.write_artifacts(initial, output)
        release.write_artifacts(initial, output)
        self.write("README.md", "Updated source.\n")
        changed = release.build_artifacts(self.root)
        with self.assertRaisesRegex(release.ReleaseError, "Different output"):
            release.write_artifacts(changed, output)
        self.assertEqual((output / "any-skill-builder-0.1.0-source.zip").read_bytes(), initial["any-skill-builder-0.1.0-source.zip"])
        release.write_artifacts(changed, output, overwrite=True)
        self.assertEqual((output / "any-skill-builder-0.1.0-source.zip").read_bytes(), changed["any-skill-builder-0.1.0-source.zip"])

    def test_runtime_license_must_match_root(self):
        self.write("any-skill-builder/LICENSE", "Different license fixture.\n")
        with self.assertRaisesRegex(release.ReleaseError, "LICENSE files differ"):
            release.build_artifacts(self.root)

    def test_documentation_links_and_personal_paths(self):
        self.assertEqual(check_files(self.root, ["README.md"]), [])
        self.write("README.md", "Inline `[Example](not-a-file.md)`\n\n~~~md\n[Sample](also-not-a-file.md)\n~~~\n")
        self.assertEqual(check_files(self.root, ["README.md"]), [])
        self.write("README.md", "[Missing](absent.md)\nLocal path: " + "C:/" + "Users/PrivateExample/work\n")
        errors = check_files(self.root, ["README.md"])
        self.assertEqual(len(errors), 2)


if __name__ == "__main__":
    unittest.main()
