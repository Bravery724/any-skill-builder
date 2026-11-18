"""Exercise the normal revision CLI, the successor brief gate, and the actual evaluation preparer."""
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
import uuid

SCRIPTS = Path(__file__).resolve().parents[1] / "any-skill-builder/scripts"
sys.path.insert(0, str(SCRIPTS))
import builder_core as core
import revise_rule
from prepare_evaluation import prepare as prepare_evaluation
from test_decisions import decision_list
from test_question_review import two_question_fixture, completed_example_review


class RuleRevisionTests(unittest.TestCase):
    def setUp(self):
        cache = os.environ.get("SKILL_BUILDER_TEST_TMPDIR")
        if cache:
            Path(cache).mkdir(parents=True, exist_ok=True)
        temp = tempfile.TemporaryDirectory(prefix="revise-", dir=cache)
        self.addCleanup(temp.cleanup)
        self.parent = Path(temp.name)
        self.run = self.parent / "run"
        self.next = self.parent / "next"
        self.form = self.parent / "change.json"
        self.runtime = self.parent / "output" / "example"
        self.runtime.mkdir(parents=True)
        (self.runtime / "SKILL.md").write_text("Use the original rule.", encoding="utf-8")
        self.rule = "Give a draft with attributed gaps."

    def setup_run(self, *, auto=False, fixed=False, conditional=False):
        core.init_workspace(self.run, "Example", mode="auto" if auto else "questionnaire")
        if auto:
            core.set_decisions(self.run, decision_list())
        else:
            fixture = core.read_json(SCRIPTS.parents[1] / "examples/questionnaire.json") if conditional else two_question_fixture()
            core.set_questions(self.run, fixture, rebind_project=True)
            core.answer_one(self.run, "workflow", "draft" if conditional else "clarify")
            core.answer_one(self.run, "outputs", ["progress", "next"])
            if fixed:
                review = completed_example_review(self.run / "questions.json", self.parent / "review.json")
                review["requirements"].append({"id": "source", "statement": "Use the source only.",
                    "basis": {"kind": "user", "reference": "request", "evidence": "Use the source only."}})
                for row in review["question_reviews"] + review["combinations"]:
                    row["requirement_ids"].append("source")
                core.atomic_json(self.run / "question-review.json", review)
                core.atomic_json(self.run / "review-policy.json", {"schema_version": 1,
                    "run_id": core.read_json(self.run / "questions.json")["run_id"], "required": True})
        core.build_brief(self.run)
        self.design = {"skill_path": "../output/example", "features": [
            {"id": "reply", "behavior": "Ask first. Retain the source.", "files": ["SKILL.md"], "evaluation_ids": ["case"]},
            {"id": "layout", "behavior": "Keep headings.", "files": ["SKILL.md"], "evaluation_ids": ["guard"]}]}
        self.plan = {"schema_version": 1, "name": "Revised comparison", "cases": [
            {"id": "case", "prompt": "Process the notes.", "input_files": ["input.txt"], "checks": [
                {"id": "content", "category": "skill_output", "kind": "review", "criterion": "Ask first. Retain the source."},
                {"id": "data", "category": "skill_output", "kind": "json_file_equals", "artifact": "output", "expected_file": "shared.json"}]},
            {"id": "guard", "prompt": "Reformat the notes.", "checks": [
                {"id": "data", "category": "skill_output", "kind": "json_file_equals", "artifact": "output", "expected_file": "shared.json"}]}]}
        for name, doc in (("design.json", self.design), ("plan.json", self.plan), ("shared.json", {"v": False})):
            core.atomic_json(self.run / name, doc)
        (self.run / "input.txt").write_text("private task input", encoding="utf-8")
        (self.run / "iteration").mkdir()
        (self.run / "iteration/report.md").write_text("old passing grade", encoding="utf-8")

    def cli(self, *args, root=None, expected=0):
        command, *rest = args
        proc = subprocess.run([sys.executable, "-B", str(SCRIPTS / "skill_builder.py"), command, "--workspace",
                               str(root or self.run), *map(str, rest)], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, expected, proc.stderr or proc.stdout)
        return json.loads(proc.stdout if expected == 0 else proc.stderr)

    def form_for(self, kind="question", ident="workflow"):
        self.cli("revise-rule", "--" + kind, ident, "--prepare", self.form)
        change = core.read_json(self.form)
        change.update(rule=self.rule, basis="Follow-up request", feature_edits=[{"id": "reply", "replace": "Ask first."}],
                      check_edits=[{"case": "case", "id": "content", "replace": "Ask first."}])
        core.atomic_json(self.form, change)
        return change

    def apply(self, expected=0):
        return self.cli("revise-rule", "--input", self.form, "--destination", self.next, expected=expected)

    def test_legacy_untagged_run_publishes_once_and_preserves_old_evidence(self):
        self.setup_run()
        # Pre-identity data in a completed run must remain byte-for-byte recoverable.
        for name in ("questions.json", "answers.json"):
            record = core.read_json(self.run / name)
            del record["run_id"]
            core.atomic_json(self.run / name, record)
        original = {p: p.read_bytes() for p in self.run.rglob("*") if p.is_file()}
        change = self.form_for()
        change["value"] = "draft"
        exact = '{"v":true,"ratio":0.123456789012345678901}'
        change["check_edits"].append({"case": "case", "id": "data", "expected_json": exact})
        core.atomic_json(self.form, change)
        result = self.apply()
        self.assertFalse(result["pending_brief_items"])
        self.assertEqual(result["runtime_files_to_edit"], ["SKILL.md"])
        self.assertEqual(result["retest_cases"], ["case", "guard"])
        self.assertEqual(self.apply()["event"], "already_published")
        self.assertEqual(original, {p: p.read_bytes() for p in self.run.rglob("*") if p.is_file()})
        current = self.cli("status", "--json", root=self.next)["answers"]
        self.assertEqual(current["answers"]["workflow"]["value"], "draft")
        self.assertEqual(current["history"][-1]["answer"]["value"], "clarify")
        self.assertEqual(current["answers"]["outputs"], core.read_json(self.run / "answers.json")["answers"]["outputs"])
        self.cli("brief", root=self.next)
        self.assertIn(self.rule, (self.next / "build-brief.md").read_text(encoding="utf-8"))
        feature, neighbor = core.read_json(self.next / "design.json")["features"]
        self.assertEqual(feature["behavior"], self.rule + " Retain the source.")
        self.assertEqual(neighbor, self.design["features"][1])
        plan = core.read_json(result["plan"])
        candidate = plan["cases"][0]["checks"]
        self.assertEqual(candidate[0]["criterion"], self.rule + " Retain the source.")
        self.assertEqual(candidate[0]["question_ids"], ["workflow"])
        self.assertEqual(plan["cases"][1], self.plan["cases"][1])
        self.assertNotEqual(candidate[1]["expected_file"], "shared.json")
        self.assertEqual((self.next / "plan" / candidate[1]["expected_file"]).read_text(encoding="utf-8").strip(), exact)
        self.assertEqual(core.read_json(self.next / "plan/shared.json"), {"v": False})
        self.assertFalse((self.next / "iteration").exists())
        iteration = self.parent / "new-iteration"
        prepare_evaluation(result["plan"], result["runtime"], iteration, baseline_skill=result["baseline_runtime"])
        self.assertEqual((iteration / "inputs/input.txt").read_bytes(), (self.run / "input.txt").read_bytes())
        self.assertNotIn(self.rule, (iteration / "tasks/execute-candidate-001.md").read_text(encoding="utf-8"))

    def test_auto_requirement_preserves_neighbors_and_gates_fresh_review(self):
        self.setup_run(auto=True)
        change = self.form_for("requirement", "staged-only")
        change["source_replace"] = "staged changes only"
        core.atomic_json(self.form, change)
        result = self.apply()
        self.assertEqual(set(result["pending_brief_items"]), set(core.DECISION_CHECKS))
        current = core.read_json(self.next / core.DECISIONS_FILE)
        self.assertEqual(current["decisions"], decision_list()["decisions"])
        self.assertIn("Write the message from " + self.rule, current["requirements"][0]["statement"])
        self.assertIn("# Draft skill build brief", (self.next / "build-brief.md").read_text(encoding="utf-8"))
        self.assertFalse(self.cli("status", root=self.next)["ready_to_build"])
        self.assertEqual(self.cli("brief", root=self.next, expected=2)["error"], "not_ready")
        previous = core.read_json(self.run / core.DECISIONS_FILE)
        rejected = self.cli("set-decisions", "--input", self.write(previous), root=self.next, expected=2)
        self.assertEqual(rejected["error"], "wrong_revision_workspace")
        previous["workspace_revision_id"] = current["workspace_revision_id"]
        rejected = self.cli("set-decisions", "--input", self.write(previous), root=self.next, expected=2)
        self.assertEqual(rejected["error"], "revised_rule_mismatch")
        self.assertEqual(core.read_json(self.next / core.DECISIONS_FILE), current)
        current["check"] = decision_list()["check"]
        self.cli("set-decisions", "--input", self.write(current), root=self.next)
        self.cli("brief", root=self.next)
        self.assertIn(self.rule, (self.next / "build-brief.md").read_text(encoding="utf-8"))
        skeleton = self.parent / "skeleton.json"
        self.cli("decisions-to-questions", "--skeleton", skeleton, root=self.next)
        self.cli("set-questions", "--from-decisions", "--input", skeleton, root=self.next)
        converted = core.read_json(self.next / "questions.json")
        self.assertIn(self.rule, converted["rule_revision"]["requirements"][0]["statement"])

    def write(self, record):
        path = self.parent / "input.json"
        core.atomic_json(path, record)
        return path

    def test_auto_choice_preserves_inactive_decision_history(self):
        self.setup_run(auto=True)
        change = self.form_for("question", "body")
        change["value"] = "subject-only"
        core.atomic_json(self.form, change)
        self.apply()
        records = core.read_json(self.next / core.DECISIONS_FILE)["decisions"]
        self.assertEqual(records[1]["choice"], "subject-only")
        self.assertEqual(records[1]["choice_actor"], "user")
        self.assertIn(self.rule, records[1]["reason"])
        self.assertEqual(records[2], decision_list()["decisions"][2])
        brief = (self.next / "build-brief.md").read_text(encoding="utf-8")
        self.assertNotIn("### body-style", brief)
        self.assertIn("Choice supplied by the user.", brief)
        current = core.read_json(self.next / core.DECISIONS_FILE)
        current["decisions"][1]["choice"] = decision_list()["decisions"][1]["choice"]
        self.assertEqual(self.cli("set-decisions", "--input", self.write(current), root=self.next,
                                  expected=2)["error"], "revised_rule_mismatch")

    def test_newly_active_question_requires_an_answer_before_final_brief(self):
        self.setup_run(conditional=True)
        change = self.form_for()
        change["value"] = "clarify"
        core.atomic_json(self.form, change)
        receipt = self.apply()
        self.assertEqual(receipt["pending_brief_items"], ["clarification"])
        view = self.cli("status", "--json", root=self.next)
        self.assertEqual(view["answers"]["answers"]["outputs"]["value"], ["progress", "next"])
        self.assertFalse(view["ready_to_build"])
        self.assertEqual(self.cli("brief", root=self.next, expected=2)["error"], "not_ready")
        core.answer_one(self.next, "clarification", "Ask which decision is outstanding.")
        brief = self.cli("brief", root=self.next)
        self.assertIn(self.rule, Path(brief["path"]).read_text(encoding="utf-8"))

    def test_reviewed_questionnaire_requirement_needs_renewed_judgment(self):
        self.setup_run(fixed=True)
        self.form_for("requirement", "source")
        result = self.apply()
        self.assertIn("question-review", result["pending_brief_items"])
        self.assertIn(self.rule, (self.next / "build-brief.md").read_text(encoding="utf-8"))
        self.assertEqual(self.cli("brief", root=self.next, expected=2)["error"], "question_review_required")
        old, new = (core.read_json(path / "answers.json") for path in (self.run, self.next))
        self.assertEqual(new["answers"], old["answers"])
        self.assertEqual(new["answer_revision"], old["answer_revision"])
        old_form = core.read_saved_html(core.render(self.run)["path"], require_saved=False)
        old_form.update(saved_at="2026-11-18T10:00:00Z", export_id=str(uuid.uuid4()))
        html = self.parent / "old-form.html"
        html.write_text('<script id="skill-builder-data" type="application/json">' + json.dumps(old_form) + '</script>', encoding="utf-8")
        for path in (html, self.run / "answers.json"):
            self.assertEqual(self.cli("import-answers", "--input", path, root=self.next, expected=2)["error"],
                             "wrong_revision_workspace")
        review = core.read_json(self.next / "question-review.json")
        self.assertEqual(review["requirements"][-1]["statement"], self.rule)
        self.assertEqual(review["question_reviews"][0]["status"], "pending")
        predecessor = self.run / "question-review.json"
        self.assertEqual(self.cli("accept-review", "--input", predecessor, root=self.next,
                                  expected=2)["error"], "question_review_incomplete")
        fresh = completed_example_review(self.next / "questions.json", self.parent / "fresh-review.json")
        self.assertEqual(fresh["requirements"], review["requirements"])
        old_wording = core.read_json(predecessor)
        old_wording["questions_sha256"] = fresh["questions_sha256"]
        self.assertEqual(self.cli("accept-review", "--input", self.write(old_wording), root=self.next,
                                  expected=2)["error"], "question_review_incomplete")
        self.assertEqual(core.read_json(self.next / "question-review.json"), review)
        self.cli("accept-review", "--input", self.write(fresh), root=self.next)
        final = self.cli("brief", root=self.next)
        self.assertIn(self.rule, Path(final["path"]).read_text(encoding="utf-8"))
        self.assertEqual(self.cli("set-questions", "--input", self.run / "questions.json", root=self.next,
                                  expected=2)["error"], "wrong_revision_workspace")
        saved = core.read_saved_html(self.cli("render", root=self.next)["path"], require_saved=False)
        saved.update(saved_at="2026-11-18T11:00:00Z", export_id=str(uuid.uuid4()))
        html.write_text('<script id="skill-builder-data" type="application/json">' + json.dumps(saved) + '</script>', encoding="utf-8")
        restored = self.parent / "restored"
        self.cli("restore", "--input", html, root=restored)
        restored_review = completed_example_review(restored / "questions.json", self.parent / "restored-review.json")
        self.assertEqual(restored_review["requirements"], fresh["requirements"])
        self.cli("accept-review", "--input", self.write(restored_review), root=restored)
        self.assertIn(self.rule, Path(self.cli("brief", root=restored)["path"]).read_text(encoding="utf-8"))

    def test_invalid_scope_stale_sources_and_interrupted_publish_keep_both_sides_safe(self):
        self.setup_run()
        change = self.form_for()
        change["check_edits"] = [{"case": "guard", "id": "data", "expected": 2}]
        core.atomic_json(self.form, change)
        self.assertIn("outside", self.apply(expected=2)["message"])
        self.assertFalse(self.next.exists())
        change["check_edits"] = [{"case": "case", "id": "data"}]
        core.atomic_json(self.form, change)
        self.assertIn("explicit expected", self.apply(expected=2)["message"])
        change["check_edits"][0]["expected"] = {"v": True}
        core.atomic_json(self.form, change)
        with patch.object(Path, "rename", side_effect=OSError("publication interrupted")), self.assertRaisesRegex(OSError, "interrupted"):
            revise_rule.apply(self.run, change, self.next)
        self.assertFalse(self.next.exists())
        self.assertFalse(list(self.parent.glob(".revise-rule-*")))
        (self.run / "input.txt").write_text("changed after planning", encoding="utf-8")
        self.assertEqual(self.apply(expected=2)["error"], "stale_revision")
        self.assertFalse(self.next.exists())
        self.next.mkdir()
        (self.next / "user-data").write_bytes(b"keep")
        self.assertEqual(self.apply(expected=2)["error"], "already_exists")
        self.assertEqual((self.next / "user-data").read_bytes(), b"keep")

    def test_one_form_binds_missing_case_links_and_prepares_all_revised_expectations(self):
        self.setup_run()
        selected = ["case", "second", "late-source", "mixed-format"]
        for cid in selected[1:]:
            case = copy.deepcopy(self.plan["cases"][0])
            case["id"] = cid
            self.plan["cases"].append(case)
        # One older case already lists other rule IDs. The other has only partial traceability.
        self.plan["cases"][-2]["question_ids"] = ["outputs"]
        self.design["features"][0].update(evaluation_ids=selected[:2], question_ids=["workflow"])
        self.design["features"][1].update(evaluation_ids=["guard", "mixed-format"], question_ids=["outputs"])
        core.atomic_json(self.run / "design.json", self.design)
        core.atomic_json(self.run / "plan.json", self.plan)
        prepared = self.cli("revise-rule", "--question", "workflow", "--prepare", self.form)
        self.assertEqual(prepared["case_features"], {"case": ["reply"], "second": ["reply"], "late-source": [],
                                                   "mixed-format": ["layout"], "guard": ["layout"]})
        self.assertEqual(set(prepared["checks"]), set(prepared["case_features"]))
        change = core.read_json(self.form)
        change.update(rule=self.rule, basis="Changed drafting preference",
                      check_edits=[{"case": cid, "id": "data", "expected": {"draft": cid}} for cid in selected])
        feature = change["feature_edits"][0]
        feature["replace"] = "Ask first."
        for links, expected_error in (([], "add_evaluation_ids"), (["unknown"], "Unknown evaluation case"),
                                      (["case"], "Duplicate"), (["late-source", "late-source"], "Duplicate"),
                                      (["late-source", "mixed-format"], "shared_with"),
                                      ([{"id": "mixed-format", "shared_with": ["reply"]}], "shared_with")):
            with self.subTest(links=links):
                feature["add_evaluation_ids"] = links
                core.atomic_json(self.form, change)
                self.assertIn(expected_error, self.apply(expected=2)["message"])
                self.assertFalse(self.next.exists())
        feature["add_evaluation_ids"] = ["late-source", {"id": "mixed-format", "shared_with": ["layout"]}]
        core.atomic_json(self.form, change)
        result = self.apply()
        self.assertEqual(self.apply()["event"], "already_published")
        self.assertEqual(core.read_json(self.run / "design.json"), self.design)
        self.assertEqual(core.read_json(self.run / "plan.json"), self.plan)
        features = core.read_json(self.next / "design.json")["features"]
        self.assertEqual(features[0]["evaluation_ids"], selected)
        self.assertEqual(features[1], self.design["features"][1])
        self.assertEqual(set(result["retest_cases"]), set(selected + ["guard"]))
        iteration = self.parent / "iteration"
        prepare_evaluation(result["plan"], result["runtime"], iteration, baseline_skill=result["baseline_runtime"])
        cases = {c["id"]: c for c in core.read_json(iteration / "plan.json")["cases"]}
        self.assertEqual(cases["guard"], self.plan["cases"][1])
        self.assertEqual(cases["late-source"]["question_ids"], ["outputs", "workflow"])
        self.assertNotIn("question_ids", cases["mixed-format"])
        for cid in selected:
            review, output = cases[cid]["checks"]
            self.assertEqual(review, self.plan["cases"][0]["checks"][0])
            self.assertEqual(output["question_ids"], ["workflow"])
            self.assertEqual(core.read_json(iteration / "expectations" / output["expected_file"]), {"draft": cid})
        self.assertEqual(core.read_json(iteration / "expectations/shared.json"), {"v": False})


if __name__ == "__main__":
    unittest.main()
