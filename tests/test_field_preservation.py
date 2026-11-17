"""Replay reviewed handoff outputs and prepare the same two tasks for a new skill."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

FIXTURES = Path(__file__).resolve().parent / "fixtures/field-preservation"
SCRIPTS = FIXTURES.parents[2] / "any-skill-builder/scripts"
sys.path.insert(0, str(SCRIPTS))
import evaluate_skill
import prepare_evaluation


class FieldPreservationTests(unittest.TestCase):
    def setUp(self):
        cache = os.environ.get("SKILL_BUILDER_TEST_TMPDIR")
        if cache:
            Path(cache).mkdir(parents=True, exist_ok=True)
        temp = tempfile.TemporaryDirectory(prefix="handoff-cases-", dir=cache)
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.suite = self.root / "suite"
        shutil.copytree(FIXTURES, self.suite)
        self.plan = json.loads((self.suite / "plan.json").read_text(encoding="utf-8"))
        controls = json.loads((self.suite / "calibration.json").read_text(encoding="utf-8"))
        self.controls = {control["output"]: control for control in controls}

    def score(self, output, review=None):
        sample = self.controls[output]
        case = next(case for case in self.plan["cases"] if case["id"] == sample["case"])
        record = {"case_id": case["id"], "status": "completed", "artifacts": {"output": f"controls/{output}.md"}}
        if review:
            record["reviews"] = {review["check"]: {
                "status": review["status"], "reason": review["reason"], "reviewer": "Calibration fixture author",
                "evidence": [{"artifact": "output", "quote": review["quote"]}],
            }}
        manifest = {**self.plan, "cases": [case],
                    "runs": [{"id": "calibration", "variant": "with_skill", "cases": [record]}]}
        path = self.suite / "evaluation.json"
        path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        return evaluate_skill.evaluate(path)["runs"][0]["cases"][0]["checks"]

    def test_calibration_preserves_archived_failures_and_adversarial_controls(self):
        expected = {
            "ops-aliases": {"minseo-present", "jinwoo-present", "source-to-claim"},
            "ops-attributed": set(),
            "ops-swapped": {"source-to-claim"},
            "db-unnamed": {"action-to-recipients"},
            "db-addressed": set(),
            "db-wrong-recipient": {"action-to-recipients"},
        }
        self.assertEqual(set(self.controls), set(expected))
        for output, failures in expected.items():
            with self.subTest(output=output):
                checks = self.score(output, self.controls[output])
                self.assertEqual({c["id"] for c in checks if c["status"] == "fail"}, failures)
                self.assertTrue(all(c["status"] in {"pass", "fail"} for c in checks))

    def test_names_and_address_literals_cannot_settle_relationships(self):
        for output in ("ops-swapped", "db-unnamed", "db-wrong-recipient"):
            with self.subTest(output=output):
                checks = self.score(output)
                self.assertTrue(all(c["status"] == "pass" for c in checks if c["method"] == "automatic"))
                pending = {c["id"] for c in checks if c["status"] == "not_run"}
                self.assertEqual(pending, {self.controls[output]["check"]})

    def test_passing_evidence_cannot_be_replayed_after_names_are_swapped(self):
        for actual, stale in (("ops-swapped", "ops-attributed"), ("db-wrong-recipient", "db-addressed")):
            with self.subTest(output=actual), self.assertRaisesRegex(evaluate_skill.EvaluationError, "quote was not found"):
                self.score(actual, self.controls[stale])

    def test_forward_packets_use_original_requests_and_raw_notes_without_calibration(self):
        skill = self.root / "candidate"
        skill.mkdir()
        (skill / "SKILL.md").write_text("Use the supplied notes to write a shift handoff.", encoding="utf-8")
        iteration = self.root / "next"
        prepare_evaluation.prepare(self.suite / "plan.json", skill, iteration)
        report = evaluate_skill.evaluate(iteration / "evaluation.json")
        for index, case in enumerate(self.plan["cases"], 1):
            with self.subTest(case=case["id"]):
                result = report["runs"][0]["cases"][index - 1]
                self.assertEqual(result["counts"]["not_run"], len(case["checks"]))
                packet = (iteration / f"tasks/execute-candidate-{index:03d}.md").read_text(encoding="utf-8")
                self.assertIn(case["prompt"], packet)
                raw_input, = case["input_files"]
                self.assertEqual((iteration / "inputs" / raw_input).read_bytes(), (self.suite / raw_input).read_bytes())
                self.assertIn(str(iteration / "inputs" / raw_input), packet)
        self.assertEqual({path.name for path in (iteration / "inputs").iterdir()}, {"ops.txt", "db.txt"})


if __name__ == "__main__":
    unittest.main()
