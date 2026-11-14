"""Regression cases for compatibility, editing, and basic skill validation."""
from __future__ import annotations

import copy
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY / "any-skill-builder" / "scripts"))
import builder_core as core

CACHE = os.environ.get("SKILL_BUILDER_TEST_TMPDIR")
if CACHE:
    Path(CACHE).mkdir(parents=True, exist_ok=True)


class RuntimeFixTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="runtime-fixes-", dir=CACHE)
        self.parent = Path(self.temp.name)
        self.root = self.parent / "example"
        core.init_workspace(self.root, "Create a weekly update skill")
        self.fixture = core.read_json(REPOSITORY / "examples" / "questionnaire.json")

    def tearDown(self):
        self.temp.cleanup()

    def install_answered(self):
        core.set_questions(self.root, self.fixture)
        core.answer_one(self.root, "workflow", "clarify")
        core.answer_one(self.root, "clarification", "Ask about missing dates")
        core.answer_one(self.root, "outputs", ["progress", "next"])
        return core.status(self.root)

    def canonical_bytes(self):
        return tuple((self.root / name).read_bytes() for name in ("questions.json", "answers.json"))

    def test_image_hash_does_not_require_python311_file_digest(self):
        content = b"multi-chunk content\x00" * 120000
        asset = self.root / "assets" / "hash.bin"
        asset.write_bytes(content)
        with patch.object(hashlib, "file_digest", None, create=True):
            self.assertEqual(core.image_digest(asset), hashlib.sha256(content).hexdigest())

    def test_empty_image_hash_matches_standard_digest(self):
        asset = self.root / "assets" / "empty.png"
        asset.write_bytes(b"")
        self.assertEqual(core.image_digest(asset), hashlib.sha256(b"").hexdigest())






    def test_explicit_cosmetic_edit_preserves_answer_and_descendants(self):
        before = self.install_answered()
        data = copy.deepcopy(before["questionnaire"])
        data["questions"][0]["help"] = "Choose your workflow."
        result = core.set_questions(self.root, data, presentation_only=["workflow"])
        self.assertEqual(result["answers"]["answers"], before["answers"]["answers"])
        self.assertEqual(result["answers"]["history"], before["answers"]["history"])
        self.assertEqual(result["questionnaire"]["revision"], before["questionnaire"]["revision"] + 1)
        self.assertEqual(result["questionnaire"]["questions"][0]["version"], 1)
        self.assertEqual(result["change_summary"]["presentation_only"], ["workflow"])
        self.assertEqual(result["change_summary"]["invalidated_answers"], [])
        edit = result["questionnaire"]["presentation_history"][-1]
        self.assertEqual(edit["question_id"], "workflow")
        self.assertEqual(edit["after"]["help"], "Choose your workflow.")
        self.assertTrue(result["ready_to_build"])
        with self.assertRaisesRegex(core.BuilderError, "Questions changed"):
            core.update_answers(self.root, {
                "project_id": before["questionnaire"]["project_id"],
                "run_id": before["questionnaire"]["run_id"],
                "revision": before["questionnaire"]["revision"],
                "base_answer_revision": before["answers"]["answer_revision"], "changes": {},
            })

    def test_cosmetic_edit_preserves_custom_user_direction(self):
        core.set_questions(self.root, self.fixture)
        before = core.answer_one(self.root, "workflow", {"other": "Draft only when evidence is sufficient", "selected": []})
        data = copy.deepcopy(before["questionnaire"])
        data["questions"][0]["title"] = "Which working style do you prefer?"
        result = core.set_questions(self.root, data, presentation_only=["workflow"])
        self.assertEqual(result["answers"]["answers"], before["answers"]["answers"])
        self.assertEqual(result["counts"]["answered"], 1)
        self.assertFalse(result["ready_to_build"])

    def test_cosmetic_update_coexists_with_semantic_change_elsewhere(self):
        before = self.install_answered()
        data = copy.deepcopy(before["questionnaire"])
        data["questions"][0]["help"] = "Choose your workflow."
        data["questions"][2]["options"][0]["effect"] = "Include verified progress percentages"
        result = core.set_questions(self.root, data, presentation_only=["workflow"])
        self.assertIn("workflow", result["answers"]["answers"])
        self.assertIn("clarification", result["answers"]["answers"])
        self.assertNotIn("outputs", result["answers"]["answers"])
        self.assertEqual(result["change_summary"]["revised"], ["outputs"])
        self.assertEqual(result["change_summary"]["invalidated_answers"], ["outputs"])

    def test_cosmetic_flag_does_not_allow_behavior_changes(self):
        before = self.install_answered()
        original = self.canonical_bytes()
        mutations = [
            lambda q: q.update(decision="Invent missing milestones"),
            lambda q: q["options"][0].update(effect="Invent missing dates"),
            lambda q: q["options"][0].update(id="renamed-option"),
            lambda q: q.update(type="multi"),
            lambda q: q.update(recommendation={"value": "clarify", "rationale": "Changed decision"}),
            lambda q: q.update(source_ids=["other-source"]),
            lambda q: q.update(when=[{"question_id": "outputs", "includes": "progress"}]),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                data = copy.deepcopy(before["questionnaire"])
                mutate(data["questions"][0])
                with self.assertRaises(core.BuilderError) as error:
                    core.set_questions(self.root, data, presentation_only=["workflow"])
                self.assertEqual(error.exception.code, "non_presentation_change")
                self.assertEqual(self.canonical_bytes(), original)

    def test_cosmetic_flag_rejects_goal_or_referenced_evidence_change(self):
        data = copy.deepcopy(self.fixture)
        data["sources"] = [{"id": "source", "title": "Fixture", "kind": "user", "status": "unavailable", "notes": "Original note"}]
        data["questions"][0]["source_ids"] = ["source"]
        core.set_questions(self.root, data)
        before = core.status(self.root)["questionnaire"]
        for field in ("goal", "source"):
            with self.subTest(field=field):
                changed = copy.deepcopy(before)
                if field == "goal":
                    changed["goal"] = "A materially different goal"
                else:
                    changed["sources"][0]["notes"] = "Different evidence"
                with self.assertRaises(core.BuilderError) as error:
                    core.set_questions(self.root, changed, presentation_only=["workflow"])
                self.assertEqual(error.exception.code, "non_presentation_change")

    def test_cosmetic_flag_cannot_preserve_a_changed_image_selection(self):
        data = copy.deepcopy(self.fixture)
        question = data["questions"][0]
        question["type"] = "image"
        for option in question["options"]:
            option["image"] = f"assets/{option['id']}.svg"
            (self.root / option["image"]).write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>", encoding="utf-8")
        core.set_questions(self.root, data)
        core.answer_one(self.root, "workflow", "draft")
        before = core.status(self.root)
        incoming = copy.deepcopy(before["questionnaire"])
        image = self.root / incoming["questions"][0]["options"][0]["image"]
        image.write_text("<svg xmlns='http://www.w3.org/2000/svg'><circle r='2'/></svg>", encoding="utf-8")
        original = self.canonical_bytes()
        with self.assertRaises(core.BuilderError) as error:
            core.set_questions(self.root, incoming, presentation_only=["workflow"])
        self.assertEqual(error.exception.code, "non_presentation_change")
        self.assertEqual(self.canonical_bytes(), original)
        result = core.set_questions(self.root, incoming)
        self.assertNotIn("workflow", result["answers"]["answers"])
        self.assertEqual(result["answers"]["history"][-1]["answer"]["value"], "draft")

    def test_cosmetic_flag_rejects_new_or_removed_ids(self):
        core.set_questions(self.root, self.fixture)
        data = core.status(self.root)["questionnaire"]
        for ids in (["missing"], ["workflow", "workflow"], "workflow"):
            with self.subTest(ids=ids), self.assertRaises(core.BuilderError):
                core.set_questions(self.root, data, presentation_only=ids)
        changed = copy.deepcopy(data)
        changed["questions"] = [q for q in changed["questions"] if q["id"] != "clarification"]
        with self.assertRaises(core.BuilderError):
            core.set_questions(self.root, changed, presentation_only=["clarification"])

    def test_cosmetic_history_is_managed_not_replaced_by_input(self):
        before = self.install_answered()
        data = copy.deepcopy(before["questionnaire"])
        data["questions"][0]["help"] = "Corrected wording"
        first = core.set_questions(self.root, data, presentation_only=["workflow"])
        data = copy.deepcopy(first["questionnaire"])
        data["presentation_history"] = [{"forged": "entry"}]
        result = core.set_questions(self.root, data)
        self.assertEqual(result["questionnaire"]["presentation_history"], first["questionnaire"]["presentation_history"])
        self.assertEqual(result["questionnaire"]["revision"], first["questionnaire"]["revision"])

    def test_normal_edit_still_invalidates_answers_and_keeps_history(self):
        before = self.install_answered()
        data = copy.deepcopy(before["questionnaire"])
        data["questions"][0]["help"] = "This wording could change the decision."
        result = core.set_questions(self.root, data)
        self.assertNotIn("workflow", result["answers"]["answers"])
        self.assertNotIn("clarification", result["answers"]["answers"])
        self.assertIn("outputs", result["answers"]["answers"])
        self.assertEqual({entry["question_id"] for entry in result["answers"]["history"]}, {"workflow", "clarification"})

    def test_fixture_can_be_bound_to_a_different_empty_workspace_name(self):
        root = self.parent / "another-name"
        identity = core.init_workspace(root, "Create a weekly update skill")
        with self.assertRaises(core.BuilderError) as error:
            core.set_questions(root, self.fixture)
        self.assertEqual(error.exception.code, "wrong_project")
        result = core.set_questions(root, self.fixture, rebind_project=True)
        self.assertEqual(result["questionnaire"]["project_id"], "another-name")
        self.assertEqual(result["questionnaire"]["run_id"], identity["run_id"])
        self.assertEqual(result["answers"]["run_id"], identity["run_id"])
        self.assertEqual(self.fixture["project_id"], "example")

    def test_fixture_rebinding_cannot_replace_an_existing_questionnaire(self):
        before = self.install_answered()
        with self.assertRaises(core.BuilderError) as error:
            core.set_questions(self.root, before["questionnaire"], rebind_project=True)
        self.assertEqual(error.exception.code, "rebind_requires_empty_run")

    def test_fixture_rebinding_rejects_run_identity_and_answer_records(self):
        identity = core.status(self.root)["questionnaire"]["run_id"]
        for field, value in (("run_id", identity), ("answers", {}), ("answer_revision", 0), ("history", [])):
            with self.subTest(field=field):
                data = copy.deepcopy(self.fixture)
                data[field] = value
                with self.assertRaises(core.BuilderError) as error:
                    core.set_questions(self.root, data, rebind_project=True)
                self.assertEqual(error.exception.code, "not_authored_questionnaire")
        self.assertEqual(core.status(self.root)["questionnaire"]["questions"], [])

    def test_bound_fixture_does_not_allow_answers_from_another_run(self):
        self.install_answered()
        foreign = core.status(self.root)["answers"]
        other = self.parent / "other"
        core.init_workspace(other, "Create a weekly update skill")
        core.set_questions(other, self.fixture, rebind_project=True)
        foreign["project_id"] = "other"
        with self.assertRaises(core.BuilderError) as error:
            core.import_answers(other, foreign)
        self.assertEqual(error.exception.code, "wrong_run")


class SkillCheckFixTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="skill-check-", dir=CACHE)
        self.root = Path(self.temp.name) / "sample-skill"
        self.root.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def write_skill(self, description, body="Use the supplied source to answer the request.\n"):
        (self.root / "SKILL.md").write_text(
            "---\nname: sample-skill\ndescription: " + description + "\n---\n\n" + body, encoding="utf-8")

    def test_common_multiline_yaml_string_forms_are_accepted(self):
        for description in (
            "|\n  Explain supplied sources\n  when the user asks.",
            ">-\n  Explain supplied sources\n  when the user asks.",
            '"Explain supplied sources\n  when the user asks."',
            "'Explain supplied sources\n  when the user asks.'",
            "Explain supplied sources\n  when the user asks.",
            "\n  Explain supplied sources\n  when the user asks.",
        ):
            with self.subTest(description=description):
                self.write_skill(description)
                self.assertTrue(core.check_skill(self.root)["valid"])

    def test_yaml_specific_escapes_and_comments_are_supported(self):
        self.write_skill('"Explain \\x73ources and \\N newlines" # comment')
        self.assertTrue(core.check_skill(self.root)["valid"])
        self.write_skill("'Explain the user''s source' # comment")
        self.assertTrue(core.check_skill(self.root)["valid"])
        self.write_skill("|\n  # This line is literal scalar content.")
        self.assertTrue(core.check_skill(self.root)["valid"])

    def test_invalid_or_empty_description_is_still_rejected(self):
        for description in ('"Unclosed', "'Unclosed", '"Bad \\q escape"', '"value" trailing text', "|\n  ", "# only a comment"):
            with self.subTest(description=description):
                self.write_skill(description)
                with self.assertRaises(core.BuilderError):
                    core.check_skill(self.root)

    def test_fenced_inline_and_indented_example_links_are_not_resources(self):
        self.write_skill("Explain sources when requested.", """# Instructions

```markdown
[Output](output/not-yet-created.md)
```

~~~md
[Another](missing.md)
~~~

Use `[Example](also-missing.md)` when showing Markdown syntax.
Use ``[Example](missing-again.md) `inside` `` for longer code spans.

    [Indented code](not-a-resource.md)

[Actual reference](reference.md)
""")
        (self.root / "reference.md").write_text("Actual instructions.\n", encoding="utf-8")
        result = core.check_skill(self.root)
        self.assertEqual(result["references_checked"], ["reference.md"])

    def test_shorter_fence_inside_longer_fence_does_not_expose_examples(self):
        self.write_skill("Explain sources.", "````markdown\n```\n[Example](missing.md)\n```\n````\nUse sources.\n")
        self.assertEqual(core.check_skill(self.root)["references_checked"], [])

    def test_missing_real_link_is_still_rejected_after_fence(self):
        self.write_skill("Explain sources.", "```md\n[Example](ignore.md)\n```\n[Reference](required.md)\n")
        with self.assertRaisesRegex(core.BuilderError, "required.md"):
            core.check_skill(self.root)

    def test_path_escape_is_still_rejected(self):
        self.write_skill("Explain sources.", "[Reference](../outside.md)\n")
        with self.assertRaisesRegex(core.BuilderError, "escapes skill folder"):
            core.check_skill(self.root)


if __name__ == "__main__":
    unittest.main()
