#!/usr/bin/env python3
"""Verify final runtime bytes against a completed, reviewed evaluation snapshot."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import stat
import sys
import zipfile

import evaluate_skill as evaluation
from prepare_evaluation import MAX_FILES, MAX_TOTAL_BYTES, portable_relative, register_path, safe_source


def directory_inventory(root, allow_missing=False):
    root = safe_source(root)
    if allow_missing and not root.exists():
        return {}
    evaluation.require(root.is_dir(), f"Runtime directory does not exist: {root}")
    result, spellings = {}, {}
    pending, entries, size = [root], 0, 0
    while pending:
        directory = pending.pop()
        for path in sorted(directory.iterdir()):
            entries += 1
            evaluation.require(entries <= MAX_FILES, "Runtime exceeds the 2048-entry limit.")
            safe_source(path)
            relative = path.relative_to(root).as_posix()
            register_path(relative, spellings)
            if path.is_dir():
                pending.append(path)
                continue
            evaluation.require(path.is_file(), f"Runtime contains a nonregular file: {relative}")
            evaluation.require(size + path.stat().st_size <= MAX_TOTAL_BYTES, "Runtime exceeds the 64 MiB limit.")
            blob = evaluation.read_bytes(path)
            size += len(blob)
            evaluation.require(size <= MAX_TOTAL_BYTES, "Runtime exceeds the 64 MiB limit.")
            result[relative] = evaluation.fingerprint(blob)
    return result


def archive_inventory(path, folder):
    path = safe_source(path)
    evaluation.require(path.is_file(), "Archive must be an existing ZIP file.")
    evaluation.require(path.stat().st_size <= MAX_TOTAL_BYTES, "ZIP archive exceeds the 64 MiB limit.")
    result, spellings, members, files, directories = {}, {}, set(), set(), set()
    size = 0
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        evaluation.require(len(entries) <= MAX_FILES, "ZIP archive exceeds the 2048-entry limit.")
        for entry in entries:
            evaluation.require(entry.filename == entry.orig_filename, "ZIP contains a truncated or unsafe member name.")
            name = entry.filename[:-1] if entry.is_dir() else entry.filename
            parts = portable_relative(name).parts
            register_path(name, spellings)
            evaluation.require(name not in members, f"ZIP contains duplicate paths: {name}")
            members.add(name)
            parents = {"/".join(parts[:index]) for index in range(1, len(parts))}
            evaluation.require(not parents & files and name not in (files if entry.is_dir() else directories),
                               f"ZIP contains a file/directory collision: {name}")
            directories.update(parents)
            (directories if entry.is_dir() else files).add(name)
            evaluation.require(parts[0] == folder, f"ZIP must contain only the top-level skill folder {folder}.")
            mode = entry.external_attr >> 16
            kind = stat.S_IFMT(mode)
            evaluation.require(kind in {0, stat.S_IFDIR if entry.is_dir() else stat.S_IFREG},
                               f"ZIP contains a symlink or nonregular member: {name}")
            evaluation.require(not entry.external_attr & 1024, f"ZIP contains a Windows reparse member: {name}")
            evaluation.require(entry.is_dir() or not entry.external_attr & 16,
                               f"ZIP file has conflicting directory attributes: {name}")
            evaluation.require(not entry.flag_bits & 1, "Encrypted ZIP entries are unsupported.")
            if entry.is_dir():
                continue
            evaluation.require(len(parts) > 1, "ZIP skill root must be a directory.")
            evaluation.require(entry.file_size <= evaluation.MAX_BYTES and size + entry.file_size <= MAX_TOTAL_BYTES,
                               "ZIP contents exceed the 16 MiB file or 64 MiB total limit.")
            try:
                with archive.open(entry) as member:
                    blob = member.read(evaluation.MAX_BYTES + 1)
            except Exception as error:
                raise evaluation.EvaluationError(f"Cannot read ZIP member {name}: {error}") from error
            evaluation.require(len(blob) == entry.file_size and len(blob) <= evaluation.MAX_BYTES,
                               "ZIP member has an invalid or oversized uncompressed length.")
            size += len(blob)
            result["/".join(parts[1:])] = evaluation.fingerprint(blob)
    return result


def differences(expected, actual):
    return {"added": sorted(actual.keys() - expected.keys()),
            "deleted": sorted(expected.keys() - actual.keys()),
            "changed": sorted(path for path in expected.keys() & actual.keys() if expected[path] != actual[path])}


def checked_references(root, document):
    """Inspect original references before the evaluator resolves any links."""
    paths = []
    for case in evaluation.sequence(document.get("cases"), "Cases"):
        evaluation.object_value(case, "Case")
        paths.extend(evaluation.sequence(case.get("input_files", []), "Case inputs", allow_empty=True))
    for run in evaluation.sequence(document.get("runs"), "Runs"):
        evaluation.object_value(run, "Run")
        for case in evaluation.sequence(run.get("cases", []), "Run cases", allow_empty=True):
            evaluation.object_value(case, "Run case")
            paths.extend(evaluation.object_value(case.get("artifacts", {}), "Case artifacts").values())
    if "snapshots" in document:
        for snapshot in evaluation.sequence(document["snapshots"], "Snapshots"):
            evaluation.object_value(snapshot, "Snapshot")
            for item in evaluation.sequence(snapshot.get("files"), "Snapshot files"):
                paths.append(evaluation.object_value(item, "Snapshot file").get("path"))
    for relative in paths:
        portable_relative(relative)
        evaluation.local_file(root, relative)
        safe_source(root / relative)


def verify(skill_path, evaluation_path, run_id="candidate", archive=None, extracted=None):
    evaluation.require(bool(archive) == bool(extracted), "Supply --archive and --extracted together, or omit both.")
    skill = safe_source(skill_path)
    manifest = safe_source(evaluation_path)
    manifest_blob = evaluation.read_bytes(manifest)
    document = evaluation.object_value(evaluation.strict_json(manifest_blob, "Evaluation"), "Evaluation")
    if extracted:
        evaluation.require(safe_source(extracted) != skill, "Extracted delivery must be a separate directory from the final runtime.")
    run_records = evaluation.unique_records(document.get("runs"), "Runs")
    evaluation.require(run_id in run_records, f"Selected run does not exist: {run_id}")
    selected = run_records[run_id]
    evaluation.require(selected.get("variant") == "with_skill", "Selected run must be a with_skill run.")
    checked_references(manifest.parent, document)
    actual = directory_inventory(skill)
    result = {"verified": False, "run": run_id, "skill": str(skill), "evaluation": str(manifest),
              "manifest_sha256": evaluation.fingerprint(manifest_blob), "reasons": [],
              "runtime": {"files": len(actual), "status": "unverified"},
              "packaging": {"status": "not_requested", "note": "Folder-only verification; no archive or extracted delivery was checked."},
              "limits": ["Checks saved execution and review records; does not execute a skill or authenticate those records.",
                         "Does not certify fresh contexts, blind review, evaluator independence, or general skill quality."]}
    reasons = result["reasons"]
    binding = selected.get("skill_snapshot")
    expected = None
    if binding is None:
        reasons.append("Selected run has no skill_snapshot binding; the executed runtime is not identified.")
    else:
        evaluation.require(len(portable_relative(binding).parts) == 1, "skill_snapshot must name one snapshot ID.")
        snapshots = evaluation.unique_records(document.get("snapshots", []), "Snapshots", allow_empty=True)
        if binding not in snapshots:
            reasons.append("The selected run's skill snapshot inventory is missing.")
        else:
            expected, spellings = {}, {}
            prefix = f"snapshots/{binding}/"
            for item in evaluation.sequence(snapshots[binding].get("files"), "Snapshot files"):
                relative = evaluation.text(item.get("path"), "Snapshot path")
                evaluation.require(relative.startswith(prefix), "Selected snapshot files must stay below snapshots/<skill_snapshot>/.")
                relative = relative[len(prefix):]
                register_path(relative, spellings)
                evaluation.require(relative not in expected, "Snapshot contains duplicate file paths.")
                digest = item.get("sha256")
                evaluation.require(isinstance(digest, str) and len(digest) == 64
                                   and all(character in "0123456789abcdef" for character in digest), "Snapshot SHA256 is invalid.")
                expected[relative] = digest
            if "SKILL.md" not in expected:
                reasons.append("Selected snapshot inventory does not contain SKILL.md.")
            snapshot_root = manifest.parent / "snapshots" / binding
            snapshot_diff = differences(expected, directory_inventory(snapshot_root, allow_missing=True))
            runtime_diff = differences(expected, actual)
            result["runtime"].update(snapshot=binding, snapshot_differences=snapshot_diff, differences=runtime_diff,
                                     status="matched" if not any(snapshot_diff.values()) and not any(runtime_diff.values()) else "changed")
            if any(snapshot_diff.values()):
                reasons.append("The saved skill snapshot no longer matches its exact recorded inventory and hashes.")
            if any(runtime_diff.values()):
                reasons.append("The final runtime differs from the evaluated skill snapshot; rerun evaluation after final edits.")
    try:
        report = evaluation.evaluate(manifest)
    except (TypeError, KeyError) as error:
        raise evaluation.EvaluationError(f"Malformed evaluation record: {error}") from error
    except evaluation.EvaluationError as error:
        if result["runtime"].get("snapshot_differences") and any(result["runtime"]["snapshot_differences"].values()):
            result["execution"] = {"status": "unverified", "reason": str(error)}
            report = None
        else:
            raise
    if report is not None and report["manifest_sha256"] != result["manifest_sha256"]:
        reasons.append("Evaluation manifest changed during verification; rerun with stable files.")
        result["execution"] = {"status": "unverified", "reason": reasons[-1]}
        report = None
    if report is not None:
        run = next(item for item in report["runs"] if item["id"] == run_id)
        result["execution"] = {"status": "checked", "cases": len(run["cases"]), "checks": run["counts"]}
        if not run["cases"] or not run["counts"]["pass"] or run["counts"]["fail"] or run["counts"]["not_run"]:
            reasons.append("Selected run must have nonzero cases and checks, with every check passing.")
        for case in run["cases"]:
            label = case["case_id"]
            if case["execution_status"] != "completed" or "execution" not in case:
                reasons.append(f"Case {label} lacks a completed execution with validated provenance.")
            feedback = case.get("eval_feedback", {})
            if feedback.get("status") != "completed":
                reasons.append(f"Case {label} has no completed evaluation feedback.")
            elif any(item.get("severity", "blocking") == "blocking" for item in feedback.get("findings", [])):
                reasons.append(f"Case {label} has unresolved workflow findings marked blocking.")
        reuse = report.get("reuse_review", {})
        if reuse.get("status") != "completed" or run_id not in reuse.get("inspected_runs", []):
            reasons.append("A completed reuse review must include the selected run.")
    if archive:
        zipped = archive_inventory(archive, skill.name)
        unpacked = directory_inventory(extracted)
        zip_diff, extracted_diff = differences(actual, zipped), differences(actual, unpacked)
        matched = not any(zip_diff.values()) and not any(extracted_diff.values())
        result["packaging"] = {"status": "matched" if matched else "changed", "archive": str(safe_source(archive)),
                               "extracted": str(safe_source(extracted)), "archive_differences": zip_diff,
                               "extracted_differences": extracted_diff}
        if not matched:
            reasons.append("Archive and extracted skill must contain exactly the final runtime's files and bytes.")
    result["verified"] = not reasons and report is not None and expected is not None
    result["status"] = "verified" if result["verified"] else "unmet"
    return result


class JsonParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"verified": False, "status": "invalid", "error": message}), file=sys.stderr)
        raise SystemExit(2)


def main(argv=None):
    parser = JsonParser(description=__doc__)
    parser.add_argument("--skill", type=Path, required=True, help="Final runtime directory, including README and all delivered resources")
    parser.add_argument("--evaluation", type=Path, required=True, help="Completed evaluation.json with the executed snapshot inventory")
    parser.add_argument("--run", default="candidate", help="with_skill run ID (default: candidate)")
    parser.add_argument("--archive", type=Path, help="ZIP with one top-level folder matching the final skill folder name")
    parser.add_argument("--extracted", type=Path, help="Extracted skill folder containing SKILL.md; required with --archive")
    args = parser.parse_args(argv)
    try:
        result = verify(args.skill, args.evaluation, args.run, args.archive, args.extracted)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["verified"] else 1
    except (evaluation.EvaluationError, OSError, UnicodeError, zipfile.BadZipFile, RuntimeError, NotImplementedError) as error:
        print(json.dumps({"verified": False, "status": "invalid", "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
