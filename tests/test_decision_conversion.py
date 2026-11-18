"""Import a Full Auto decision list as a questionnaire through the public CLI."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_decisions import SCRIPTS, core, decision_list


class DecisionConversionTests(unittest.TestCase):
    def setUp(self):
        cache = os.environ.get("SKILL_BUILDER_TEST_TMPDIR")
        if cache:
            Path(cache).mkdir(parents=True, exist_ok=True)
        temp = tempfile.TemporaryDirectory(prefix="decision-conversion-", dir=cache)
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "run"
        self.input = self.root.parent / "authored.json"
        self.cli("init", "--goal", "Synthetic commit-message skill", "--mode", "auto", "--review-policy", "legacy")
        self.decisions = decision_list()
        core.set_decisions(self.root, self.decisions)
        skeleton = self.root.parent / "skeleton.json"
        self.cli("decisions-to-questions", "--skeleton", skeleton)
        self.skeleton = core.read_json(skeleton)

    def cli(self, command, *args, expected=0):
        result = subprocess.run([sys.executable, "-B", str(SCRIPTS / "skill_builder.py"), command,
                                 "--workspace", str(self.root), *map(str, args)],
                                capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, expected, result.stderr or result.stdout)
        return json.loads(result.stderr if expected else result.stdout)

    def snapshot(self):
        return {path.name: path.read_bytes() for path in self.root.iterdir() if path.is_file()}

    def test_only_presentation_edits_can_be_imported(self):
        self.cli("brief")
        before = self.snapshot()
        # Each replacement names its target in a fresh exported skeleton.
        cases = [
            (("questions", 0, "recommendation", "value"), "suggest"),
            (("questions", 0, "recommendation", "rationale"), "Someone preferred it"),
            (("questions", 2, "recommendation", "assumptions"), []),
            (("questions", 0, "options", 1, "effect"), "Reads only staged files"),
            (("questions", 0, "options", 1, "id"), "invented"),
            (("questions", 0, "options"), list(reversed(self.skeleton["questions"][0]["options"]))),
            (("questions", 0, "source_ids"), []),
            (("questions", 0, "decision"), "Change report delivery"),
            (("questions", 0, "origin"), "user"),
            (("questions", 0, "importance"), "detail"),
            (("questions", 1, "type"), "multi"),
            (("questions", 1, "max_choices"), 1),
            (("questions", 2, "when"), []),
            (("questions",), self.skeleton["questions"][:2]),
            (("questions",), list(reversed(self.skeleton["questions"]))),
            (("sources", 0, "notes"), "Unsupported claim"),
            (("goal",), "A different skill"),
            (("requirements",), [{"id": "replacement", "statement": "Read all files"}]),
        ]
        for path, value in cases:
            with self.subTest(path=path):
                authored = copy.deepcopy(self.skeleton)
                target = authored
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                core.atomic_json(self.input, authored)
                result = self.cli("set-questions", "--input", self.input, "--from-decisions", expected=2)
                self.assertEqual(result["error"], "decision_conversion_mismatch")
                location = self.skeleton["questions"][path[1]]["id"] if path[0] == "questions" and len(path) > 1 else path[0]
                self.assertIn(location, result["message"])
                self.assertEqual(self.snapshot(), before)
        self.assertTrue(self.cli("status")["ready_to_build"])

        authored = copy.deepcopy(self.skeleton)
        authored["locale"] = {"language": "ko", "direction": "ltr"}
        authored["groups"][0]["label"] = "결정 사항"
        question = authored["questions"][0]
        question.update(title="스테이징된 변경이 없으면 어떻게 할까요?", help="빈 스테이징 영역에서의 동작을 선택하세요.")
        question["options"][0].update(label="알리고 중단", description="메시지를 작성하기 전에 멈춥니다.")
        authored["questions"][2]["placeholder"] = "원하는 문체를 입력하세요."
        core.atomic_json(self.input, authored)
        result = self.cli("set-questions", "--input", self.input, "--from-decisions")
        self.assertTrue(result["question_review"]["required"])
        self.assertEqual(result["mode"], "questionnaire")
        self.assertEqual(core.read_json(self.root / "questions.json"), authored)
        self.assertEqual(core.read_json(self.root / "answers.json")["answers"], {})
        self.assertEqual((self.root / "decisions.json").read_bytes(), before["decisions.json"])

    def test_import_compares_with_the_latest_list_and_rejects_legacy_mode_bypass(self):
        self.decisions["decisions"][0].update(choice="suggest", reason="Offer the next step")
        core.set_decisions(self.root, self.decisions)
        before = self.snapshot()
        core.atomic_json(self.input, self.skeleton)
        stale = self.cli("set-questions", "--input", self.input, "--from-decisions", expected=2)
        self.assertEqual(stale["error"], "decision_conversion_mismatch")
        self.assertIn("empty-staging.recommendation", stale["message"])
        self.skeleton.update(mode="auto")
        del self.skeleton["run_id"]
        core.atomic_json(self.input, self.skeleton)
        for flags in ([], ["--rebind-project"]):
            result = self.cli("set-questions", "--input", self.input, *flags, expected=2)
            self.assertEqual(result["error"], "decision_list_in_use")
        self.assertEqual(self.snapshot(), before)

    def test_direct_legacy_conversion_requires_review_and_stales_the_full_auto_checkpoint(self):
        state = self.cli("status")
        self.cli("checkpoint", "--stage", 5, "--summary", "Decisions checked", "--next-action", "Build",
                 "--revision", state["revision"], "--answer-revision", state["answer_revision"])
        self.assertTrue(self.cli("status", "--json")["workflow"]["progress"]["current"])
        self.assertFalse((self.root / "review-policy.json").exists())
        core.set_questions(self.root, self.skeleton, from_decisions=True)
        state = self.cli("status", "--json")
        self.assertTrue(state["question_review"]["required"])
        self.assertFalse(state["workflow"]["progress"]["current"])
        self.assertEqual(self.cli("render", expected=2)["error"], "question_review_required")

    def test_interrupted_legacy_conversion_recovers_its_required_policy(self):
        policy = self.root / "review-policy.json"
        write_json = core.atomic_json

        def interrupt_policy_write(path, value):
            if path == policy:
                raise OSError("Conversion interrupted before the review policy was written")
            write_json(path, value)

        with patch.object(core, "atomic_json", side_effect=interrupt_policy_write), self.assertRaises(OSError):
            core.set_questions(self.root, self.skeleton, from_decisions=True)
        self.assertFalse(policy.exists())
        self.assertTrue((self.root / ".pending-state.json").exists())
        self.assertEqual(self.cli("recommend", expected=2)["error"], "question_review_required")
        self.assertFalse((self.root / ".pending-state.json").exists())
        self.assertEqual(core.read_json(policy), {"schema_version": 1, "run_id": self.skeleton["run_id"], "required": True})
        self.assertEqual(core.read_json(self.root / "answers.json")["answers"], {})
