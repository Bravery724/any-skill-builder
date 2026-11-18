import concurrent.futures
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / "any-skill-builder" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import evaluate_skill as evaluation
import run_cli_cases as runner
from verify_delivery import verify


SCRIPT = """import json, sys
from pathlib import Path
raw = Path(sys.argv[2]).read_bytes() if len(sys.argv) == 3 else sys.stdin.buffer.read()
print(json.dumps({"words": raw.decode("utf-8").split(), "label": sys.argv[1]}))
sys.stderr.buffer.write(b"counted\\r\\n")
sys.exit(7 if raw.startswith(b"!") else 0)
"""


class CliCases(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.plan = self.root / "spec" / "plan.json"
        self.plan.parent.mkdir()
        (self.plan.parent / "raw.txt").write_bytes("one 둘\r\n".encode())
        self.expected = self.plan.parent / "answer.json"
        self.label = "literal ; & > $"
        self.answer = {"label": self.label, "words": ["one", "둘"]}
        self.expected.write_text(json.dumps(self.answer), encoding="utf-8")
        self.skill = self.root / "skill"
        (self.skill / "scripts").mkdir(parents=True)
        (self.skill / "SKILL.md").write_text("# Word reader", encoding="utf-8")
        self.script = self.skill / "scripts" / "read.py"
        self.script.write_text(SCRIPT, encoding="utf-8")
        self.case = {"id": "read", "prompt": "Return all words and the label.",
                     "input_files": ["raw.txt"], "cli": {"script": "scripts/read.py", "args": [self.label, {"input": "raw.txt"}]},
                     "checks": [
                         {"id": "words", "category": "skill_output", "kind": "json_file_equals", "artifact": "stdout", "expected_file": "answer.json"},
                         {"id": "exit", "category": "mechanics", "kind": "json_equals", "artifact": "process", "path": ["exit_code"], "expected": 0},
                         {"id": "review", "category": "question_quality", "kind": "review", "criterion": "Did the requirements cover the label policy?"},
                     ]}
        self.out = self.root / "iterations" / "one"
        self.save()

    def save(self):
        self.plan.write_text(json.dumps({"schema_version": 1, "name": "Word reader", "cases": [self.case]}), encoding="utf-8")

    def run_cli(self, out=None, baseline=None):
        return subprocess.run([sys.executable, "-B", str(SCRIPTS / "run_cli_cases.py"),
                               "--plan", str(self.plan), "--skill", str(self.skill), "--out", str(out or self.out),
                               *(["--baseline-skill", str(baseline)] if baseline else [])],
                              capture_output=True, text=True, encoding="utf-8", timeout=30)

    def load_manifest(self):
        return json.loads((self.out / "evaluation.json").read_bytes())

    def test_real_cli_passes_keeps_raw_streams_and_review_pending(self):
        # The execution directory contains the runtime and declared raw inputs. Fixtures and plan stay with the grader.
        self.script.write_text("from pathlib import Path\nassert not list(Path('..').rglob('answer.json'))\n"
                               "assert not list(Path('..').rglob('plan.json'))\n" + SCRIPT, encoding="utf-8")
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        summary = json.loads(result.stdout)
        self.assertEqual(summary["deterministic_status"], "pass")
        self.assertEqual(summary["automatic_checks"], {"pass": 2, "fail": 0, "not_run": 0})
        self.assertEqual(summary["reviewed_checks"]["not_run"], 1)
        self.assertFalse(summary["delivery_verified"])
        self.assertEqual(summary["workflow"]["pending_reviews"], 2)
        document = self.load_manifest()
        self.assertEqual((self.out / "plan.json").read_bytes(), self.plan.read_bytes())
        self.assertEqual((self.out / "expectations/answer.json").read_bytes(), self.expected.read_bytes())
        self.assertNotIn("answer.json", (self.out / "tasks/execute-candidate-001.md").read_text())
        record = document["runs"][0]["cases"][0]
        process = json.loads((self.out / record["artifacts"]["process"]).read_bytes())
        self.assertEqual(process["exit_code"], 0)
        stderr = (self.out / record["artifacts"]["stderr"]).read_bytes()
        self.assertEqual(stderr, b"counted\r\n")
        self.assertEqual(process["stderr_sha256"], hashlib.sha256(stderr).hexdigest())
        report = evaluation.evaluate(self.out / "evaluation.json")
        self.assertEqual(report, json.loads((self.out / "evaluation-report.json").read_bytes()))
        self.assertEqual(report["runs"][0]["cases"][0]["checks"][0]["expected_sha256"],
                         hashlib.sha256(self.expected.read_bytes()).hexdigest())
        self.assertEqual(verify(self.skill, self.out / "evaluation.json")["execution"]["checks"]["pass"], 2)

    def test_candidate_and_expectations_can_change_only_in_a_new_iteration(self):
        self.expected.write_text('{"incorrect": true}', encoding="utf-8")
        self.case["checks"][1]["expected"] = 12
        self.save()
        failed = self.run_cli()
        self.assertEqual(failed.returncode, 1, failed.stderr)
        first = json.loads(failed.stdout)
        self.assertEqual(first["automatic_checks"]["fail"], 2)
        self.assertEqual(first["deterministic_status"], "fail")
        snapshot = {p.relative_to(self.out): p.read_bytes() for p in self.out.rglob("*") if p.is_file()}
        self.case["checks"][1]["expected"] = 0
        self.expected.write_text(json.dumps(self.answer), encoding="utf-8")
        self.script.write_text(SCRIPT + "# corrected version\n", encoding="utf-8")
        self.save()
        self.assertEqual(self.run_cli().returncode, 2)
        self.assertEqual(self.run_cli(self.out.with_name("two")).returncode, 0)
        self.assertEqual(snapshot, {p.relative_to(self.out): p.read_bytes() for p in self.out.rglob("*") if p.is_file()})

    def test_stdin_and_expected_nonzero_exit(self):
        (self.plan.parent / "raw.txt").write_bytes(b"! empty")
        self.case["cli"].update(args=[self.label], stdin="raw.txt")
        self.case["checks"][1]["expected"] = 7
        self.expected.write_text(json.dumps(dict(self.answer, words=["!", "empty"])), encoding="utf-8")
        self.save()
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_revised_and_old_cli_show_changed_output_and_preserved_exit(self):
        old = self.root / "old"
        shutil.copytree(self.skill, old)
        (old / "scripts/read.py").write_text(SCRIPT.replace('raw.decode("utf-8").split()', '[]'), encoding="utf-8")
        result = self.run_cli(baseline=old)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        summary = json.loads(result.stdout)
        self.assertEqual(summary["variants"]["candidate"]["deterministic_status"], "pass")
        self.assertEqual(summary["variants"]["baseline"]["deterministic_status"], "fail")
        compared, = summary["comparisons"]
        self.assertTrue(compared["comparable"])
        self.assertEqual((compared["improved"], compared["regressed"]), (1, 0))
        self.assertEqual([(c["check_id"], c["baseline"], c["with_skill"]) for c in compared["paired_checks"]],
                         [("words", "fail", "pass"), ("exit", "pass", "pass")])
        cases = [v["cases"][0] for v in summary["variants"].values()]
        self.assertEqual(len({case["artifacts"]["process"] for case in cases}), 2)
        receipts = [json.loads((self.out / case["artifacts"]["process"]).read_bytes()) for case in cases]
        self.assertEqual(receipts[0]["input_sha256"], receipts[1]["input_sha256"])
        self.assertNotEqual(receipts[0]["script_sha256"], receipts[1]["script_sha256"])
        self.assertEqual(compared, evaluation.evaluate(self.out / "evaluation.json")["comparisons"][0])
        (self.out / summary["variants"]["baseline"]["cases"][0]["artifacts"]["stderr"]).write_bytes(b"edited")
        with self.assertRaisesRegex(evaluation.EvaluationError, "changed"):
            evaluation.evaluate(self.out / "evaluation.json")

    def test_partial_baseline_is_incomplete_even_when_another_case_passes(self):
        old = self.root / "old"
        shutil.copytree(self.skill, old)
        shutil.copy(self.script, self.skill / "scripts/new.py")
        doc = json.loads(self.plan.read_bytes())
        second = dict(self.case, id="new-entry", cli=dict(self.case["cli"], script="scripts/new.py"))
        doc["cases"].append(second)
        self.plan.write_text(json.dumps(doc), encoding="utf-8")
        result = self.run_cli(baseline=old)
        self.assertEqual(result.returncode, 3, result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual(summary["deterministic_status"], "pass")
        self.assertEqual(summary["variants"]["baseline"]["pending_cases"], ["new-entry"])
        self.assertFalse(summary["comparisons"][0]["comparable"])
        self.assertNotIn("paired_checks", summary["comparisons"][0])
        self.assertIn("new-entry", summary["comparisons"][0]["reasons"][0])

    def test_expected_invalid_input_requires_exactly_empty_stdout_and_observed_stderr(self):
        self.case["checks"] = [
            {"id": "silent", "kind": "json_equals", "category": "skill_output", "artifact": "process", "path": ["stdout_bytes"], "expected": 0},
            {"id": "invalid", "kind": "json_equals", "category": "mechanics", "artifact": "process", "path": ["exit_code"], "expected": 2},
            {"id": "message", "kind": "contains", "category": "skill_output", "artifact": "stderr", "text": "Invalid record"},
        ]
        self.save()
        self.script.write_text('import sys\nprint("Invalid record", file=sys.stderr)\nsys.exit(2)\n', encoding="utf-8")
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        summary = json.loads(result.stdout)
        case, = summary["variants"]["candidate"]["cases"]
        process = json.loads((self.out / case["artifacts"]["process"]).read_bytes())
        self.assertEqual(process["stdout_bytes"], 0)
        self.assertEqual(process["stderr_bytes"], len((self.out / case["artifacts"]["stderr"]).read_bytes()))
        self.script.write_text("print()\n" + self.script.read_text(encoding="utf-8"), encoding="utf-8")
        result = self.run_cli(out=self.out.with_name("bad"))
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(json.loads(result.stdout)["variants"]["candidate"]["cases"][0]["checks"]["silent"], "fail")
        self.case["checks"][1]["expected"] = 0
        self.save()
        result = self.run_cli(out=self.out.with_name("bad-spec"))
        self.assertEqual(result.returncode, 2, result.stderr)

    def test_tampered_fixture_stream_process_and_artifact_aliases_rejected(self):
        self.assertEqual(self.run_cli().returncode, 0)
        manifest = self.out / "evaluation.json"
        record = self.load_manifest()["runs"][0]["cases"][0]
        for relative in ("expectations/answer.json", *record["artifacts"].values()):
            with self.subTest(path=relative):
                path = self.out / relative
                old = path.read_bytes()
                path.write_bytes(old + b" ")
                with self.assertRaisesRegex(evaluation.EvaluationError, "changed"):
                    verify(self.skill, manifest)
                path.write_bytes(old)
        doc = self.load_manifest()
        doc["runs"][0]["cases"][0]["artifacts"]["stdout"] = "expectations/answer.json"
        manifest.write_text(json.dumps(doc), encoding="utf-8")
        with self.assertRaisesRegex(evaluation.EvaluationError, "this case's captured"):
            evaluation.evaluate(manifest)

    def test_rejects_shell_commands_unbound_inputs_missing_checks_and_leaked_fixture(self):
        for changes in ({"script": "../read.py"}, {"script": "cmd.exe"}, {"command": "python scripts/read.py"},
                        {"args": "--input raw.txt"}, {"args": [{"input": "other.txt"}]}):
            with self.subTest(changes=changes):
                self.case["cli"] = {"script": "scripts/read.py", "args": [self.label, {"input": "raw.txt"}], **changes}
                self.save()
                self.assertEqual(self.run_cli().returncode, 2)
                self.assertFalse(self.out.exists())
        self.case["cli"] = {"script": "scripts/read.py", "args": [self.label], "stdin": "raw.txt"}
        self.case["input_files"].append("answer.json")
        self.save()
        self.assertIn("separate from executor", self.run_cli().stderr)
        self.case["input_files"].pop()
        self.case["checks"].pop(1)
        self.save()
        self.assertIn("expected process exit_code", self.run_cli().stderr)

    def test_timeout_records_incomplete_evidence_and_atomic_failure_publishes_nothing(self):
        self.script.write_text("import time\ntime.sleep(8)\n", encoding="utf-8")
        with patch.object(runner, "TIMEOUT_SECONDS", 0.1):
            result = runner.run_cases(self.plan, self.skill, self.out)
        self.assertEqual(result["deterministic_status"], "incomplete")
        self.assertEqual(result["automatic_checks"]["not_run"], 2)
        record = self.load_manifest()["runs"][0]["cases"][0]
        self.assertIn("timeout", record["reason"])
        self.assertEqual(json.loads((self.out / record["artifacts"]["process"]).read_bytes())["status"], "timeout")
        other = self.out.with_name("interrupted")
        with patch.object(runner, "execute_case", side_effect=OSError("interrupted")), self.assertRaises(OSError):
            runner.run_cases(self.plan, self.skill, other)
        self.assertFalse(other.exists())
        self.assertEqual(list(self.out.parent.iterdir()), [self.out])

    def test_concurrent_one_command_publication_never_mixes_evidence(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.run_cli(), range(2)))
        self.assertEqual(sorted(r.returncode for r in results), [0, 2])
        self.assertEqual(evaluation.evaluate(self.out / "evaluation.json")["runs"][0]["counts"]["pass"], 2)
        self.assertEqual(list(self.out.parent.iterdir()), [self.out])


if __name__ == "__main__":
    unittest.main()
