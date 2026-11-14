"""Host receipts and last-observed progress remain bound to accepted run state."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

PACKAGE = Path(__file__).resolve().parents[1] / "any-skill-builder"
sys.path.insert(0, str(PACKAGE / "scripts"))
import builder_core as core


class HandoffTests(unittest.TestCase):
    def setUp(self):
        cache = os.environ.get("SKILL_BUILDER_TEST_TMPDIR")
        if cache:
            Path(cache).mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="handoff-", dir=cache)
        self.root = Path(self.temp.name) / "run"
        initialized = core.init_workspace(self.root, "Create a useful study skill")
        self.data = {
            "schema_version": 1, "project_id": initialized["project_id"], "revision": 1,
            "goal": "Create a useful study skill", "mode": "user", "locale": {"language": "en", "direction": "ltr"},
            "groups": [{"id": "scope", "label": "Direction"}], "sources": [],
            "questions": [
                {"id": "scope", "version": 1, "group_id": "scope", "type": "single", "importance": "core",
                 "title": "Include related work?", "decision": "Which sources to inspect", "origin": "proposal", "source_ids": [], "when": [],
                 "options": [{"id": "yes", "label": "Include", "effect": "Search relevant related work"},
                             {"id": "no", "label": "Supplied only", "effect": "Review supplied sources only"}],
                 "recommendation": {"value": "yes", "rationale": "A reasoned test recommendation"}},
                {"id": "detail", "version": 1, "group_id": "scope", "type": "text", "title": "Output details",
                 "decision": "Useful output shape", "origin": "proposal", "source_ids": [], "when": [],
                 "recommendation": {"value": "Useful findings and next steps", "rationale": "Support action"}},
            ],
        }
        core.set_questions(self.root, self.data)

    def tearDown(self):
        self.temp.cleanup()

    def workflow(self):
        return core.status(self.root, include_workflow=True)["workflow"]

    def complete(self):
        core.answer_one(self.root, "scope", "yes")
        core.answer_one(self.root, "detail", "A practical summary")

    def ack(self, record):
        return core.acknowledge(self.root, record["request_id"], record["revision"], record["answer_revision"])

    def checkpoint(self, *args, **kwargs):
        view = core.status(self.root)
        kwargs.setdefault("revision", view["questionnaire"]["revision"])
        kwargs.setdefault("answer_revision", view["answers"]["answer_revision"])
        return core.checkpoint(self.root, *args, **kwargs)

    def snapshot(self):
        return {p.name: p.read_bytes() for p in self.root.iterdir() if p.is_file() and p.name != ".builder.lock"}

    def cli(self, *args):
        result = subprocess.run([sys.executable, "-B", str(PACKAGE / "scripts/skill_builder.py"), *args, "--workspace", str(self.root)],
                                capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        return json.loads(result.stdout)

    def test_core_questions_are_recommended_and_delegated_without_requiring_user_answer(self):
        requested = core.request_ai(self.root)["request"]
        self.assertIn("scope", requested["unanswered_question_ids"])
        self.assertIsNone(self.workflow()["handoff"]["record"]["receipt"])
        filled = core.recommend(self.root)
        self.assertEqual(filled["answers"]["answers"]["scope"]["actor"], "ai")
        self.assertTrue(filled["ready_to_build"])

    def test_importance_defaults_and_validates_without_adding_to_legacy_data(self):
        self.assertNotIn("importance", core.status(self.root)["questionnaire"]["questions"][1])
        for value in ("mandatory", None, [], 1):
            data = copy.deepcopy(self.data)
            data["questions"][0]["importance"] = value
            with self.subTest(value=value), self.assertRaises(core.BuilderError):
                core.set_questions(self.root, data)

    def test_explicit_display_importance_change_preserves_answer(self):
        self.complete()
        before = core.status(self.root)["answers"]["answers"]
        data = copy.deepcopy(core.status(self.root)["questionnaire"])
        data["questions"][1]["importance"] = "core"
        updated = core.set_questions(self.root, data, presentation_only=["detail"])
        self.assertEqual(updated["answers"]["answers"], before)

    def test_submit_registers_receipt_pending_then_host_ack_is_idempotent(self):
        self.complete()
        first = core.submission(self.root)
        request = first["request"]
        core.valid_run_id(request["request_id"])
        self.assertTrue(self.workflow()["handoff"]["current"])
        self.assertFalse(self.workflow()["handoff"]["receipt_current"])
        receipt = self.ack(request)
        self.assertEqual(receipt["receipt"]["request_id"], request["request_id"])
        saved = self.snapshot()
        self.assertEqual(self.ack(request), receipt)
        self.assertEqual(core.submission(self.root), first)
        self.assertEqual(self.snapshot(), saved)
        self.assertTrue(self.workflow()["handoff"]["receipt_current"])

    def test_wrong_id_versions_and_changed_answers_do_not_acknowledge(self):
        request = core.request_ai(self.root)["request"]
        for rid, rev, arev in [("00000000-0000-0000-0000-000000000000", request["revision"], request["answer_revision"]),
                               (request["request_id"], request["revision"] + 1, request["answer_revision"]),
                               (request["request_id"], request["revision"], request["answer_revision"] + 1)]:
            before = self.snapshot()
            with self.assertRaises(core.BuilderError):
                core.acknowledge(self.root, rid, rev, arev)
            self.assertEqual(before, self.snapshot())
        core.answer_one(self.root, "scope", "yes")
        with self.assertRaises(core.BuilderError):
            self.ack(request)
        self.assertFalse(self.workflow()["handoff"]["current"])
        self.assertFalse(self.workflow()["handoff"]["receipt_current"])

    def test_reset_supersedes_ack_and_checkpoint_without_erasing_history(self):
        request = core.request_ai(self.root)["request"]
        self.ack(request)
        self.checkpoint(4, "Read submitted answers", "Resolve unanswered decisions", ["Decide scope"], request["request_id"])
        core.reset_answers(self.root)
        self.assertFalse(self.workflow()["handoff"]["current"])
        self.assertFalse(self.workflow()["progress"]["current"])
        for action in (lambda: self.ack(request), lambda: self.checkpoint(4, "Stale work", "Continue", request_id=request["request_id"])):
            before = self.snapshot()
            with self.assertRaises(core.BuilderError):
                action()
            self.assertEqual(before, self.snapshot())
        self.assertEqual(core.read_json(self.root / "handoff.json")["receipt"]["request_id"], request["request_id"])

    def test_changed_questions_and_replaced_submission_reject_old_request(self):
        request = core.request_ai(self.root)["request"]
        self.ack(request)
        changed = copy.deepcopy(core.status(self.root)["questionnaire"])
        changed["questions"][0]["help"] = "New scope context"
        core.set_questions(self.root, changed)
        with self.assertRaises(core.BuilderError):
            self.checkpoint(4, "Old design", "Continue", request_id=request["request_id"])
        newest = core.request_ai(self.root)["request"]
        self.assertNotEqual(newest["request_id"], request["request_id"])
        self.assertEqual(self.workflow()["handoff"]["history_count"], 1)
        with self.assertRaises(core.BuilderError):
            self.ack(request)

    def test_ack_before_ai_fill_then_checkpoint_records_new_snapshot(self):
        request = core.request_ai(self.root)["request"]
        with self.assertRaises(core.BuilderError):
            self.checkpoint(4, "Not yet read", "Decide", request_id=request["request_id"])
        self.ack(request)
        filled = core.recommend(self.root)
        self.assertFalse(self.workflow()["handoff"]["receipt_current"])
        saved = self.checkpoint(5, "Decisions resolved", "Create the skill", [], request["request_id"])
        self.assertEqual(saved["progress"]["answer_revision"], filled["answers"]["answer_revision"])
        self.assertTrue(self.workflow()["progress"]["current"])
        self.checkpoint(6, "Instructions drafted", "Verify package", ["Check resources"], request["request_id"])
        self.assertEqual(self.workflow()["progress"]["history_count"], 1)
        self.assertNotIn("running", saved["progress"])

    def test_offline_import_is_not_a_submission_and_cli_explicitly_accepts_it(self):
        answers = core.status(self.root)["answers"]
        for qid, value in [("scope", "no"), ("detail", "Summary")]:
            answers["answers"][qid] = {"status": "answered", "actor": "user", "question_version": 1, "rationale": "", "value": value}
        core.import_answers(self.root, answers)
        self.assertIsNone(self.workflow()["handoff"])
        result = self.cli("submit")
        request = result["request"]
        ack = self.cli("acknowledge", "--request-id", request["request_id"], "--revision", str(request["revision"]),
                       "--answer-revision", str(request["answer_revision"]))
        self.assertEqual(ack["event"], "acknowledged")
        self.cli("checkpoint", "--stage", "5", "--revision", str(request["revision"]), "--answer-revision", str(request["answer_revision"]),
                 "--summary", "Answers read", "--next-action", "Prepare build brief",
                 "--remaining", "Confirm resource paths", "--request-id", request["request_id"])
        state = self.cli("status", "--json")
        self.assertTrue(state["workflow"]["handoff"]["receipt_current"])
        self.assertTrue(state["workflow"]["progress"]["current"])

    def test_deferred_submission_registers_same_receipt_protocol(self):
        core.answer_one(self.root, "scope", defer=True)
        core.answer_one(self.root, "detail", "A concise result")
        accepted = core.submission(self.root)
        self.assertEqual(accepted["event"], "deferred_review")
        self.ack(accepted["request"])
        self.assertTrue(self.workflow()["handoff"]["receipt_current"])

    def test_submit_rejects_an_ignored_answer_envelope(self):
        self.complete()
        incoming = core.status(self.root)["answers"]
        incoming["answers"]["scope"]["value"] = "no"
        saved = self.snapshot()
        with self.assertRaises(core.BuilderError):
            core.submission(self.root, {"action": "submit_answers", "answers": incoming})
        self.assertEqual(saved, self.snapshot())

    def test_new_kind_of_submission_supersedes_previous_same_version(self):
        self.complete()
        first = core.request_ai(self.root)["request"]
        self.ack(first)
        self.checkpoint(4, "Read request", "Prepare brief", request_id=first["request_id"])
        second = core.submission(self.root)["request"]
        self.assertNotEqual(first["request_id"], second["request_id"])
        self.assertFalse(self.workflow()["progress"]["current"])
        with self.assertRaises(core.BuilderError):
            self.ack(first)
        third = core.request_ai(self.root)["request"]
        self.assertNotEqual(third["request_id"], first["request_id"])
        self.assertEqual(self.workflow()["handoff"]["history_count"], 2)

    def test_submission_recovery_replays_handoff_as_one_transaction(self):
        self.complete()
        original = core.atomic_json
        def interrupted(path, value):
            if Path(path).name == "handoff.json":
                raise OSError("Simulated interruption")
            return original(path, value)
        with patch.object(core, "atomic_json", interrupted), self.assertRaises(OSError):
            core.submission(self.root)
        workflow = self.workflow()
        self.assertTrue(workflow["handoff"]["current"])
        self.assertEqual(core.read_json(self.root / "submission.json")["request_id"], workflow["handoff"]["record"]["request_id"])
        self.assertFalse((self.root / ".pending-state.json").exists())

    def test_resume_boot_contains_only_identity_and_path_not_token(self):
        html = core.render_html(self.root, "live", "secret-local-token")
        encoded = re.search(r'<script id="skill-builder-data" type="application/json">(.*?)</script>', html, re.S).group(1)
        boot = json.loads(encoded)
        self.assertEqual(set(boot["resume"]), {"workspace", "run_id", "project_id"})
        self.assertEqual(boot["resume"]["workspace"], str(self.root.resolve()))
        self.assertNotIn("secret-local-token", json.dumps(boot["resume"]))

    def test_checkpoint_before_submission_is_last_observed_and_validated(self):
        result = self.checkpoint(3, "Questions reviewed", "Open questionnaire", ["Collect answers"])
        self.assertTrue(self.workflow()["progress"]["current"])
        self.assertIsNone(result["progress"]["request_id"])
        self.assertIn("at", result["progress"])
        for stage in (0, 8, True):
            with self.subTest(stage=stage), self.assertRaises(core.BuilderError):
                self.checkpoint(stage, "Summary", "Next")
        with self.assertRaises(core.BuilderError):
            self.checkpoint(3, "Summary", "Next", [""])

    def test_checkpoint_rejects_unseen_answer_and_question_changes_before_writing(self):
        request = core.request_ai(self.root)["request"]
        self.ack(request)
        observed = core.status(self.root)
        core.answer_one(self.root, "scope", "no")
        saved = self.snapshot()
        with self.assertRaises(core.BuilderError) as failure:
            self.checkpoint(4, "Stale summary", "Build old design", request_id=request["request_id"],
                            revision=observed["questionnaire"]["revision"], answer_revision=observed["answers"]["answer_revision"])
        self.assertEqual(failure.exception.code, "stale_answers")
        self.assertEqual(self.snapshot(), saved)
        observed = core.status(self.root)
        changed = copy.deepcopy(observed["questionnaire"])
        changed["questions"][0]["title"] = "Review related research?"
        core.set_questions(self.root, changed, presentation_only=["scope"])
        saved = self.snapshot()
        with self.assertRaises(core.BuilderError) as failure:
            self.checkpoint(3, "Stale questions", "Present old form", revision=observed["questionnaire"]["revision"],
                            answer_revision=observed["answers"]["answer_revision"])
        self.assertEqual(failure.exception.code, "stale_revision")
        self.assertEqual(self.snapshot(), saved)


if __name__ == "__main__":
    unittest.main()
