"""Automatic unanswered decisions preserve meaningful human input and branching."""
from __future__ import annotations
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import uuid

PACKAGE = Path(__file__).resolve().parents[1] / "any-skill-builder"
sys.path.insert(0, str(PACKAGE / "scripts"))
import builder_core as core
from test_backend import questionnaire


class DelegationTests(unittest.TestCase):
    def setUp(self):
        cache = os.environ.get("SKILL_BUILDER_TEST_TMPDIR")
        if cache:
            Path(cache).mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="offline-decisions-", dir=cache)
        self.parent = Path(self.temp.name)
        self.root = self.parent / "run"
        result = core.init_workspace(self.root, "Create a study skill")
        self.data = questionnaire(result["project_id"])
        core.set_questions(self.root, self.data)

    def tearDown(self):
        self.temp.cleanup()

    def boot(self):
        text = core.render_html(self.root).split('<script id="skill-builder-data" type="application/json">')[1].split('</script>', 1)[0]
        boot = json.loads(text)
        boot.update(export_id=str(uuid.uuid4()), saved_at="2026-11-15T10:00:00Z")
        boot["view"]["answers"].pop("pending_inputs", None)
        return boot

    def multi(self, dependency=False):
        data = core.status(self.root)["questionnaire"]
        q = data["questions"][2]
        q["min_choices"] = 2
        q["options"].append({"id": "table", "label": "Table", "effect": "Compare source facts"})
        q["recommendation"]["value"] = ["chart", "note"]
        if dependency:
            q["when"] = [{"question_id": "q1", "equals": "yes"}]
        core.set_questions(self.root, data)

    def pending(self, selected, dependency=False):
        self.multi(dependency)
        core.answer_one(self.root, "q1", "yes")
        boot = self.boot()
        boot["drafts"] = {"q3": {"selected": selected, "other_enabled": False, "other_text": ""}}
        return core.import_answers(self.root, boot)

    def test_full_auto_builds_decisions_without_creating_html(self):
        auto = self.parent / "auto"
        core.init_workspace(auto, "Create a study skill", "auto")
        core.set_questions(auto, self.data, rebind_project=True)
        self.assertEqual(core.status(auto)["questionnaire"]["mode"], "auto")
        self.assertTrue(core.recommend(auto)["ready_to_build"])
        core.build_brief(auto)
        self.assertEqual(list(auto.glob("*.html")), [])
        with self.assertRaises(core.BuilderError) as caught:
            core.render(auto)
        self.assertEqual(caught.exception.code, "auto_no_html")
        self.assertEqual(list(auto.glob("*.html")), [])

    def test_question_update_cannot_change_an_explicit_run_mode(self):
        data = core.status(self.root)["questionnaire"]
        data["mode"] = "auto"
        with self.assertRaises(core.BuilderError) as caught:
            core.set_questions(self.root, data)
        self.assertEqual(caught.exception.code, "mode_mismatch")

    def test_missing_recommendation_stays_unanswered_and_ai_requires_reason(self):
        data = core.status(self.root)["questionnaire"]
        del data["questions"][0]["recommendation"]
        core.set_questions(self.root, data)
        view = core.recommend(self.root)
        self.assertFalse(view["ready_to_build"])
        self.assertNotIn("q1", view["answers"]["answers"])
        with self.assertRaises(core.BuilderError):
            core.answer_one(self.root, "q1", "no", actor="ai")

    def test_contextual_resolution_retains_original_text_and_rationale(self):
        core.answer_one(self.root, "q1", "yes")
        core.answer_one(self.root, "q2", ".")
        view = core.resolve_input(self.root, "q2", "A lone dot does not specify an execution environment here.")
        self.assertNotIn("q2", view["answers"]["answers"])
        rejected = [x for x in view["answers"]["history"] if x["reason"] == "uninterpretable_input"]
        self.assertEqual(rejected[0]["answer"]["value"], ".")
        self.assertIn("environment", rejected[0]["rationale"])
        self.assertIn("q2", core.recommend(self.root)["filled"])

    def test_short_meaningful_text_is_never_rejected_by_length(self):
        core.answer_one(self.root, "q1", "yes")
        for value in ("0", "없음", "No", "π", "使用しない"):
            core.answer_one(self.root, "q2", value)
            view = core.recommend(self.root)
            self.assertEqual(view["answers"]["answers"]["q2"]["value"], value)
            self.assertEqual(view["answers"]["answers"]["q2"]["actor"], "user")

    def test_contextual_resolution_cannot_discard_ordinary_options(self):
        core.answer_one(self.root, "q1", "no")
        with self.assertRaises(core.BuilderError):
            core.resolve_input(self.root, "q1", "AI prefers the other option")
        self.assertEqual(core.status(self.root)["answers"]["answers"]["q1"]["value"], "no")

    def test_resolving_meaningless_other_preserves_valid_multi_selections(self):
        core.answer_one(self.root, "q3", {"other": ".", "selected": ["note"]})
        view = core.resolve_input(self.root, "q3", "The dot conveys no additional output request.")
        self.assertEqual(view["answers"]["answers"]["q3"]["value"], ["note"])
        self.assertEqual(view["answers"]["answers"]["q3"]["actor"], "user")
        self.assertNotIn("q3", core.recommend(self.root)["filled"])

    def test_custom_parent_waits_for_interpretation_without_discarding_text(self):
        value = {"other": "Reproduce only after the runtime has been confirmed", "selected": []}
        view = core.answer_one(self.root, "q1", value)
        self.assertEqual(view["states"]["q2"], "waiting")
        self.assertEqual(view["unresolved_branch_ids"], ["q1"])
        self.assertFalse(core.recommend(self.root)["ready_to_build"])
        view = core.interpret_answer(self.root, "q1", "yes", "The custom answer permits reproduction with a runtime prerequisite.")
        self.assertEqual(view["states"]["q2"], "active")
        self.assertEqual(view["answers"]["answers"]["q1"]["value"], value)
        self.assertEqual(view["answers"]["answers"]["q1"]["actor"], "user")
        self.assertTrue(core.recommend(self.root)["ready_to_build"])

    def test_custom_parent_can_explicitly_match_no_existing_branch(self):
        core.answer_one(self.root, "q1", {"other": "Only develop conceptual hypotheses", "selected": []})
        view = core.interpret_answer(self.root, "q1", None, "This custom direction does not include code reproduction.")
        self.assertEqual(view["states"]["q2"], "inactive")

    def test_brief_retains_custom_text_option_effects_and_branch_interpretation(self):
        core.answer_one(self.root, "q1", {"other": "Conceptual study only", "selected": []})
        core.interpret_answer(self.root, "q1", None, "No reproduction environment is needed.")
        core.answer_one(self.root, "q3", {"other": "Also list open questions", "selected": ["note"]})
        path = Path(core.build_brief(self.root)["path"])
        body = path.read_text(encoding="utf-8")
        self.assertIn("Custom direction: Also list open questions", body)
        self.assertIn("Write research notes", body)
        self.assertIn("Branch interpretation: null", body)
        self.assertIn("No reproduction environment is needed.", body)

    def test_incomplete_multi_is_recorded_and_never_silently_replaced(self):
        view = self.pending(["table"])
        self.assertEqual(view["pending_input_ids"], ["q3"])
        self.assertFalse(view["ready_to_build"])
        view = core.recommend(self.root)
        self.assertNotIn("q3", view["filled"])
        self.assertEqual(view["answers"]["pending_inputs"]["q3"]["selected"], ["table"])
        with self.assertRaises(core.BuilderError):
            core.complete_input(self.root, "q3", ["chart", "note"], "Discarding table is not allowed")
        view = core.complete_input(self.root, "q3", ["table", "note"], "Retain the table and add notes for context.")
        answer = view["answers"]["answers"]["q3"]
        self.assertEqual(answer["value"], ["table", "note"])
        self.assertEqual(answer["user_selected"], ["table"])
        self.assertEqual(view["pending_input_ids"], [])

    def test_compatible_recommendation_completes_multi_and_records_human_portion(self):
        self.pending(["chart"])
        view = core.recommend(self.root)
        self.assertEqual(view["answers"]["answers"]["q3"]["user_selected"], ["chart"])
        self.assertTrue(view["ready_to_build"])

    def test_plain_ai_answer_cannot_bypass_partial_human_input_protection(self):
        self.pending(["table"])
        with self.assertRaises(core.BuilderError) as caught:
            core.answer_one(self.root, "q3", ["chart", "note"], actor="ai", rationale="A different preferred combination")
        self.assertEqual(caught.exception.code, "protected_input")
        self.assertEqual(core.status(self.root)["answers"]["pending_inputs"]["q3"]["selected"], ["table"])

    def test_question_revision_invalidates_partial_input(self):
        self.pending(["table"])
        data = core.status(self.root)["questionnaire"]
        data["questions"][2]["options"][-1]["effect"] = "Produce a different table interpretation"
        view = core.set_questions(self.root, data)
        self.assertNotIn("q3", view["answers"].get("pending_inputs", {}))
        self.assertTrue(any(x.get("pending_input", {}).get("selected") == ["table"] for x in view["answers"]["history"]))

    def test_replacing_partial_input_keeps_the_previous_selection_in_history(self):
        self.pending(["table"])
        boot = self.boot()
        boot["drafts"] = {"q3": {"selected": ["chart"], "other_enabled": False, "other_text": ""}}
        view = core.import_answers(self.root, boot)
        self.assertEqual(view["answers"]["pending_inputs"]["q3"]["selected"], ["chart"])
        self.assertTrue(any(x.get("pending_input", {}).get("selected") == ["table"] for x in view["answers"]["history"]))

    def test_parent_change_invalidates_partial_dependent_input(self):
        self.pending(["table"], dependency=True)
        view = core.answer_one(self.root, "q1", "no")
        self.assertNotIn("q3", view["answers"].get("pending_inputs", {}))
        self.assertEqual(view["states"]["q3"], "inactive")

    def test_malformed_partial_selection_does_not_modify_state(self):
        self.multi()
        boot = self.boot()
        boot["drafts"] = {"q3": {"selected": ["missing"], "other_enabled": False, "other_text": ""}}
        before = core.status(self.root)["answers"]
        with self.assertRaises(core.BuilderError):
            core.import_answers(self.root, boot)
        self.assertEqual(core.status(self.root)["answers"], before)

    def test_blank_other_can_coexist_with_valid_multi_answer(self):
        boot = self.boot()
        boot["view"]["answers"]["answers"]["q3"] = {"status": "answered", "actor": "user", "question_version": 1, "value": ["note"], "rationale": ""}
        boot["drafts"] = {"q3": {"selected": ["note"], "other_enabled": True, "other_text": ""}}
        view = core.import_answers(self.root, boot)
        self.assertEqual(view["answers"]["answers"]["q3"]["value"], ["note"])
        self.assertEqual(view["pending_input_ids"], [])

    def test_reset_retains_questions_and_archives_complete_and_partial_answers(self):
        self.pending(["table"])
        before = core.status(self.root)["questionnaire"]
        view = core.reset_answers(self.root)
        self.assertEqual(view["questionnaire"], before)
        self.assertEqual(view["answers"]["answers"], {})
        self.assertEqual(view["answers"].get("pending_inputs"), {})
        self.assertTrue(any(x.get("pending_input") for x in view["answers"]["history"]))
        self.assertEqual(core.reset_answers(self.root)["answers"], view["answers"])

    def test_legacy_deferral_is_rejected_without_modifying_saved_files(self):
        answers = core.read_json(self.root / "answers.json")
        answers["answers"]["q1"] = {"status": "deferred", "actor": "user", "question_version": 1, "rationale": "Historical preference"}
        core.atomic_json(self.root / "answers.json", answers)
        before = (self.root / "answers.json").read_bytes()
        with self.assertRaises(core.BuilderError) as caught:
            core.status(self.root)
        self.assertEqual(caught.exception.code, "unsupported_answer_status")
        self.assertEqual((self.root / "answers.json").read_bytes(), before)

    def conditional_custom_multi(self, *, partial=False):
        data = core.status(self.root)["questionnaire"]
        data["questions"][1]["when"] = [{"question_id": "q3", "includes": "note"}]
        if partial:
            data["questions"][2]["min_choices"] = 2
            data["questions"][2]["recommendation"]["value"] = ["note", "chart"]
        data["questions"].append({"id": "q4", "version": 1, "group_id": "scope", "type": "text",
            "title": "Nested preference", "decision": "Nested behavior", "origin": "user", "source_ids": [],
            "when": [{"question_id": "q2", "equals": "Keep my exact environment choice"}]})
        core.set_questions(self.root, data)
        core.answer_one(self.root, "q1", "no")
        core.answer_one(self.root, "q3", {"other": ".", "selected": ["note"]})
        core.answer_one(self.root, "q2", "Keep my exact environment choice")
        core.answer_one(self.root, "q4", "Keep the nested human choice too")
        return copy.deepcopy(core.status(self.root)["answers"]["answers"])

    def test_interpreting_custom_multi_preserves_known_active_human_descendants(self):
        before = self.conditional_custom_multi()
        view = core.interpret_answer(self.root, "q3", ["note"], "The extra text adds no separate branch.")
        self.assertEqual(view["answers"]["answers"]["q2"], before["q2"])
        self.assertEqual(view["answers"]["answers"]["q4"], before["q4"])
        self.assertNotIn("q2", core.recommend(self.root)["filled"])

    def test_resolving_only_other_preserves_known_active_human_descendants(self):
        before = self.conditional_custom_multi()
        view = core.resolve_input(self.root, "q3", "The dot has no additional meaning in this output question.")
        self.assertEqual(view["answers"]["answers"]["q3"]["value"], ["note"])
        self.assertEqual(view["answers"]["answers"]["q2"], before["q2"])
        self.assertEqual(view["answers"]["answers"]["q4"], before["q4"])

    def test_resolve_to_pending_save_restore_and_ai_completion_preserve_explicit_branch(self):
        before = self.conditional_custom_multi(partial=True)
        view = core.resolve_input(self.root, "q3", "The dot is not an additional output preference.")
        self.assertEqual(view["pending_input_ids"], ["q3"])
        self.assertEqual(view["states"]["q2"], "active")
        self.assertEqual(view["answers"]["answers"]["q2"], before["q2"])
        boot = self.boot()
        imported = core.import_answers(self.root, boot)
        self.assertEqual(imported["answers"]["answers"]["q2"], before["q2"])
        html = '<script id="skill-builder-data" type="application/json">' + json.dumps(boot).replace("<", "\\u003c") + '</script>'
        file = self.parent / "pending.html"
        file.write_text(html, encoding="utf-8")
        restored = self.parent / "pending-restored"
        snapshot = core.restore_html(restored, file)
        self.assertEqual(snapshot["answers"]["answers"]["q2"], before["q2"])
        for workspace in (self.root, restored):
            completed = core.recommend(workspace)
            self.assertTrue(completed["ready_to_build"])
            self.assertEqual(completed["answers"]["answers"]["q2"], before["q2"])
            self.assertEqual(completed["answers"]["answers"]["q4"], before["q4"])

    def test_explicit_complete_input_preserves_human_child_on_known_selected_branch(self):
        before = self.conditional_custom_multi(partial=True)
        core.resolve_input(self.root, "q3", "The dot has no interpretable meaning.")
        view = core.complete_input(self.root, "q3", ["note", "chart"], "Keep the selected note and add a chart.")
        self.assertEqual(view["answers"]["answers"]["q2"], before["q2"])
        self.assertEqual(view["answers"]["answers"]["q4"], before["q4"])


if __name__ == "__main__":
    unittest.main()
