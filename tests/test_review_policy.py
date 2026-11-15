"""CLI review gates and locked snapshot use with explicitly synthetic audit records."""
from __future__ import annotations

import copy
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid
from unittest.mock import patch

REPOSITORY = Path(__file__).resolve().parents[1]
SCRIPTS = REPOSITORY / "any-skill-builder/scripts"
sys.path.insert(0, str(SCRIPTS))
import builder_core as core
import review_questions
import skill_builder
from test_question_review import completed_example_review, two_question_fixture


class ReviewPolicyTests(unittest.TestCase):
    def setUp(self):
        cache = os.environ.get("SKILL_BUILDER_TEST_TMPDIR")
        if cache:
            Path(cache).mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="review-policy-", dir=cache)
        self.parent = Path(self.temp.name)
        self.root = self.parent / "run"
        self.counter = 0
        self.new_workspace(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def cli(self, command, *arguments, workspace=None, expected=0):
        result = subprocess.run([sys.executable, "-B", str(SCRIPTS / "skill_builder.py"), command,
                                 "--workspace", str(workspace or self.root), *map(str, arguments)],
                                capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, expected, result.stderr or result.stdout)
        return json.loads(result.stdout if result.returncode == 0 else result.stderr)

    def new_workspace(self, path, *, mode="questionnaire", legacy=False):
        arguments = ["--goal", "Synthetic weekly-update review gate test", "--mode", mode]
        if legacy:
            arguments.extend(["--review-policy", "legacy"])
        self.cli("init", *arguments, workspace=path)
        authored = self.parent / (path.name + "-authored.json")
        core.atomic_json(authored, two_question_fixture())
        self.cli("set-questions", "--input", authored, "--rebind-project", workspace=path)

    def completed_review(self, root=None):
        self.counter += 1
        root = root or self.root
        review = self.parent / f"synthetic-review-{self.counter}.json"
        record = completed_example_review(root / "questions.json", review)
        core.atomic_json(review, record)
        return review

    def accept(self, root=None):
        root = root or self.root
        review = self.completed_review(root)
        result = self.cli("accept-review", "--input", review, workspace=root)
        self.assertTrue(result["recorded"])
        self.assertTrue(result["review"]["passed"])
        return review

    def answer(self, question, value, root=None):
        self.counter += 1
        value_file = self.parent / f"answer-{self.counter}.json"
        core.atomic_json(value_file, value)
        return self.cli("answer", "--question", question, "--value-file", value_file, workspace=root)

    def assert_blocked(self, root=None):
        root = root or self.root
        for command in ("render", "recommend", "brief"):
            with self.subTest(command=command):
                error = self.cli(command, workspace=root, expected=2)
                self.assertEqual(error["error"], "question_review_required")

    def test_new_cli_default_blocks_render_recommend_and_brief_even_after_user_answers(self):
        self.answer("workflow", "clarify")
        answered = self.answer("outputs", ["progress"])
        self.assertTrue(answered["traversal_complete"])
        self.assertFalse(answered["ready_to_build"])
        self.assertTrue(answered["question_review"]["required"])
        before = (self.root / "answers.json").read_bytes()
        self.assert_blocked()
        self.assertEqual((self.root / "answers.json").read_bytes(), before)
        self.assertFalse((self.root / "questionnaire.html").exists())
        self.assertFalse((self.root / "build-brief.md").exists())
        status = self.cli("status", "--json")
        self.assertTrue(status["traversal_complete"])
        self.assertFalse(status["ready_to_build"])
        self.assertTrue(status["question_review"]["required"])
        self.assertEqual(status["question_review"]["status"], "missing")

    def test_accepting_current_completed_review_permits_real_cli_operations(self):
        self.accept()
        recommended = self.cli("recommend")
        self.assertEqual(set(recommended["filled"]), {"workflow", "outputs"})
        status = self.cli("status", "--json")
        self.assertTrue(status["ready_to_build"])
        self.assertTrue(status["question_review"]["passed"])
        rendered = self.cli("render")
        boot = core.read_saved_html(rendered["path"], require_saved=False)
        self.assertTrue(boot["view"]["question_review"]["passed"])
        self.assertEqual(boot["view"]["questionnaire"], status["questionnaire"])
        brief = self.cli("brief")
        self.assertIn("workflow", Path(brief["path"]).read_text(encoding="utf-8"))

    def test_brief_lists_the_reviews_fixed_requirements(self):
        self.accept()
        self.cli("recommend")
        brief = Path(self.cli("brief")["path"]).read_text(encoding="utf-8")
        self.assertIn("## Fixed requirements\n\n- None recorded beyond the goal.", brief)

        other = self.parent / "with-requirement"
        self.new_workspace(other)
        self.counter += 1
        review = self.parent / f"synthetic-review-{self.counter}.json"
        record = completed_example_review(other / "questions.json", review)
        record["requirements"].append({"id": "no-invented-owners", "statement": "Never invent owners or deadlines",
                                       "basis": {"kind": "user", "reference": "original request",
                                                 "evidence": "Do not make up who owns what."}})
        for row in record["question_reviews"] + record["combinations"]:
            row["requirement_ids"].append("no-invented-owners")
        core.atomic_json(review, record)
        self.cli("accept-review", "--input", review, workspace=other)
        self.cli("recommend", workspace=other)
        brief = Path(self.cli("brief", workspace=other)["path"]).read_text(encoding="utf-8")
        self.assertIn("- no-invented-owners: Never invent owners or deadlines (basis: user, original request)", brief)
        self.assertNotIn("None recorded beyond the goal", brief)

    def test_pending_or_stale_reviews_cannot_be_accepted(self):
        review = self.parent / "pending-review.json"
        review_questions.prepare(self.root / "questions.json", review)
        error = self.cli("accept-review", "--input", review, expected=2)
        self.assertEqual(error["error"], "question_review_incomplete")
        self.assertFalse((self.root / "question-review.json").exists())
        review = self.completed_review()
        questions = self.root / "questions.json"
        questions.write_bytes(questions.read_bytes() + b"\n")
        error = self.cli("accept-review", "--input", review, expected=2)
        self.assertEqual(error["error"], "question_review_incomplete")
        self.assertFalse((self.root / "question-review.json").exists())

    def test_presentation_edit_reblocks_review_without_erasing_user_answers(self):
        self.accept()
        self.answer("workflow", "clarify")
        self.answer("outputs", ["progress"])
        before = core.status(self.root)["answers"]
        incoming = core.read_json(self.root / "questions.json")
        incoming["questions"][0]["title"] = "How should an unclear note be handled?"
        source = self.parent / "cosmetic-edit.json"
        core.atomic_json(source, incoming)
        self.cli("set-questions", "--input", source, "--presentation-only", "workflow")
        status = self.cli("status", "--json")
        self.assertEqual(status["answers"]["answers"], before["answers"])
        self.assertEqual(status["question_review"]["status"], "stale")
        self.assertFalse(status["ready_to_build"])
        self.assert_blocked()
        self.assertEqual(core.status(self.root)["answers"]["answers"], before["answers"])

    def test_whitespace_only_byte_change_stales_review_without_altering_answers(self):
        self.accept()
        self.cli("recommend")
        before = (self.root / "answers.json").read_bytes()
        questions = self.root / "questions.json"
        questions.write_bytes(questions.read_bytes() + b"\n")
        status = self.cli("status", "--json")
        self.assertEqual(status["question_review"]["status"], "stale")
        self.assertFalse(status["ready_to_build"])
        self.assert_blocked()
        self.assertEqual((self.root / "answers.json").read_bytes(), before)

    def test_foreign_run_policy_is_rejected_without_mutating_answers(self):
        self.accept()
        policy = core.read_json(self.root / "review-policy.json")
        policy["run_id"] = str(uuid.uuid4())
        core.atomic_json(self.root / "review-policy.json", policy)
        before = (self.root / "answers.json").read_bytes()
        for command in ("status", "recommend", "render", "brief"):
            error = self.cli(command, expected=2)
            self.assertEqual(error["error"], "invalid_review_policy")
        self.assertEqual((self.root / "answers.json").read_bytes(), before)

    def test_existing_legacy_workspace_remains_usable_without_claiming_review(self):
        legacy = self.parent / "existing-legacy"
        result = core.init_workspace(legacy, "Legacy unit fixture")
        fixture = two_question_fixture()
        fixture["project_id"] = result["project_id"]
        core.set_questions(legacy, fixture)
        self.cli("recommend", workspace=legacy)
        self.cli("render", workspace=legacy)
        self.cli("brief", workspace=legacy)
        status = self.cli("status", "--json", workspace=legacy)
        self.assertTrue(status["ready_to_build"])
        self.assertEqual(status["question_review"]["status"], "legacy")
        self.assertFalse(status["question_review"]["required"])
        self.assertFalse(status["question_review"]["passed"])

    def test_explicit_legacy_fixture_preview_can_enable_review_without_losing_answers(self):
        legacy = self.parent / "explicit-legacy"
        self.new_workspace(legacy, legacy=True)
        self.cli("recommend", workspace=legacy)
        before = (legacy / "answers.json").read_bytes()
        self.cli("require-review", workspace=legacy)
        self.assert_blocked(legacy)
        self.assertEqual((legacy / "answers.json").read_bytes(), before)
        self.accept(legacy)
        self.assertTrue(self.cli("status", "--json", workspace=legacy)["ready_to_build"])

    def test_full_auto_requires_review_and_still_creates_no_html(self):
        auto = self.parent / "full-auto"
        self.new_workspace(auto, mode="auto")
        self.assert_blocked(auto)
        self.accept(auto)
        self.cli("recommend", workspace=auto)
        self.cli("brief", workspace=auto)
        self.assertEqual(self.cli("render", workspace=auto, expected=2)["error"], "auto_no_html")
        self.assertFalse(list(auto.rglob("*.html")))

    def test_restored_saved_html_requires_a_current_review_and_preserves_user_answers(self):
        self.accept()
        self.answer("workflow", "clarify")
        self.cli("recommend")
        rendered = self.cli("render")
        boot = core.read_saved_html(rendered["path"], require_saved=False)
        boot.update(saved_at="2026-11-15T10:00:00Z", export_id=str(uuid.uuid4()))
        saved = self.parent / "saved-by-unit-fixture.html"
        payload = json.dumps(boot, ensure_ascii=False).replace("<", "\\u003c")
        saved.write_text('<!doctype html><script id="skill-builder-data" type="application/json">' + payload + '</script>', encoding="utf-8")
        restored = self.parent / "restored"
        result = self.cli("restore", "--input", saved, workspace=restored)
        self.assertFalse(result["ready_to_build"])
        self.assertTrue(result["question_review"]["required"])
        status = self.cli("status", "--json", workspace=restored)
        self.assertFalse(status["ready_to_build"])
        self.assertFalse(status["question_review"]["passed"])
        self.assertEqual(status["answers"]["answers"]["workflow"]["actor"], "user")
        self.assertEqual(status["answers"]["answers"]["workflow"]["value"], "clarify")
        self.assert_blocked(restored)

    def test_imported_complete_user_answers_do_not_claim_readiness_without_current_review(self):
        self.accept()
        rendered = self.cli("render")
        boot = core.read_saved_html(rendered["path"], require_saved=False)
        boot.update(saved_at="2026-11-15T10:00:00Z", export_id=str(uuid.uuid4()))
        for question, value in (("workflow", "clarify"), ("outputs", ["progress"])):
            boot["view"]["answers"]["answers"][question] = {
                "status": "answered", "actor": "user", "question_version": 1,
                "rationale": "", "value": value}
        saved = self.parent / "complete-import-fixture.html"
        payload = json.dumps(boot, ensure_ascii=False).replace("<", "\\u003c")
        saved.write_text('<!doctype html><script id="skill-builder-data" type="application/json">' + payload + '</script>', encoding="utf-8")
        (self.root / "question-review.json").unlink()
        imported = self.cli("import-answers", "--input", saved, "--full")
        self.assertTrue(imported["traversal_complete"])
        self.assertFalse(imported["ready_to_build"])
        self.assertTrue(imported["question_review"]["required"])
        self.assertFalse(imported["question_review"]["passed"])
        self.assertEqual(imported["answers"]["answers"]["workflow"]["actor"], "user")
        self.assertEqual(imported["answers"]["answers"]["workflow"]["value"], "clarify")

    def test_set_questions_fills_omitted_identity_and_names_expected_values(self):
        current = core.read_json(self.root / "questions.json")
        authored = {key: value for key, value in copy.deepcopy(current).items()
                    if key not in {"schema_version", "project_id", "run_id", "mode", "revision"}}
        authored["questions"][0]["help"] = "Edited help text."
        result = self.cli("set-questions", "--input", self.write_json(authored))
        self.assertEqual(result["identity_filled_from_run"], ["schema_version", "project_id", "mode", "revision"])
        self.assertEqual(result["revision"], current["revision"] + 1)
        for key, value, code in (("project_id", "other-project", "wrong_project"), ("mode", "auto", "mode_mismatch"),
                                 ("revision", 1, "stale_revision")):
            with self.subTest(key=key):
                wrong = {**authored, key: value}
                error = self.cli("set-questions", "--input", self.write_json(wrong), expected=2)
                self.assertEqual(error["error"], code)
                self.assertIn(repr(value), error["message"])

    def write_json(self, value):
        self.counter += 1
        path = self.parent / f"authored-{self.counter}.json"
        core.atomic_json(path, value)
        return path

    def test_routine_commands_print_a_summary_unless_full_output_is_requested(self):
        self.accept()
        summary = self.cli("answer", "--question", "workflow", "--value-json", '"clarify"')
        self.assertNotIn("questionnaire", summary)
        self.assertNotIn("answers", summary)
        self.assertEqual(summary["run_id"], core.read_json(self.root / "questions.json")["run_id"])
        self.assertIn("answer_revision", summary)
        self.assertIn("ready_to_build", summary)
        self.assertIn("states", summary)
        saved = self.parent / "full-answer-view.json"
        summary = self.cli("answer", "--question", "workflow", "--value-json", '"clarify"', "--out", saved)
        self.assertIn(str(saved), summary["full_view"])
        self.assertEqual(core.read_json(saved)["answers"]["answers"]["workflow"]["value"], "clarify")
        full = self.cli("answer", "--question", "workflow", "--value-json", '"clarify"', "--full")
        self.assertEqual(full["answers"]["answers"]["workflow"]["value"], "clarify")
        self.assertIn("questionnaire", self.cli("status", "--json"))

    def test_recommend_checks_review_inside_the_same_lock_as_read_and_commit(self):
        self.accept()
        real_lock = core.workspace_lock
        real_review = core.require_question_review
        real_load = core.load_workspace
        real_commit = core.commit_workspace
        locked = False
        events = []

        @contextmanager
        def tracked_lock(workspace):
            nonlocal locked
            with real_lock(workspace):
                self.assertFalse(locked)
                locked = True
                events.append("lock")
                try:
                    yield
                finally:
                    events.append("unlock")
                    locked = False

        def locked_operation(name, operation):
            def call(*arguments, **keywords):
                self.assertTrue(locked, name + " escaped the workspace lock")
                events.append(name)
                return operation(*arguments, **keywords)
            return call

        with patch.object(core, "workspace_lock", tracked_lock), \
             patch.object(core, "load_workspace", locked_operation("load", real_load)), \
             patch.object(core, "require_question_review", locked_operation("review", real_review)), \
             patch.object(core, "commit_workspace", locked_operation("commit", real_commit)):
            self.assertTrue(core.recommend(self.root)["ready_to_build"])
        self.assertEqual(events, ["lock", "load", "review", "commit", "unlock"])

    def test_render_metadata_and_embedded_questions_share_the_captured_reviewed_view(self):
        self.accept()
        real_status = core.status
        calls = 0

        def capture_then_revise(*arguments, **keywords):
            nonlocal calls
            captured = real_status(*arguments, **keywords)
            calls += 1
            if calls == 1:
                incoming = copy.deepcopy(captured["questionnaire"])
                incoming["questions"][0]["title"] = "A later reviewed wording"
                core.set_questions(self.root, incoming, presentation_only=["workflow"])
                path = self.completed_review()
                skill_builder.accept_review(self.root, path)
            return captured

        with patch.object(core, "status", side_effect=capture_then_revise):
            result = core.render(self.root)
        boot = core.read_saved_html(result["path"], require_saved=False)
        metadata = core.read_json(self.root / "questionnaire-export.json")
        self.assertEqual(metadata["revision"], boot["view"]["questionnaire"]["revision"])
        self.assertEqual(metadata["questionnaire_sha256"], boot["questionnaire_sha256"])
        self.assertTrue(boot["view"]["question_review"]["passed"])


if __name__ == "__main__":
    unittest.main()
