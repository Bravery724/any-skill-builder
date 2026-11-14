"""Behavioral checks for skill-builder state and its local HTTP bridge."""
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

PACKAGE = Path(__file__).resolve().parents[1] / "any-skill-builder"
sys.path.insert(0, str(PACKAGE / "scripts"))
import builder_core as core
from builder_server import QuestionnaireServer

CACHE = os.environ.get("SKILL_BUILDER_TEST_TMPDIR")
if CACHE:
    CACHE = Path(CACHE)
    CACHE.mkdir(parents=True, exist_ok=True)


def questionnaire(project_id):
    return {
        "schema_version": 1, "project_id": project_id, "revision": 1, "goal": "Create a paper-analysis skill", "mode": "user",
        "groups": [{"id": "scope", "label": "Scope"}, {"id": "output", "label": "Output"}],
        "sources": [{"id": "s1", "title": "Source fixture", "url": "https://example.org/paper", "kind": "paper",
                     "status": "read", "accessed_at": "2026-11-14", "notes": "Synthetic test evidence; not a real research claim."}],
        "questions": [
            {"id": "q1", "version": 1, "group_id": "scope", "type": "single", "title": "Reproduce?",
             "decision": "Whether to execute supplied code", "origin": "inference", "source_ids": ["s1"],
             "options": [{"id": "yes", "label": "Yes", "effect": "Prepare a reproduction environment"},
                         {"id": "no", "label": "No", "effect": "Analyze without execution"}],
             "recommendation": {"value": "yes", "rationale": "Test recommendation", "assumptions": ["Test context only"]}, "when": []},
            {"id": "q2", "version": 1, "group_id": "scope", "type": "text", "title": "What environment?",
             "decision": "Which environment to target", "origin": "proposal", "source_ids": [],
             "recommendation": {"value": "Ask for runtime details when executing", "rationale": "Do not invent private hardware", "assumptions": []},
             "when": [{"question_id": "q1", "equals": "yes"}]},
            {"id": "q3", "version": 1, "group_id": "output", "type": "multi", "title": "Which outputs?",
             "decision": "Output formats", "origin": "proposal", "source_ids": [],
             "options": [{"id": "chart", "label": "Chart", "effect": "Render data charts"},
                         {"id": "note", "label": "Note", "effect": "Write research notes"},
                         {"id": "none", "label": "Neither", "effect": "Return a concise answer", "exclusive": True}],
             "recommendation": {"value": ["note"], "rationale": "A note captures evidence", "assumptions": []}, "when": []}
        ]
    }


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="case-", dir=CACHE)
        self.parent = Path(self.temp.name)
        self.root = self.parent / "run"
        result = core.init_workspace(self.root, "Create a paper-analysis skill")
        self.data = questionnaire(result["project_id"])

    def tearDown(self):
        self.temp.cleanup()

    def install(self):
        return core.set_questions(self.root, self.data)

    def request_payload(self, changes=None):
        view = core.status(self.root)
        payload = {"project_id": view["questionnaire"]["project_id"], "run_id": view["questionnaire"]["run_id"], "revision": view["questionnaire"]["revision"],
                   "base_answer_revision": view["answers"]["answer_revision"]}
        if changes is not None:
            payload["changes"] = changes
        return payload

    def test_empty_init_is_not_complete_and_cannot_overwrite(self):
        view = core.status(self.root)
        self.assertFalse(view["traversal_complete"])
        self.assertFalse(view["ready_to_build"])
        with self.assertRaises(core.BuilderError):
            core.build_brief(self.root)
        with self.assertRaises(core.BuilderError):
            core.init_workspace(self.root, "Overwrite")

    def test_unknown_source_and_dependency_cycle_rejected(self):
        bad = copy.deepcopy(self.data)
        bad["questions"][0]["source_ids"] = ["missing"]
        with self.assertRaises(core.BuilderError):
            core.set_questions(self.root, bad)
        bad = copy.deepcopy(self.data)
        bad["questions"][0]["when"] = [{"question_id": "q2", "equals": "cycle"}]
        with self.assertRaisesRegex(core.BuilderError, "Circular"):
            core.set_questions(self.root, bad)

    def test_empty_evidence_and_inaccessible_source_are_not_read_evidence(self):
        bad = copy.deepcopy(self.data)
        bad["questions"][0]["origin"] = "source"
        bad["sources"][0]["status"] = "unavailable"
        with self.assertRaisesRegex(core.BuilderError, "accessible evidence"):
            core.set_questions(self.root, bad)
        bad = copy.deepcopy(self.data)
        bad["questions"][0]["decision"] = ""
        with self.assertRaises(core.BuilderError):
            core.set_questions(self.root, bad)

    def test_conditional_states_and_deferral_completion(self):
        self.install()
        self.assertEqual(core.status(self.root)["states"]["q2"], "waiting")
        core.answer_one(self.root, "q1", defer=True)
        core.answer_one(self.root, "q3", ["note"])
        view = core.status(self.root)
        self.assertEqual(view["counts"], {"total": 3, "active": 2, "answered": 1, "deferred": 1, "unanswered": 0, "waiting": 1, "inactive": 0})
        self.assertTrue(view["traversal_complete"])
        self.assertFalse(view["ready_to_build"])
        result = core.submission(self.root, self.request_payload())
        self.assertEqual(result["event"], "deferred_review")
        with self.assertRaises(core.BuilderError):
            core.build_brief(self.root)

    def test_parent_answer_change_removes_child_and_keeps_history(self):
        self.install()
        core.answer_one(self.root, "q1", "yes")
        core.answer_one(self.root, "q2", "CPU only")
        core.answer_one(self.root, "q3", ["note"])
        view = core.answer_one(self.root, "q1", "no")
        self.assertEqual(view["states"]["q2"], "inactive")
        self.assertNotIn("q2", view["answers"]["answers"])
        self.assertTrue(any(row["question_id"] == "q2" for row in view["answers"]["history"]))
        self.assertTrue(view["ready_to_build"])
        view = core.answer_one(self.root, "q1", "yes")
        self.assertEqual(view["states"]["q2"], "active")
        self.assertNotIn("q2", view["answers"]["answers"])
        self.assertFalse(view["traversal_complete"])

    def test_clear_parent_removes_descendant_and_preserves_other_answer(self):
        self.install()
        core.recommend(self.root)
        view = core.answer_one(self.root, "q1", clear=True)
        self.assertNotIn("q1", view["answers"]["answers"])
        self.assertNotIn("q2", view["answers"]["answers"])
        self.assertIn("q3", view["answers"]["answers"])

    def test_auto_recommend_preserves_user_choice_and_deferral(self):
        self.install()
        core.answer_one(self.root, "q1", defer=True)
        core.answer_one(self.root, "q3", ["chart"])
        view = core.recommend(self.root)
        self.assertEqual(view["filled"], [])
        self.assertEqual(view["answers"]["answers"]["q3"]["value"], ["chart"])
        with self.assertRaisesRegex(core.BuilderError, "cannot overwrite"):
            core.answer_one(self.root, "q1", "yes", actor="ai", rationale="override")

    def test_auto_recommend_follows_newly_active_branch_and_brief_records_evidence(self):
        self.install()
        view = core.recommend(self.root)
        self.assertTrue(view["ready_to_build"])
        self.assertEqual(set(view["filled"]), {"q1", "q2", "q3"})
        path = Path(core.build_brief(self.root)["path"])
        body = path.read_text(encoding="utf-8")
        self.assertIn("q2 —", body)
        self.assertIn("Source fixture", body)
        self.assertIn("Assumption to retain", body)

    def test_invalid_exclusive_or_hidden_answer_rejected_without_mutation(self):
        self.install()
        baseline = core.status(self.root)["answers"]
        with self.assertRaises(core.BuilderError):
            core.answer_one(self.root, "q3", ["chart", "none"])
        with self.assertRaises(core.BuilderError):
            core.answer_one(self.root, "q2", "Parent is unanswered")
        self.assertEqual(core.status(self.root)["answers"], baseline)

    def test_revised_question_invalidates_its_descendants_only(self):
        self.install()
        core.recommend(self.root)
        replacement = copy.deepcopy(self.data)
        replacement["questions"][0]["options"][0]["label"] = "Yes, including environment setup"
        view = core.set_questions(self.root, replacement)
        self.assertEqual(view["questionnaire"]["revision"], 2)
        self.assertEqual(view["questionnaire"]["questions"][0]["version"], 2)
        self.assertEqual(set(view["answers"]["answers"]), {"q3"})
        with self.assertRaisesRegex(core.BuilderError, "current questionnaire revision"):
            core.set_questions(self.root, replacement)

    def test_stale_live_update_does_not_overwrite(self):
        self.install()
        old = self.request_payload({"q1": {"status": "answered", "value": "yes"}})
        core.answer_one(self.root, "q3", ["note"])
        with self.assertRaises(core.BuilderError) as caught:
            core.update_answers(self.root, old)
        self.assertEqual(caught.exception.status, 409)
        self.assertNotIn("q1", core.status(self.root)["answers"]["answers"])

    def test_offline_import_rejects_stale_and_forged_actor_history(self):
        self.install()
        envelope = copy.deepcopy(core.status(self.root)["answers"])
        envelope["answers"]["q1"] = {"status": "answered", "value": "no", "actor": "ai", "rationale": "Forged", "question_version": 1}
        envelope["history"] = [{"fake": "history"}]
        view = core.import_answers(self.root, envelope)
        self.assertEqual(view["answers"]["answers"]["q1"]["actor"], "user")
        self.assertFalse(any("fake" in h for h in view["answers"]["history"]))
        with self.assertRaises(core.BuilderError) as caught:
            core.import_answers(self.root, envelope)
        self.assertEqual(caught.exception.status, 409)

    def test_offline_import_restores_same_value_descendants_after_parent_edit(self):
        parent = self.data["questions"][0]
        parent["type"] = "multi"
        parent["options"] = [{"id": value, "label": value.upper(), "effect": "Enable " + value} for value in ["a", "b", "c"]]
        parent["recommendation"]["value"] = ["a", "b"]
        self.data["questions"][1]["when"] = [{"question_id": "q1", "includes": "a"}]
        self.data["questions"].append({"id": "q4", "version": 1, "group_id": "scope", "type": "text", "title": "Nested detail?",
                                       "decision": "A dependent output detail", "origin": "proposal", "source_ids": [],
                                       "when": [{"question_id": "q2", "equals": "Same answer"}]})
        self.install()
        core.answer_one(self.root, "q1", ["a", "b"])
        core.answer_one(self.root, "q2", "Same answer")
        core.answer_one(self.root, "q3", ["note"])
        core.answer_one(self.root, "q4", "Same nested answer")
        incoming = copy.deepcopy(core.status(self.root)["answers"])
        incoming["answers"]["q1"]["value"] = ["a", "c"]
        incoming["history"] = [{"fake": "untrusted imported history"}]
        view = core.import_answers(self.root, incoming)
        self.assertTrue(view["ready_to_build"])
        self.assertEqual(view["answers"]["answers"]["q2"]["value"], "Same answer")
        self.assertEqual(view["answers"]["answers"]["q4"]["value"], "Same nested answer")
        self.assertTrue(any(h["question_id"] == "q2" and h["reason"] == "parent_answer_changed" for h in view["answers"]["history"]))
        self.assertFalse(any("fake" in h for h in view["answers"]["history"]))

    def test_offline_import_rejects_final_inactive_child_even_if_unchanged(self):
        self.install()
        core.recommend(self.root)
        before = core.status(self.root)["answers"]
        incoming = copy.deepcopy(before)
        incoming["answers"]["q1"]["value"] = "no"
        with self.assertRaisesRegex(core.BuilderError, "inactive or waiting"):
            core.import_answers(self.root, incoming)
        self.assertEqual(core.status(self.root)["answers"], before)

    def test_same_folder_names_have_distinct_run_id_and_reject_cross_import(self):
        self.install()
        second = self.parent / "another-parent" / "run"
        second_init = core.init_workspace(second, "A different run with identical folder name")
        core.set_questions(second, self.data)
        first = core.status(self.root)
        other = core.status(second)
        self.assertEqual(first["questionnaire"]["project_id"], other["questionnaire"]["project_id"])
        self.assertNotEqual(first["questionnaire"]["run_id"], second_init["run_id"])
        self.assertEqual(other["questionnaire"]["run_id"], other["answers"]["run_id"])
        with self.assertRaises(core.BuilderError) as caught:
            core.import_answers(second, first["answers"])
        self.assertEqual(caught.exception.code, "wrong_run")
        payload = self.request_payload({"q1": {"status": "answered", "value": "yes"}})
        with self.assertRaises(core.BuilderError) as caught:
            core.update_answers(second, payload)
        self.assertEqual(caught.exception.code, "wrong_run")

    def test_legacy_workspace_migration_preserves_answers_and_assigns_stable_id(self):
        self.install()
        core.recommend(self.root)
        before = core.status(self.root)
        q, a = copy.deepcopy(before["questionnaire"]), copy.deepcopy(before["answers"])
        del q["run_id"]
        del a["run_id"]
        core.atomic_json(self.root / "questions.json", q)
        core.atomic_json(self.root / "answers.json", a)
        migrated = core.status(self.root)
        core.valid_run_id(migrated["questionnaire"]["run_id"])
        self.assertEqual(migrated["questionnaire"]["run_id"], migrated["answers"]["run_id"])
        self.assertEqual(migrated["answers"]["answers"], before["answers"]["answers"])
        self.assertEqual(migrated["answers"]["answer_revision"], before["answers"]["answer_revision"])
        self.assertEqual(core.status(self.root)["questionnaire"]["run_id"], migrated["questionnaire"]["run_id"])
        with self.assertRaises(core.BuilderError) as caught:
            core.import_answers(self.root, a)
        self.assertEqual(caught.exception.code, "wrong_run")

    def test_authored_questions_allow_omitted_run_id_but_reject_conflict(self):
        self.install()
        view = core.status(self.root)
        self.assertIn("run_id", view["questionnaire"])
        unchanged = copy.deepcopy(self.data)
        self.assertEqual(core.set_questions(self.root, unchanged)["questionnaire"]["run_id"], view["questionnaire"]["run_id"])
        unchanged["run_id"] = "00000000-0000-0000-0000-000000000000"
        with self.assertRaises(core.BuilderError) as caught:
            core.set_questions(self.root, unchanged)
        self.assertEqual(caught.exception.code, "wrong_run")

    def test_conflicting_canonical_run_ids_are_not_silently_repaired(self):
        self.install()
        answers = core.read_json(self.root / "answers.json")
        answers["run_id"] = "00000000-0000-0000-0000-000000000000"
        core.atomic_json(self.root / "answers.json", answers)
        with self.assertRaises(core.BuilderError) as caught:
            core.status(self.root)
        self.assertEqual(caught.exception.code, "wrong_run")
        self.assertEqual(core.read_json(self.root / "answers.json"), answers)

    def test_batch_updates_are_all_or_nothing_and_dependency_ordered(self):
        self.install()
        before = core.status(self.root)["answers"]
        bad = self.request_payload({"q1": {"status": "answered", "value": "yes"}, "q2": {"status": "answered", "value": ""}})
        with self.assertRaises(core.BuilderError):
            core.update_answers(self.root, bad)
        self.assertEqual(core.status(self.root)["answers"], before)
        good = self.request_payload({"q2": {"status": "answered", "value": "Runtime input"}, "q1": {"status": "answered", "value": "yes"}})
        view = core.update_answers(self.root, good)
        self.assertEqual(view["answers"]["answers"]["q2"]["value"], "Runtime input")

    def test_registered_asset_containment_and_read(self):
        image = self.root / "assets" / "layout.svg"
        image.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
        self.assertEqual(core.safe_asset(self.root, "assets/layout.svg"), image.resolve())
        for path in ("../secret.png", "assets/../secret.png", "assets/%2e%2e/secret.png", "C:/private.png", "assets\\private.png", "assets//private.png", "assets/secret.txt"):
            with self.subTest(path=path), self.assertRaises(core.BuilderError):
                core.safe_asset(self.root, path)

    def test_changed_image_bytes_invalidate_existing_choice(self):
        image = self.root / "assets" / "layout.svg"
        image.write_text('<svg xmlns="http://www.w3.org/2000/svg"><rect width="10"/></svg>', encoding="utf-8")
        q = self.data["questions"][0]
        q["type"] = "image"
        for option in q["options"]:
            option["image"] = "assets/layout.svg"
        self.install()
        core.recommend(self.root)
        before = core.status(self.root)
        self.assertIn("image_sha256", before["questionnaire"]["questions"][0]["options"][0])
        image.write_text('<svg xmlns="http://www.w3.org/2000/svg"><rect width="20"/></svg>', encoding="utf-8")
        with self.assertRaises(core.BuilderError) as caught:
            core.status(self.root)
        self.assertEqual(caught.exception.code, "stale_asset")
        view = core.set_questions(self.root, self.data)
        self.assertEqual(view["questionnaire"]["questions"][0]["version"], 2)
        self.assertNotIn("q1", view["answers"]["answers"])
        self.assertNotIn("q2", view["answers"]["answers"])

    def test_malformed_answer_record_is_a_useful_validation_error(self):
        self.install()
        incoming = core.status(self.root)["answers"]
        incoming["answers"]["q1"] = None
        with self.assertRaisesRegex(core.BuilderError, "must be an object"):
            core.import_answers(self.root, incoming)

    def test_recovery_journal_restores_consistent_revision(self):
        self.install()
        q, a = core.load_workspace(self.root)
        q["revision"] += 1
        a["revision"] = q["revision"]
        core.atomic_json(self.root / ".pending-state.json", {"questionnaire": q, "answers": a})
        core.atomic_json(self.root / "questions.json", q)
        view = core.status(self.root)
        self.assertEqual(view["questionnaire"]["revision"], view["answers"]["revision"])
        self.assertFalse((self.root / ".pending-state.json").exists())

    def test_skill_structure_checker_is_explicitly_not_behavior_test(self):
        skill = self.parent / "tiny-skill"
        (skill / "references").mkdir(parents=True)
        (skill / "references" / "example.md").write_text("Example", encoding="utf-8")
        (skill / "SKILL.md").write_text('---\nname: tiny-skill\ndescription: "Test a specific task"\n---\nRead [example](references/example.md).\n', encoding="utf-8")
        result = core.check_skill(skill)
        self.assertTrue(result["valid"])
        self.assertFalse(result["behavior_tested"])
        (skill / "references" / "example.md").unlink()
        with self.assertRaisesRegex(core.BuilderError, "Missing referenced file"):
            core.check_skill(skill)

    def test_http_bridge_rejects_stale_cross_origin_and_premature_submit(self):
        self.install()
        server = QuestionnaireServer(self.root)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()
        def request(method, path, data=None, extra=None):
            conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
            headers = {"Content-Type": "application/json"}
            headers.update(extra or {})
            conn.request(method, path, body=json.dumps(data) if data is not None else None, headers=headers)
            response = conn.getresponse()
            result = response.status, json.loads(response.read())
            conn.close()
            return result
        try:
            token = "?token=" + server.token
            self.assertEqual(request("GET", "/api/state")[0], 401)
            self.assertEqual(request("GET", "/api/state" + token)[0], 200)
            self.assertEqual(request("POST", "/api/answers" + token, self.request_payload({}), {"Origin": "https://unrelated.example"})[0], 403)
            self.assertEqual(request("POST", "/api/submit" + token, self.request_payload())[0], 422)
            old = self.request_payload({"q1": {"status": "answered", "value": "no", "actor": "user"}})
            self.assertEqual(request("POST", "/api/answers" + token, old)[0], 200)
            self.assertEqual(request("POST", "/api/answers" + token, old)[0], 409)
            self.assertEqual(request("GET", "/assets/../answers.json" + token)[0], 404)
            core.answer_one(self.root, "q3", ["note"])
            code, body = request("POST", "/api/submit" + token, self.request_payload())
            self.assertEqual(code, 200)
            self.assertEqual(body["event"], "submitted")
            thread.join(3)
            self.assertFalse(thread.is_alive())
        finally:
            if thread.is_alive():
                server.shutdown()
            server.server_close()

    def test_cli_invalid_json_is_friendly_nonzero(self):
        self.install()
        run = subprocess.run([sys.executable, "-B", str(PACKAGE / "scripts" / "skill_builder.py"), "answer", "--workspace", str(self.root),
                              "--question", "q1", "--value-json", "{"], text=True, capture_output=True, encoding="utf-8")
        self.assertEqual(run.returncode, 2)
        self.assertNotIn("Traceback", run.stderr)
        self.assertEqual(json.loads(run.stderr)["error"], "io_or_json_error")

    def test_serve_cli_emits_ready_then_timeout_and_keeps_answers(self):
        self.install()
        core.answer_one(self.root, "q1", "no")
        run = subprocess.run([sys.executable, "-B", str(PACKAGE / "scripts" / "skill_builder.py"), "serve", "--workspace", str(self.root),
                              "--timeout", "0.2"], text=True, capture_output=True, encoding="utf-8", timeout=8)
        self.assertEqual(run.returncode, 0, run.stderr)
        events = [json.loads(line) for line in run.stdout.splitlines()]
        self.assertEqual([event["event"] for event in events], ["ready", "timeout"])
        self.assertTrue(events[0]["url"].startswith("http://127.0.0.1:"))
        self.assertEqual(core.status(self.root)["answers"]["answers"]["q1"]["value"], "no")

    def test_standalone_render_escapes_boot_data(self):
        self.data["goal"] = '</script><script>alert("untrusted source")</script>'
        self.install()
        rendered = Path(core.render(self.root)["path"]).read_text(encoding="utf-8")
        self.assertNotIn(self.data["goal"], rendered)
        self.assertIn('\\u003c/script\\u003e', rendered)
        self.assertIn('"transport": "offline"', rendered)
        self.assertNotIn('<!--BOOT_JSON-->', rendered)

    def test_locale_defaults_region_variants_and_builtin_overrides(self):
        default = core.resolve_locale()
        self.assertEqual((default["language"], default["direction"]), ("en", "ltr"))
        english = core.locale_catalog()["en"]
        resolved = core.resolve_locale({"language": "en-GB", "direction": "ltr", "messages": {"next": "Continue"}})
        self.assertEqual(resolved["language"], "en-GB")
        self.assertEqual(resolved["messages"]["next"], "Continue")
        self.assertEqual(resolved["messages"]["previous"], english["previous"])
        self.install()
        self.assertIn('<html lang="en" dir="ltr">', core.render_html(self.root))

    def test_new_workspace_records_english_and_import_inherits_it(self):
        initialized = core.read_json(self.root / "questions.json")
        self.assertEqual(initialized["locale"], {"language": "en", "direction": "ltr"})
        self.assertNotIn("locale", self.data)
        installed = self.install()
        self.assertEqual(installed["questionnaire"]["locale"], initialized["locale"])
        self.assertEqual(core.resolve_questionnaire_locale(installed["questionnaire"])["messages"]["next"], "Next")

    def test_explicit_korean_and_omitted_locale_update_preserve_answers(self):
        self.data["locale"] = {"language": "ko", "direction": "ltr"}
        self.install()
        core.recommend(self.root)
        before = core.status(self.root)
        incoming = copy.deepcopy(before["questionnaire"])
        del incoming["locale"]
        after = core.set_questions(self.root, incoming)
        self.assertEqual(after, before)
        self.assertIn('<html lang="ko" dir="ltr">', core.render_html(self.root))
        self.assertIn("다음", core.render_html(self.root))

    def test_legacy_missing_locale_keeps_korean_without_rewriting_records(self):
        self.install()
        core.recommend(self.root)
        legacy = core.read_json(self.root / "questions.json")
        del legacy["locale"]
        core.atomic_json(self.root / "questions.json", legacy)
        before = {name: (self.root / name).read_bytes() for name in ("questions.json", "answers.json")}
        view = core.status(self.root)
        self.assertNotIn("locale", view["questionnaire"])
        self.assertIn('<html lang="ko" dir="ltr">', core.render_html(self.root))
        self.assertEqual(core.set_questions(self.root, copy.deepcopy(legacy)), view)
        self.assertEqual(before, {name: (self.root / name).read_bytes() for name in before})

    def test_legacy_null_locale_keeps_korean(self):
        self.data["locale"] = None
        self.install()
        self.assertIn('<html lang="ko" dir="ltr">', core.render_html(self.root))

    def test_custom_japanese_and_unicode_answers_survive_import_and_render(self):
        messages = {key: "日本語: " + value for key, value in core.locale_catalog()["en"].items()}
        messages["page_title"] = "スキル作成の質問"
        self.data["locale"] = {"language": "ja-JP", "direction": "ltr", "messages": messages}
        self.data["questions"][1]["title"] = "どの環境で実行しますか？"
        self.install()
        before = core.recommend(self.root)
        incoming = copy.deepcopy(before["answers"])
        value = "日本語の回答。 العربية 中文 한글 🧪 e\u0301\n次の行"
        incoming["answers"]["q2"]["value"] = value
        export_path = self.parent / "回答-إجابات.json"
        core.atomic_json(export_path, incoming)
        imported = core.import_answers(self.root, core.read_json(export_path))
        self.assertEqual(imported["answers"]["answers"]["q2"]["value"], value)
        self.assertIn(value.splitlines()[0], (self.root / "answers.json").read_text(encoding="utf-8"))
        for transport in ("offline", "live"):
            rendered = core.render_html(self.root, transport=transport)
            boot_text = rendered.split('<script id="skill-builder-data" type="application/json">', 1)[1].split('</script>', 1)[0]
            boot = json.loads(boot_text)
            self.assertEqual(boot["locale"], self.data["locale"])
            self.assertEqual(boot["view"]["answers"]["answers"]["q2"]["value"], value)
            self.assertIn('<html lang="ja-JP" dir="ltr">', rendered)
            self.assertIn('<title>スキル作成の質問</title>', rendered)
            self.assertNotIn('{{t:', rendered)

    def test_custom_arabic_rtl_and_markup_are_safely_rendered(self):
        messages = {key: "العربية: " + value for key, value in core.locale_catalog()["en"].items()}
        unsafe = '</script><script>alert("locale")</script> & "attribute"'
        messages["page_title"] = unsafe
        messages["load_failed"] = unsafe
        self.data["locale"] = {"language": "ar", "direction": "rtl", "messages": messages}
        self.install()
        rendered = core.render_html(self.root)
        self.assertIn('<html lang="ar" dir="rtl">', rendered)
        self.assertNotIn(unsafe, rendered)
        self.assertIn('&lt;/script&gt;&lt;script&gt;alert(&quot;locale&quot;)', rendered)
        boot_text = rendered.split('<script id="skill-builder-data" type="application/json">', 1)[1].split('</script>', 1)[0]
        self.assertEqual(json.loads(boot_text)["locale"]["messages"]["load_failed"], unsafe)

    def test_locale_rejects_missing_unknown_and_changed_placeholders(self):
        bad_locales = [
            {"language": "ja", "direction": "ltr"},
            {"language": "en", "direction": "ltr", "messages": {"unknown_key": "Text"}},
            {"language": "en", "direction": "ltr", "messages": {"counts": "{active} only"}},
            {"language": "en", "direction": "ltr", "messages": {"next": "{unexpected}"}},
            {"language": "en", "direction": "ltr", "messages": {"counts": 3}},
            {"language": "en", "direction": "ltr", "messages": None},
            {"language": "en_US", "direction": "ltr"},
            {"language": "en", "direction": "sideways"},
            {"language": "en", "direction": ["rtl"]},
            {"language": 'en\" onload=\"alert(1)', "direction": "ltr"},
            {"language": "en-u-ca-gregory-u-nu-latn", "direction": "ltr"},
        ]
        for locale in bad_locales:
            with self.subTest(locale=locale), self.assertRaises(core.BuilderError):
                data = copy.deepcopy(self.data)
                data["locale"] = locale
                core.set_questions(self.root, data)
        messages = core.locale_catalog()["en"]
        messages.pop("next")
        with self.assertRaisesRegex(core.BuilderError, "missing: next"):
            core.resolve_locale({"language": "ja", "direction": "ltr", "messages": messages})
        self.assertEqual(core.status(self.root)["questionnaire"]["questions"], [])

    def test_locale_revision_preserves_unchanged_answer_values_and_versions(self):
        self.install()
        before = core.recommend(self.root)
        incoming = copy.deepcopy(before["questionnaire"])
        incoming["locale"] = {"language": "en-GB", "direction": "ltr"}
        changed = core.set_questions(self.root, incoming)
        self.assertEqual(changed["questionnaire"]["revision"], before["questionnaire"]["revision"] + 1)
        self.assertEqual(changed["questionnaire"]["questions"], before["questionnaire"]["questions"])
        self.assertEqual(changed["answers"]["answers"], before["answers"]["answers"])
        self.assertEqual(changed["answers"]["history"], before["answers"]["history"])
        self.assertTrue(changed["ready_to_build"])

    def test_locale_accepts_structural_tags_without_a_language_allowlist(self):
        messages = core.locale_catalog()["en"]
        for language in ("zh-Hant-TW", "sr-Latn-RS", "qaa", "x-test", "i-klingon", "en-US-u-ca-gregory"):
            with self.subTest(language=language):
                resolved = core.resolve_locale({"language": language, "direction": "ltr", "messages": messages})
                self.assertEqual(resolved["language"], language)


if __name__ == "__main__":
    unittest.main(verbosity=2)
