"""Installation must preserve existing data and copy only the shipped runtime."""
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from install_skill import install, NAME
from package_release import load_release, ReleaseError


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get('SKILL_BUILDER_TEST_TMPDIR'))
        self.parent = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_install_and_identical_repeat(self):
        result = install(self.parent)
        self.assertTrue(result['changed'])
        target = self.parent / NAME
        _, runtime, _ = load_release()
        expected = {str(Path(p).relative_to(NAME)).replace('\\', '/') for p in runtime} | {'VERSION'}
        self.assertEqual({p.relative_to(target).as_posix() for p in target.rglob('*') if p.is_file()}, expected)
        self.assertEqual((target / 'SKILL.md').read_bytes(), (ROOT / NAME / 'SKILL.md').read_bytes())
        self.assertFalse(install(self.parent)['changed'])

    def test_existing_modified_install_is_not_overwritten(self):
        install(self.parent)
        path = self.parent / NAME / 'SKILL.md'
        path.write_text('User changes', encoding='utf-8')
        with self.assertRaises(ReleaseError):
            install(self.parent)
        self.assertEqual(path.read_text(encoding='utf-8'), 'User changes')

    def test_repository_is_not_an_install_destination(self):
        with self.assertRaises(ReleaseError):
            install(ROOT / 'unwanted-install')
        self.assertFalse((ROOT / 'unwanted-install').exists())


if __name__ == '__main__':
    unittest.main()
