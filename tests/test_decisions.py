"""Full Auto decision lists: validation, the single check, the build brief, and conversion to a questionnaire."""
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

REPOSITORY = Path(__file__).resolve().parents[1]
SCRIPTS = REPOSITORY / "any-skill-builder/scripts"
sys.path.insert(0, str(SCRIPTS))
import builder_core as core
import review_questions
from test_question_review import two_question_fixture


def decision_list():
    """Synthetic Full Auto decisions for a commit-message skill."""
    return {
        "schema_version": 1,
        "language": "en",
        "requirements": [{"id": "staged-only", "statement": "Write the message from staged changes only", "basis": "user request"}],
        "sources": [{"id": "git-diff", "title": "git diff documentation", "url": "https://git-scm.com/docs/git-diff",
                     "kind": "official documentation", "status": "read", "accessed_at": "2026-11-15",
                     "notes": "--cached shows only staged changes"}],
        "decisions": [
            {"id": "empty-staging", "question": "What should happen when nothing is staged?",
             "affects": "Behavior when the staging area is empty", "importance": "core", "origin": "source",
             "source_ids": ["git-diff"],
             "options": [{"id": "stop", "label": "Say so and stop", "tradeoff": "No wrong message; the user reruns"},
                         {"id": "suggest", "label": "Suggest what to stage", "tradeoff": "Convenient but reads unstaged files"}],
             "choice": "stop", "reason": "The message must match what will be committed"},
            {"id": "body", "question": "Should the message have a body?", "affects": "Message length",
             "options": [{"id": "subject-only", "label": "Subject only", "tradeoff": "Short; loses the why"},
                         {"id": "with-body", "label": "Subject and body", "tradeoff": "Explains the why; longer"}],
             "choice": "with-body", "reason": "Reviewers need the reason for a change"},
            {"id": "body-style", "question": "How should the body read?", "affects": "Body tone", "type": "text",
             "when": [{"question_id": "body", "equals": "with-body"}],
             "choice": "One or two plain sentences", "reason": "Matches common repository style",
             "assumptions": ["The repository has no stricter style guide"]},
        ],
        "check": {
            "reviewer": "self",
            "requirements_preserved": {"status": "pass", "reason": "Every choice reads staged changes only"},
            "no_forbidden_choices": {"status": "pass", "reason": "The unstaged option was considered, not chosen"},
            "no_invented_private_facts": {"status": "pass", "reason": "Repository style is recorded as an assumption"},
            "revisions": 0,
            "known_limits": ["Repository style assumption needs checking on a real repository"],
        },
    }


