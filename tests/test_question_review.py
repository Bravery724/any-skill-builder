"""Review records fail closed on missing coverage, stale input, and open work."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPOSITORY = Path(__file__).resolve().parents[1]
SCRIPTS = REPOSITORY / "any-skill-builder" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import builder_core as core
import review_questions as reviews

CACHE = os.environ.get("SKILL_BUILDER_TEST_TMPDIR")
if CACHE is None and os.name == "nt" and Path("D:/projects").exists():
    CACHE = "D:/projects/CodexCache/skill-builder-release/question-review-tests"
if CACHE:
    Path(CACHE).mkdir(parents=True, exist_ok=True)


def two_question_fixture():
    """Two unconditional example decisions for review/gate integration tests."""
    fixture = core.read_json(REPOSITORY / "examples" / "questionnaire.json")
    fixture["questions"] = [fixture["questions"][0], fixture["questions"][2]]
    return fixture


def completed_example_review(questions_path, review_path):
    """Synthetic test record for two_question_fixture(); not a production reviewer."""
    record = reviews.prepare(questions_path, review_path)
    record["status"] = "pass"
    record["reviewer"] = {"identity": "Test fixture reviewer", "relationship": "self"}
    for row in record["question_reviews"]:
        row.update(status="pass", reason="Both working styles preserve a factual update; output sections use supplied evidence.")
    record["combinations"][0].update(
        status="pass", reason="Drafting with visible gaps works with all evidence-backed output sections.",
        answers=[{"question_id": "workflow", "value": "draft"},
                 {"question_id": "outputs", "value": ["progress", "next", "risks"]}])
    record["combinations"][1].update(
        status="pass", reason="Clarifying first also supports a shorter progress-only update without inventing facts.",
        answers=[{"question_id": "workflow", "value": "clarify"},
                 {"question_id": "outputs", "value": ["progress"]}])
    record["localization"].update(status="pass", reason="All inventoried authored text is English; source titles may preserve spelling.")
    record["fair_alternatives"].update(status="pass", reason="Drafting and clarifying both serve the goal with different delay and uncertainty tradeoffs.")
    record["unknown_private_facts"].update(status="pass", reason="Neither path assigns unprovided owners or deadlines; uncertainty remains explicit.")
    return record


class QuestionReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="question-review-", dir=CACHE)
        self.root = Path(self.temp.name)
        self.questions_path = self.root / "questions.json"
        self.review_path = self.root / "review.json"
        fixture = two_question_fixture()
        self.questionnaire = fixture
        core.atomic_json(self.questions_path, fixture)

    def tearDown(self):
        self.temp.cleanup()

    def template(self):
        return reviews.prepare(self.questions_path, self.review_path)

    def completed(self):
        return completed_example_review(self.questions_path, self.review_path)

    def checked(self, record):
        core.atomic_json(self.review_path, record)
        return reviews.check(self.questions_path, self.review_path)

    def test_prepare_is_pending_and_bound_to_exact_bytes(self):
        record = self.template()
        self.assertEqual(record["questions_sha256"], hashlib.sha256(self.questions_path.read_bytes()).hexdigest())
        self.assertEqual(record["reviewer"], {"identity": "", "relationship": "unknown"})
        report = self.checked(record)
        self.assertEqual(report["status"], "pending")
        self.assertFalse(report["passed"])
        self.assertIn("does not certify", report["limitations"])

    def test_prepare_never_overwrites_questionnaire_or_existing_review(self):
        before = self.questions_path.read_bytes()
        with self.assertRaises(reviews.ReviewError):
            reviews.prepare(self.questions_path, self.questions_path)
        self.template()
        self.review_path.write_text("preserve me", encoding="utf-8")
        with self.assertRaises(reviews.ReviewError):
            self.template()
        self.assertEqual(self.questions_path.read_bytes(), before)
        self.assertEqual(self.review_path.read_text(encoding="utf-8"), "preserve me")

    def test_missing_review_does_not_pass(self):
        self.assertEqual(reviews.check(self.questions_path, self.review_path)["status"], "missing")

    def test_completed_record_passes_without_claiming_semantic_certification(self):
        report = self.checked(self.completed())
        self.assertTrue(report["passed"], report)
        self.assertEqual(report["findings"], [])

    def test_any_questionnaire_byte_change_stales_review(self):
        record = self.completed()
        self.questions_path.write_bytes(self.questions_path.read_bytes() + b"\n")
        report = self.checked(record)
        self.assertEqual(report["status"], "stale")
        self.assertFalse(report["passed"])

    def test_omitted_questions_and_ordinary_options_fail(self):
        original = self.completed()
        for mutation in (lambda record: record["question_reviews"].pop(),
                         lambda record: record["question_reviews"][0]["option_ids"].pop()):
            with self.subTest(mutation=mutation):
                record = copy.deepcopy(original)
                mutation(record)
                self.assertFalse(self.checked(record)["passed"])

    def test_option_requirement_and_question_references_are_checked(self):
        original = self.completed()
        mutations = [
            lambda record: record["question_reviews"][0]["option_ids"].append("invented"),
            lambda record: record["question_reviews"][0]["option_ids"].append("draft"),
            lambda record: record["question_reviews"][0].update(requirement_ids=["invented"]),
            lambda record: record["question_reviews"][0].update(question_id="invented"),
            lambda record: record["question_reviews"].append(copy.deepcopy(record["question_reviews"][0])),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                record = copy.deepcopy(original)
                mutation(record)
                self.assertEqual(self.checked(record)["status"], "invalid")

    def test_goal_invariant_cannot_be_replaced_by_easy_alternative(self):
        record = self.completed()
        record["requirements"][0]["statement"] = "Keep the default answer convenient"
        self.assertFalse(self.checked(record)["passed"])

    def test_source_requirement_needs_real_source_reference(self):
        record = self.completed()
        record["requirements"].append({"id": "factual", "statement": "Do not invent owners",
                                       "basis": {"kind": "source", "reference": "invented", "evidence": "Quoted source"}})
        self.assertFalse(self.checked(record)["passed"])

    def test_every_question_and_combination_must_consider_all_fixed_requirements(self):
        record = self.completed()
        record["requirements"].append({"id": "factual", "statement": "Never invent an owner or deadline",
                                       "basis": {"kind": "user", "reference": "original request",
                                                 "evidence": "Only use factual details from the supplied notes"}})
        self.assertFalse(self.checked(record)["passed"], "A listed but unused fixed requirement must not pass.")
        for row in record["question_reviews"] + record["combinations"]:
            row["requirement_ids"].append("factual")
        self.assertTrue(self.checked(record)["passed"])
        for section in ("question_reviews", "combinations"):
            with self.subTest(section=section):
                incomplete = copy.deepcopy(record)
                incomplete[section][0]["requirement_ids"].remove("factual")
                self.assertFalse(self.checked(incomplete)["passed"], "A fixed requirement cannot be skipped in just one review row.")

    def test_empty_questionnaire_cannot_claim_completed_requirement_review(self):
        self.questionnaire["questions"] = []
        core.atomic_json(self.questions_path, self.questionnaire)
        record = self.template()
        self.assertEqual(self.checked(record)["status"], "pending")
        record.update(status="pass", reviewer={"identity": "Test reviewer", "relationship": "self"})
        for section in ("localization", "fair_alternatives", "unknown_private_facts"):
            record[section].update(status="pass", reason="No questions are present.")
        record["no_combinations_reason"] = "There are no decisions to combine."
        self.assertFalse(self.checked(record)["passed"])

    def test_top_level_pass_does_not_override_pending_or_failed_checks(self):
        original = self.completed()
        for status in ("pending", "needs-revision"):
            with self.subTest(status=status):
                record = copy.deepcopy(original)
                record["question_reviews"][0].update(status=status, reason="An option would invent a deadline.")
                report = self.checked(record)
                self.assertFalse(report["passed"])
                self.assertEqual(report["status"], status)
                self.assertTrue(any(finding["message"] == "An option would invent a deadline." for finding in report["findings"]))

    def test_open_findings_block_pass_until_resolution_is_recorded(self):
        record = self.completed()
        record["findings"] = [{"id": "unfair", "status": "open", "area": "fair_alternatives",
                               "question_ids": ["workflow"], "description": "Clarification option understates its delay.", "resolution": ""}]
        report = self.checked(record)
        self.assertEqual(report["status"], "needs-revision")
        self.assertIn("open_finding", {finding["code"] for finding in report["findings"]})
        record["findings"][0].update(status="resolved", resolution="Existing help already states the timing tradeoff; checked both options.")
        self.assertTrue(self.checked(record)["passed"])

    def test_combination_references_values_and_duplicates_are_checked(self):
        original = self.completed()
        mutations = [
            lambda record: record["combinations"][0]["answers"][0].update(question_id="invented"),
            lambda record: record["combinations"][0]["answers"][0].update(value="invented"),
            lambda record: record["combinations"][0]["answers"][0].update(value="clarify"),
            lambda record: record["combinations"][0]["answers"].append(copy.deepcopy(record["combinations"][0]["answers"][0])),
            lambda record: record["combinations"].pop(),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                record = copy.deepcopy(original)
                mutation(record)
                self.assertFalse(self.checked(record)["passed"])

    def test_contrast_cannot_relabel_or_reorder_recommended_choices(self):
        record = self.completed()
        record["combinations"][1]["answers"] = copy.deepcopy(record["combinations"][0]["answers"])
        record["combinations"][1]["answers"][1]["value"].reverse()
        self.assertFalse(self.checked(record)["passed"])

    def test_one_decision_requires_explicitly_inactive_other_questions(self):
        record = self.completed()
        record["combinations"][1]["answers"].pop()
        record["combinations"][1]["fewer_decisions_reason"] = "I chose to skip the output decision."
        self.assertFalse(self.checked(record)["passed"])

    def test_conditionally_inactive_questions_allow_honest_single_decision_contrast(self):
        self.questionnaire["questions"][1]["when"] = [{"question_id": "workflow", "equals": "draft"}]
        core.atomic_json(self.questions_path, self.questionnaire)
        record = self.completed()
        contrast = record["combinations"][1]
        contrast["answers"].pop()
        contrast["inapplicable_question_ids"] = ["outputs"]
        contrast["fewer_decisions_reason"] = "Clarification does not select output sections until the later drafting branch."
        self.assertTrue(self.checked(record)["passed"])
        contrast["inapplicable_question_ids"] = []
        self.assertFalse(self.checked(record)["passed"])

    def test_combination_cannot_include_inactive_question(self):
        self.questionnaire["questions"][1]["when"] = [{"question_id": "workflow", "equals": "draft"}]
        core.atomic_json(self.questions_path, self.questionnaire)
        record = self.completed()
        self.assertFalse(self.checked(record)["passed"])

    def test_custom_value_and_explained_branch_interpretation_are_supported(self):
        self.questionnaire["questions"][1]["when"] = [{"question_id": "workflow", "equals": "draft"}]
        core.atomic_json(self.questions_path, self.questionnaire)
        record = self.completed()
        record["combinations"][1]["answers"][0].update(
            value={"other": "Draft only corroborated material and leave gaps marked", "selected": []},
            branch_value="draft", branch_rationale="This is a cautious drafting variant, so output sections apply.")
        self.assertTrue(self.checked(record)["passed"])
        del record["combinations"][1]["answers"][0]["branch_value"]
        del record["combinations"][1]["answers"][0]["branch_rationale"]
        self.assertFalse(self.checked(record)["passed"])

    def test_review_reuses_ordinary_minimum_exclusive_and_custom_answer_rules(self):
        outputs = self.questionnaire["questions"][1]
        outputs["min_choices"] = 2
        outputs["options"].append({"id": "none", "label": "No standard sections",
                                   "effect": "Use a single narrative update instead", "exclusive": True})
        core.atomic_json(self.questions_path, self.questionnaire)
        record = self.completed()
        answer = record["combinations"][1]["answers"][1]
        self.assertFalse(self.checked(record)["passed"], "An ordinary one-option answer violates min_choices=2.")
        answer["value"] = ["none"]
        self.assertTrue(self.checked(record)["passed"], "Exclusive ordinary choices can stand alone.")
        answer["value"] = {"other": "Write a short narrative using only verified facts", "selected": []}
        self.assertTrue(self.checked(record)["passed"], "A meaningful Other can replace the ordinary option list.")
        answer["value"]["selected"] = ["none"]
        self.assertFalse(self.checked(record)["passed"], "An exclusive ordinary option cannot coexist with Other.")

    def test_single_question_requires_honest_no_combination_reason(self):
        self.questionnaire["questions"] = self.questionnaire["questions"][:1]
        core.atomic_json(self.questions_path, self.questionnaire)
        record = self.template()
        record.update(status="pass", reviewer={"identity": "Test reviewer", "relationship": "separate"})
        for row in record["question_reviews"] + [record["localization"], record["fair_alternatives"], record["unknown_private_facts"]]:
            row.update(status="pass", reason="Both supplied options remain supported by the single decision.")
        self.assertFalse(self.checked(record)["passed"])
        record["no_combinations_reason"] = "Only one decision exists, so there is no pair of decisions to combine."
        self.assertTrue(self.checked(record)["passed"])

    def test_localization_inventory_includes_all_authored_display_text(self):
        q = self.questionnaire["questions"][0]
        q["placeholder"] = "Describe another working style"
        q["options"][0].update(description="Produce a reviewable draft", traits=["clear"])
        self.questionnaire["sources"] = [{"id": "guide", "title": "원본 제목", "kind": "document", "status": "read",
                                         "accessed_at": "2026-11-15", "notes": "Reviewed the full guide", "quote": "원문"}]
        core.atomic_json(self.questions_path, self.questionnaire)
        record = self.completed()
        paths = set(record["localization"]["fields"])
        for path in ("/goal", "/groups/0/label", "/questions/0/title", "/questions/0/help", "/questions/0/decision", "/questions/0/placeholder",
                     "/questions/0/options/0/label", "/questions/0/options/0/description", "/questions/0/options/0/effect",
                     "/questions/0/recommendation/rationale", "/questions/0/recommendation/assumptions/0", "/sources/0/notes", "/sources/0/accessed_at"):
            self.assertIn(path, paths)
        record["localization"]["original_language_fields"] = ["/sources/0/title", "/sources/0/quote"]
        self.assertTrue(self.checked(record)["passed"])
        record["localization"]["fields"].remove("/sources/0/notes")
        self.assertFalse(self.checked(record)["passed"])

    def test_localization_cannot_omit_placeholder_or_visible_source_date(self):
        self.questionnaire["questions"][0]["placeholder"] = "Describe another approach"
        self.questionnaire["sources"] = [{"id": "guide", "title": "Style guide", "kind": "document", "status": "read",
                                         "accessed_at": "2026-11-15", "notes": "Reviewed the whole guide"}]
        core.atomic_json(self.questions_path, self.questionnaire)
        original = self.completed()
        for path in ("/questions/0/placeholder", "/sources/0/accessed_at"):
            with self.subTest(path=path):
                record = copy.deepcopy(original)
                record["localization"]["fields"].remove(path)
                self.assertFalse(self.checked(record)["passed"])

    def test_localization_cannot_exempt_help_or_use_wrong_language(self):
        original = self.completed()
        record = copy.deepcopy(original)
        record["localization"]["original_language_fields"] = ["/questions/0/help"]
        self.assertFalse(self.checked(record)["passed"])
        record = copy.deepcopy(original)
        record["localization"]["language"] = "ko"
        self.assertFalse(self.checked(record)["passed"])

    def test_review_requires_actual_identity_but_does_not_infer_isolation(self):
        record = self.completed()
        record["reviewer"]["identity"] = ""
        self.assertFalse(self.checked(record)["passed"])
        record["reviewer"] = {"identity": "Host assistant", "relationship": "unknown"}
        self.assertTrue(self.checked(record)["passed"])
        record["reviewer"]["relationship"] = "blind-and-guaranteed-independent"
        self.assertFalse(self.checked(record)["passed"])

    def test_unknown_fields_duplicate_json_keys_and_empty_pass_reasons_fail(self):
        original = self.completed()
        for record in (dict(original, certified=True), copy.deepcopy(original)):
            if "certified" not in record:
                record["fair_alternatives"]["reason"] = ""
            self.assertFalse(self.checked(record)["passed"])
        self.review_path.write_text('{"status":"pending","status":"pass"}', encoding="utf-8")
        report = reviews.check(self.questions_path, self.review_path)
        self.assertFalse(report["passed"])
        self.assertIn("Duplicate JSON key", report["findings"][0]["message"])

    def test_cli_returns_nonzero_for_pending_and_zero_only_after_pass(self):
        record = self.completed()
        pending = subprocess.run([sys.executable, str(SCRIPTS / "review_questions.py"), "check", "--questions", str(self.questions_path),
                                  "--review", str(self.review_path)], capture_output=True, text=True, check=False)
        self.assertEqual(pending.returncode, 1, pending.stderr)
        self.assertEqual(json.loads(pending.stdout)["status"], "pending")
        core.atomic_json(self.review_path, record)
        passed = subprocess.run([sys.executable, str(SCRIPTS / "review_questions.py"), "check", "--questions", str(self.questions_path),
                                 "--review", str(self.review_path)], capture_output=True, text=True, check=False)
        self.assertEqual(passed.returncode, 0, passed.stderr)
        self.assertTrue(json.loads(passed.stdout)["passed"])


if __name__ == "__main__":
    unittest.main()
