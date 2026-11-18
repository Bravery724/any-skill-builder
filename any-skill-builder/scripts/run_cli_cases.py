#!/usr/bin/env python3
"""Prepare, run and grade fixed JSON cases for a trusted generated local Python CLI."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

import evaluate_skill as evaluation
import prepare_evaluation as preparation
from verify_delivery import verify

TIMEOUT_SECONDS = 30


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def capture(argv, runtime, stdin, stdout, stderr, scratch):
    environment = dict(os.environ, TMP=str(scratch), TEMP=str(scratch), TMPDIR=str(scratch))
    try:
        child = subprocess.Popen(argv, cwd=runtime, stdin=stdin, stdout=stdout, stderr=stderr, env=environment)
    except OSError as error:
        return {"status": "unavailable", "reason": str(error), "exit_code": None}
    deadline = time.monotonic() + TIMEOUT_SECONDS
    with child:
        while True:
            exited = child.poll() is not None
            if max(os.fstat(stream.fileno()).st_size for stream in (stdout, stderr)) > evaluation.MAX_BYTES:
                status = "output_limit"
            elif exited:
                return {"status": "exited", "exit_code": child.returncode}
            elif time.monotonic() >= deadline:
                status = "timeout"
            else:
                time.sleep(0.05)
                continue
            if not exited:
                child.kill()
            return {"status": status, "exit_code": child.wait()}


def execute_case(stage, run, index, case, record):
    cli = case["cli"]
    source = stage / "snapshots" / run["skill_snapshot"]
    if not (source / cli["script"]).is_file():
        record["reason"] = f"The {run['id']} snapshot lacks the declared script {cli['script']}."
        return
    paths = evaluation.cli_artifacts(run["id"], index)
    evidence = stage / paths["process"]
    evidence.parent.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix=".cli-work-", dir=stage.parent) as temporary:
        work = Path(temporary)
        runtime = work / "runtime"
        shutil.copytree(source, runtime)
        (work / "tmp").mkdir()
        input_hashes = {}
        for mapping in case["input_mapping"]:
            raw = evaluation.read_bytes(stage / mapping["snapshot"])
            path = work / "inputs" / mapping["original"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            input_hashes[mapping["original"]] = evaluation.fingerprint(raw)
        args = [arg if isinstance(arg, str) else "../inputs/" + arg["input"] for arg in cli["args"]]
        script = evaluation.read_bytes(runtime / cli["script"])
        argv = [sys.executable, "-E", "-s", "-B", "-X", "utf8", "./" + cli["script"], *args]
        stdin_path = work / "inputs" / cli["stdin"] if "stdin" in cli else Path(os.devnull)
        with stdin_path.open("rb") as stdin, (work / "stdout").open("wb") as stdout, (work / "stderr").open("wb") as stderr:
            process = capture(argv, runtime, stdin, stdout, stderr, work / "tmp")
        process.update(case_id=case["id"], cli=cli, argv=argv, cwd="runtime",
                       python_version=sys.version, timeout_seconds=TIMEOUT_SECONDS,
                       script_sha256=evaluation.fingerprint(script), input_sha256=input_hashes)
        for name in ("stdout", "stderr"):
            with (work / name).open("rb") as stream:
                blob = stream.read(evaluation.MAX_BYTES)
            (stage / paths[name]).write_bytes(blob)
            process[name + "_sha256"] = evaluation.fingerprint(blob)
            process[name + "_bytes"] = len(blob)
    process_blob = json_bytes(process)
    evidence.write_bytes(process_blob)
    record.update(artifacts=paths, process_sha256=evaluation.fingerprint(process_blob))
    if process["status"] == "exited":
        record.pop("reason")
        record.update(status="completed", execution={"executor": "Local Python subprocess",
                                                      "relationship": "unknown", "transcript": "process"})
    else:
        record["reason"] = f"CLI execution incomplete ({process['status']}). Inspect the process and captured streams."


def variant_summary(run):
    automatic = run["by_method"]["automatic"]
    pending = [case["case_id"] for case in run["cases"] if case["execution_status"] == "not_run"]
    status = "fail" if automatic["fail"] else "incomplete" if automatic["not_run"] or pending else "pass"
    return {"deterministic_status": status, "automatic_checks": automatic, "reviewed_checks": run["by_method"]["reviewed"],
            "pending_cases": pending}


def run_cases(plan, skill, out, baseline_skill=None):
    summary = {}

    def execute_iteration(stage):
        manifest = stage / "evaluation.json"
        document = evaluation.strict_json(evaluation.read_bytes(manifest), "Prepared evaluation")
        evaluation.require(any("cli" in case for case in document["cases"]), "Declare a local cli on at least one plan case.")
        for run in document["runs"]:
            run.update(execution_mode="local_python_cli",
                       context={"model": "No model (local subprocess)", "effort": "No model reasoning",
                                "tools": [f"Python {sys.version}"], "budget": f"{TIMEOUT_SECONDS}s per case, {evaluation.MAX_BYTES} bytes per stream"})
            for index, (case, record) in enumerate(zip(document["cases"], run["cases"]), 1):
                if "cli" in case:
                    execute_case(stage, run, index, case, record)
        manifest.write_bytes(json_bytes(document))
        report = evaluation.evaluate(manifest)
        evaluation.write_report(manifest, stage / "evaluation-report", report)
        delivery = verify(skill, manifest)
        variants = {}
        for run in report["runs"]:
            variants[run["id"]] = dict(variant_summary(run), cases=[
                {"case_id": case["case_id"], "checks": {c["id"]: c["status"] for c in case["checks"]},
                 "artifacts": {name: artifact["path"] for name, artifact in case["artifacts"].items()}}
                for case in run["cases"]])
        summary.update(**variant_summary(report["runs"][0]), variants=variants, comparisons=report["comparisons"],
                       workflow=report["workflow"], runtime=delivery["runtime"]["status"],
                       delivery_verified=delivery["verified"], delivery_reasons=delivery["reasons"])

    prepared = preparation.prepare(plan, skill, out, baseline_skill=baseline_skill, before_publish=execute_iteration)
    return dict(iteration=prepared["path"], manifest=prepared["manifest"],
                report=str(Path(prepared["path"]) / "evaluation-report.json"), **summary)


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--plan", type=Path, required=True, help="Plan with frozen raw inputs, expected JSON fixtures and exit codes")
    cli.add_argument("--skill", type=Path, required=True, help="Trusted local skill runtime containing its Python script")
    cli.add_argument("--baseline-skill", type=Path, help="Old trusted skill to execute against the same frozen cases")
    cli.add_argument("--out", type=Path, required=True, help="New iteration directory")
    args = cli.parse_args(argv)
    try:
        result = run_cases(args.plan, args.skill, args.out, args.baseline_skill)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if result["runtime"] != "matched" or result["deterministic_status"] == "fail":
            return 1
        if any(not item["comparable"] for item in result["comparisons"]):
            return 3
        return 0 if result["deterministic_status"] == "pass" else 3
    except (evaluation.EvaluationError, OSError, UnicodeError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
