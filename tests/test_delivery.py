"""Delivery verifies recorded execution and exact final bytes without inventing provenance."""
from __future__ import annotations

import copy
import io
import json
import os
from pathlib import Path
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

PACKAGE = Path(__file__).resolve().parents[1] / "any-skill-builder"
sys.path.insert(0, str(PACKAGE / "scripts"))
import prepare_evaluation as preparation
import verify_delivery as delivery


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        cache = os.environ.get("SKILL_BUILDER_TEST_TMPDIR")
        if cache:
            Path(cache).mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="delivery-", dir=cache)
        self.root = Path(self.temp.name)
        self.skill = self.root / "note-summary"
        self.skill.mkdir()
        (self.skill / "SKILL.md").write_text("Preserve unknown dates.\n", encoding="utf-8")
        (self.skill / "README.md").write_text("Summarize supplied notes.\n", encoding="utf-8")
        self.plan_path = self.root / "plan.json"
        self.plan_path.write_text(json.dumps({"schema_version": 1, "name": "Delivery unit fixture", "cases": [
            {"id": "unknown-date", "prompt": "Summarize an unknown date.", "input_files": [], "checks": [
                {"id": "unknown", "kind": "contains", "category": "skill_output", "artifact": "output", "text": "unconfirmed"}]}]}), encoding="utf-8")
        self.out = self.root / "iteration"
        preparation.prepare(self.plan_path, self.skill, self.out, without_skill=True)
        self.manifest = self.out / "evaluation.json"
        self.document = json.loads(self.manifest.read_text(encoding="utf-8"))
        (self.out / "result.md").write_text("The date is unconfirmed.\n", encoding="utf-8")
        (self.out / "execution.md").write_text("Unit-test execution record: read candidate snapshot and wrote result.md.\n", encoding="utf-8")
        self.record = self.document["runs"][0]["cases"][0]
        self.record.update(status="completed", artifacts={"output": "result.md", "log": "execution.md"},
                           execution={"executor": "Unit-test fixture", "relationship": "self", "transcript": "log"},
                           eval_feedback={"status": "completed", "reviewer": "Unit-test fixture", "relationship": "self",
                                          "summary": "Inspected fixture output and criterion.", "findings": []})
        self.record.pop("reason")
        self.document["reuse_review"] = {"status": "completed", "reviewer": "Unit-test fixture", "relationship": "self",
                                         "summary": "Inspected the single fixture; no repeated operation.", "inspected_runs": ["candidate"], "items": []}
        self.archive = self.root / "delivery.zip"
        self.extracted = self.root / "extracted/note-summary"
        self.save()

    def tearDown(self):
        self.temp.cleanup()

    def save(self):
        self.manifest.write_text(json.dumps(self.document), encoding="utf-8")

    def check(self, *arguments):
        self.save()
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = delivery.main(["--skill", str(self.skill), "--evaluation", str(self.manifest), *arguments])
        return code, json.loads(stdout.getvalue() or stderr.getvalue())

    def package(self):
        with zipfile.ZipFile(self.archive, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in self.skill.rglob("*"):
                if path.is_file():
                    archive.write(path, self.skill.name + "/" + path.relative_to(self.skill).as_posix())
        shutil.copytree(self.skill, self.extracted, dirs_exist_ok=True)
        return ["--archive", str(self.archive), "--extracted", str(self.extracted)]

    def test_completed_self_review_and_unknown_context_verify_with_honest_limits(self):
        code, result = self.check()
        self.assertEqual(code, 0, result)
        self.assertTrue(result["verified"])
        self.assertEqual(result["runtime"]["files"], 2)
        self.assertEqual(result["packaging"]["status"], "not_requested")
        self.assertIn("Does not certify fresh contexts", " ".join(result["limits"]))
        self.assertEqual(self.document["runs"][1]["cases"][0]["status"], "not_run")

    def test_unrelated_baseline_failures_and_findings_do_not_change_candidate_result(self):
        baseline = copy.deepcopy(self.record)
        baseline["reviews"] = {}
        (self.out / "baseline.md").write_text("Invented date.")
        baseline["artifacts"]["output"] = "baseline.md"
        baseline["eval_feedback"]["findings"] = [{"kind": "unsupported_claim", "reason": "Baseline invented a date.",
                                                    "evidence": [{"artifact": "output", "quote": "Invented date."}]}]
        self.document["runs"][1]["cases"] = [baseline]
        code, result = self.check()
        self.assertEqual(code, 0, result)

    def test_final_changed_added_and_deleted_files_all_require_a_new_evaluation(self):
        readme = self.skill / "README.md"
        original = readme.read_bytes()
        for operation in ("changed", "added", "deleted"):
            with self.subTest(operation=operation):
                readme.write_bytes(original)
                extra = self.skill / "extra.md"
                if extra.exists():
                    extra.unlink()
                if operation == "changed":
                    readme.write_text("Final README edit after execution.")
                elif operation == "added":
                    extra.write_text("Untested addition.")
                else:
                    readme.unlink()
                code, result = self.check()
                self.assertEqual(code, 1, result)
                self.assertFalse(result["verified"])
                self.assertTrue(result["runtime"]["differences"][operation])

    def test_snapshot_changed_deleted_and_unlisted_files_never_verify(self):
        snapshot = self.out / "snapshots/candidate/README.md"
        original = snapshot.read_bytes()
        for operation in ("changed", "added", "deleted"):
            with self.subTest(operation=operation):
                snapshot.write_bytes(original)
                extra = snapshot.parent / "extra.md"
                if extra.exists():
                    extra.unlink()
                if operation == "changed":
                    snapshot.write_text("Modified snapshot.")
                elif operation == "added":
                    extra.write_text("Unlisted snapshot file.")
                else:
                    snapshot.unlink()
                code, result = self.check()
                self.assertEqual(code, 1, result)
                self.assertTrue(result["runtime"]["snapshot_differences"][operation])

    def test_snapshot_inventory_cannot_omit_an_existing_runtime_file(self):
        snapshot = next(item for item in self.document["snapshots"] if item["id"] == "candidate")
        snapshot["files"] = [item for item in snapshot["files"] if not item["path"].endswith("README.md")]
        code, result = self.check()
        self.assertEqual(code, 1, result)
        self.assertEqual(result["runtime"]["snapshot_differences"]["added"], ["README.md"])

    def test_missing_run_binding_and_missing_snapshot_inventory_are_unmet(self):
        original = copy.deepcopy(self.document)
        for mutate in (lambda: self.document["runs"][0].pop("skill_snapshot"),
                       lambda: self.document.pop("snapshots")):
            self.document = copy.deepcopy(original)
            mutate()
            code, result = self.check()
            self.assertEqual(code, 1, result)
            self.assertFalse(result["verified"])

    def test_missing_provenance_and_unperformed_reviews_are_unmet(self):
        original = copy.deepcopy(self.document)
        mutations = [lambda: self.document["runs"][0]["cases"][0].pop("execution"),
                     lambda: self.document["runs"][0]["cases"][0].pop("eval_feedback"),
                     lambda: self.document["runs"][0]["cases"][0].update(eval_feedback={"status": "not_run", "reason": "Pending."}),
                     lambda: self.document.pop("reuse_review"),
                     lambda: self.document.update(reuse_review={"status": "not_run", "reason": "Pending."})]
        for mutate in mutations:
            self.document = copy.deepcopy(original)
            mutate()
            code, result = self.check()
            self.assertEqual(code, 1, result)
            self.assertFalse(result["verified"])

    def test_legacy_passing_checks_without_execution_workflow_do_not_verify(self):
        self.record.pop("execution")
        self.record.pop("eval_feedback")
        self.document.pop("reuse_review")
        code, result = self.check()
        self.assertEqual(code, 1, result)
        self.assertEqual(result["execution"]["checks"]["pass"], 1)

    def test_pending_case_and_failed_check_do_not_verify(self):
        original = copy.deepcopy(self.document)
        self.document["runs"][0]["cases"] = []
        self.document.pop("reuse_review")
        code, result = self.check()
        self.assertEqual(code, 1, result)
        self.document = original
        (self.out / "result.md").write_text("An invented date.")
        code, result = self.check()
        self.assertEqual(code, 1, result)
        self.assertEqual(result["execution"]["checks"]["fail"], 1)

    def test_unresolved_criteria_findings_block_delivery_despite_passed_checks(self):
        self.record["eval_feedback"]["findings"] = [{"kind": "weak_check", "check_id": "unknown", "reason": "Keyword alone can accept invented facts.",
                                                       "evidence": [{"artifact": "output", "quote": "unconfirmed"}]}]
        code, result = self.check()
        self.assertEqual(code, 1, result)
        self.assertEqual(result["execution"]["checks"]["pass"], 1)
        self.assertIn("unresolved workflow", " ".join(result["reasons"]))

    def test_minor_findings_do_not_block_delivery(self):
        self.record["eval_feedback"]["findings"] = [{"kind": "weak_check", "severity": "minor", "reason": "Keyword check is loose but adequate here.",
                                                       "evidence": [{"artifact": "output", "quote": "unconfirmed"}]}]
        code, result = self.check()
        self.assertEqual(code, 0, result)

    def test_empty_cases_or_checks_are_invalid_instead_of_vacuously_passing(self):
        original = copy.deepcopy(self.document)
        for mutate in (lambda: self.document.update(cases=[]),
                       lambda: self.document["cases"][0].update(checks=[])):
            self.document = copy.deepcopy(original)
            mutate()
            code, result = self.check()
            self.assertEqual(code, 2, result)
            self.assertFalse(result["verified"])

    def test_malformed_evaluator_fields_return_invalid_json_without_tracebacks(self):
        original = copy.deepcopy(self.document)
        for mutate in (lambda: self.document["cases"][0]["checks"][0].update(kind=[]),
                       lambda: self.document["runs"][1].update(variant=[]),
                       lambda: self.document["runs"][0]["cases"][0].update(status=[])):
            self.document = copy.deepcopy(original)
            mutate()
            code, result = self.check()
            self.assertEqual(code, 2, result)
            self.assertEqual(result["status"], "invalid")

    def test_missing_or_empty_execution_transcript_is_invalid(self):
        transcript = self.out / "execution.md"
        for remove in (False, True):
            if remove:
                transcript.unlink()
            else:
                transcript.write_bytes(b"")
            code, result = self.check()
            self.assertEqual(code, 2, result)

    def test_explicit_nondefault_run_selection_preserves_snapshot_binding(self):
        self.document["runs"][0]["id"] = "final-revision"
        self.document["reuse_review"]["inspected_runs"] = ["final-revision"]
        code, result = self.check("--run", "final-revision")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["runtime"]["snapshot"], "candidate")
        for name in ("candidate", "baseline"):
            code, result = self.check("--run", name)
            self.assertEqual(code, 2, result)

    def test_archive_and_extracted_folder_match_exact_final_content(self):
        code, result = self.check(*self.package())
        self.assertEqual(code, 0, result)
        self.assertEqual(result["packaging"]["status"], "matched")

    def test_final_folder_cannot_stand_in_for_the_extracted_delivery(self):
        self.package()
        code, result = self.check("--archive", str(self.archive), "--extracted", str(self.skill))
        self.assertEqual(code, 2, result)
        self.assertIn("separate directory", result["error"])

    def test_manifest_changed_during_verification_cannot_be_certified(self):
        evaluate = delivery.evaluation.evaluate

        def changed_manifest(path):
            document = json.loads(path.read_text(encoding="utf-8"))
            document["name"] = "Edited concurrently"
            path.write_text(json.dumps(document), encoding="utf-8")
            return evaluate(path)

        with patch.object(delivery.evaluation, "evaluate", side_effect=changed_manifest):
            code, result = self.check()
        self.assertEqual(code, 1, result)
        self.assertIn("changed during verification", " ".join(result["reasons"]))

    def test_archive_and_extracted_changes_are_unmet(self):
        args = self.package()
        with zipfile.ZipFile(self.archive, "a") as archive:
            archive.writestr("note-summary/extra.md", "An extra archived file.")
        (self.extracted / "README.md").write_text("Different extracted bytes.")
        code, result = self.check(*args)
        self.assertEqual(code, 1, result)
        self.assertEqual(result["packaging"]["archive_differences"]["added"], ["extra.md"])
        self.assertEqual(result["packaging"]["extracted_differences"]["changed"], ["README.md"])

    def test_missing_archive_or_extracted_files_are_unmet(self):
        args = self.package()
        with zipfile.ZipFile(self.archive, "w") as archive:
            archive.writestr("note-summary/SKILL.md", (self.skill / "SKILL.md").read_bytes())
        (self.extracted / "README.md").unlink()
        code, result = self.check(*args)
        self.assertEqual(code, 1, result)
        self.assertEqual(result["packaging"]["archive_differences"]["deleted"], ["README.md"])
        self.assertEqual(result["packaging"]["extracted_differences"]["deleted"], ["README.md"])

    def test_archive_unsafe_paths_case_aliases_and_duplicate_members_are_invalid(self):
        bad_names = ("../escape.md", "/absolute.md", "C:/outside.md", "note-summary/../escape.md",
                     "note-summary\\escape.md", "note-summary/./alias.md", "note-summary//alias.md",
                     "note-summary/file:stream", "note-summary/NUL", "wrong-root/file.md",
                     "note-summary/skill.md", "note-summary/SKILL.md", "note-summary/CONIN$",
                     "note-summary/CONOUT$", "note-summary/con .txt", "note-summary/aux .txt")
        for name in bad_names:
            with self.subTest(name=name):
                args = self.package()
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    with zipfile.ZipFile(self.archive, "a") as archive:
                        member = zipfile.ZipInfo(name)
                        member.filename = name
                        archive.writestr(member, "Unsafe member.")
                code, result = self.check(*args)
                self.assertEqual(code, 2, result)

    def test_zip_file_directory_collisions_are_invalid_in_both_orders(self):
        for names in (("note-summary/dir", "note-summary/dir/file.md"),
                      ("note-summary/dir/file.md", "note-summary/dir")):
            args = self.package()
            with zipfile.ZipFile(self.archive, "a") as archive:
                for name in names:
                    archive.writestr(name, "Conflicting path.")
            code, result = self.check(*args)
            self.assertEqual(code, 2, result)
            self.assertIn("collision", result["error"])

    def test_corrupt_compressed_archive_returns_invalid_json_without_traceback(self):
        args = self.package()
        with zipfile.ZipFile(self.archive) as archive:
            offset = archive.getinfo("note-summary/SKILL.md").header_offset
        blob = bytearray(self.archive.read_bytes())
        name_length, extra_length = struct.unpack_from("<HH", blob, offset + 26)
        blob[offset + 30 + name_length + extra_length] = 0xff
        self.archive.write_bytes(blob)
        code, result = self.check(*args)
        self.assertEqual(code, 2, result)
        self.assertIn("Cannot read ZIP member", result["error"])

    def test_zip_symlink_and_oversized_contents_are_invalid(self):
        args = self.package()
        link = zipfile.ZipInfo("note-summary/link.md")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        with zipfile.ZipFile(self.archive, "a") as archive:
            archive.writestr(link, "../outside.md")
        code, result = self.check(*args)
        self.assertEqual(code, 2, result)
        args = self.package()
        with patch.object(delivery.evaluation, "MAX_BYTES", 8):
            with self.assertRaisesRegex(delivery.evaluation.EvaluationError, "16 MiB file"):
                delivery.archive_inventory(self.archive, self.skill.name)

    def test_symlink_runtime_or_evidence_is_invalid(self):
        target = self.root / "target.md"
        target.write_text("Outside runtime.")
        link = self.skill / "linked.md"
        try:
            link.symlink_to(target)
        except OSError:
            self.skipTest("Creating symlinks requires platform support or permission.")
        code, result = self.check()
        self.assertEqual(code, 2, result)
        link.unlink()
        log = self.out / "execution.md"
        log.unlink()
        log.symlink_to(target)
        code, result = self.check()
        self.assertEqual(code, 2, result)

    def test_packaging_arguments_must_be_paired_and_cli_emits_machine_json(self):
        for arguments in (["--archive", str(self.archive)], ["--extracted", str(self.extracted)]):
            code, result = self.check(*arguments)
            self.assertEqual(code, 2, result)
        completed = subprocess.run([sys.executable, "-B", str(PACKAGE / "scripts/verify_delivery.py"),
                                    "--skill", str(self.skill), "--evaluation", str(self.manifest)],
                                   capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(json.loads(completed.stdout)["verified"])
        invalid = subprocess.run([sys.executable, "-B", str(PACKAGE / "scripts/verify_delivery.py")],
                                 capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(invalid.returncode, 2)
        self.assertEqual(json.loads(invalid.stderr)["status"], "invalid")


if __name__ == "__main__":
    unittest.main()
