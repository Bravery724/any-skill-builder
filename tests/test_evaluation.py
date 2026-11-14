"""Evidence and comparison boundaries for the saved-artifact evaluation helper."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PACKAGE = Path(__file__).resolve().parents[1] / "any-skill-builder"
sys.path.insert(0, str(PACKAGE / "scripts"))
import evaluate_skill as evaluation


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        cache = os.environ.get("SKILL_BUILDER_TEST_TMPDIR")
        if cache:
            Path(cache).mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="evaluation-", dir=cache)
        self.parent = Path(self.temp.name)
        self.root = self.parent / "suite"
        self.root.mkdir()
        self.write("inputs/task.md", "Summarize the supplied project notes.")
        self.write("outputs/result.md", "The release is delayed. The revised date is unconfirmed.\n")
        self.write("outputs/result.json", json.dumps({"facts": [{"confirmed": False, "title": "한글"}]}))
        self.manifest_path = self.root / "evaluation.json"
        self.document = {
            "schema_version": 1, "name": "Weekly update evidence",
            "cases": [{"id": "uncertainty", "prompt": "Write a useful update from the notes.",
                       "input_files": ["inputs/task.md"], "checks": [
                           {"id": "delay", "category": "skill_output", "kind": "contains", "artifact": "output", "text": "release is delayed"},
                           {"id": "no-invented-date", "category": "skill_output", "kind": "not_contains", "artifact": "output", "text": "November 20"},
                           {"id": "truth", "category": "mechanics", "kind": "json_equals", "artifact": "data", "path": ["facts", 0, "confirmed"], "expected": False},
                           {"id": "useful", "category": "question_quality", "kind": "review", "criterion": "The chosen uncertainty policy changes the output usefully.", "question_ids": ["q-uncertainty"]}]}],
            "runs": [{"id": "candidate", "variant": "with_skill", "context": {"model": None, "effort": None, "tools": None, "budget": None},
                      "cases": [{"case_id": "uncertainty", "status": "completed", "artifacts": {"output": "outputs/result.md", "data": "outputs/result.json"},
                                 "reviews": {"useful": {"status": "pass", "reviewer": "Independent reviewer", "reason": "The selected policy preserves the uncertainty.",
                                                         "evidence": [{"artifact": "output", "quote": "The revised date is unconfirmed."}]}}}]}],
        }

    def tearDown(self):
        self.temp.cleanup()

    def write(self, path, content):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")

    def save(self):
        self.write("evaluation.json", json.dumps(self.document, ensure_ascii=False, indent=2))

    def run_report(self):
        self.save()
        return evaluation.evaluate(self.manifest_path)

    def test_passes_preserve_evidence_and_separate_automatic_from_reviewed(self):
        report = self.run_report()
        run = report["runs"][0]
        self.assertEqual(run["counts"], {"pass": 4, "fail": 0, "not_run": 0})
        self.assertEqual(run["by_method"]["automatic"]["pass"], 3)
        self.assertEqual(run["by_category"]["question_quality"]["pass"], 1)
        last = run["cases"][0]["checks"][-1]
        self.assertEqual(last["question_ids"], ["q-uncertainty"])
        self.assertEqual(len(last["evidence"][0]["sha256"]), 64)
        self.assertEqual(report["comparisons"], [])

    def test_missing_artifact_and_empty_negative_assertion_do_not_pass(self):
        self.document["runs"][0]["cases"][0]["artifacts"]["output"] = "missing.md"
        self.document["runs"][0]["cases"][0]["reviews"] = {}
        report = self.run_report()
        self.assertEqual(report["runs"][0]["counts"], {"pass": 1, "fail": 2, "not_run": 1})
        self.write("missing.md", "")
        self.assertEqual(self.run_report()["runs"][0]["counts"]["fail"], 2)

    def test_unexecuted_case_preserves_all_checks_as_not_run(self):
        self.document["runs"][0]["cases"] = [{"case_id": "uncertainty", "status": "not_run", "reason": "The required host was unavailable."}]
        report = self.run_report()
        self.assertEqual(report["runs"][0]["counts"], {"pass": 0, "fail": 0, "not_run": 4})
        self.document["runs"][0]["cases"] = []
        self.assertEqual(self.run_report()["runs"][0]["counts"]["not_run"], 4)

    def test_missing_and_explicitly_unperformed_reviews_stay_not_run(self):
        record = self.document["runs"][0]["cases"][0]
        record["reviews"] = {}
        self.assertEqual(self.run_report()["runs"][0]["counts"]["not_run"], 1)
        record["reviews"]["useful"] = {"status": "not_run", "reason": "Reviewer has not inspected this result."}
        self.assertEqual(self.run_report()["runs"][0]["counts"]["not_run"], 1)

    def test_review_pass_requires_real_evidence_and_matching_quote(self):
        review = self.document["runs"][0]["cases"][0]["reviews"]["useful"]
        review["evidence"] = []
        with self.assertRaisesRegex(evaluation.EvaluationError, "Review evidence"):
            self.run_report()
        review["evidence"] = [{"artifact": "output", "quote": "A passage that was never present"}]
        with self.assertRaisesRegex(evaluation.EvaluationError, "quote was not found"):
            self.run_report()
        review["evidence"] = [{"artifact": "missing", "note": "Claimed inspection"}]
        with self.assertRaisesRegex(evaluation.EvaluationError, "not registered"):
            self.run_report()

    def test_nontext_inspection_is_labeled_as_reviewed_evidence(self):
        (self.root / "outputs/image.png").write_bytes(b"\x89PNG\r\n\xff")
        record = self.document["runs"][0]["cases"][0]
        record["artifacts"]["image"] = "outputs/image.png"
        record["reviews"]["useful"]["evidence"] = [{"artifact": "image", "note": "Synthetic fixture: an inspection note is a reviewer claim, not an automated image judgment."}]
        result = self.run_report()["runs"][0]["cases"][0]["checks"][-1]
        self.assertEqual(result["method"], "reviewed")
        self.assertIn("note", result["evidence"][0])

    def test_traversal_and_absolute_paths_are_rejected_even_for_not_run_case(self):
        for relative in ("../outside.md", "C:/private/file.txt", "/private/file.txt", "..\\outside.md"):
            with self.subTest(path=relative):
                record = self.document["runs"][0]["cases"][0]
                record.update(status="not_run", reason="Pending", artifacts={"output": relative})
                with self.assertRaises(evaluation.EvaluationError):
                    self.run_report()

    def test_symlink_cannot_reference_outside_the_suite(self):
        outside = self.parent / "outside.md"
        outside.write_text("Private fixture", encoding="utf-8")
        link = self.root / "linked.md"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("This environment does not permit symlink creation")
        self.document["cases"][0]["input_files"] = ["linked.md"]
        with self.assertRaisesRegex(evaluation.EvaluationError, "escapes"):
            self.run_report()

    def test_json_boolean_is_not_equal_to_number_and_missing_path_fails(self):
        check = self.document["cases"][0]["checks"][2]
        check["expected"] = 0
        self.assertEqual(self.run_report()["runs"][0]["counts"]["fail"], 1)
        check["path"] = ["facts", 3, "title"]
        self.assertEqual(self.run_report()["runs"][0]["counts"]["fail"], 1)
        check.update(path=["facts", 0, "title"], expected="한글")
        self.assertEqual(self.run_report()["runs"][0]["counts"]["fail"], 0)

    def test_question_quality_is_not_scored_by_text_matches(self):
        self.document["cases"][0]["checks"][0]["category"] = "question_quality"
        with self.assertRaisesRegex(evaluation.EvaluationError, "reviewed judgment"):
            self.run_report()

    def add_baseline(self):
        baseline = copy.deepcopy(self.document["runs"][0])
        baseline.update(id="baseline", variant="baseline")
        self.document["runs"].append(baseline)
        return baseline

    def known_context(self):
        return {"model": "synthetic-test-model-v1", "effort": "high", "tools": ["file-read-v1", "search-v1"], "budget": "max_tokens=4000; max_tool_calls=8"}

    def test_unknown_or_different_context_prevents_comparison(self):
        baseline = self.add_baseline()
        pair = self.run_report()["comparisons"][0]
        self.assertFalse(pair["comparable"])
        self.assertEqual(len(pair["reasons"]), 4)
        self.document["runs"][0]["context"] = self.known_context()
        baseline["context"] = self.known_context()
        for key, value in (("model", "different"), ("effort", "low"), ("tools", ["file-read-v1"]), ("budget", "max_tokens=2000")):
            with self.subTest(field=key):
                baseline["context"] = self.known_context()
                baseline["context"][key] = value
                pair = self.run_report()["comparisons"][0]
                self.assertFalse(pair["comparable"])
                self.assertIn(key, pair["reasons"][0])

    def test_comparison_uses_only_exercised_pairs_and_reports_assertion_changes(self):
        baseline = self.add_baseline()
        self.document["runs"][0]["context"] = self.known_context()
        baseline["context"] = self.known_context()
        baseline["context"]["tools"].reverse()
        baseline["cases"][0]["artifacts"]["output"] = "outputs/baseline.md"
        baseline["cases"][0]["reviews"] = {}
        self.write("outputs/baseline.md", "The release ships on November 20.")
        pair = self.run_report()["comparisons"][0]
        self.assertTrue(pair["comparable"])
        self.assertEqual(len(pair["paired_checks"]), 3)
        self.assertEqual(pair["improved"], 2)
        self.assertEqual(pair["regressed"], 0)
        baseline["cases"] = []
        self.assertFalse(self.run_report()["comparisons"][0]["comparable"])

    def test_invalid_or_ambiguous_records_cannot_silently_drop_checks(self):
        original = copy.deepcopy(self.document)
        for change in (lambda: self.document["cases"].append(copy.deepcopy(self.document["cases"][0])),
                       lambda: self.document["runs"][0]["cases"][0].update(case_id="unknown"),
                       lambda: self.document["runs"][0]["cases"][0]["reviews"].update(unknown={"status": "pass"}),
                       lambda: self.document["cases"][0]["checks"][0].update(kind="execute")):
            self.document = copy.deepcopy(original)
            change()
            with self.assertRaises(evaluation.EvaluationError):
                self.run_report()

    def test_report_cannot_overwrite_inputs_or_escape_and_is_reproducible(self):
        report = self.run_report()
        with self.assertRaisesRegex(evaluation.EvaluationError, "overwrite a source"):
            evaluation.write_report(self.manifest_path, self.root / "evaluation", report, True)
        with self.assertRaisesRegex(evaluation.EvaluationError, "inside"):
            evaluation.write_report(self.manifest_path, self.parent / "outside", report)
        paths = evaluation.write_report(self.manifest_path, self.root / "reports/result", report)
        first = [Path(path).read_bytes() for path in paths]
        evaluation.write_report(self.manifest_path, self.root / "reports/result", self.run_report())
        self.assertEqual(first, [Path(path).read_bytes() for path in paths])
        self.assertIn("No comparative quality claim", Path(paths[1]).read_text(encoding="utf-8"))

    def test_cli_distinguishes_pass_failure_invalid_and_incomplete(self):
        original = copy.deepcopy(self.document)
        for expected in (0, 1, 2, 3):
            self.document = copy.deepcopy(original)
            if expected == 1:
                self.document["cases"][0]["checks"][0]["text"] = "absent expected text"
            elif expected == 2:
                self.document["schema_version"] = 200
            elif expected == 3:
                self.document["runs"][0]["cases"] = []
            self.save()
            result = subprocess.run([sys.executable, "-B", str(PACKAGE / "scripts/evaluate_skill.py"), "--manifest", str(self.manifest_path),
                                     "--out", str(self.root / f"report-{expected}")], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, expected, result.stderr)
            if expected != 2:
                self.assertTrue((self.root / f"report-{expected}.md").is_file())


if __name__ == "__main__":
    unittest.main()
