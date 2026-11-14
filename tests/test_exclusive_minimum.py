"""Exclusive choices complete multi-select answers without weakening other limits."""
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


class ExclusiveMinimumTests(unittest.TestCase):
    def setUp(self):
        cache = os.environ.get("SKILL_BUILDER_TEST_TMPDIR")
        if cache:
            Path(cache).mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="exclusive-minimum-", dir=cache)
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name)
        self.root = self.parent / "run"
        initialized = core.init_workspace(self.root, "Choose supporting sections")
        self.question = {
            "id": "extras", "version": 1, "group_id": "output", "type": "multi",
            "title": "Choose two sections, or omit them", "decision": "Supporting sections",
            "origin": "proposal", "source_ids": [], "min_choices": 2, "max_choices": 2,
            "options": [{"id": option, "label": option, "effect": "Include " + option}
                        for option in ("a", "b", "none")]
                       + [{"id": "omit", "label": "No supporting sections", "effect": "Omit sections", "exclusive": True}],
            "recommendation": {"value": ["omit"], "rationale": "The required output is sufficient", "assumptions": []},
        }
        self.data = {
            "schema_version": 1, "project_id": initialized["project_id"], "revision": 1,
            "goal": "Choose supporting sections", "mode": "questionnaire",
            "groups": [{"id": "output", "label": "Output"}], "sources": [], "questions": [self.question],
        }
        core.set_questions(self.root, self.data)

    def boot(self):
        rendered = core.render_html(self.root)
        raw = rendered.split('<script id="skill-builder-data" type="application/json">', 1)[1].split('</script>', 1)[0]
        boot = json.loads(raw)
        boot.update(saved_at="2026-11-15T10:00:00Z", export_id=str(uuid.uuid4()))
        return boot

    def draft(self, selected):
        return {"selected": selected, "other_enabled": False, "other_text": ""}

    def save(self, boot):
        path = self.parent / "saved.html"
        raw = json.dumps(boot).replace("<", "\\u003c")
        path.write_text('<!doctype html><script id="skill-builder-data" type="application/json">' + raw + '</script>', encoding="utf-8")
        return path

    def test_exclusive_answer_and_recommendation_are_complete(self):
        view = core.answer_one(self.root, "extras", ["omit"])
        self.assertTrue(view["ready_to_build"])
        self.assertEqual(view["answers"]["answers"]["extras"]["actor"], "user")
        core.answer_one(self.root, "extras", clear=True)
        recommended = core.recommend(self.root)
        self.assertEqual(recommended["filled"], ["extras"])
        self.assertTrue(recommended["ready_to_build"])
        self.assertEqual(recommended["answers"]["answers"]["extras"]["value"], ["omit"])

    def test_only_explicit_sole_exclusive_bypasses_minimum(self):
        core.validate_value(self.question, ["omit"])
        core.validate_value(self.question, ["a", "b"])
        for value in ([], ["a"], ["none"], ["omit", "a"], ["omit", "omit"], ["missing"], ["a", "b", "none"]):
            with self.subTest(value=value), self.assertRaises(core.BuilderError):
                core.validate_value(self.question, value)

    def test_custom_answers_preserve_exclusive_and_maximum_constraints(self):
        core.validate_value(self.question, {"other": "A custom section", "selected": []})
        core.validate_value(self.question, {"other": "A custom section", "selected": ["a"]})
        for selected in (["omit"], ["omit", "a"], ["a", "b", "none"]):
            with self.subTest(selected=selected), self.assertRaises(core.BuilderError):
                core.validate_value(self.question, {"other": "A custom section", "selected": selected})

    def test_saved_answer_import_resume_and_restore_preserve_exclusive(self):
        boot = self.boot()
        boot["view"]["answers"]["answers"]["extras"] = {
            "status": "answered", "actor": "user", "question_version": 1, "rationale": "", "value": ["omit"],
        }
        path = self.save(boot)
        view = core.import_answers(self.root, path)
        self.assertTrue(view["ready_to_build"])
        self.assertFalse(view["answers"].get("pending_inputs"))
        self.assertEqual(core.recommend(self.root)["filled"], [])
        self.assertEqual(core.resume(self.root, path)["event"], "already_imported")
        restored = core.restore_html(self.parent / "restored", path)
        self.assertTrue(restored["ready_to_build"])
        self.assertEqual(restored["answers"]["answers"]["extras"]["value"], ["omit"])

    def test_legacy_exclusive_draft_becomes_user_answer(self):
        boot = self.boot()
        boot["drafts"] = {"extras": self.draft(["omit"])}
        view = core.import_answers(self.root, self.save(boot))
        self.assertTrue(view["ready_to_build"])
        self.assertFalse(view["answers"].get("pending_inputs"))
        self.assertEqual(view["answers"]["answers"]["extras"]["value"], ["omit"])
        self.assertEqual(view["answers"]["answers"]["extras"]["actor"], "user")
        with self.assertRaisesRegex(core.BuilderError, "No incomplete input"):
            core.complete_input(self.root, "extras", ["omit"], "Already complete")

    def test_legacy_exclusive_draft_cannot_replace_conflicting_answer_or_newer_clear(self):
        boot = self.boot()
        boot["drafts"] = {"extras": self.draft(["omit"])}
        conflicting = copy.deepcopy(boot)
        conflicting["view"]["answers"]["answers"]["extras"] = {
            "status": "answered", "actor": "user", "question_version": 1, "rationale": "", "value": ["a", "b"],
        }
        with self.assertRaisesRegex(core.BuilderError, "conflicts with its answer"):
            core.import_answers(self.root, conflicting)
        core.answer_one(self.root, "extras", ["omit"])
        cleared = core.answer_one(self.root, "extras", clear=True)
        with self.assertRaises(core.BuilderError) as caught:
            core.import_answers(self.root, boot)
        self.assertEqual(caught.exception.code, "stale_answers")
        self.assertEqual(core.status(self.root)["answers"], cleared["answers"])

    def test_invalid_exclusive_drafts_are_rejected(self):
        for selected, text in ((["omit", "a"], ""), (["omit"], "Custom direction")):
            boot = self.boot()
            boot["drafts"] = {"extras": {**self.draft(selected), "other_enabled": bool(text), "other_text": text}}
            with self.subTest(selected=selected, text=text), self.assertRaises(core.BuilderError):
                core.import_answers(self.root, boot)
        pending = {"extras": {**self.draft(["omit"]), "question_version": 1}}
        with self.assertRaisesRegex(core.BuilderError, "Exclusive pending"):
            core.validate_pending_inputs(self.data, pending)

    def test_ordinary_under_minimum_stays_pending_and_completion_retains_it(self):
        boot = self.boot()
        boot["drafts"] = {"extras": self.draft(["a"])}
        view = core.import_answers(self.root, boot)
        self.assertFalse(view["ready_to_build"])
        self.assertNotIn("extras", view["answers"]["answers"])
        self.assertEqual(view["answers"]["pending_inputs"]["extras"]["selected"], ["a"])
        self.assertEqual(core.recommend(self.root)["filled"], [])
        with self.assertRaisesRegex(core.BuilderError, "preserve user selections"):
            core.complete_input(self.root, "extras", ["omit"], "Replace explicit choice")
        with self.assertRaisesRegex(core.BuilderError, "cannot be combined"):
            core.complete_input(self.root, "extras", ["a", "omit"], "Conflicting completion")
        view = core.complete_input(self.root, "extras", ["a", "b"], "Keep the selected section and add supporting detail")
        self.assertTrue(view["ready_to_build"])
        self.assertEqual(view["answers"]["answers"]["extras"]["user_selected"], ["a"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
