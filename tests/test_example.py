"""Public example checks preserve evidence and detect stale release records."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_example


class PublicExampleTests(unittest.TestCase):
    def setUp(self):
        cache = os.environ.get("SKILL_BUILDER_TEST_TMPDIR")
        if cache:
            Path(cache).mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="public-example-", dir=cache)
        self.example = Path(self.temp.name) / "copied example"
        shutil.copytree(ROOT / "examples" / "complete", self.example)

    def tearDown(self):
        self.temp.cleanup()

    def snapshot(self):
        return {path.relative_to(self.example).as_posix(): path.read_bytes()
                for path in self.example.rglob("*") if path.is_file()}

    def regenerate(self):
        manifest = self.example / "evaluation.json"
        evaluation = check_example.evaluation
        evaluation.write_report(manifest, self.example / "evaluation-report", evaluation.evaluate(manifest), True)

    def test_clean_example_and_cli_are_read_only_and_match_the_saved_report(self):
        before = self.snapshot()
        result = check_example.check_example(self.example)
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["checks"], {"pass": 9, "fail": 0, "not_run": 0})
        completed = subprocess.run([sys.executable, "-B", str(ROOT / "tools" / "check_example.py"),
                                    "--example", str(self.example)], cwd=self.temp.name,
                                   capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(json.loads(completed.stdout)["valid"])
        self.assertEqual(before, self.snapshot())

    def test_crlf_is_rejected_even_when_reports_match_the_windows_bytes(self):
        output = self.example / "outputs" / "routine.md"
        output.write_bytes(output.read_bytes().replace(b"\n", b"\r\n"))
        self.regenerate()
        before = self.snapshot()
        result = check_example.check_example(self.example)
        self.assertFalse(result["valid"])
        self.assertTrue(any("outputs/routine.md: contains CRLF" in error for error in result["errors"]))
        self.assertEqual(before, self.snapshot())

    def test_changed_evidence_is_detected_even_when_existing_quotes_still_match(self):
        output = self.example / "outputs" / "routine.md"
        output.write_bytes(output.read_bytes() + b"\nAdditional unreviewed output.\n")
        result = check_example.check_example(self.example)
        self.assertFalse(result["valid"])
        self.assertTrue(any("artifacts.output.bytes" in error for error in result["errors"]))

    def test_edited_or_missing_report_is_detected(self):
        markdown = self.example / "evaluation-report.md"
        markdown.write_bytes(markdown.read_bytes() + b"Unexpected stale note.\n")
        result = check_example.check_example(self.example)
        self.assertTrue(any("evaluation-report.md: stale" in error for error in result["errors"]))
        markdown.unlink()
        result = check_example.check_example(self.example)
        self.assertTrue(any("evaluation-report.md: saved report is missing" in error for error in result["errors"]))

    def test_explicit_not_run_records_are_preserved_without_becoming_failure(self):
        manifest = self.example / "evaluation.json"
        document = json.loads(manifest.read_text(encoding="utf-8"))
        document["runs"][0]["cases"][0] = {"case_id": "routine", "status": "not_run", "reason": "Not rerun in this synthetic test."}
        manifest.write_bytes((json.dumps(document, indent=2) + "\n").encode("utf-8"))
        self.regenerate()
        result = check_example.check_example(self.example)
        self.assertTrue(result["valid"], result)
        self.assertGreater(result["checks"]["not_run"], 0)
        self.assertEqual(result["checks"]["fail"], 0)

    def test_failed_completed_check_is_not_a_successful_release_check(self):
        manifest = self.example / "evaluation.json"
        document = json.loads(manifest.read_text(encoding="utf-8"))
        document["cases"][0]["checks"][0]["text"] = "Missing expected evidence in this synthetic test"
        manifest.write_bytes((json.dumps(document, indent=2) + "\n").encode("utf-8"))
        self.regenerate()
        result = check_example.check_example(self.example)
        self.assertFalse(result["valid"])
        self.assertTrue(any("1 failed checks" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