class DecisionListTests(unittest.TestCase):
    def setUp(self):
        cache = os.environ.get("SKILL_BUILDER_TEST_TMPDIR")
        if cache:
            Path(cache).mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="decisions-", dir=cache)
        self.parent = Path(self.temp.name)
        self.root = self.parent / "run"
        self.counter = 0
        self.cli("init", "--goal", "Synthetic commit-message skill", "--mode", "auto")

    def tearDown(self):
        self.temp.cleanup()

    def cli(self, command, *arguments, workspace=None, expected=0):
        result = subprocess.run([sys.executable, "-B", str(SCRIPTS / "skill_builder.py"), command,
                                 "--workspace", str(workspace or self.root), *map(str, arguments)],
                                capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, expected, result.stderr or result.stdout)
        return json.loads(result.stdout if result.returncode == 0 else result.stderr)

    def write(self, value):
        self.counter += 1
        path = self.parent / f"input-{self.counter}.json"
        core.atomic_json(path, value)
        return path

    def record(self, decisions, expected=0, workspace=None):
        return self.cli("set-decisions", "--input", self.write(decisions), workspace=workspace, expected=expected)

    def test_checked_decision_list_builds_a_brief_without_a_question_review(self):
        result = self.record(decision_list())
        self.assertTrue(result["ready_to_build"])
        self.assertEqual(result["decisions"]["counts"], {"decisions": 3, "active": 3, "inactive": 0, "waiting": 0})
        self.assertEqual(result["question_review"]["status"], "not_applicable")
        status = self.cli("status")
        self.assertTrue(status["ready_to_build"])
        self.assertEqual(status["decisions"]["known_limits"], decision_list()["check"]["known_limits"])
        self.cli("brief")
        brief = (self.root / "build-brief.md").read_text(encoding="utf-8")
        self.assertIn("Mode: Full Auto decision list", brief)
        self.assertIn("staged-only: Write the message from staged changes only", brief)
        self.assertIn("- (chosen) Say so and stop: No wrong message; the user reruns", brief)
        self.assertIn("- (considered) Suggest what to stage", brief)
        self.assertIn("Assumption to retain or verify: The repository has no stricter style guide", brief)
        self.assertIn("Repository style assumption needs checking", brief)
        self.assertFalse(list(self.root.glob("*.html")))
        self.assertEqual(self.cli("render", expected=2)["error"], "auto_no_html")
        self.assertEqual(self.cli("recommend", expected=2)["error"], "decision_list_in_use")

    def test_pending_or_failing_checks_block_the_brief(self):
        for status in ("pending", "needs-revision"):
            with self.subTest(status=status):
                decisions = decision_list()
                decisions["check"]["no_invented_private_facts"] = {"status": status, "reason": "" if status == "pending" else "Assumes a team account"}
                result = self.record(decisions)
                self.assertFalse(result["ready_to_build"])
                key = "pending_checks" if status == "pending" else "failing_checks"
                self.assertEqual(result["decisions"][key], ["no_invented_private_facts"])
                self.assertEqual(self.cli("brief", expected=2)["error"], "not_ready")

    def test_fully_specified_build_uses_only_fixed_requirements(self):
        spec = decision_list()
        spec.update(groups=[], decisions=[], sources=[], requirements=[
            {"id": "staged-only", "statement": "Use staged changes only", "basis": "user request"},
            {"id": "format", "statement": "Return one English subject of 50 characters or fewer", "basis": "user request"},
            {"id": "empty", "statement": "If nothing is staged, reply 'Nothing staged.'", "basis": "user request"},
        ])
        checked = {"reviewer": "self", **{k: {"status": "pass", "reason": "All behavior comes from the supplied requirements."}
                                          for k in core.DECISION_CHECKS}}
        spec["check"] = {**checked, "requirements_preserved": {"status": "pending"}}
        self.assertFalse(self.record(spec)["ready_to_build"])
        self.assertEqual(self.cli("brief", expected=2)["error"], "not_ready")
        spec["check"] = checked
        self.assertTrue(self.record(spec)["ready_to_build"])
        status = self.cli("status")
        self.assertEqual(status["decisions"]["counts"], {"decisions": 0, "active": 0, "inactive": 0, "waiting": 0})
        self.assertEqual(status["decisions"]["requirements"], 3)
        self.cli("checkpoint", "--stage", 5, "--summary", "Checked the fixed requirements", "--next-action", "Build and evaluate",
                 "--revision", status["revision"], "--answer-revision", status["answer_revision"])
        resumed = self.cli("status", "--json")
        self.assertTrue(resumed["workflow"]["progress"]["current"])
        self.assertTrue(resumed["ready_to_build"])
        self.cli("brief")
        brief = (self.root / "build-brief.md").read_text(encoding="utf-8")
        for req in spec["requirements"]:
            self.assertIn(req["statement"], brief)
        self.assertIn("The fixed requirements specify the build in full.", brief)
        self.assertNotIn("AI decisions to review together:", brief)
        skeleton = self.parent / "skeleton.json"
        self.assertEqual(self.cli("decisions-to-questions", "--skeleton", skeleton, expected=2)["error"], "no_questions_to_convert")
        self.assertFalse(skeleton.exists())
        fixture = {"mode": "questionnaire", "questions": []}
        self.assertEqual(self.cli("set-questions", "--from-decisions", "--input", self.write(fixture), expected=2)["error"],
                         "no_questions_to_convert")
        self.assertEqual(self.cli("status")["mode"], "auto")

    def test_every_active_decision_needs_a_choice_but_inactive_ones_do_not(self):
        decisions = decision_list()
        del decisions["decisions"][0]["choice"]
        result = self.record(decisions)
        self.assertEqual(result["decisions"]["unchosen_ids"], ["empty-staging"])
        self.assertFalse(result["ready_to_build"])
        decisions = decision_list()
        decisions["decisions"][1]["choice"] = "subject-only"
        del decisions["decisions"][2]["choice"]
        result = self.record(decisions)
        self.assertTrue(result["ready_to_build"])
        self.assertEqual(result["decisions"]["counts"]["inactive"], 1)
        self.cli("brief")
        brief = (self.root / "build-brief.md").read_text(encoding="utf-8")
        self.assertNotIn("body-style", brief)
        self.assertIn("AI decisions to review together: empty-staging, body", brief.splitlines())

    def test_conversion_before_brief_lock_uses_the_new_questionnaire_review(self):
        self.record(decision_list())
        skeleton = self.parent / "skeleton.json"
        self.cli("decisions-to-questions", "--skeleton", skeleton)
        real_lock = core.workspace_lock

        def convert_before_lock(workspace):
            self.cli("set-questions", "--from-decisions", "--input", skeleton)
            return real_lock(workspace)

        with patch.object(core, "workspace_lock", side_effect=convert_before_lock):
            with self.assertRaises(core.BuilderError) as error:
                core.build_brief(self.root)
        self.assertEqual(error.exception.code, "question_review_required")
        self.assertFalse((self.root / "build-brief.md").exists())

    def test_checkpoint_tracks_decision_content_across_reimports(self):
        data = decision_list()
        self.record(data)
        status = self.cli("status")
        flags = ("--stage", 3, "--summary", "Checked the decisions", "--next-action", "Prepare the brief",
                 "--revision", status["revision"], "--answer-revision", status["answer_revision"])
        self.cli("checkpoint", *flags)
        self.record(dict(reversed(data.items())))
        self.assertTrue(self.cli("status", "--json")["workflow"]["progress"]["current"])
        data["decisions"][1]["choice"] = "subject-only"
        self.record(data)
        progress = self.cli("status", "--json")["workflow"]["progress"]
        self.assertFalse(progress["current"])
        self.assertEqual(progress["record"]["summary"], "Checked the decisions")
        checkpoint = self.cli("checkpoint", *flags)["checkpoint"]
        self.assertEqual(len(checkpoint["history"]), 1)
        self.assertTrue(self.cli("status", "--json")["workflow"]["progress"]["current"])
        del checkpoint["decisions_sha256"]
        core.atomic_json(self.root / "progress.json", checkpoint)
        legacy = self.cli("status", "--json")["workflow"]["progress"]
        self.assertFalse(legacy["current"])
        self.assertEqual(legacy["record"], checkpoint)

    def test_invalid_decisions_are_rejected_without_replacing_the_stored_list(self):
        self.record(decision_list())
        stored = (self.root / "decisions.json").read_bytes()
        mutations = {
            "one option": lambda d: d["decisions"][0]["options"].pop(),
            "unknown source": lambda d: d["decisions"][0].update(source_ids=["invented"]),
            "choice outside options": lambda d: d["decisions"][0].update(choice="invented"),
            "missing tradeoff": lambda d: d["decisions"][0]["options"][0].pop("tradeoff"),
            "choice without reason": lambda d: d["decisions"][0].pop("reason"),
            "image choice": lambda d: d["decisions"][0].update(type="image"),
            "duplicate requirement": lambda d: d["requirements"].append(copy.deepcopy(d["requirements"][0])),
            "empty spec": lambda d: d.update(decisions=[], requirements=[]),
            "empty requirement basis": lambda d: d.update(decisions=[], requirements=[{"id": "format", "statement": "Use English", "basis": " "}]),
            "unknown reviewer": lambda d: d["check"].update(reviewer="someone"),
            "missing check reason": lambda d: d["check"]["requirements_preserved"].update(reason=""),
            "unknown condition": lambda d: d["decisions"][2].update(when=[{"question_id": "invented", "equals": "x"}]),
        }
        for name, mutate in mutations.items():
            with self.subTest(name):
                decisions = decision_list()
                mutate(decisions)
                self.record(decisions, expected=2)
                self.assertEqual((self.root / "decisions.json").read_bytes(), stored)

    def test_custom_choice_blocks_brief_until_its_dependents_are_resolved(self):
        data = decision_list()
        parent, child = data["decisions"][1:]
        parent["choice"] = {"other": "Include a short body for breaking changes only", "selected": []}
        data["decisions"].append({**child, "id": "body-example", "when": [
            {"question_id": child["id"], "equals": child["choice"]}]})
        recorded = self.record(data)
        for response in (recorded, self.cli("status"), self.cli("status", "--json")):
            self.assertFalse(response["ready_to_build"])
            self.assertEqual(response["decisions"]["counts"]["waiting"], 2)
            self.assertEqual(response["decisions"]["waiting_ids"], ["body-example", "body-style"])
            self.assertEqual(response["decisions"]["unresolved_branch_ids"], ["body"])
        self.assertEqual(self.cli("brief", expected=2)["error"], "not_ready")
        self.assertFalse((self.root / "build-brief.md").exists())

        for interpretation, rationale in (("with-body", "The conditional body still needs a writing style."),
                                          (None, "The custom rule defines its own style.")):
            with self.subTest(interpretation=interpretation):
                parent.update(branch_value=interpretation, branch_rationale=rationale)
                self.assertTrue(self.record(data)["ready_to_build"])
                self.assertEqual(self.cli("status")["decisions"]["waiting_ids"], [])
                self.cli("brief")
                brief = (self.root / "build-brief.md").read_text(encoding="utf-8")
                self.assertIn("Custom direction: " + parent["choice"]["other"], brief)
                self.assertIn("Branch interpretation: " + json.dumps(interpretation), brief)
                self.assertIn("Branch rationale: " + rationale, brief)
                for qid in ("body-style", "body-example"):
                    self.assertEqual("### " + qid in brief, interpretation == "with-body")

    def test_explicit_multi_selection_resolves_its_branch_without_classifying_custom_text(self):
        data = decision_list()
        first, multi, child = data["decisions"]
        first["choice"] = {"other": "Report an empty staging area", "selected": []}
        multi.update(type="multi", choice={"other": "Also include a change type", "selected": ["with-body"]})
        child["when"] = [{"question_id": multi["id"], "includes": "with-body"},
                         {"question_id": first["id"], "equals": "stop"}]
        state = self.record(data)["decisions"]
        self.assertEqual(state["waiting_ids"], ["body-style"])
        self.assertEqual(state["unresolved_branch_ids"], [first["id"]])

        first.update(branch_value="stop", branch_rationale="Both choices stop after reporting the condition.")
        self.assertTrue(self.record(data)["ready_to_build"])
        child["when"][0]["includes"] = "subject-only"
        self.assertEqual(self.record(data)["decisions"]["unresolved_branch_ids"], [multi["id"]])
        multi.update(branch_value=["subject-only"], branch_rationale="The change type also applies to a subject.")
        self.record(data, expected=2)
        multi["branch_value"].append("with-body")
        self.assertTrue(self.record(data)["ready_to_build"])
        self.cli("brief")
        brief = (self.root / "build-brief.md").read_text(encoding="utf-8")
        self.assertIn("### body-style", brief)
        self.assertIn("Custom direction: " + multi["choice"]["other"], brief)

    def test_invalid_interpretation_rejects_the_update_atomically(self):
        data = decision_list()
        self.record(data)
        saved = (self.root / "decisions.json").read_bytes()
        custom = {"other": "A short body for breaking changes", "selected": []}
        for fields in ({"branch_value": None, "branch_rationale": "Ordinary choice."},
                       {"choice": None, "branch_value": None, "branch_rationale": "No choice."},
                       {"choice": custom, "branch_rationale": "Missing classification."},
                       {"choice": custom, "branch_value": None},
                       {"choice": custom, "branch_value": "alien", "branch_rationale": "Unknown option."}):
            with self.subTest(fields=fields):
                changed = copy.deepcopy(data)
                changed["decisions"][1].update(fields)
                self.record(changed, expected=2)
                self.assertEqual((self.root / "decisions.json").read_bytes(), saved)

    def test_extra_revisions_are_noted_but_do_not_block(self):
        decisions = decision_list()
        decisions["check"]["revisions"] = 2
        result = self.record(decisions)
        self.assertTrue(result["ready_to_build"])
        self.assertIn("Full Auto allows 1", result["decisions"]["notes"][0])

    def test_decision_lists_belong_to_full_auto_runs_without_questions(self):
        questionnaire_run = self.parent / "questionnaire-run"
        self.cli("init", "--goal", "Synthetic questionnaire", "--mode", "questionnaire", workspace=questionnaire_run)
        self.assertEqual(self.record(decision_list(), expected=2, workspace=questionnaire_run)["error"], "mode_mismatch")
        older_auto = self.parent / "older-auto"
        self.cli("init", "--goal", "Synthetic older auto run", "--mode", "auto", workspace=older_auto)
        fixture = two_question_fixture()
        self.cli("set-questions", "--input", self.write(fixture), "--rebind-project", workspace=older_auto)
        self.assertEqual(self.record(decision_list(), expected=2, workspace=older_auto)["error"], "questions_in_use")

    def test_conversion_maps_fields_one_to_one_and_switches_to_a_reviewed_questionnaire(self):
        decisions = decision_list()
        self.record(decisions)
        skeleton = self.parent / "skeleton.json"
        result = self.cli("decisions-to-questions", "--skeleton", skeleton)
        self.assertEqual(result["questions"], 3)
        self.assertEqual(result["requirements"], decisions["requirements"])
        self.assertEqual(self.cli("decisions-to-questions", "--skeleton", skeleton, expected=2)["error"], "already_exists")
        authored = core.read_json(skeleton)
        self.assertEqual(authored["mode"], "questionnaire")
        self.assertEqual(authored["sources"], decisions["sources"])
        for source, question in zip(decisions["decisions"], authored["questions"]):
            self.assertEqual(question["id"], source["id"])
            self.assertEqual(question["title"], source["question"])
            self.assertEqual(question["decision"], source["affects"])
            self.assertEqual(question["recommendation"]["value"], source["choice"])
            self.assertEqual(question["recommendation"]["rationale"], source["reason"])
            self.assertEqual([o["effect"] for o in question.get("options", [])], [o["tradeoff"] for o in source.get("options", [])])
        self.assertEqual(authored["questions"][2]["when"], decisions["decisions"][2]["when"])

        self.assertEqual(self.cli("set-questions", "--input", skeleton, expected=2)["error"], "mode_mismatch")
        authored["questions"][0]["help"] = "Display text added after conversion."
        converted = self.cli("set-questions", "--input", self.write(authored), "--from-decisions")
        self.assertEqual(converted["mode"], "questionnaire")
        self.assertTrue(converted["question_review"]["required"])
        status = self.cli("status")
        self.assertEqual(status["mode"], "questionnaire")
        self.assertNotIn("decisions", status)
        self.assertEqual(status["question_review"]["status"], "missing")
        self.assertEqual(self.cli("render", expected=2)["error"], "question_review_required")
        self.assertEqual(self.cli("brief", expected=2)["error"], "question_review_required")
        self.assertTrue((self.root / "decisions.json").exists())
        self.assertEqual(self.cli("set-decisions", "--input", self.write(decisions), expected=2)["error"], "mode_mismatch")

    def converted_review(self, decisions=None):
        """Convert the decision list to a questionnaire and return a passing synthetic review of it."""
        self.record(decision_list() if decisions is None else decisions)
        skeleton = self.parent / "skeleton.json"
        self.cli("decisions-to-questions", "--skeleton", skeleton)
        self.cli("set-questions", "--input", skeleton, "--from-decisions")
        review = review_questions.prepare(self.root / "questions.json", self.parent / "review-draft.json")
        self.prepared = copy.deepcopy(review)
        review["status"] = "pass"
        review["reviewer"] = {"identity": "Test fixture reviewer", "relationship": "self"}
        review["decision_coverage"]["comparisons"] = [
            {"sample": "Example staged diff renames an option and updates the matching usage text.",
             "outcomes": ["One subject line summarizes the rename.", "The subject includes a body explaining the usage update."],
             "question_id": "body"}]
        for row in review["question_reviews"]:
            row.update(status="pass", reason="Every option reads staged changes only.")
        review["combinations"][0].update(status="pass", reason="Recommended choices keep staged-only input.", answers=[
            {"question_id": "empty-staging", "value": "stop"}, {"question_id": "body", "value": "with-body"},
            {"question_id": "body-style", "value": "One or two plain sentences"}])
        review["combinations"][1].update(status="pass", reason="A subject-only message also keeps staged-only input.",
                                         answers=[{"question_id": "empty-staging", "value": "stop"},
                                                  {"question_id": "body", "value": "subject-only"}],
                                         inapplicable_question_ids=["body-style"])
        for key in ("localization", "fair_alternatives", "unknown_private_facts"):
            review[key].update(status="pass", reason="Synthetic fixture check.")
        return review

    def brief_after(self, review):
        self.cli("accept-review", "--input", self.write(review))
        self.cli("recommend")
        self.cli("brief")
        return (self.root / "build-brief.md").read_text(encoding="utf-8")

    def test_converted_run_keeps_fixed_requirements_in_the_review_and_the_brief(self):
        review = self.converted_review()
        carried = [r for r in self.prepared["requirements"] if r["id"] == "staged-only"]
        self.assertEqual(len(carried), 1)
        self.assertEqual(carried[0]["statement"], "Write the message from staged changes only")
        self.assertEqual(carried[0]["basis"]["kind"], "user")
        self.assertEqual(carried[0]["basis"]["reference"], "user request")
        for row in self.prepared["question_reviews"] + self.prepared["combinations"]:
            self.assertEqual(row["requirement_ids"], ["goal", "staged-only"])
        brief = self.brief_after(review)
        self.assertIn("## Fixed requirements", brief)
        self.assertIn("- staged-only: Write the message from staged changes only (basis: user, user request)", brief)
        self.assertEqual(brief.count("staged-only:"), 1)

    def test_converted_custom_recommendation_applies_its_interpretation_only_to_the_ai_choice(self):
        data = decision_list()
        custom = {"other": "Add a short body for breaking changes", "selected": []}
        rationale = "Breaking changes need the body style."
        data["decisions"][1].update(choice=custom, branch_value="with-body", branch_rationale=rationale)
        review = self.converted_review(data)
        review["combinations"][0]["answers"][1]["value"] = custom
        different_branch = copy.deepcopy(review)
        combination = different_branch["combinations"][0]
        combination["answers"][1].update(branch_value=None, branch_rationale="Assumes no body style applies.")
        combination["answers"].pop()
        combination["inapplicable_question_ids"] = ["body-style"]
        self.assertEqual(self.cli("accept-review", "--input", self.write(different_branch), expected=2)["error"],
                         "question_review_incomplete")
        brief = self.brief_after(review)
        self.assertIn("Branch rationale: " + rationale, brief)
        self.assertIn("### body-style", brief)
        self.cli("answer", "--question", "body", "--value-file", self.write({"other": "Use a footer", "selected": []}))
        self.cli("recommend")
        state = self.cli("status", "--json")
        self.assertEqual(state["unresolved_branch_ids"], ["body"])
        self.assertFalse(state["ready_to_build"])
        self.assertEqual(state["answers"]["answers"]["body"]["value"]["other"], "Use a footer")
        self.assertNotIn("branch_value", state["answers"]["answers"]["body"])

    def test_requirement_ids_colliding_with_the_review_goal_all_reach_the_brief(self):
        data = decision_list()
        data["requirements"] = [
            {"id": "decision-goal", "statement": "Keep A", "basis": "user request"},
            {"id": "goal", "statement": "Keep B", "basis": "git-diff"},
            {"id": "decision-goal-2", "statement": "Keep C", "basis": "user request"},
        ]
        review = self.converted_review(data)
        carried = review["requirements"][1:]
        self.assertEqual([r["statement"] for r in carried], ["Keep A", "Keep B", "Keep C"])
        ids = ["goal", "decision-goal", "decision-goal-3", "decision-goal-2"]
        self.assertEqual([r["id"] for r in review["requirements"]], ids)
        self.assertEqual(carried[1]["basis"]["reference"], "git-diff")
        for row in review["question_reviews"] + review["combinations"]:
            self.assertEqual(row["requirement_ids"], ids)
        brief = self.brief_after(review)
        for requirement in carried:
            self.assertIn(f"- {requirement['id']}: {requirement['statement']} (basis:", brief)

    def test_requirement_released_in_the_review_stays_out_of_the_brief(self):
        review = self.converted_review()
        review["requirements"] = [r for r in review["requirements"] if r["id"] != "staged-only"]
        for row in review["question_reviews"] + review["combinations"]:
            row["requirement_ids"].remove("staged-only")
        brief = self.brief_after(review)
        self.assertIn("## Fixed requirements\n\n- None recorded beyond the goal.", brief)
        self.assertNotIn("staged-only", brief)
        self.assertTrue((self.root / "decisions.json").exists())

    def test_from_decisions_requires_a_decision_list_run(self):
        other = self.parent / "plain-auto"
        self.cli("init", "--goal", "Synthetic plain auto run", "--mode", "auto", workspace=other)
        fixture = two_question_fixture()
        fixture["mode"] = "questionnaire"
        result = self.cli("set-questions", "--input", self.write(fixture), "--rebind-project", "--from-decisions",
                          workspace=other, expected=2)
        self.assertEqual(result["error"], "not_a_decision_conversion")


if __name__ == "__main__":
    unittest.main()
