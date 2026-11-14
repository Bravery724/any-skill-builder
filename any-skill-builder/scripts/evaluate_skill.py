#!/usr/bin/env python3
"""Check saved evaluation artifacts and report evidence, failures, and untested cases."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PureWindowsPath
import sys

MAX_BYTES = 16 * 1024 * 1024
CATEGORIES = ("mechanics", "question_quality", "skill_output")
STATUSES = ("pass", "fail", "not_run")
UNKNOWN = {"", "unknown", "not exposed", "not recorded", "unavailable", "unspecified", "n/a"}


class EvaluationError(ValueError):
    """An invalid manifest or unsafe file reference prevents evaluation."""


def require(condition, message):
    if not condition:
        raise EvaluationError(message)


def text(value, label):
    require(isinstance(value, str) and bool(value.strip()), f"{label} must be nonempty text.")
    return value


def sequence(value, label, allow_empty=False):
    require(isinstance(value, list) and (allow_empty or value),
            f"{label} must be a {'possibly empty ' if allow_empty else 'nonempty '}list.")
    return value


def object_value(value, label):
    require(isinstance(value, dict), f"{label} must be an object.")
    return value


def unique_records(value, label, key="id", allow_empty=False):
    result = {}
    for record in sequence(value, label, allow_empty):
        object_value(record, label)
        identifier = text(record.get(key), f"{label}.{key}")
        require(identifier not in result, f"Duplicate {label} identifier: {identifier}")
        result[identifier] = record
    return result


def local_file(root, relative):
    text(relative, "File path")
    require(not Path(relative).is_absolute() and not PureWindowsPath(relative).drive
            and "\\" not in relative and ".." not in Path(relative).parts,
            f"Use a relative path inside the evaluation directory: {relative}")
    path = (root / relative).resolve()
    require(path.is_relative_to(root), f"File reference escapes the evaluation directory: {relative}")
    return path


def read_bytes(path):
    require(path.is_file(), f"Artifact is missing or is not a regular file: {path.name}")
    require(path.stat().st_size <= MAX_BYTES, f"File exceeds the {MAX_BYTES}-byte limit: {path.name}")
    return path.read_bytes()


def strict_json(blob, label):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f"Duplicate JSON key in {label}: {key}")
            result[key] = value
        return result

    try:
        return json.loads(blob, object_pairs_hook=pairs,
                          parse_constant=lambda value: (_ for _ in ()).throw(EvaluationError(f"Invalid JSON number: {value}")))
    except (ValueError, UnicodeError) as error:
        raise EvaluationError(f"Invalid JSON in {label}: {error}") from error


def fingerprint(blob):
    return hashlib.sha256(blob).hexdigest()


def counts(results):
    return {status: sum(item["status"] == status for item in results) for status in STATUSES}


def check_definition(check):
    require(check.get("category") in CATEGORIES, "Each check needs a supported category.")
    kind = check.get("kind")
    require(kind in {"contains", "not_contains", "json_equals", "review"}, "Unsupported check kind.")
    if "question_ids" in check:
        for qid in sequence(check["question_ids"], "question_ids", allow_empty=True):
            text(qid, "Question ID")
    if kind == "review":
        text(check.get("criterion"), "Review criterion")
    else:
        require(check["category"] != "question_quality", "Question quality needs a reviewed judgment, not a text-match score.")
        text(check.get("artifact"), "Checked artifact name")
        if kind in {"contains", "not_contains"}:
            text(check.get("text"), "Expected text")
        else:
            for part in sequence(check.get("path"), "JSON path", allow_empty=True):
                require(isinstance(part, str) or (type(part) is int and part >= 0), "JSON path uses keys or nonnegative array indices.")
            require("expected" in check, "json_equals needs an expected value.")


def context_value(context):
    object_value(context, "Run context")
    for key in ("model", "effort", "budget"):
        require(context.get(key) is None or isinstance(context[key], str), f"Context {key} must be text or null.")
    tool_list = context.get("tools")
    require(tool_list is None or isinstance(tool_list, list), "Context tools must be a list or null.")
    if tool_list is not None:
        for tool in sequence(tool_list, "Context tools", allow_empty=True):
            text(tool, "Tool name/version")
    return {"model": context.get("model"), "effort": context.get("effort"),
            "tools": sorted(set(tool_list)) if tool_list is not None else None, "budget": context.get("budget")}


def artifact_snapshot(root, artifacts):
    object_value(artifacts, "Case artifacts")
    result = {}
    for name, relative in artifacts.items():
        text(name, "Artifact name")
        path = local_file(root, relative)
        result[name] = {"path": relative, "exists": path.is_file()}
        if path.is_file():
            blob = read_bytes(path)
            result[name].update({"bytes": len(blob), "sha256": fingerprint(blob)})
    return result


def artifact_data(root, artifacts, name):
    require(name in artifacts, f"Artifact is not registered: {name}")
    blob = read_bytes(local_file(root, artifacts[name]))
    require(bool(blob), f"Artifact is empty: {name}")
    return blob


def review_result(root, artifacts, review):
    if review is None:
        return {"status": "not_run", "reason": "No reviewed judgment was supplied."}
    object_value(review, "Review")
    status = review.get("status")
    require(status in STATUSES, "Review status must be pass, fail, or not_run.")
    reason = text(review.get("reason"), "Review reason")
    if status == "not_run":
        return {"status": status, "reason": reason}
    reviewer = text(review.get("reviewer"), "Reviewer")
    evidence = []
    for item in sequence(review.get("evidence"), "Review evidence"):
        object_value(item, "Evidence")
        name = text(item.get("artifact"), "Evidence artifact")
        blob = artifact_data(root, artifacts, name)
        if "quote" in item:
            quote = text(item["quote"], "Evidence quote")
            try:
                require(quote in blob.decode("utf-8-sig"), f"Evidence quote was not found in artifact: {name}")
            except UnicodeError as error:
                raise EvaluationError(f"Quoted evidence is not UTF-8 text: {name}") from error
            evidence.append({"artifact": name, "quote": quote, "sha256": fingerprint(blob)})
        else:
            note = text(item.get("note"), "Evidence inspection note")
            evidence.append({"artifact": name, "note": note, "sha256": fingerprint(blob)})
    return {"status": status, "reason": reason, "reviewer": reviewer, "evidence": evidence}


def automatic_result(root, artifacts, check):
    try:
        blob = artifact_data(root, artifacts, check["artifact"])
        content = blob.decode("utf-8-sig")
        if check["kind"] == "contains":
            passed = check["text"] in content
        elif check["kind"] == "not_contains":
            passed = check["text"] not in content
        else:
            value = strict_json(content, check["artifact"])
            for part in check["path"]:
                if isinstance(part, str):
                    require(isinstance(value, dict) and part in value, "JSON object key was not found.")
                else:
                    require(isinstance(value, list) and part < len(value), "JSON array index was not found.")
                value = value[part]
            passed = json.dumps(value, sort_keys=True, ensure_ascii=False) == json.dumps(check["expected"], sort_keys=True, ensure_ascii=False)
        return {"status": "pass" if passed else "fail", "reason": "Assertion matched." if passed else "Assertion did not match.",
                "artifact": check["artifact"], "sha256": fingerprint(blob)}
    except (EvaluationError, OSError, UnicodeError) as error:
        return {"status": "fail", "reason": str(error), "artifact": check["artifact"]}


def comparison(baseline, candidate):
    reasons = []
    for key in ("model", "effort", "tools", "budget"):
        a, b = baseline["context"][key], candidate["context"][key]
        unknown = lambda value: value is None or (isinstance(value, str) and value.strip().lower() in UNKNOWN) or (isinstance(value, list) and any(item.strip().lower() in UNKNOWN for item in value))
        if unknown(a) or unknown(b):
            reasons.append(f"{key} was not recorded for both runs.")
        elif a != b:
            reasons.append(f"{key} differs between runs.")
    result = {"baseline": baseline["id"], "with_skill": candidate["id"], "comparable": not reasons, "reasons": reasons}
    if reasons:
        return result
    paired = []
    for baseline_case, candidate_case in zip(baseline["cases"], candidate["cases"]):
        for a, b in zip(baseline_case["checks"], candidate_case["checks"]):
            if "not_run" not in {a["status"], b["status"]}:
                paired.append({"case_id": baseline_case["case_id"], "check_id": a["id"], "category": a["category"],
                               "baseline": a["status"], "with_skill": b["status"]})
    result.update({"paired_checks": paired,
                   "improved": sum(item["baseline"] == "fail" and item["with_skill"] == "pass" for item in paired),
                   "regressed": sum(item["baseline"] == "pass" and item["with_skill"] == "fail" for item in paired)})
    if not paired:
        result.update({"comparable": False, "reasons": ["No checks were exercised in both runs."]})
    return result


def relationship(record):
    value = record.get("relationship")
    require(isinstance(value, str) and value in {"independent", "self", "unknown"}, "Relationship must be independent, self, or unknown.")
    return value


def assessment(root, artifacts, record, definitions):
    """Validate a recorded critique without treating it as an output grade."""
    object_value(record, "Evaluation feedback")
    require(isinstance(record.get("status"), str) and record["status"] in {"completed", "not_run"}, "Feedback status must be completed or not_run.")
    if record["status"] == "not_run":
        return {"status": "not_run", "reason": text(record.get("reason"), "Feedback reason")}
    reviewer = text(record.get("reviewer"), "Feedback reviewer")
    result = {"status": "completed", "reviewer": reviewer, "relationship": relationship(record),
              "summary": text(record.get("summary"), "Feedback summary"), "findings": []}
    for item in sequence(record.get("findings"), "Feedback findings", allow_empty=True):
        object_value(item, "Feedback finding")
        require(isinstance(item.get("kind"), str) and item["kind"] in {"weak_check", "missing_check", "unsupported_claim"}, "Unknown feedback finding kind.")
        if "check_id" in item:
            require(text(item["check_id"], "Feedback check ID") in definitions, "Feedback refers to an unknown check.")
        inspected = review_result(root, artifacts, {"status": "fail", "reviewer": reviewer,
                                  "reason": item.get("reason"), "evidence": item.get("evidence")})
        finding = {"kind": item["kind"], "reason": inspected["reason"], "evidence": inspected["evidence"]}
        if "check_id" in item:
            finding["check_id"] = item["check_id"]
        result["findings"].append(finding)
    return result


def execution_record(root, artifacts, record):
    object_value(record, "Execution record")
    transcript = text(record.get("transcript"), "Execution transcript artifact")
    blob = artifact_data(root, artifacts, transcript)
    return {"executor": text(record.get("executor"), "Executor"), "relationship": relationship(record),
            "transcript": transcript, "sha256": fingerprint(blob)}


def snapshots(root, records):
    result = []
    seen = set()
    for identifier, record in unique_records(records, "Snapshots").items():
        files = []
        for item in sequence(record.get("files"), "Snapshot files"):
            object_value(item, "Snapshot file")
            relative = text(item.get("path"), "Snapshot path")
            path = local_file(root, relative)
            require(path not in seen, "Snapshot files must not overlap.")
            seen.add(path)
            blob = read_bytes(path)
            require(item.get("sha256") == fingerprint(blob), f"Snapshot changed: {relative}")
            files.append({"path": relative, "sha256": fingerprint(blob), "bytes": len(blob)})
        result.append({"id": identifier, "files": files})
    return result


def reuse_assessment(root, record, run_definitions, runs):
    object_value(record, "Reuse review")
    require(isinstance(record.get("status"), str) and record["status"] in {"completed", "not_run"}, "Reuse review status must be completed or not_run.")
    if record["status"] == "not_run":
        return {"status": "not_run", "reason": text(record.get("reason"), "Reuse review reason")}
    reviewer = text(record.get("reviewer"), "Reuse reviewer")
    inspected = sequence(record.get("inspected_runs"), "Inspected runs")
    for run_id in inspected:
        text(run_id, "Inspected run ID")
    require(len(set(inspected)) == len(inspected), "Inspected runs must be unique.")
    indexed = {(run["id"], case["case_id"]): case for run in runs for case in run["cases"]}
    for run_id in inspected:
        require(run_id in run_definitions and any(rid == run_id and case["execution_status"] == "completed"
                for (rid, _), case in indexed.items()), "Reuse review requires an actually completed inspected run.")

    def locate(reference):
        object_value(reference, "Reuse reference")
        key = (text(reference.get("run_id"), "Reuse run ID"), text(reference.get("case_id"), "Reuse case ID"))
        require(key in indexed and indexed[key]["execution_status"] == "completed", "Reuse reference needs a known completed case.")
        require(key[0] in inspected, "Reuse reference must belong to an inspected run.")
        return key, indexed[key]

    def artifact(reference, evidence=False):
        key, case = locate(reference)
        name = text(reference.get("artifact"), "Reuse artifact")
        paths = {name: item["path"] for name, item in case["artifacts"].items()}
        blob = artifact_data(root, paths, name)
        result = {"run_id": key[0], "case_id": key[1], "artifact": name, "sha256": fingerprint(blob)}
        if evidence:
            reviewed = review_result(root, paths, {"status": "pass", "reviewer": reviewer, "reason": "Recorded repeated work.",
                                                   "evidence": [reference]})
            result.update(reviewed["evidence"][0])
        return result

    result = {"status": "completed", "reviewer": reviewer, "relationship": relationship(record),
              "summary": text(record.get("summary"), "Reuse summary"), "inspected_runs": inspected, "items": []}
    for identifier, item in unique_records(record.get("items"), "Reuse items", allow_empty=True).items():
        require(isinstance(item.get("decision"), str) and item["decision"] in {"extract", "keep_inline"}, "Reuse decision must be extract or keep_inline.")
        occurrences = [artifact(ref, True) for ref in sequence(item.get("occurrences"), "Reuse occurrences")]
        require(len({(ref["run_id"], ref["case_id"]) for ref in occurrences}) >= 2,
                "Repeated work needs evidence from at least two distinct completed executions.")
        reviewed = {"id": identifier, "operation": text(item.get("operation"), "Reusable operation"),
                    "decision": item["decision"], "reason": text(item.get("reason"), "Reuse reason"), "occurrences": occurrences}
        if item["decision"] == "extract":
            reviewed["helper"] = artifact(item.get("helper"))
            checks = []
            for reference in sequence(item.get("validation"), "Extracted helper validation"):
                key, case = locate(reference)
                check_id = text(reference.get("check_id"), "Validation check ID")
                check = next((check for check in case["checks"] if check["id"] == check_id), None)
                require(check is not None and check["status"] == "pass", "Extracted helper needs an actually passed validation check.")
                checks.append({"run_id": key[0], "case_id": key[1], "check_id": check_id})
            reviewed["validation"] = checks
        result["items"].append(reviewed)
    return result


def evaluate(manifest_path):
    manifest_path = Path(manifest_path).resolve()
    root = manifest_path.parent
    manifest_blob = read_bytes(manifest_path)
    document = object_value(strict_json(manifest_blob, manifest_path.name), "Manifest")
    require(type(document.get("schema_version")) is int and document["schema_version"] == 1, "Use schema_version 1.")
    name = text(document.get("name"), "Evaluation name")
    cases = unique_records(document.get("cases"), "Cases")
    definitions, case_inputs = {}, []
    for case_id, case in cases.items():
        text(case.get("prompt"), "Case prompt")
        definitions[case_id] = unique_records(case.get("checks"), f"Checks for {case_id}")
        for check in definitions[case_id].values():
            check_definition(check)
        inputs = []
        for relative in sequence(case.get("input_files", []), "Case inputs", allow_empty=True):
            blob = read_bytes(local_file(root, relative))
            inputs.append({"path": relative, "sha256": fingerprint(blob), "bytes": len(blob)})
        case_inputs.append({"id": case_id, "prompt": case["prompt"], "input_files": inputs})
    run_definitions = unique_records(document.get("runs"), "Runs")
    runs = []
    for run_id, run in run_definitions.items():
        require(run.get("variant") in {"baseline", "with_skill"}, "Run variant must be baseline or with_skill.")
        context = context_value(run.get("context", {}))
        records = unique_records(run.get("cases", []), "Run cases", key="case_id", allow_empty=True)
        require(set(records) <= set(cases), "Run refers to an unknown case.")
        results = []
        for case_id, case in cases.items():
            record = records.get(case_id, {"status": "not_run", "reason": "No run record was supplied."})
            require(record.get("status") in {"completed", "not_run"}, "Case status must be completed or not_run.")
            artifacts = record.get("artifacts", {})
            snapshot = artifact_snapshot(root, artifacts)
            reviews = object_value(record.get("reviews", {}), "Case reviews")
            review_ids = {key for key, value in definitions[case_id].items() if value["kind"] == "review"}
            require(set(reviews) <= review_ids, "Review refers to an unknown or automatic check.")
            checks = []
            for check in definitions[case_id].values():
                if record["status"] == "not_run":
                    result = {"status": "not_run", "reason": text(record.get("reason"), "Untested case reason")}
                elif check["kind"] == "review":
                    result = review_result(root, artifacts, reviews.get(check["id"]))
                else:
                    result = automatic_result(root, artifacts, check)
                checks.append({"id": check["id"], "category": check["category"], "method": "reviewed" if check["kind"] == "review" else "automatic",
                               "question_ids": check.get("question_ids", []), **result})
            case_result = {"case_id": case_id, "execution_status": record["status"], "artifacts": snapshot,
                           "checks": checks, "counts": counts(checks)}
            if "execution" in record:
                require(record["status"] == "completed", "Execution metadata requires a completed case.")
                case_result["execution"] = execution_record(root, artifacts, record["execution"])
            if "eval_feedback" in record:
                feedback = assessment(root, artifacts, record["eval_feedback"], definitions[case_id])
                require(record["status"] == "completed" or feedback["status"] == "not_run", "Completed feedback requires an executed case.")
                case_result["eval_feedback"] = feedback
            results.append(case_result)
        all_checks = [check for result in results for check in result["checks"]]
        runs.append({"id": run_id, "variant": run["variant"], "context": context, "cases": results, "counts": counts(all_checks),
                     "by_category": {category: counts([item for item in all_checks if item["category"] == category]) for category in CATEGORIES},
                     "by_method": {method: counts([item for item in all_checks if item["method"] == method]) for method in ("automatic", "reviewed")}})
    comparisons = [comparison(a, b) for a in runs if a["variant"] == "baseline" for b in runs if b["variant"] == "with_skill"]
    report = {"schema_version": 1, "name": name, "manifest_sha256": fingerprint(manifest_blob), "cases": case_inputs,
            "runs": runs, "comparisons": comparisons,
            "limits": ["This tool does not execute a skill or call a model; it checks saved artifacts and recorded judgments.",
                       "Text matches do not prove useful questions, correct reasoning, or better skill quality.",
                       "Review conclusions and execution metadata are supplied by the evaluator; file hashes preserve the inspected evidence.",
                       "Comparison eligibility uses shared cases and declared context, not proof of identical real execution conditions."]}
    if "snapshots" in document:
        report["snapshots"] = snapshots(root, document["snapshots"])
    if "reuse_review" in document:
        report["reuse_review"] = reuse_assessment(root, document["reuse_review"], run_definitions, runs)
    audits = [case["eval_feedback"] for run in runs for case in run["cases"] if "eval_feedback" in case]
    if audits or "reuse_review" in report:
        pending = sum(item["status"] == "not_run" for item in audits) + int(report.get("reuse_review", {}).get("status") == "not_run")
        missing_execution = sum(case["execution_status"] == "completed" and "execution" not in case
                                for run in runs for case in run["cases"])
        findings = sum(len(item.get("findings", [])) for item in audits)
        report["workflow"] = {"disposition": "needs_attention" if findings else "incomplete" if pending or missing_execution else "reviewed",
                              "open_findings": findings, "pending_reviews": pending, "pending_execution_records": missing_execution,
                              "note": "Recorded reviews are separate from task check counts. Declared independence and actual execution are not authenticated by this tool."}
    return report


def markdown(report):
    clean = lambda value: str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")
    lines = [f"# {clean(report['name'])}", "", "Saved artifact checks and recorded reviews; not an automatic quality certification.", "",
             "| Run | Method | Passed | Failed | Not run |", "| --- | --- | ---: | ---: | ---: |"]
    for run in report["runs"]:
        for method, summary in run["by_method"].items():
            lines.append(f"| {clean(run['id'])} | {method} | {summary['pass']} | {summary['fail']} | {summary['not_run']} |")
    for run in report["runs"]:
        lines += ["", f"## {clean(run['id'])}", "", "| Case | Check | Category | Method | Result | Evidence or reason |",
                  "| --- | --- | --- | --- | --- | --- |"]
        for case in run["cases"]:
            for item in case["checks"]:
                reason = item["reason"]
                if item.get("evidence"):
                    reason += " " + "; ".join(e.get("quote", e.get("note", "")) for e in item["evidence"])
                lines.append("| " + " | ".join(clean(value) for value in (case["case_id"], item["id"], item["category"], item["method"], item["status"], reason)) + " |")
    lines += ["", "## Comparisons", ""]
    if not report["comparisons"]:
        lines.append("No baseline and with-skill pair was supplied. No comparative quality claim is made.")
    for item in report["comparisons"]:
        label = f"{clean(item['baseline'])} / {clean(item['with_skill'])}"
        if item["comparable"]:
            lines.append(f"- {label}: declared context matches; {len(item['paired_checks'])} paired checks, {item['improved']} improved, {item['regressed']} regressed. These are assertion outcomes, not a general quality score.")
        else:
            lines.append(f"- {label}: not comparable. {' '.join(item['reasons'])}")
    if "workflow" in report:
        lines += ["", "## Evaluation workflow", "", f"Disposition: {report['workflow']['disposition']}.",
                  f"Pending reviews: {report['workflow']['pending_reviews']}; missing execution records: {report['workflow']['pending_execution_records']}.",
                  "", report["workflow"]["note"]]
    for run in report["runs"]:
        for case in run["cases"]:
            label = f"{clean(run['id'])} / {clean(case['case_id'])}"
            if "execution" in case:
                item = case["execution"]
                lines.append(f"- {label}: executor {clean(item['executor'])}; declared relationship {item['relationship']}; transcript {clean(item['transcript'])}.")
            if "eval_feedback" in case:
                item = case["eval_feedback"]
                lines.append(f"- {label}: test critique {item['status']}. {clean(item.get('summary', item.get('reason')))}")
                if item["status"] == "completed":
                    lines.append(f"  - Reviewer: {clean(item['reviewer'])}; declared relationship: {item['relationship']}.")
                for finding in item.get("findings", []):
                    lines.append(f"  - {finding['kind']}: {clean(finding['reason'])}")
    if "reuse_review" in report:
        item = report["reuse_review"]
        lines += ["", "## Repeated work review", "", f"{item['status']}: {clean(item.get('summary', item.get('reason')))}"]
        if item["status"] == "completed":
            lines.append(f"Reviewer: {clean(item['reviewer'])}; declared relationship: {item['relationship']}.")
        for decision in item.get("items", []):
            lines.append(f"- {clean(decision['operation'])}: {decision['decision']}. {clean(decision['reason'])}")
    lines += ["", "## Limits", ""] + ["- " + item for item in report["limits"]]
    return "\n".join(lines) + "\n"


def write_report(manifest_path, output, report, overwrite=False):
    root = Path(manifest_path).resolve().parent
    prefix = Path(output).resolve()
    require(prefix.is_relative_to(root), "Report output must stay inside the evaluation directory.")
    payloads = {Path(str(prefix) + ".json"): (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
                Path(str(prefix) + ".md"): markdown(report).encode("utf-8")}
    protected = {Path(manifest_path).resolve()}
    protected.update(local_file(root, item["path"]) for case in report["cases"] for item in case["input_files"])
    protected.update(local_file(root, item["path"]) for run in report["runs"] for case in run["cases"] for item in case["artifacts"].values())
    protected.update(local_file(root, item["path"]) for snapshot in report.get("snapshots", []) for item in snapshot["files"])
    for path, blob in payloads.items():
        require(path.resolve().is_relative_to(root) and not path.is_symlink(), "Unsafe report output path.")
        require(path.resolve() not in protected, "Report output would overwrite a source artifact or manifest.")
        require(not path.exists() or path.is_file(), "Report output is not a regular file.")
        require(not path.exists() or path.read_bytes() == blob or overwrite, "A different report already exists; choose another --out or use --overwrite.")
    for path, blob in payloads.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(blob)
    return [str(path) for path in payloads]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True, help="Evaluation JSON; all referenced files stay below its directory")
    parser.add_argument("--out", type=Path, help="Output path prefix for .json and .md reports (default: evaluation-report beside manifest)")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing generated report, never input evidence")
    args = parser.parse_args(argv)
    try:
        report = evaluate(args.manifest)
        output = args.out or args.manifest.resolve().parent / "evaluation-report"
        paths = write_report(args.manifest, output, report, args.overwrite)
        total = {status: sum(run["counts"][status] for run in report["runs"]) for status in STATUSES}
        result = {"reports": paths, "checks": total, "comparisons": report["comparisons"]}
        if "workflow" in report:
            result["workflow"] = report["workflow"]
        print(json.dumps(result, ensure_ascii=False, indent=2))
        disposition = report.get("workflow", {}).get("disposition")
        return 1 if total["fail"] or disposition == "needs_attention" else 3 if total["not_run"] or disposition == "incomplete" else 0
    except (EvaluationError, OSError, UnicodeError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
