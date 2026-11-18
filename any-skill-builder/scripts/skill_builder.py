#!/usr/bin/env python3
"""Offline skill creation with Full Auto and portable HTML questionnaires."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
import builder_core as core
import review_questions


def review_state(workspace):
    """Report recorded review coverage without claiming semantic correctness."""
    root = Path(workspace)
    with core.workspace_lock(root):
        core.recover_workspace(root)
        questionnaire, _ = core.load_workspace(root)
        return core.question_review_state(root, questionnaire)


def require_review(workspace):
    result = review_state(workspace)
    core.require(not result["required"] or result["passed"],
                 "Question review is " + result["status"] + ". Review the current questions and use accept-review before rendering, recommending, or building.",
                 "question_review_required", 409)
    return result


def enable_review(workspace):
    root = Path(workspace)
    with core.workspace_lock(root):
        core.recover_workspace(root)
        questionnaire, _ = core.load_workspace(root)
        core.atomic_json(root / "review-policy.json", {"schema_version": 1, "run_id": questionnaire["run_id"], "required": True})
    return {"required": True, "event": "question_review_enabled"}


def accept_review(workspace, input_path):
    root = Path(workspace)
    with core.workspace_lock(root):
        core.recover_workspace(root)
        questionnaire, _ = core.load_workspace(root, True)
        report = review_questions.check(root / "questions.json", input_path)
        core.require(report["passed"], "Question review did not pass: " + json.dumps(report, ensure_ascii=False),
                     "question_review_incomplete", 409)
        core.atomic_json(root / "question-review.json", core.read_json(input_path))
        core.atomic_json(root / "review-policy.json", {"schema_version": 1, "run_id": questionnaire["run_id"], "required": True})
    return {"recorded": True, "review": report,
            "note": "Recorded judgments and coverage were checked. No model ran and semantic correctness is not certified."}


def compact(result, out_path=None):
    """Summarize a full run view so routine commands do not flood the agent's context.

    The full questionnaire and answer records stay on disk (questions.json, answers.json) and are
    available with --full, --out, or status --json.
    """
    if not (isinstance(result, dict) and "questionnaire" in result and "answers" in result):
        return result
    questionnaire, answers = result["questionnaire"], result["answers"]
    summary = {"project_id": questionnaire.get("project_id"), "run_id": questionnaire.get("run_id"),
               "mode": questionnaire.get("mode"), "revision": questionnaire.get("revision"),
               "answer_revision": answers.get("answer_revision")}
    summary.update({key: value for key, value in result.items() if key not in {"questionnaire", "answers"}})
    summary["full_view"] = (f"Saved to {out_path}." if out_path else
                            "Omitted. Read questions.json/answers.json, or rerun with --full or --out FILE; status --json prints everything.")
    return summary


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="command", required=True)
    names = ("init", "set-questions", "validate", "status", "answer", "recommend", "render", "import-answers",
             "resume", "restore", "brief", "reset-answers", "checkpoint", "resolve-input", "interpret-answer", "complete-input",
             "require-review", "accept-review", "set-decisions", "decisions-to-questions")
    for name in names:
        sub = commands.add_parser(name)
        sub.add_argument("--workspace", required=True, help="Task-owned run directory, separate from the installed skill")
        sub.add_argument("--full", action="store_true", help="Print the full questionnaire and answer records instead of a summary")
        sub.add_argument("--out", help="Also save the full JSON result to this file")
        if name == "init":
            sub.add_argument("--goal", required=True)
            sub.add_argument("--mode", choices=sorted(core.MODES), default="questionnaire")
            sub.add_argument("--review-policy", choices=("required", "legacy"), default="required",
                             help="New authoring requires a recorded question review; legacy is for explicit structural fixture previews")
        elif name == "accept-review":
            sub.add_argument("--input", required=True, help="Completed review bound to the current questions.json bytes")
        elif name == "set-decisions":
            sub.add_argument("--input", required=True, help="Full Auto decision list JSON")
        elif name == "decisions-to-questions":
            sub.add_argument("--skeleton", required=True, help="New file for the questionnaire skeleton built from decisions.json")
        elif name in {"set-questions", "import-answers", "restore", "resume"}:
            sub.add_argument("--input", required=name != "resume", help="Authored JSON or saved questionnaire HTML, depending on command")
            if name == "set-questions":
                sub.add_argument("--rebind-project", action="store_true", help="Bind an authored fixture to an empty run while preserving its selected mode")
                sub.add_argument("--presentation-only", nargs="+", metavar="QUESTION_ID", help="Preserve answers for explicitly reviewed cosmetic edits")
                sub.add_argument("--from-decisions", action="store_true", help="Convert a Full Auto decision list run into a questionnaire run")
        elif name == "status":
            sub.add_argument("--json", action="store_true", help="Print full records and resume information")
        elif name == "checkpoint":
            sub.add_argument("--stage", type=int, required=True, choices=range(1, 8))
            sub.add_argument("--revision", type=int, required=True)
            sub.add_argument("--answer-revision", type=int, required=True)
            sub.add_argument("--summary", required=True)
            sub.add_argument("--next-action", required=True)
            sub.add_argument("--remaining", action="append", default=[])
        elif name in {"answer", "resolve-input", "interpret-answer", "complete-input"}:
            sub.add_argument("--question", required=True)
            if name != "resolve-input":
                values = sub.add_mutually_exclusive_group(required=True)
                values.add_argument("--value-json", help="JSON answer or branch classification; null classifies no single-choice branch")
                values.add_argument("--value-file", help="UTF-8 JSON value file, avoiding shell quoting")
                if name == "answer":
                    values.add_argument("--clear", action="store_true")
            if name == "answer":
                sub.add_argument("--actor", choices=("user", "ai"), default="user")
            sub.add_argument("--rationale", required=name != "answer", default="")
    sub = commands.add_parser("check-skill", help="Structural checks, not a behavioral evaluation")
    sub.add_argument("--path", required=True)
    return cli


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        name = args.command
        if name in {"recommend", "render"}:
            if core.decision_list_in_use(args.workspace):
                core.require(name != "render", "Full Auto does not generate HTML. To let the user answer, run decisions-to-questions "
                             "and import it with set-questions --from-decisions.", "auto_no_html")
                core.require(name != "recommend", "Choices are already recorded in decisions.json; run brief when it is ready.",
                             "decision_list_in_use", 409)
            else:
                require_review(args.workspace)
        if name == "init":
            result = core.init_workspace(args.workspace, args.goal, args.mode)
            if args.review_policy == "required":
                result["question_review"] = enable_review(args.workspace)
        elif name == "require-review":
            result = enable_review(args.workspace)
        elif name == "accept-review":
            result = accept_review(args.workspace, args.input)
        elif name == "set-questions":
            result = core.set_questions(args.workspace, core.read_json(args.input), presentation_only=args.presentation_only,
                                        rebind_project=args.rebind_project, from_decisions=args.from_decisions)
        elif name == "set-decisions":
            result = core.set_decisions(args.workspace, core.read_json(args.input))
        elif name == "decisions-to-questions":
            result = core.export_decisions_as_questions(args.workspace, args.skeleton)
        elif name == "validate":
            view = core.status(args.workspace, True)
            result = {"valid": True, "project_id": view["questionnaire"]["project_id"], "run_id": view["questionnaire"]["run_id"], "counts": view["counts"],
                      "checks": ["schema", "evidence references", "options", "dependency graph", "registered assets", "answer versions"],
                      "semantic_question_quality_tested": False, "question_review": view["question_review"]}
        elif name == "status":
            view = core.status(args.workspace, include_workflow=args.json)
            review = view["question_review"]
            view["question_review"] = review
            view["ready_to_build"] = view["ready_to_build"] and (not review["required"] or review["passed"])
            result = view if args.json else {"project_id": view["questionnaire"]["project_id"], "run_id": view["questionnaire"]["run_id"],
                "mode": view["questionnaire"]["mode"], "revision": view["questionnaire"]["revision"], "answer_revision": view["answers"]["answer_revision"],
                "counts": view["counts"], "pending_input_ids": view["pending_input_ids"], "unresolved_branch_ids": view["unresolved_branch_ids"],
                "traversal_complete": view["traversal_complete"], "ready_to_build": view["ready_to_build"], "question_review": review}
            if "decisions" in view and not args.json:
                result["decisions"] = view["decisions"]
        elif name in {"answer", "interpret-answer", "complete-input"}:
            value = core.read_json(args.value_file) if args.value_file else json.loads(args.value_json) if args.value_json is not None else None
            if name == "answer":
                result = core.answer_one(args.workspace, args.question, value, args.actor, args.rationale, args.clear)
            elif name == "interpret-answer":
                result = core.interpret_answer(args.workspace, args.question, value, args.rationale)
            else:
                result = core.complete_input(args.workspace, args.question, value, args.rationale)
        elif name == "resolve-input":
            result = core.resolve_input(args.workspace, args.question, args.rationale)
        elif name == "recommend":
            result = core.recommend(args.workspace)
        elif name == "render":
            result = core.render(args.workspace)
        elif name == "import-answers":
            result = core.import_answers(args.workspace, args.input)
        elif name == "resume":
            result = core.resume(args.workspace, args.input)
        elif name == "restore":
            result = core.restore_html(args.workspace, args.input)
            result["question_review"] = enable_review(args.workspace)
            result["ready_to_build"] = False
        elif name == "reset-answers":
            result = core.reset_answers(args.workspace)
        elif name == "checkpoint":
            result = core.checkpoint(args.workspace, args.stage, args.summary, args.next_action, args.remaining,
                                     revision=args.revision, answer_revision=args.answer_revision)
        elif name == "brief":
            result = core.build_brief(args.workspace)
        elif name == "check-skill":
            result = core.check_skill(args.path)
        else:
            raise core.BuilderError("Unknown command.")
        if name != "status" and isinstance(result, dict) and "ready_to_build" in result and hasattr(args, "workspace"):
            current = core.status(args.workspace)
            review = current["question_review"]
            same_state = (core.questionnaire_digest(result["questionnaire"]) == core.questionnaire_digest(current["questionnaire"])
                          and result["answers"]["answer_revision"] == current["answers"]["answer_revision"]) if "questionnaire" in result else True
            result["question_review"] = review if same_state else {"required": review["required"], "status": "stale", "passed": False,
                                                                 "note": "Run changed during this command; inspect current status."}
            result["ready_to_build"] = bool(result["ready_to_build"] and current["ready_to_build"] and same_state)
        if getattr(args, "out", None):
            core.atomic_json(Path(args.out), result)
        full_requested = getattr(args, "full", False) or (name == "status" and args.json)
        print(json.dumps(result if full_requested else compact(result, getattr(args, "out", None)), ensure_ascii=False, indent=2))
        return 0
    except core.BuilderError as exc:
        print(json.dumps({"error": exc.code, "message": exc.message}, ensure_ascii=False), file=sys.stderr)
        return 2
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": "io_or_json_error", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
