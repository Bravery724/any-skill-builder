#!/usr/bin/env python3
"""Plan the edits and regression cases for one changed requirement or decision."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import evaluate_skill as evaluation
from prepare_evaluation import portable_relative


def read_document(path):
    return evaluation.object_value(evaluation.strict_json(evaluation.read_bytes(path), path.name), path.name)


def identifiers(row, key):
    values = evaluation.sequence(row.get(key, []), key, allow_empty=True)
    return {evaluation.text(value, key) for value in values}


def find_plan(run):
    names = ("plan.json", "evaluation-plan.json", "plan/evaluation-plan.json", "plan/plan.json")
    found = [run / name for name in names if (run / name).is_file()]
    evaluation.require(len(found) <= 1, "Several working plans exist. Supply the current one with --plan.")
    return next(iter(found), None)


def case_scope(cases, features, key, identifier, notes):
    """Check tags provide positive evidence. Only explicit case-level lists can narrow a feature."""
    linked = set()
    for case_id, case in cases.items():
        if identifier in identifiers(case, key) or any(identifier in identifiers(check, key)
                                                       for check in case.get("checks", [])):
            linked.add(case_id)
    provisional = set()
    for feature in features:
        mapped = identifiers(feature, "evaluation_ids")
        if not mapped & linked:
            provisional.update(mapped)
            notes.append(f"{feature['id']}: no case positively traces {key}={identifier}. "
                         "Inspect every mapped case and add a discriminating case if needed.")
        else:
            provisional.update(case for case in mapped if key not in cases.get(case, {}))
    return linked, provisional - linked


def plan_change(run, key, identifier, *, plan=None, keep=(), keep_cases=()):
    evaluation.require(run.is_dir(), f"Run directory is missing: {run}")
    design_path = run / "design.json"
    plan = plan or find_plan(run)
    evaluation.require(design_path.exists() or plan, "No design.json or working case inventory found in this run.")
    design = read_document(design_path) if design_path.exists() else {}
    features = evaluation.unique_records(design.get("features", []), "Features", allow_empty=True)
    cases = evaluation.unique_records(read_document(plan).get("cases"), "Plan cases") if plan else {}
    for case in cases.values():
        checks = evaluation.sequence(case.get("checks", []), "Case checks", allow_empty=True)
        for check in checks:
            evaluation.object_value(check, "Check")
        for row in [case, *checks]:
            for field in ("requirement_ids", "question_ids"):
                identifiers(row, field)

    notes, full_reasons = [], []
    files, mapped_cases = {}, {}
    for fid, feature in features.items():
        files[fid] = {portable_relative(file).as_posix() for file in identifiers(feature, "files")}
        mapped_cases[fid] = identifiers(feature, "evaluation_ids")
        if not files[fid] or not mapped_cases[fid]:
            full_reasons.append(f"{fid} has missing file or case links.")
        if key not in feature:
            full_reasons.append(f"{fid} has no {key} mapping. Inspect its original sources.")
        for field in ("requirement_ids", "question_ids"):
            identifiers(feature, field)

    direct = {fid: feature for fid, feature in features.items() if identifier in identifiers(feature, key)}
    edit_files = set().union(*(files[fid] for fid in direct))
    shared = {fid: sorted(paths & edit_files) for fid, paths in files.items()
              if paths & edit_files and fid not in direct}
    declared = set().union(*mapped_cases.values())
    available = set(cases) if plan else declared
    missing = declared - available
    if not plan:
        full_reasons.append("No working case inventory found. Supply --plan or locate and run the original suite.")
    if not direct:
        full_reasons.append(f"No feature traces {key}={identifier}. Check the ID and consult the original source and runtime.")
    if missing:
        full_reasons.append("Some design case IDs do not exist in the supplied plan. Reconcile the inventories.")
    if available - declared:
        full_reasons.append("Some plan cases have no feature link. Inspect those cases and repair the design map.")

    changed, uncertain = case_scope(cases, direct.values(), key, identifier, notes)
    direct_mapped = set().union(*(mapped_cases[fid] for fid in direct))
    if changed - direct_mapped:
        full_reasons.append("A tagged change case is outside its feature's case links. Inspect all features and cases.")
    guard_cases = set().union(*(mapped_cases[fid] for fid in shared))
    guards = []
    for guard_key, guard_id in dict.fromkeys(keep):
        evaluation.require((guard_key, guard_id) != (key, identifier), "The changed ID cannot also be an invariant.")
        owners = [f for f in features.values() if guard_id in identifiers(f, guard_key)]
        exact, broad = case_scope(cases, owners, guard_key, guard_id, notes)
        linked = exact | broad
        if not owners or not linked:
            full_reasons.append(f"Invariant {guard_key}={guard_id} lacks feature or case coverage.")
        guard_cases.update(linked)
        guards.append({"field": guard_key, "id": guard_id, "cases": sorted(linked)})
    for case_id in keep_cases:
        evaluation.require(case_id in available, f"Unknown --keep-case ID: {case_id}. Supply the current --plan.")
        guard_cases.add(case_id)

    rerun = available if full_reasons else (changed | uncertain | guard_cases) & available
    return {
        "changed": {"field": key, "id": identifier}, "plan": str(plan) if plan else None,
        "scope": "full_suite_review" if full_reasons else "mapped_cases",
        "skill_path_in_design": design.get("skill_path"),
        "features_to_change": list(direct),
        "files_to_inspect_for_edits": sorted(edit_files),
        "mapped_files_for_full_review": sorted(set().union(*files.values())) if full_reasons else [],
        "shared_files_by_regression_feature": shared,
        "explicit_invariants": guards,
        "cases_tracing_change": sorted(changed), "feature_fallback_cases": sorted(uncertain),
        "regression_cases": sorted(guard_cases), "retest_cases": sorted(rerun),
        "design_cases_missing_from_plan": sorted(missing), "coverage_notes": full_reasons + notes,
        "next_steps": [
            "Use skill_builder.py revise-rule --workspace RUN --prepare CHANGE.json with the changed ID. "
            "Record the rule and its scoped feature/check edits, then use --input CHANGE.json --destination NEXT_RUN. "
            "Continue in that successor workspace, resolve pending brief items and implement the affected runtime changes.",
            "Inspect the full runtime and suite for missing links before narrowing scope." if full_reasons else
            "Inspect callers, shared files, and co-occurring rules. Add cases for dependencies absent from the map.",
            "Use the successor working plan with its inputs. Select the retest cases. If they cannot "
            "distinguish the new behavior from the old while preserving neighboring invariants, add a case that can. "
            "Change only criteria the new rule supersedes.",
            "For a generated local Python CLI, run run_cli_cases.py --plan NEW_PLAN --skill REVISED_RUNTIME "
            "--baseline-skill OLD_RUNTIME --out NEW_ITERATION to execute and grade both snapshots on identical inputs. "
            "For host-run tasks use prepare_evaluation.py with the same arguments and execute both task packets. "
            "Keep earlier plans, outputs, and grades intact. Review old and new outputs against the same revised "
            "criteria, including the invariant checks, and record observed differences and untested cases.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True, help="Builder run containing design.json")
    changed = parser.add_mutually_exclusive_group(required=True)
    changed.add_argument("--requirement", metavar="ID", help="Changed fixed requirement")
    changed.add_argument("--question", metavar="ID", help="Changed questionnaire or Full Auto decision")
    parser.add_argument("--plan", type=Path, help="Current evaluation plan if outside the usual run locations")
    parser.add_argument("--keep-requirement", action="append", default=[], metavar="ID", help="Invariant to retest (repeatable)")
    parser.add_argument("--keep-question", action="append", default=[], metavar="ID", help="Decision to preserve (repeatable)")
    parser.add_argument("--keep-case", action="append", default=[], metavar="ID", help="Additional regression case (repeatable)")
    args = parser.parse_args(argv)
    key, identifier = ("question_ids", args.question) if args.question is not None else ("requirement_ids", args.requirement)
    try:
        evaluation.text(identifier, "Changed ID")
        keep = [("requirement_ids", item) for item in args.keep_requirement] + [("question_ids", item) for item in args.keep_question]
        result = plan_change(args.run, key, identifier, plan=args.plan, keep=keep, keep_cases=args.keep_case)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (evaluation.EvaluationError, OSError, UnicodeError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
