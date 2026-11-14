#!/usr/bin/env python3
"""Verify the public example's saved evidence and reports without rewriting them."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "any-skill-builder" / "scripts"))
import evaluate_skill as evaluation


def differences(saved, current, path="report"):
    """Identify changed record fields without printing the evidence contents."""
    if type(saved) is not type(current):
        return [path]
    if isinstance(current, dict):
        result = []
        for key in sorted(set(saved) | set(current)):
            child = f"{path}.{key}"
            result.extend([child] if key not in saved or key not in current
                          else differences(saved[key], current[key], child))
        return result
    if isinstance(current, list):
        if len(saved) != len(current):
            return [path]
        return [change for index, (before, after) in enumerate(zip(saved, current))
                for change in differences(before, after, f"{path}[{index}]")]
    return [] if saved == current else [path]


def check_example(example: Path) -> dict:
    example = example.resolve()
    manifest = example / "evaluation.json"
    report = evaluation.evaluate(manifest)
    references = {"evaluation.json"}
    references.update(item["path"] for case in report["cases"] for item in case["input_files"])
    references.update(item["path"] for run in report["runs"] for case in run["cases"]
                      for item in case["artifacts"].values())
    errors = []
    for relative in sorted(references):
        path = evaluation.local_file(example, relative)
        if path.is_file() and path.suffix.lower() in {".md", ".json", ".txt"}:
            if b"\r\n" in evaluation.read_bytes(path):
                errors.append(f"{relative}: contains CRLF; normalize text to LF before recording hashes for Git.")
    payloads = {
        "evaluation-report.json": (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        "evaluation-report.md": evaluation.markdown(report).encode("utf-8"),
    }
    for name, expected in payloads.items():
        path = example / name
        if not path.is_file():
            errors.append(f"{name}: saved report is missing.")
            continue
        saved = evaluation.read_bytes(path)
        if saved == expected:
            continue
        detail = "content or formatting differs"
        if name.endswith(".json"):
            try:
                changed = differences(evaluation.strict_json(saved, name), report)
                if changed:
                    detail = ", ".join(changed[:8]) + (", ..." if len(changed) > 8 else "")
            except evaluation.EvaluationError:
                detail = "saved JSON is invalid"
        errors.append(f"{name}: stale report ({detail}). Review changed evidence before regenerating the report.")
    totals = {status: sum(run["counts"][status] for run in report["runs"]) for status in evaluation.STATUSES}
    if totals["fail"]:
        errors.append(f"Existing completed example cases contain {totals['fail']} failed checks.")
    return {"valid": not errors, "checks": totals, "errors": errors,
            "note": "Rechecked existing artifacts and recorded judgments; no model ran and no files were rewritten."}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--example", type=Path, default=ROOT / "examples" / "complete",
                        help="Example directory containing evaluation.json and its saved reports")
    args = parser.parse_args(argv)
    try:
        result = check_example(args.example)
        print(json.dumps(result, indent=2))
        return 0 if result["valid"] else 1
    except (evaluation.EvaluationError, OSError, UnicodeError) as error:
        print(json.dumps({"valid": False, "errors": [str(error)]}, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
