"""AI handoff and explicit reset preserve user decisions and durable workflow state."""
from __future__ import annotations

import copy
import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

PACKAGE = Path(__file__).resolve().parents[1] / "any-skill-builder"
sys.path.insert(0, str(PACKAGE / "scripts"))
import builder_core as core
from builder_server import QuestionnaireHandler, QuestionnaireServer


class DelegationTests(unittest.TestCase):
    def setUp(self):
        cache = os.environ.get("SKILL_BUILDER_TEST_TMPDIR")
        if cache:
            Path(cache).mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="delegation-", dir=cache)
        self.parent = Path(self.temp.name)
        self.root = self.parent / "run"
        result = core.init_workspace(self.root, "Create a study skill", "hybrid")
        def question(qid, kind, dependency=None):
            q = {"id": qid, "version": 1, "group_id": "scope", "type": kind, "title": qid,
                 "decision": "Define " + qid, "origin": "proposal", "source_ids": [], "when": dependency or []}
            if kind == "single":
                q["options"] = [{"id": "yes", "label": "Yes", "effect": "Include"}, {"id": "no", "label": "No", "effect": "Omit"}]
            q["recommendation"] = {"value": "yes" if kind == "single" else "Suggested environment", "rationale": "An explicit test proposal", "assumptions": []}
            return q
        self.data = {"schema_version": 1, "project_id": result["project_id"], "revision": 1,
                     "goal": "Create a study skill", "mode": "hybrid", "groups": [{"id": "scope", "label": "Scope"}], "sources": [],
                     "questions": [question("q1", "single"), question("q2", "text", [{"question_id": "q1", "equals": "yes"}]),
                                   question("q3", "single"), question("q4", "text")]}
        core.set_questions(self.root, self.data)

    def tearDown(self):
        self.temp.cleanup()

    def partial(self):
        core.answer_one(self.root, "q1", "yes", rationale="My explicit choice")
        core.answer_one(self.root, "q2", "한글 · 日本語 · العربية", rationale="User environment")
        core.answer_one(self.root, "q3", defer=True, rationale="Revisit after reviewing alternatives")
        return core.status(self.root)

    def payload(self):
        return core.answer_envelope_version(core.status(self.root)["answers"])

    def snapshot(self):
        return {p.name: p.read_bytes() for p in self.root.iterdir() if p.is_file() and p.name != ".builder.lock"}

    def test_delegate_preserves_decisions_deferrals_history_and_mode(self):
        before = self.partial()
        result = core.request_ai(self.root, self.payload())
        self.assertEqual(result["event"], "ai_requested")
        self.assertEqual(result["scope"], "unanswered")
        self.assertEqual(result["view"], before)
        self.assertEqual(result["request"]["protected_question_ids"], ["q1", "q2", "q3"])
        self.assertEqual(result["request"]["unanswered_question_ids"], ["q4"])
        self.assertFalse(result["view"]["traversal_complete"])
        self.assertEqual(core.read_json(self.root / "ai-request.json"), result["request"])
        filled = core.recommend(self.root)
        self.assertEqual(filled["filled"], ["q4"])
        for qid, record in before["answers"]["answers"].items():
            self.assertEqual(filled["answers"]["answers"][qid], record)
        self.assertEqual(filled["answers"]["history"], before["answers"]["history"])
        self.assertFalse(filled["ready_to_build"])

    def test_browser_recovery_file_cannot_submit_delegate_or_reset(self):
        view = self.partial()
        draft = {"action": "restore_draft", "answers": view["answers"],
                 "partial_multi": {"unfinished": ["first-choice"]}, "reset_pending": True}
        before = self.snapshot()
        for operation in (core.import_answers, core.request_ai, core.reset_answers):
            with self.subTest(operation=operation.__name__):
                with self.assertRaises(core.BuilderError) as error:
                    operation(self.root, draft)
                self.assertEqual(error.exception.code, "browser_draft")
                self.assertIn("same questionnaire", str(error.exception))
                self.assertEqual(self.snapshot(), before)
        path = self.parent / "browser-draft.json"
        path.write_text(json.dumps(draft), encoding="utf-8")
        result = subprocess.run([sys.executable, "-B", str(PACKAGE / "scripts" / "skill_builder.py"),
                                 "import-answers", "--workspace", str(self.root), "--input", str(path)],
                                capture_output=True, text=True, encoding="utf-8", timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stderr)["error"], "browser_draft")
        self.assertEqual(self.snapshot(), before)

    def test_delegate_same_live_request_is_idempotent_without_history_writes(self):
        payload = self.payload()
        first = core.request_ai(self.root, payload)
        saved = self.snapshot()
        second = core.request_ai(self.root, payload)
        self.assertEqual(second, first)
        self.assertEqual(self.snapshot(), saved)

    def test_stale_foreign_and_malformed_requests_do_not_change_files(self):
        self.partial()
        valid = self.payload()
        bad = [dict(valid, run_id="00000000-0000-0000-0000-000000000000"), dict(valid, project_id="another"),
               dict(valid, revision=99), dict(valid, base_answer_revision=0), [], dict(valid, changes={})]
        for operation in (core.request_ai, core.reset_answers):
            for payload in bad:
                with self.subTest(operation=operation.__name__, payload=payload):
                    before = self.snapshot()
                    with self.assertRaises(core.BuilderError):
                        operation(self.root, payload)
                    self.assertEqual(self.snapshot(), before)

    def test_offline_delegate_imports_user_edits_once_and_requests_only_missing(self):
        envelope = core.status(self.root)["answers"]
        envelope["answers"]["q1"] = {"status": "answered", "actor": "user", "question_version": 1, "value": "no", "rationale": "Keep execution out"}
        envelope["answers"]["q3"] = {"status": "deferred", "actor": "user", "question_version": 1, "rationale": "Need more options"}
        request = {"action": "delegate_unanswered", "answers": envelope}
        result = core.request_ai(self.root, request)
        self.assertEqual(result["request"]["unanswered_question_ids"], ["q4"])
        self.assertEqual(result["request"]["protected_question_ids"], ["q1", "q3"])
        self.assertEqual(result["view"]["answers"]["answers"], envelope["answers"])
        before = self.snapshot()
        self.assertEqual(core.request_ai(self.root, request), result)
        self.assertEqual(self.snapshot(), before)
        core.answer_one(self.root, "q4", "Later user answer")
        before = self.snapshot()
        with self.assertRaises(core.BuilderError):
            core.request_ai(self.root, request)
        self.assertEqual(self.snapshot(), before)

    def test_invalid_offline_reset_delegate_is_atomic(self):
        self.partial()
        envelope = core.status(self.root)["answers"]
        envelope["answers"] = {"q2": {"status": "answered", "actor": "user", "question_version": 1, "rationale": "", "value": "Parent is missing"}}
        before = self.snapshot()
        with self.assertRaisesRegex(core.BuilderError, "inactive or waiting"):
            core.request_ai(self.root, {"action": "delegate_unanswered", "answers": envelope, "reset_all": True})
        self.assertEqual(self.snapshot(), before)

    def test_offline_foreign_stale_and_invalid_reset_history_leave_state_untouched(self):
        self.partial()
        original = {"action": "delegate_unanswered", "answers": core.status(self.root)["answers"], "reset_all": True}
        invalid = []
        for key, value in (("run_id", "00000000-0000-0000-0000-000000000000"), ("project_id", "another"), ("revision", 99), ("answer_revision", 0)):
            item = copy.deepcopy(original)
            item["answers"][key] = value
            invalid.append(item)
        item = copy.deepcopy(original)
        item["reset_all"] = "true"
        invalid.append(item)
        item = copy.deepcopy(original)
        item["answers"]["history"].append({"question_id": "not-a-question", "reason": "browser_reset_all", "answer": {}, "at": "now"})
        invalid.append(item)
        for request in invalid:
            with self.subTest(request=request):
                before = self.snapshot()
                with self.assertRaises(core.BuilderError):
                    core.request_ai(self.root, request)
                self.assertEqual(self.snapshot(), before)

    def test_reset_archives_every_answer_and_deferral_without_changing_questions(self):
        before = self.partial()
        question_bytes = (self.root / "questions.json").read_bytes()
        payload = self.payload()
        result = core.reset_answers(self.root, payload)
        self.assertEqual((self.root / "questions.json").read_bytes(), question_bytes)
        self.assertEqual(result["answers"]["answers"], {})
        self.assertEqual(result["answers"]["answer_revision"], before["answers"]["answer_revision"] + 1)
        archived = {entry["question_id"]: entry["answer"] for entry in result["answers"]["history"] if entry["reason"] == "user_reset"}
        self.assertEqual(archived, before["answers"]["answers"])
        self.assertFalse((self.root / "ai-request.json").exists())
        saved = self.snapshot()
        self.assertEqual(core.reset_answers(self.root, payload), result)
        self.assertEqual(core.reset_answers(self.root), result)
        self.assertEqual(self.snapshot(), saved)

    def test_reset_preserves_prior_submission_and_invalidates_pending_request(self):
        core.recommend(self.root)
        core.submission(self.root, self.payload())
        old = core.read_json(self.root / "submission.json")
        requested = core.request_ai(self.root)
        result = core.reset_answers(self.root)
        self.assertEqual(core.read_json(self.root / "submission-history.json"), [old])
        self.assertEqual(core.read_json(self.root / "submission.json")["event"], "answers_reset")
        self.assertEqual(core.read_json(self.root / "ai-request.json"), requested["request"])
        self.assertNotEqual(requested["request"]["answer_revision"], result["answers"]["answer_revision"])

    def test_offline_reset_keeps_browser_only_history_and_post_reset_answers(self):
        self.partial()
        envelope = core.status(self.root)["answers"]
        snapshot = {"status": "answered", "actor": "user", "question_version": 1, "rationale": "Offline rationale", "value": "Browser-only answer"}
        envelope["history"].append({"question_id": "q4", "answer": snapshot, "reason": "browser_reset_all", "at": "2026-11-14T00:00:00.000Z"})
        envelope["answers"] = {"q1": {"status": "answered", "actor": "user", "question_version": 1, "rationale": "New deliberate choice", "value": "no"}}
        request = {"action": "delegate_unanswered", "answers": envelope, "reset_all": True}
        result = core.request_ai(self.root, request)
        self.assertEqual(result["view"]["answers"]["answers"], envelope["answers"])
        browser = [item for item in result["view"]["answers"]["history"] if item.get("source") == "offline_reset_export"]
        self.assertEqual(len(browser), 1)
        self.assertEqual(browser[0]["answer"], snapshot)
        self.assertEqual(result["request"]["unanswered_question_ids"], ["q3", "q4"])
        self.assertEqual(core.request_ai(self.root, request), result)

    def test_reset_wrapper_is_accepted_by_import_and_preserves_old_question_history(self):
        envelope = core.status(self.root)["answers"]
        snapshot = {"status": "answered", "actor": "user", "question_version": 1, "rationale": "", "value": "Old offline text"}
        envelope["history"] = [{"question_id": "q4", "answer": snapshot, "reason": "browser_reset_all", "at": "2026-11-14T00:00:00Z"}]
        first = core.import_answers(self.root, {"action": "reset_answers", "answers": envelope})
        updated = copy.deepcopy(first["questionnaire"])
        updated["questions"] = [q for q in updated["questions"] if q["id"] != "q4"]
        changed = core.set_questions(self.root, updated)
        second = core.import_answers(self.root, {"action": "reset_answers", "answers": changed["answers"]})
        self.assertEqual(second["answers"]["history"], first["answers"]["history"])

    def test_journal_recovers_request_and_import_together_after_interrupted_write(self):
        envelope = core.status(self.root)["answers"]
        envelope["answers"]["q1"] = {"status": "answered", "actor": "user", "question_version": 1, "rationale": "", "value": "no"}
        request = {"action": "delegate_unanswered", "answers": envelope}
        original = core.atomic_json
        def interrupt(path, value):
            if Path(path).name == "ai-request.json":
                raise OSError("Simulated interruption before event write")
            original(path, value)
        with patch.object(core, "atomic_json", interrupt), self.assertRaises(OSError):
            core.request_ai(self.root, request)
        self.assertTrue((self.root / ".pending-state.json").exists())
        view = core.status(self.root)
        record = core.read_json(self.root / "ai-request.json")
        self.assertEqual(view["answers"]["answers"], envelope["answers"])
        self.assertEqual(record["answer_revision"], view["answers"]["answer_revision"])
        self.assertFalse((self.root / ".pending-state.json").exists())
        self.assertEqual(core.request_ai(self.root, request)["request"], record)

    def test_http_reset_keeps_server_active_then_delegate_returns_host_event(self):
        self.partial()
        server = QuestionnaireServer(self.root)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()
        def post(route, payload):
            conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
            conn.request("POST", route + "?token=" + server.token, json.dumps(payload), {"Content-Type": "application/json"})
            response = conn.getresponse()
            result = response.status, json.loads(response.read())
            conn.close()
            return result
        try:
            old_payload = self.payload()
            self.assertEqual(post("/api/reset", old_payload)[0], 200)
            self.assertTrue(thread.is_alive())
            self.assertIsNone(server.final_event)
            self.assertEqual(post("/api/delegate", old_payload)[0], 409)
            code, response = post("/api/delegate", self.payload())
            self.assertEqual((code, response["event"]), (200, "ai_requested"))
            thread.join(3)
            self.assertFalse(thread.is_alive())
            self.assertEqual(server.final_event["scope"], "unanswered")
            self.assertEqual(server.final_event["protected_question_ids"], [])
        finally:
            if thread.is_alive():
                server.shutdown()
            server.server_close()

    def test_durable_handoff_survives_disconnected_response(self):
        server = QuestionnaireServer(self.root)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()
        original = QuestionnaireHandler._send
        def broken(handler, code, payload, *args, **kwargs):
            if isinstance(payload, dict) and payload.get("event") == "ai_requested":
                raise BrokenPipeError("Client disconnected")
            return original(handler, code, payload, *args, **kwargs)
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
        try:
            with patch.object(QuestionnaireHandler, "_send", broken):
                conn.request("POST", "/api/delegate?token=" + server.token, json.dumps(self.payload()), {"Content-Type": "application/json"})
                with self.assertRaises(http.client.RemoteDisconnected):
                    conn.getresponse()
                thread.join(3)
            self.assertFalse(thread.is_alive())
            self.assertEqual(server.final_event["event"], "ai_requested")
            self.assertTrue((self.root / "ai-request.json").is_file())
        finally:
            conn.close()
            if thread.is_alive():
                server.shutdown()
            server.server_close()

    def test_cli_delegation_and_reset_export_commands(self):
        self.partial()
        script = PACKAGE / "scripts/skill_builder.py"
        for command in ("delegate", "reset-answers"):
            result = subprocess.run([sys.executable, "-B", str(script), command, "--workspace", str(self.root)],
                                    capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stderr)
            body = json.loads(result.stdout)
            self.assertEqual(body.get("event"), "ai_requested" if command == "delegate" else None)
        self.assertEqual(core.status(self.root)["answers"]["answers"], {})
        path = self.parent / "delegate.json"
        core.atomic_json(path, {"action": "delegate_unanswered", "answers": core.status(self.root)["answers"]})
        result = subprocess.run([sys.executable, "-B", str(script), "delegate", "--workspace", str(self.root), "--input", str(path)],
                                capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["event"], "ai_requested")


if __name__ == "__main__":
    unittest.main()
