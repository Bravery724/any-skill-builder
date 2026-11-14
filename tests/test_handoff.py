"""Portable saved questionnaires, identity checks, and durable offline continuation."""
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
import uuid
from unittest.mock import patch

PACKAGE = Path(__file__).resolve().parents[1] / "any-skill-builder"
sys.path.insert(0, str(PACKAGE / "scripts"))
import builder_core as core
from test_backend import questionnaire


class HandoffTests(unittest.TestCase):
    def setUp(self):
        cache = os.environ.get("SKILL_BUILDER_TEST_TMPDIR")
        if cache:
            Path(cache).mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="offline-handoff-", dir=cache)
        self.parent = Path(self.temp.name)
        self.root = self.parent / "run"
        result = core.init_workspace(self.root, "Create a paper-analysis skill")
        core.set_questions(self.root, questionnaire(result["project_id"]))

    def tearDown(self):
        self.temp.cleanup()

    def boot(self):
        html = core.render_html(self.root)
        text = html.split('<script id="skill-builder-data" type="application/json">')[1].split('</script>', 1)[0]
        boot = json.loads(text)
        boot.update(saved_at="2026-11-15T10:00:00Z", export_id=str(uuid.uuid4()))
        return boot

    def answer(self, boot, qid, value):
        boot["view"]["answers"]["answers"][qid] = {"status": "answered", "actor": "user", "question_version": 1, "rationale": "", "value": value}

    def save(self, boot, name="questionnaire.html", extra=""):
        path = self.root / name
        raw = json.dumps(boot, ensure_ascii=False).replace("<", "\\u003c")
        path.write_text('<!doctype html><html><script id="skill-builder-data" type="application/json">' + raw + '</script>' + extra + '</html>', encoding="utf-8")
        return path

    def canonical(self):
        return {name: (self.root / name).read_bytes() for name in ("questions.json", "answers.json")}

    def test_saved_html_import_preserves_custom_text_and_ai_fills_blanks(self):
        boot = self.boot()
        self.answer(boot, "q1", "no")
        self.answer(boot, "q3", {"other": "한글 · 日本語 · العربية · 0", "selected": ["note"]})
        view = core.import_answers(self.root, self.save(boot))
        self.assertEqual(view["unanswered_policy"], "host_ai_decides")
        self.assertTrue(view["ready_to_build"])
        self.assertEqual(core.recommend(self.root)["filled"], [])
        self.assertEqual(view["answers"]["answers"]["q3"]["value"], boot["view"]["answers"]["answers"]["q3"]["value"])

    def test_blank_save_can_resume_then_recommend_newly_active_questions(self):
        boot = self.boot()
        self.save(boot)
        result = core.resume(self.root)
        self.assertEqual(result["counts"]["unanswered"], 2)
        done = core.recommend(self.root)
        self.assertEqual(set(done["filled"]), {"q1", "q2", "q3"})
        self.assertTrue(done["ready_to_build"])
        canonical = self.canonical()
        self.assertEqual(core.resume(self.root)["event"], "already_imported")
        self.assertEqual(self.canonical(), canonical)

    def test_unsaved_template_is_never_mistaken_for_explicit_saved_answers(self):
        path = core.render(self.root)["path"]
        with self.assertRaisesRegex(core.BuilderError, "original questionnaire template"):
            core.import_answers(self.root, path)
        with self.assertRaises(core.BuilderError) as caught:
            core.resume(self.root)
        self.assertEqual(caught.exception.code, "saved_answers_not_found")

    def test_stale_and_foreign_snapshots_do_not_change_canonical_files(self):
        boot = self.boot()
        self.answer(boot, "q1", "no")
        other = copy.deepcopy(boot)
        run = str(uuid.uuid4())
        other["view"]["questionnaire"]["run_id"] = run
        other["view"]["answers"]["run_id"] = run
        other["questionnaire_sha256"] = core.questionnaire_digest(other["view"]["questionnaire"])
        baseline = self.canonical()
        with self.assertRaises(core.BuilderError) as caught:
            core.import_answers(self.root, other)
        self.assertEqual(caught.exception.code, "wrong_run")
        self.assertEqual(self.canonical(), baseline)
        core.answer_one(self.root, "q3", ["note"])
        baseline = self.canonical()
        with self.assertRaises(core.BuilderError) as caught:
            core.import_answers(self.root, boot)
        self.assertEqual(caught.exception.code, "stale_answers")
        self.assertEqual(self.canonical(), baseline)

    def test_idempotent_import_does_not_erase_later_ai_decisions(self):
        boot = self.boot()
        self.answer(boot, "q1", "no")
        core.import_answers(self.root, boot)
        core.recommend(self.root)
        baseline = self.canonical()
        imports = (self.root / "imports.json").read_bytes()
        result = core.import_answers(self.root, boot)
        self.assertEqual(result["event"], "already_imported")
        self.assertEqual(self.canonical(), baseline)
        self.assertEqual((self.root / "imports.json").read_bytes(), imports)

    def test_same_export_id_with_different_content_is_rejected(self):
        boot = self.boot()
        self.answer(boot, "q1", "no")
        core.import_answers(self.root, boot)
        changed = copy.deepcopy(boot)
        self.answer(changed, "q1", "yes")
        baseline = self.canonical()
        with self.assertRaises(core.BuilderError) as caught:
            core.import_answers(self.root, changed)
        self.assertEqual(caught.exception.code, "export_id_conflict")
        self.assertEqual(self.canonical(), baseline)

    def test_same_revision_but_changed_question_text_is_rejected(self):
        boot = self.boot()
        boot["view"]["questionnaire"]["goal"] = "A different goal"
        boot["questionnaire_sha256"] = core.questionnaire_digest(boot["view"]["questionnaire"])
        with self.assertRaises(core.BuilderError) as caught:
            core.import_answers(self.root, boot)
        self.assertEqual(caught.exception.code, "questionnaire_mismatch")

    def test_duplicate_json_blocks_and_duplicate_json_keys_are_rejected(self):
        boot = self.boot()
        path = self.save(boot)
        original = path.read_text(encoding="utf-8")
        path.write_text(original + original, encoding="utf-8")
        with self.assertRaises(core.BuilderError):
            core.read_saved_html(path)
        duplicate = original.replace('"format":', '"format":"forged","format":', 1)
        path.write_text(duplicate, encoding="utf-8")
        with self.assertRaisesRegex(core.BuilderError, "Duplicate JSON"):
            core.read_saved_html(path)
        duplicate = original.replace('id="skill-builder-data"', 'id="skill-builder-data" id="other"', 1)
        path.write_text(duplicate, encoding="utf-8")
        with self.assertRaises(core.BuilderError):
            core.read_saved_html(path)

    def test_size_and_malformed_saved_timestamp_are_rejected(self):
        boot = self.boot()
        path = self.save(boot)
        with patch.object(core, "MAX_HTML_BYTES", 8):
            with self.assertRaises(core.BuilderError) as caught:
                core.read_saved_html(path)
            self.assertEqual(caught.exception.code, "saved_html_too_large")
        boot["saved_at"] = "yesterday"
        with self.assertRaises(core.BuilderError):
            core.import_answers(self.root, boot)

    def test_restore_uses_explicit_destination_and_rebuilds_trusted_html(self):
        boot = self.boot()
        self.answer(boot, "q1", "no")
        boot["resume"]["workspace"] = str(self.parent / "do-not-create")
        malicious = '<script>globalThis.DO_NOT_RUN = "INJECTED_EXECUTABLE";</script>'
        path = self.save(boot, extra=malicious)
        target = self.parent / "restored"
        result = core.restore_html(target, path)
        self.assertEqual(result["event"], "restored")
        self.assertEqual(result["answers"]["answers"]["q1"]["value"], "no")
        self.assertFalse((self.parent / "do-not-create").exists())
        self.assertNotIn("INJECTED_EXECUTABLE", (target / "questionnaire.html").read_text(encoding="utf-8"))
        self.assertEqual(core.resume(target)["event"], "resumed_from_import")
        with self.assertRaises(core.BuilderError):
            core.restore_html(target, path)

    def test_portable_images_restore_and_unsafe_or_corrupt_assets_are_rejected(self):
        image = self.root / "assets" / "candidate.svg"
        image.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="2" height="2"></svg>', encoding="utf-8")
        data = core.status(self.root)["questionnaire"]
        data["questions"][0]["type"] = "image"
        for option in data["questions"][0]["options"]:
            option["image"] = "assets/candidate.svg"
        core.set_questions(self.root, data)
        boot = self.boot()
        target = self.parent / "image-restore"
        core.restore_html(target, self.save(boot))
        self.assertEqual((target / "assets/candidate.svg").read_bytes(), image.read_bytes())
        corrupt = copy.deepcopy(boot)
        corrupt["assets"]["assets/candidate.svg"] = "data:image/svg+xml;base64,Zm9yZ2Vk"
        with self.assertRaises(core.BuilderError):
            core.restore_html(self.parent / "corrupt", self.save(corrupt))
        self.assertFalse((self.parent / "corrupt").exists())
        unsafe = copy.deepcopy(boot)
        for option in unsafe["view"]["questionnaire"]["questions"][0]["options"]:
            option["image"] = "assets/../../outside.svg"
        unsafe["questionnaire_sha256"] = core.questionnaire_digest(unsafe["view"]["questionnaire"])
        with self.assertRaises(core.BuilderError):
            core.restore_html(self.parent / "unsafe", self.save(unsafe))
        self.assertFalse((self.parent / "unsafe").exists())

    def test_restore_preserves_declared_ai_actor_and_rationale(self):
        core.recommend(self.root)
        boot = self.boot()
        target = self.parent / "provenance"
        result = core.restore_html(target, self.save(boot))
        self.assertEqual(result["answers"]["answers"]["q1"]["actor"], "ai")
        self.assertEqual(result["answers"]["answers"]["q1"]["rationale"], "Test recommendation")

    def test_restore_preserves_discarded_raw_input_and_its_resolution_history(self):
        core.answer_one(self.root, "q1", "yes")
        core.answer_one(self.root, "q2", ".")
        core.resolve_input(self.root, "q2", "A lone dot does not name an execution environment.")
        core.recommend(self.root)
        boot = self.boot()
        history = copy.deepcopy(boot["view"]["answers"]["history"])
        self.assertGreaterEqual(len(history), 2)
        result = core.restore_html(self.parent / "history", self.save(boot))
        self.assertEqual(result["answers"]["history"], history)
        self.assertTrue(any(entry.get("answer", {}).get("value") == "." and entry.get("reason") == "uninterpretable_input"
                            for entry in result["answers"]["history"]))

    def test_restore_rejects_malformed_history_before_creating_a_workspace(self):
        boot = self.boot()
        boot["view"]["answers"]["history"] = [{"action": "execute", "command": "untrusted input"}]
        target = self.parent / "malformed-history"
        with self.assertRaises(core.BuilderError):
            core.restore_html(target, self.save(boot))
        self.assertFalse(target.exists())

    def test_import_same_value_parent_reselection_keeps_untouched_ai_child_provenance(self):
        core.recommend(self.root)
        boot = self.boot()
        child = copy.deepcopy(boot["view"]["answers"]["answers"]["q2"])
        self.assertEqual(child["actor"], "ai")
        boot["view"]["answers"]["answers"]["q1"]["actor"] = "user"
        result = core.import_answers(self.root, boot)
        self.assertEqual(result["answers"]["answers"]["q1"]["actor"], "user")
        self.assertEqual(result["answers"]["answers"]["q2"], child)

    def test_resume_rejects_conflicting_unseen_copies_instead_of_picking_latest(self):
        first = self.boot()
        second = self.boot()
        self.answer(first, "q1", "no")
        self.answer(second, "q1", "yes")
        self.save(first)
        self.save(second, "questionnaire (1).html")
        with self.assertRaises(core.BuilderError) as caught:
            core.resume(self.root)
        self.assertEqual(caught.exception.code, "ambiguous_saved_html")
        core.import_answers(self.root, first)
        with self.assertRaises(core.BuilderError) as caught:
            core.resume(self.root)
        self.assertEqual(caught.exception.code, "stale_answers")

    def test_identical_copies_are_not_ambiguous(self):
        boot = self.boot()
        self.save(boot)
        self.save(boot, "questionnaire (1).html")
        self.assertEqual(core.resume(self.root)["event"], "answers_imported")

    def test_all_previous_imports_resume_current_canonical_state(self):
        first = self.boot()
        self.answer(first, "q1", "no")
        self.save(first)
        core.import_answers(self.root, first)
        second = self.boot()
        self.answer(second, "q3", ["note"])
        self.save(second, "questionnaire (1).html")
        core.import_answers(self.root, second)
        baseline = self.canonical()
        result = core.resume(self.root)
        self.assertEqual(result["event"], "resumed_from_import")
        self.assertTrue(result["ready_to_build"])
        self.assertEqual(self.canonical(), baseline)

    def test_render_does_not_overwrite_saved_answers(self):
        boot = self.boot()
        original = self.save(boot)
        before = original.read_bytes()
        result = core.render(self.root)
        self.assertNotEqual(Path(result["path"]), original)
        self.assertEqual(original.read_bytes(), before)
        parsed = core.read_saved_html(result["path"], require_saved=False)
        self.assertEqual(parsed["resume"]["html_path"], result["path"])

    def test_failed_import_journal_recovers_answers_and_import_identity_together(self):
        boot = self.boot()
        self.answer(boot, "q1", "no")
        original = core.atomic_json
        def interrupt(path, value):
            if Path(path).name == "answers.json":
                raise OSError("simulated interrupted write")
            return original(path, value)
        with patch.object(core, "atomic_json", side_effect=interrupt):
            with self.assertRaises(OSError):
                core.import_answers(self.root, boot)
        view = core.status(self.root, include_workflow=True)
        self.assertEqual(view["answers"]["answers"]["q1"]["value"], "no")
        self.assertEqual(view["workflow"]["last_import"]["export_id"], boot["export_id"])
        self.assertFalse((self.root / ".pending-state.json").exists())
        self.assertEqual(core.import_answers(self.root, boot)["event"], "already_imported")

    def test_checkpoint_rejects_unseen_revision_and_keeps_last_observed_history(self):
        view = core.status(self.root)
        record = core.checkpoint(self.root, 3, "Questions reviewed", "Save and return", ["User choices"],
                                 revision=view["questionnaire"]["revision"], answer_revision=view["answers"]["answer_revision"])
        self.assertEqual(record["checkpoint"]["stage"], 3)
        core.answer_one(self.root, "q1", "no")
        with self.assertRaises(core.BuilderError):
            core.checkpoint(self.root, 4, "Stale", "Continue", revision=view["questionnaire"]["revision"], answer_revision=view["answers"]["answer_revision"])
        self.assertFalse(core.status(self.root, include_workflow=True)["workflow"]["progress"]["current"])

    def test_cli_removed_commands_and_legacy_modes_cannot_start_servers(self):
        for command in ("serve", "delegate", "submit", "acknowledge"):
            result = subprocess.run([sys.executable, "-B", str(PACKAGE / "scripts/skill_builder.py"), command,
                                     "--workspace", str(self.root)], text=True, capture_output=True, encoding="utf-8")
            self.assertEqual(result.returncode, 2)
            self.assertIn("invalid choice", result.stderr)
        for mode in ("user", "hybrid"):
            with self.assertRaises(core.BuilderError):
                core.init_workspace(self.parent / mode, "Goal", mode)
            self.assertFalse((self.parent / mode).exists())


if __name__ == "__main__":
    unittest.main()
