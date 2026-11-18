"""One-rule maintenance plans should stay conservative when traceability is incomplete."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "any-skill-builder" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from plan_change import plan_change
from prepare_evaluation import prepare


class PlanChangeTests(unittest.TestCase):
    def setUp(self):
        cache = os.environ.get("SKILL_BUILDER_TEST_TMPDIR")
        if cache:
            Path(cache).mkdir(parents=True, exist_ok=True)
        temp = tempfile.TemporaryDirectory(dir=cache)
        self.addCleanup(temp.cleanup)
        self.run = Path(temp.name)
        self.design = {"features": [
            {"id": "merge", "files": ["scripts/merge.py"], "requirement_ids": ["latest", "conflict"],
             "question_ids": ["format"], "evaluation_ids": ["cancel", "reopen", "pretty"]},
            {"id": "errors", "files": ["scripts/merge.py", "README.md"], "requirement_ids": [],
             "question_ids": ["failure"], "evaluation_ids": ["invalid"]},
            {"id": "guide", "files": ["guide.md"], "requirement_ids": [], "question_ids": ["help"],
             "evaluation_ids": ["help"]}]}
        self.plan = {"schema_version": 1, "name": "Maintenance fixture", "cases": []}
        for case_id, req, question in [("cancel", ["conflict"], []), ("reopen", ["latest"], []),
                                       ("pretty", [], ["format"]), ("invalid", [], ["failure"]), ("help", [], ["help"])]:
            self.plan["cases"].append({"id": case_id, "requirement_ids": req, "question_ids": question,
                                       "prompt": "Process the supplied records.", "checks": [
                                           {"id": "output", "kind": "review", "category": "skill_output",
                                            "criterion": "Keep the private grading key here."}]})
        self.save()

    def save(self):
        for name, data in [("design.json", self.design), ("plan.json", self.plan)]:
            (self.run / name).write_text(json.dumps(data, indent=2), encoding="utf-8")

    def cli(self, *args):
        return subprocess.run([sys.executable, "-B", str(SCRIPTS / "plan_change.py"),
                               "--run", str(self.run), *args], capture_output=True, text=True)

    def test_only_change_explicit_invariants_and_shared_file_cases(self):
        before = {p: p.read_bytes() for p in self.run.iterdir()}
        result = self.cli("--requirement", "conflict", "--keep-requirement", "latest")
        self.assertEqual(result.returncode, 0, result.stderr)
        out = json.loads(result.stdout)
        self.assertEqual(out["scope"], "mapped_cases")
        self.assertEqual(out["features_to_change"], ["merge"])
        self.assertEqual(out["files_to_inspect_for_edits"], ["scripts/merge.py"])
        self.assertEqual(out["shared_files_by_regression_feature"], {"errors": ["scripts/merge.py"]})
        self.assertEqual(out["cases_tracing_change"], ["cancel"])
        self.assertEqual(out["regression_cases"], ["invalid", "reopen"])
        self.assertEqual(out["retest_cases"], ["cancel", "invalid", "reopen"])
        self.assertNotIn("private grading key", result.stdout)
        self.assertEqual(before, {p: p.read_bytes() for p in self.run.iterdir()})

    def test_question_and_explicit_case_survive_preparation_without_leaking_keys(self):
        # Prepare the actual extended plan and exercise its normal task-packet entry point.
        skill = self.run / "skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text("Handle each record.")
        iteration = self.run / "iteration"
        prepare(self.run / "plan.json", skill, iteration)
        packet = (iteration / "tasks/execute-candidate-001.md").read_text(encoding="utf-8")
        self.assertNotIn("private grading key", packet)
        self.assertNotIn("conflict", packet)
        out = plan_change(self.run, "question_ids", "format", keep_cases=["help"])
        self.assertEqual(out["cases_tracing_change"], ["pretty"])
        self.assertEqual(out["retest_cases"], ["help", "invalid", "pretty"])
        frozen = json.loads((iteration / "plan.json").read_bytes())
        self.assertEqual(frozen, self.plan)

    def test_legacy_feature_only_with_partial_check_annotations(self):
        for case in self.plan["cases"]:
            del case["requirement_ids"]
        self.plan["cases"][0]["checks"][0]["requirement_ids"] = ["conflict"]
        self.save()
        out = plan_change(self.run, "requirement_ids", "conflict")
        self.assertEqual(out["cases_tracing_change"], ["cancel"])
        self.assertEqual(out["feature_fallback_cases"], ["pretty", "reopen"])
        self.assertEqual(out["retest_cases"], ["cancel", "invalid", "pretty", "reopen"])
        # A partially annotated case is not evidence that other cases can be dropped.
        self.plan["cases"][0]["checks"][0].pop("requirement_ids")
        self.save()
        out = plan_change(self.run, "requirement_ids", "conflict")
        self.assertEqual(out["feature_fallback_cases"], ["cancel", "pretty", "reopen"])
        self.assertTrue(out["coverage_notes"])

    def test_legacy_source_only_without_a_plan(self):
        feature = self.design["features"][0]
        feature.pop("requirement_ids")
        feature["source_ids"] = ["desk-rules"]
        self.save()
        (self.run / "plan.json").unlink()
        out = plan_change(self.run, "requirement_ids", "desk-rules")
        self.assertEqual(out["features_to_change"], [])
        self.assertEqual(out["scope"], "full_suite_review")
        self.assertEqual(out["retest_cases"], sorted(case["id"] for case in self.plan["cases"]))
        self.assertIn("scripts/merge.py", out["mapped_files_for_full_review"])

    def test_orphan_cases_stale_case_ids_and_unknown_invariants(self):
        self.design["features"][0]["evaluation_ids"] = ["old", "reopen", "pretty"]
        self.save()
        out = plan_change(self.run, "requirement_ids", "conflict", keep=[("question_ids", "unknown")])
        self.assertEqual(out["scope"], "full_suite_review")
        self.assertIn("old", out["design_cases_missing_from_plan"])
        self.assertEqual(out["retest_cases"], sorted(case["id"] for case in self.plan["cases"]))
        self.assertTrue(any("unknown" in reason for reason in out["coverage_notes"]))

    def test_explicit_plan_or_clear_error_on_ambiguity(self):
        other = self.run / "evaluation-plan.json"
        other.write_text(json.dumps(self.plan), encoding="utf-8")
        ambiguous = self.cli("--question", "format")
        self.assertEqual(ambiguous.returncode, 2)
        self.assertIn("--plan", ambiguous.stderr)
        explicit = self.cli("--plan", str(other), "--question", "format", "--keep-question", "help")
        self.assertEqual(explicit.returncode, 0, explicit.stderr)
        self.assertEqual(json.loads(explicit.stdout)["regression_cases"], ["help", "invalid"])
        bad = self.cli("--plan", str(other), "--question", "format", "--keep-case", "missing")
        self.assertEqual(bad.returncode, 2)
        self.assertIn("missing", bad.stderr)
        self.assertEqual(self.cli("--plan", str(other), "--question", "format", "--keep-question", "format").returncode, 2)

    def test_missing_design_and_bad_trace_metadata(self):
        (self.run / "design.json").unlink()
        out = plan_change(self.run, "question_ids", "format")
        self.assertEqual(out["scope"], "full_suite_review")
        self.assertEqual(len(out["retest_cases"]), 5)
        self.design["features"][0]["files"] = ["../private"]
        self.save()
        self.assertEqual(self.cli("--question", "format").returncode, 2)
        self.plan["cases"][0]["question_ids"] = "format"
        self.save()
        self.assertIn("list", self.cli("--question", "format").stderr)


if __name__ == "__main__":
    unittest.main()
