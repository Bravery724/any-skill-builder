"""Prepare workshop tasks and replay evidence-backed grades on archived and edited memos."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest

FIXTURES = Path(__file__).resolve().parent / "fixtures/workshop-handoff"
sys.path.insert(0, str(FIXTURES.parents[2] / "any-skill-builder/scripts"))
import evaluate_skill
import prepare_evaluation


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


class WorkshopHandoffTests(unittest.TestCase):
    def setUp(self):
        cache = os.environ.get("SKILL_BUILDER_TEST_TMPDIR")
        if cache:
            Path(cache).mkdir(parents=True, exist_ok=True)
        temp = tempfile.TemporaryDirectory(prefix="workshop-handoff-", dir=cache)
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        skill = root / "candidate"
        skill.mkdir()
        (skill / "SKILL.md").write_text("Placeholder snapshot for offline calibration.", encoding="utf-8")
        self.iteration = root / "iteration"
        prepare_evaluation.prepare(FIXTURES / "plan.json", skill, self.iteration)
        self.manifest_path = self.iteration / "evaluation.json"
        self.prepared = read_json(self.manifest_path)
        self.calibration = read_json(FIXTURES / "calibration.json")

    def grade(self, case_id, control, *, reviewed_as=None, suffix=""):
        document = copy.deepcopy(self.prepared)
        records = document["runs"][0]["cases"]
        index, record = next((index, record) for index, record in enumerate(records, 1)
                             if record["case_id"] == case_id)
        relative = f"results/candidate/case-{index:03d}/output.md"
        output = self.iteration / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        memo = (FIXTURES / "controls" / f"{control}.md").read_text(encoding="utf-8")
        output.write_text(memo + suffix, encoding="utf-8")
        record.update(status="completed", artifacts={"output": relative}, reviews={
            item["check"]: {
                "status": item["status"], "reason": item["reason"], "reviewer": "Calibration fixture author",
                "evidence": [{"artifact": "output", "quote": item["quote"]}],
            }
            for item in self.calibration if reviewed_as in item["controls"]
        })
        record.pop("reason")
        self.manifest_path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
        case = evaluate_skill.evaluate(self.manifest_path)["runs"][0]["cases"][index - 1]
        return {check["id"]: check["status"] for check in case["checks"]}

    def test_historical_failures_fixes_and_cross_theme_controls(self):
        failures = {
            "pottery-first": {"count-by-theme", "owner-literal", "owner-on-action"},
            "woodwork-first": {"owner-literal", "owner-on-action"},
            "pottery-revised": set(),
            "woodwork-revised": set(),
            "dyeing-card-counts": {"count-by-theme"},
            "dyeing-swapped": {"count-by-theme"},
            "dyeing-misplaced": {"owner-on-action", "assigned-action", "delegated-action", "proposal-status"},
            "dyeing-correct": set(),
        }
        self.assertEqual(set(failures), {path.stem for path in (FIXTURES / "controls").glob("*.md")})
        for control, expected in failures.items():
            with self.subTest(control=control):
                statuses = self.grade(control.split("-")[0], control, reviewed_as=control)
                self.assertNotIn("not_run", statuses.values())
                self.assertEqual({key for key, status in statuses.items() if status == "fail"}, expected)

    def test_presence_of_owner_label_and_anonymity_do_not_grade_the_relationships(self):
        for control in ("dyeing-card-counts", "dyeing-swapped", "dyeing-misplaced"):
            with self.subTest(control=control):
                statuses = self.grade("dyeing", control)
                self.assertIn("owner-literal", statuses)
                self.assertNotIn("fail", statuses.values())
                self.assertEqual({key for key, status in statuses.items() if status == "not_run"},
                                 {"count-by-theme", "owner-on-action", "assigned-action", "delegated-action", "proposal-status"})

    def test_stale_good_review_cannot_certify_moved_counts_or_owner_labels(self):
        for actual in ("dyeing-card-counts", "dyeing-swapped", "dyeing-misplaced"):
            with self.subTest(control=actual), self.assertRaisesRegex(evaluate_skill.EvaluationError, "quote was not found"):
                self.grade("dyeing", actual, reviewed_as="dyeing-correct")

    def test_correct_counts_and_owners_still_fail_if_source_identities_leak(self):
        for case in self.prepared["cases"]:
            case_id = case["id"]
            control = case_id + ("-correct" if case_id == "dyeing" else "-revised")
            notes = (self.iteration / case["input_files"][0]).read_text(encoding="utf-8")
            identities = {value for pair in re.findall(r"([PRW]\d+)\(([가-힣]+)\)", notes) for value in pair}
            redactions = {c["text"]: c["id"] for c in case["checks"] if c["kind"] == "not_contains"}
            self.assertTrue(identities)
            self.assertEqual(set(redactions), identities)
            for value, check in redactions.items():
                with self.subTest(case=case_id, leaked=value):
                    statuses = self.grade(case_id, control, reviewed_as=control, suffix=f"\n기록 참고 · {value}\n")
                    self.assertEqual({key for key, status in statuses.items() if status != "pass"}, {check})

    def test_forward_packets_keep_the_criteria_and_calibration_out_of_executor_inputs(self):
        cases = read_json(FIXTURES / "plan.json")["cases"]
        inputs = self.iteration / "inputs"
        self.assertEqual({path.name for path in inputs.iterdir()}, {"pottery.txt", "woodwork.txt", "dyeing.txt"})
        report = evaluate_skill.evaluate(self.manifest_path)
        for index, case in enumerate(cases, 1):
            with self.subTest(case=case["id"]):
                raw, = case["input_files"]
                self.assertEqual((inputs / raw).read_bytes(), (FIXTURES / raw).read_bytes())
                packet = (self.iteration / f"tasks/execute-candidate-{index:03d}.md").read_text(encoding="utf-8")
                self.assertIn(case["prompt"], packet)
                self.assertIn(str(inputs / raw), packet)
                self.assertNotIn("calibration.json", packet)
                for check in case["checks"]:
                    if check["kind"] == "review":
                        self.assertNotIn(check["criterion"], packet)
                self.assertEqual(report["runs"][0]["cases"][index - 1]["counts"]["not_run"], len(case["checks"]))


if __name__ == "__main__":
    unittest.main()
