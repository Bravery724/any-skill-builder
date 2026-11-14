"""Evaluation preparation and review records preserve evidence without inventing outcomes."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

PACKAGE = Path(__file__).resolve().parents[1] / "any-skill-builder"
sys.path.insert(0, str(PACKAGE / "scripts"))
import evaluate_skill as evaluation
import prepare_evaluation as preparation


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        cache = os.environ.get("SKILL_BUILDER_TEST_TMPDIR")
        if cache:
            Path(cache).mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="evaluation-workflow-", dir=cache)
        self.root = Path(self.temp.name)
        self.skill = self.root / "skill"
        self.write("skill/SKILL.md", "---\nname: note-summary\ndescription: Summarize supplied notes.\n---\nPreserve unknown facts.\n")
        self.write("plan/inputs/notes.md", "The date is unconfirmed.")
        self.plan = {"schema_version": 1, "name": "Fictional notes", "cases": [
            {"id": "first", "prompt": "Write a useful update.", "input_files": ["inputs/notes.md"],
             "checks": [{"id": "preserve", "category": "skill_output", "kind": "contains", "artifact": "output", "text": "unconfirmed"}]},
            {"id": "second", "prompt": "Write another useful update.", "input_files": ["inputs/notes.md"],
             "checks": [{"id": "preserve", "category": "skill_output", "kind": "contains", "artifact": "output", "text": "unconfirmed"}]},
        ]}
        self.plan_path = self.root / "plan/plan.json"
        self.plan_path.write_text(json.dumps(self.plan), encoding="utf-8")
        self.out = self.root / "iterations/one"

    def tearDown(self):
        self.temp.cleanup()

    def write(self, relative, value):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")
        return path

    def prepare(self, **kwargs):
        preparation.prepare(self.plan_path, self.skill, self.out, **kwargs)
        self.manifest_path = self.out / "evaluation.json"
        self.document = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        return self.document

    def report(self):
        self.manifest_path.write_text(json.dumps(self.document), encoding="utf-8")
        return evaluation.evaluate(self.manifest_path)

    def completed(self):
        self.prepare()
        for index, record in enumerate(self.document["runs"][0]["cases"], 1):
            directory = f"results/candidate/case-{index:03d}"
            for filename, content in [("output.md", "The date is unconfirmed."),
                                      ("execution.md", "Read supplied notes. Normalized whitespace and preserved uncertainty."),
                                      ("normalize.py", "def normalize(value):\n    return ' '.join(value.split())\n")]:
                path = self.out / directory / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            record.update(status="completed", artifacts={"output": directory + "/output.md", "log": directory + "/execution.md", "helper": directory + "/normalize.py"},
                          execution={"executor": "Actual author", "relationship": "self", "transcript": "log"},
                          eval_feedback={"status": "completed", "reviewer": "Actual author", "relationship": "self", "summary": "Reviewed task and actual output; no specific missing criterion found.", "findings": []})
            record.pop("reason")
        self.document["reuse_review"] = {"status": "completed", "reviewer": "Actual author", "relationship": "self",
                                        "summary": "Reviewed both observable execution logs.", "inspected_runs": ["candidate"], "items": []}

    def reuse(self, decision="extract"):
        item = {"id": "whitespace", "operation": "Normalize whitespace", "decision": decision, "reason": "Both completed tasks use this operation.",
                "occurrences": [{"run_id": "candidate", "case_id": cid, "artifact": "log", "quote": "Normalized whitespace"} for cid in ("first", "second")]}
        if decision == "extract":
            item.update(helper={"run_id": "candidate", "case_id": "second", "artifact": "helper"},
                        validation=[{"run_id": "candidate", "case_id": "second", "check_id": "preserve"}])
        self.document["reuse_review"]["items"] = [item]
        return item

    def cli(self):
        self.report()
        return subprocess.run([sys.executable, "-B", str(PACKAGE / "scripts/evaluate_skill.py"), "--manifest", str(self.manifest_path),
                               "--out", str(self.out / "report"), "--overwrite"], capture_output=True, text=True, encoding="utf-8")

    def test_preparation_copies_inputs_snapshots_and_separates_execution_from_grading(self):
        self.prepare(without_skill=True)
        report = self.report()
        self.assertEqual(report["workflow"]["disposition"], "incomplete")
        self.assertEqual(len(report["runs"]), 2)
        self.assertEqual(report["runs"][0]["counts"], {"pass": 0, "fail": 0, "not_run": 2})
        packet = (self.out / "tasks/execute-candidate-001.md").read_text(encoding="utf-8")
        self.assertIn(self.plan["cases"][0]["prompt"], packet)
        self.assertNotIn('"checks"', packet)
        self.assertNotIn("unconfirmed", packet)
        self.assertIn("without consulting", (self.out / "tasks/execute-baseline-001.md").read_text(encoding="utf-8"))
        self.assertEqual((self.out / "snapshots/candidate/SKILL.md").read_bytes(), (self.skill / "SKILL.md").read_bytes())
        self.assertFalse(list(self.out.rglob("*.html")))

    def test_old_skill_baseline_is_a_separate_snapshot_and_iteration_is_never_overwritten(self):
        old = self.root / "old-skill"
        self.write("old-skill/SKILL.md", "Original instructions.")
        self.prepare(baseline_skill=old)
        self.assertEqual((self.out / "snapshots/baseline/SKILL.md").read_text(), "Original instructions.")
        before = self.manifest_path.read_bytes()
        with self.assertRaisesRegex(evaluation.EvaluationError, "already exists"):
            preparation.prepare(self.plan_path, self.skill, self.out)
        self.assertEqual(self.manifest_path.read_bytes(), before)

    def test_linked_inputs_preserve_original_tree_bytes_and_packet_mapping(self):
        html = self.write("plan/site/index.html", '<link rel="stylesheet" href="./style.css"><img src="../media/cover.svg">')
        css = self.write("plan/site/style.css", "body { color: #123456 }")
        image = self.write("plan/media/cover.svg", '<svg xmlns="http://www.w3.org/2000/svg"/>')
        self.write("plan/site/private.txt", "An unrelated file must not be copied.")
        relative = ["site/index.html", "site/style.css", "media/cover.svg"]
        self.plan["cases"][0]["input_files"] = relative
        self.plan_path.write_text(json.dumps(self.plan), encoding="utf-8")
        self.prepare()
        self.assertEqual(self.document["cases"][0]["input_files"], ["inputs/" + name for name in relative])
        self.assertEqual(self.document["cases"][0]["input_mapping"],
                         [{"original": name, "snapshot": "inputs/" + name} for name in relative])
        for source, name in zip((html, css, image), relative):
            self.assertEqual(source.read_bytes(), (self.out / "inputs" / name).read_bytes())
        copied_html = self.out / "inputs/site/index.html"
        self.assertTrue((copied_html.parent / "./style.css").is_file())
        self.assertTrue((copied_html.parent / "../media/cover.svg").is_file())
        self.assertFalse((copied_html.parent / "private.txt").exists())
        packet = (self.out / "tasks/execute-candidate-001.md").read_text(encoding="utf-8")
        self.assertIn(f"site/index.html -> {copied_html}", packet)
        self.assertEqual(self.document["runs"][0]["skill_snapshot"], "candidate")

    def test_repeated_inputs_share_one_snapshot_without_renaming_equal_basenames(self):
        self.write("plan/other/notes.md", "A different note.")
        self.plan["cases"][1]["input_files"].append("other/notes.md")
        self.plan_path.write_text(json.dumps(self.plan), encoding="utf-8")
        self.prepare()
        inventory = next(item for item in self.document["snapshots"] if item["id"] == "inputs")
        self.assertEqual(len(inventory["files"]), 2)
        self.assertEqual(self.document["cases"][0]["input_files"][0], "inputs/inputs/notes.md")
        self.assertEqual(self.document["cases"][1]["input_files"], ["inputs/inputs/notes.md", "inputs/other/notes.md"])

    def test_noncanonical_input_aliases_and_case_collisions_are_rejected(self):
        for alias in ("./inputs/notes.md", "inputs//notes.md", "inputs/./notes.md",
                      "INPUTS/notes.md", "inputs/NOTES.md", "inputs/notes.md:stream"):
            with self.subTest(alias=alias):
                self.plan["cases"][0]["input_files"] = ["inputs/notes.md", alias]
                self.plan_path.write_text(json.dumps(self.plan), encoding="utf-8")
                with self.assertRaises(evaluation.EvaluationError):
                    preparation.prepare(self.plan_path, self.skill, self.out)
                self.assertFalse(self.out.exists())

    def test_input_symlink_is_rejected_without_copying_its_target(self):
        link = self.root / "plan/linked.md"
        try:
            link.symlink_to(self.root / "plan/inputs/notes.md")
        except OSError:
            self.skipTest("Creating symlinks requires platform support or permission.")
        self.plan["cases"][0]["input_files"] = ["linked.md"]
        self.plan_path.write_text(json.dumps(self.plan), encoding="utf-8")
        with self.assertRaisesRegex(evaluation.EvaluationError, "symbolic links"):
            preparation.prepare(self.plan_path, self.skill, self.out)
        self.assertFalse(self.out.exists())

    def test_preparation_rejects_nested_targets_and_escaping_inputs_without_creating_output(self):
        for output in (self.skill / "iteration", self.root / "plan/inputs/iteration"):
            with self.subTest(output=output), self.assertRaisesRegex(evaluation.EvaluationError, "outside"):
                preparation.prepare(self.plan_path, self.skill, output)
            self.assertFalse(output.exists())
        self.plan["cases"][0]["input_files"] = ["../skill/SKILL.md"]
        self.plan_path.write_text(json.dumps(self.plan))
        with self.assertRaisesRegex(evaluation.EvaluationError, "relative path"):
            preparation.prepare(self.plan_path, self.skill, self.out)
        self.assertFalse(self.out.exists())

    def test_preparation_refuses_private_runtime_files_and_completed_run_plans(self):
        self.write("skill/.agents/private.md", "Private local information.")
        with self.assertRaisesRegex(evaluation.EvaluationError, "private run"):
            preparation.prepare(self.plan_path, self.skill, self.out)
        self.assertFalse(self.out.exists())
        self.plan["runs"] = [{"id": "fake", "status": "completed"}]
        self.plan_path.write_text(json.dumps(self.plan))
        with self.assertRaisesRegex(evaluation.EvaluationError, "completed run records"):
            preparation.prepare(self.plan_path, self.skill, self.out)

    def test_snapshot_limits_fail_before_creating_destination(self):
        with patch.object(preparation, "MAX_TOTAL_BYTES", 10):
            with self.assertRaisesRegex(evaluation.EvaluationError, "64 MiB"):
                preparation.prepare(self.plan_path, self.skill, self.out)
        self.assertFalse(self.out.exists())

    def test_changed_snapshot_is_rejected_and_report_cannot_overwrite_it(self):
        self.prepare()
        report = self.report()
        with self.assertRaisesRegex(evaluation.EvaluationError, "overwrite a source"):
            evaluation.write_report(self.manifest_path, self.out / "snapshots/candidate/SKILL", report, True)
        (self.out / "snapshots/candidate/SKILL.md").write_text("Changed after preparing.")
        with self.assertRaisesRegex(evaluation.EvaluationError, "Snapshot changed"):
            self.report()

    def test_copied_inputs_are_pinned_to_the_prepared_bytes(self):
        self.prepare()
        self.assertIn("inputs", [item["id"] for item in self.document["snapshots"]])
        copied = self.out / self.document["cases"][0]["input_files"][0]
        copied.write_text("Different facts after execution.")
        with self.assertRaisesRegex(evaluation.EvaluationError, "Snapshot changed"):
            self.report()

    def test_self_review_is_labeled_in_both_reports_and_pending_audit_never_returns_success(self):
        self.completed()
        report = self.report()
        self.assertEqual(report["workflow"]["disposition"], "reviewed")
        self.assertIn("Reviewer: Actual author; declared relationship: self.", evaluation.markdown(report))
        self.document["runs"][0]["cases"][0]["eval_feedback"] = {"status": "not_run", "reason": "Review is pending."}
        result = self.cli()
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertEqual(json.loads(result.stdout)["checks"]["pass"], 2)

    def test_opted_in_workflow_requires_execution_records_for_completed_cases(self):
        self.completed()
        self.document["runs"][0]["cases"][0].pop("execution")
        result = self.cli()
        self.assertEqual(result.returncode, 3, result.stderr)
        workflow = json.loads(result.stdout)["workflow"]
        self.assertEqual(workflow["pending_execution_records"], 1)
        self.assertEqual(workflow["pending_reviews"], 0)
        self.assertEqual(json.loads(result.stdout)["checks"]["pass"], 2)

    def test_weak_check_finding_does_not_change_output_grades_but_requires_attention(self):
        self.completed()
        critique = self.document["runs"][0]["cases"][0]["eval_feedback"]
        critique["findings"] = [{"kind": "weak_check", "check_id": "preserve", "reason": "A wrong update could include this word while inventing another date.",
                                 "evidence": [{"artifact": "output", "quote": "The date is unconfirmed."}]}]
        result = self.cli()
        self.assertEqual(result.returncode, 1, result.stderr)
        report = self.report()
        self.assertEqual(report["runs"][0]["counts"]["pass"], 2)
        self.assertEqual(report["workflow"]["open_findings"], 1)

    def test_bad_audit_evidence_or_unknown_check_is_rejected(self):
        self.completed()
        finding = {"kind": "unsupported_claim", "check_id": "preserve", "reason": "Cannot verify.", "evidence": [{"artifact": "output", "quote": "invented quote"}]}
        self.document["runs"][0]["cases"][0]["eval_feedback"]["findings"] = [finding]
        with self.assertRaisesRegex(evaluation.EvaluationError, "not found"):
            self.report()
        finding["evidence"][0]["quote"] = "unconfirmed"
        finding["check_id"] = "unknown"
        with self.assertRaisesRegex(evaluation.EvaluationError, "unknown check"):
            self.report()

    def test_execution_log_is_required_for_claimed_execution_and_protected_from_report(self):
        self.completed()
        report = self.report()
        prefix = self.out / "results/candidate/case-001/execution"
        with self.assertRaisesRegex(evaluation.EvaluationError, "overwrite a source"):
            evaluation.write_report(self.manifest_path, prefix, report, True)
        self.document["runs"][0]["cases"][0]["execution"]["transcript"] = "not-registered"
        with self.assertRaisesRegex(evaluation.EvaluationError, "not registered"):
            self.report()

    def test_reuse_extract_requires_distinct_real_executions_helper_and_passed_validation(self):
        self.completed()
        item = self.reuse()
        self.assertEqual(self.report()["reuse_review"]["items"][0]["decision"], "extract")
        original = copy.deepcopy(item)
        for mutate in (lambda: item["occurrences"][1].update(case_id="first"),
                       lambda: item.update(helper={"run_id": "candidate", "case_id": "second", "artifact": "missing"}),
                       lambda: item["validation"][0].update(check_id="unknown")):
            item.clear()
            item.update(copy.deepcopy(original))
            mutate()
            with self.assertRaises(evaluation.EvaluationError):
                self.report()
        item.clear()
        item.update(copy.deepcopy(original))
        self.document["runs"][0]["cases"][1]["status"] = "not_run"
        self.document["runs"][0]["cases"][1]["reason"] = "Not executed."
        self.document["runs"][0]["cases"][1].pop("execution")
        self.document["runs"][0]["cases"][1]["eval_feedback"] = {"status": "not_run", "reason": "Not executed."}
        with self.assertRaisesRegex(evaluation.EvaluationError, "known completed"):
            self.report()

    def test_keep_inline_is_valid_and_failed_validation_cannot_support_extraction(self):
        self.completed()
        self.reuse("keep_inline")
        self.assertEqual(self.report()["reuse_review"]["items"][0]["decision"], "keep_inline")
        self.reuse()
        output = self.out / self.document["runs"][0]["cases"][1]["artifacts"]["output"]
        output.write_text("An invented release date.")
        with self.assertRaisesRegex(evaluation.EvaluationError, "actually passed"):
            self.report()

    def test_malformed_ids_and_relationships_are_validation_errors(self):
        self.completed()
        original = copy.deepcopy(self.document)
        for mutate in (lambda: self.document["reuse_review"].update(inspected_runs=[{}]),
                       lambda: self.document["runs"][0]["cases"][0]["execution"].update(relationship="proven"),
                       lambda: self.document["reuse_review"].update(items=[{"id": "test", "operation": "Op", "decision": "extract", "reason": "Test", "occurrences": [{"run_id": [], "case_id": "first", "artifact": "output", "quote": "unconfirmed"}]}])):
            self.document = copy.deepcopy(original)
            mutate()
            with self.assertRaises(evaluation.EvaluationError):
                self.report()

    def test_new_iteration_does_not_modify_the_previous_snapshot(self):
        self.prepare()
        old_bytes = (self.out / "snapshots/candidate/SKILL.md").read_bytes()
        (self.skill / "SKILL.md").write_text("Revised instructions.")
        preparation.prepare(self.plan_path, self.skill, self.root / "iterations/two")
        self.assertEqual((self.out / "snapshots/candidate/SKILL.md").read_bytes(), old_bytes)
        self.assertEqual((self.root / "iterations/two/snapshots/candidate/SKILL.md").read_text(), "Revised instructions.")


if __name__ == "__main__":
    unittest.main()
