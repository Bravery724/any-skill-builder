#!/usr/bin/env python3
"""Prepare a fresh evaluation iteration with snapshots and separate task packets."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path, PurePosixPath
import shutil
import sys
import tempfile

import evaluate_skill as evaluation

MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_FILES = 2048
FORBIDDEN = {".git", ".agents", ".codex", ".claude", ".gemini", ".venv", "venv", "node_modules", "__pycache__",
             "dist", "runs", "demo-runs", "test-results", ".builder.lock", "answers.json", "questions.json",
             "imports.json", "questionnaire-export.json", ".pending-state.json", "progress.json"}


def portable_relative(relative):
    """Require one unambiguous relative spelling on Windows and POSIX."""
    evaluation.text(relative, "File path")
    path = PurePosixPath(relative)
    evaluation.require(not path.is_absolute() and path.as_posix() == relative
                       and ".." not in path.parts and bool(path.parts),
                       f"Use a canonical relative path without traversal or aliases: {relative}")
    for part in path.parts:
        stem = part.split(".", 1)[0].rstrip(" ").upper()
        reserved = stem in {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"} or stem in {
            f"{prefix}{number}" for prefix in ("COM", "LPT") for number in "123456789¹²³"}
        evaluation.require(not reserved and not part.endswith((".", " "))
                           and not any(character in '<>:"\\|?*' or ord(character) < 32 for character in part),
                           f"Use a portable relative file path: {relative}")
    return path


def register_path(relative, spellings):
    """Reject case aliases in both filenames and their parent directories."""
    parts = portable_relative(relative).parts
    for index in range(1, len(parts) + 1):
        prefix = "/".join(parts[:index])
        key = prefix.casefold()
        evaluation.require(key not in spellings or spellings[key] == prefix,
                           f"Prepared file paths have a case collision: {relative}")
        spellings[key] = prefix


def safe_source(path):
    """Do not follow a supplied symlink or Windows junction while copying."""
    path = Path(path).expanduser().absolute()
    for part in (path, *path.parents):
        evaluation.require(not part.is_symlink(), "Source and destination paths cannot pass through symbolic links.")
        if part.exists():
            evaluation.require(not getattr(part.stat(follow_symlinks=False), "st_file_attributes", 0) & 1024,
                               "Source and destination paths cannot pass through a Windows reparse point.")
    return path.resolve()


def prepare(plan_path, skill_path, output, baseline_skill=None, without_skill=False):
    evaluation.require(not (baseline_skill and without_skill), "Choose one baseline type.")
    plan_path = safe_source(plan_path)
    plan_blob = evaluation.read_bytes(plan_path)
    plan = evaluation.object_value(evaluation.strict_json(plan_blob, "Evaluation plan"), "Evaluation plan")
    evaluation.require(type(plan.get("schema_version")) is int and plan["schema_version"] == 1, "Use schema_version 1.")
    evaluation.require(set(plan) == {"schema_version", "name", "cases"}, "Plan needs only schema_version, name, and cases; completed run records belong elsewhere.")
    evaluation.text(plan.get("name"), "Evaluation name")
    cases = evaluation.unique_records(plan.get("cases"), "Cases")
    skill = safe_source(skill_path)
    baseline = safe_source(baseline_skill) if baseline_skill else None
    out = safe_source(output)
    evaluation.require(not out.exists(), "The iteration directory already exists; choose a fresh location.")
    roots = [skill] + ([baseline] if baseline else [])
    inputs, input_spellings = {}, {}
    input_bytes = len(plan_blob)
    for case in cases.values():
        evaluation.text(case.get("prompt"), "Case prompt")
        for check in evaluation.unique_records(case.get("checks"), "Case checks").values():
            evaluation.check_definition(check)
        for relative in evaluation.sequence(case.get("input_files", []), "Case inputs", allow_empty=True):
            evaluation.local_file(plan_path.parent, relative)
            register_path(relative, input_spellings)
            path = safe_source(plan_path.parent / relative)
            if relative not in inputs:
                evaluation.require(len(inputs) < MAX_FILES and input_bytes + path.stat().st_size <= MAX_TOTAL_BYTES,
                                   "Evaluation inputs exceed 2048 files or 64 MiB; select a smaller input set.")
                blob = evaluation.read_bytes(path)
                input_bytes += len(blob)
                inputs[relative] = (path, blob)
    for source_root in roots:
        evaluation.require(source_root.is_dir() and (source_root / "SKILL.md").is_file(), "Each skill root must contain SKILL.md.")
        evaluation.require(not out.is_relative_to(source_root), "Iteration destination must be outside skill directories.")
    for source, _ in inputs.values():
        evaluation.require(not out.is_relative_to(source.parent), "Iteration destination must be outside input directories.")
    payloads = {"plan.json": plan_blob}
    inventories = [{"id": "plan", "files": [{"path": "plan.json", "sha256": evaluation.fingerprint(plan_blob)}]}]

    payload_spellings = {}

    def add(relative, blob):
        register_path(relative, payload_spellings)
        evaluation.require(relative not in payloads, "Prepared file paths collide.")
        payloads[relative] = blob
        evaluation.require(len(payloads) <= MAX_FILES and sum(map(len, payloads.values())) <= MAX_TOTAL_BYTES,
                           "Evaluation snapshot exceeds 2048 files or 64 MiB; select a smaller runtime/input set.")

    for label, source in [("candidate", skill)] + ([("baseline", baseline)] if baseline else []):
        files = []
        pending, entries = [source], 0
        collected = []
        while pending:
            directory = pending.pop()
            for path in directory.iterdir():
                entries += 1
                evaluation.require(entries <= MAX_FILES, "Skill runtime exceeds 2048 entries; select a smaller runtime.")
                safe_source(path)
                parts = path.relative_to(source).parts
                evaluation.require(not any(part.lower() in FORBIDDEN or part.startswith(".") for part in parts),
                                   "Skill snapshot contains hidden, cached, or private run files; use a clean runtime directory.")
                if path.is_dir():
                    pending.append(path)
                else:
                    evaluation.require(path.is_file(), "Skill snapshot contains a nonregular file.")
                    collected.append(path)
        for path in sorted(collected):
            safe_source(path)
            evaluation.require(path.suffix.lower() not in {".pyc", ".pyo", ".key", ".pem"}, "Skill snapshot contains a cache or credential file.")
            if path.is_file():
                relative = f"snapshots/{label}/{path.relative_to(source).as_posix()}"
                blob = evaluation.read_bytes(path)
                add(relative, blob)
                files.append({"path": relative, "sha256": evaluation.fingerprint(blob)})
        inventories.append({"id": label, "files": files})
    copied_inputs = {}
    input_inventory = []
    for relative, (source, blob) in inputs.items():
        destination = f"inputs/{relative}"
        add(destination, blob)
        copied_inputs[relative] = destination
        input_inventory.append({"path": destination, "sha256": evaluation.fingerprint(blob)})
    if input_inventory:
        inventories.append({"id": "inputs", "files": input_inventory})
    copied_cases = copy.deepcopy(list(cases.values()))
    for case in copied_cases:
        case["input_mapping"] = [{"original": path, "snapshot": copied_inputs[path]}
                                 for path in case.get("input_files", [])]
        case["input_files"] = [copied_inputs[path] for path in case.get("input_files", [])]
    variants = [("candidate", "with_skill", "snapshots/candidate")]
    if baseline or without_skill:
        variants.append(("baseline", "baseline", "snapshots/baseline" if baseline else None))
    runs = []
    for run_id, variant, snapshot in variants:
        records = []
        for index, case in enumerate(copied_cases, 1):
            directory = f"results/{run_id}/case-{index:03d}"
            records.append({"case_id": case["id"], "status": "not_run", "reason": "Execution is pending.",
                            "eval_feedback": {"status": "not_run", "reason": "A reviewer has not inspected this execution or its checks."}})
            input_lines = "\n".join(f"- {item['original']} -> {out / item['snapshot']}"
                                    for item in case["input_mapping"]) or "- No input files."
            skill_line = f"Use the skill snapshot at {out / snapshot}." if snapshot else "Perform the task without consulting the candidate skill or its snapshots."
            packet = (f"# Execute case {case['id']}\n\n{skill_line}\n\n"
                      f"## User task\n\n{case['prompt']}\n\n## Raw inputs\n\n{input_lines}\n\n"
                      f"Save the actual outputs and an observable execution log under {out / directory}.\n"
                      "Use the provided task, inputs, and skill only. Do not inspect the plan, review packet, other runs, or expected checks. "
                      "Record unavailable tools and execution limits honestly. Do not invent outputs or private reasoning traces. "
                      "The host will record your identity and whether this was a fresh context.\n")
            add(f"tasks/execute-{run_id}-{index:03d}.md", packet.encode("utf-8"))
            review = (f"# Review case {case['id']}\n\nRead evaluation.json for the original task, inputs, and checks for this case, "
                      f"then inspect the actual outputs and execution log under {out / directory}.\n\n"
                      "Grade each check using evidence from the actual files. Separately critique whether the checks would pass a wrong "
                      "output, omit an important outcome, or miss an unsupported factual/process claim. Record eval_feedback with evidence; "
                      "an empty finding list needs an explicit summary of what you reviewed. Report self-review or unknown independence "
                      "honestly. Do not infer success from an absent output or a well-written execution summary. "
                      "Do not alter the skill or old records while reviewing.\n")
            add(f"tasks/review-{run_id}-{index:03d}.md", review.encode("utf-8"))
        run = {"id": run_id, "variant": variant, "context": {"model": None, "effort": None, "tools": None, "budget": None}, "cases": records}
        if snapshot:
            run["skill_snapshot"] = run_id
        runs.append(run)
    manifest = {"schema_version": 1, "name": plan["name"], "cases": copied_cases, "runs": runs, "snapshots": inventories,
                "reuse_review": {"status": "not_run", "reason": "Actual execution logs have not been reviewed for useful repeated work."}}
    add("evaluation.json", (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    out.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".evaluation-", dir=out.parent))
    try:
        for relative, blob in payloads.items():
            path = stage / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(blob)
        evaluation.evaluate(stage / "evaluation.json")
        evaluation.require(not out.exists(), "The iteration destination appeared while preparing the snapshot.")
        stage.rename(out)
    finally:
        if stage.exists():
            evaluation.require(stage.parent.resolve() == out.parent and stage.name.startswith(".evaluation-"), "Unexpected staging path.")
            shutil.rmtree(stage)
    return {"prepared": True, "path": str(out), "manifest": str(out / "evaluation.json"), "cases": len(cases),
            "runs": len(runs), "files": len(payloads), "bytes": sum(map(len, payloads.values())),
            "note": "Task packets and pending records only; no model ran and no HTML was created."}


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--plan", type=Path, required=True, help="schema_version 1 plan with name and cases; input paths are relative to this file")
    cli.add_argument("--skill", type=Path, required=True, help="Clean candidate runtime directory containing SKILL.md")
    cli.add_argument("--out", type=Path, required=True, help="New iteration directory outside skill and input directories")
    baseline = cli.add_mutually_exclusive_group()
    baseline.add_argument("--baseline-skill", type=Path, help="Clean old runtime for a matched baseline")
    baseline.add_argument("--without-skill", action="store_true", help="Prepare a no-skill baseline task packet")
    args = cli.parse_args(argv)
    try:
        print(json.dumps(prepare(args.plan, args.skill, args.out, args.baseline_skill, args.without_skill), indent=2))
        return 0
    except (evaluation.EvaluationError, OSError, UnicodeError) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
