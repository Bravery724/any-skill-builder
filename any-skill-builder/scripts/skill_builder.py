#!/usr/bin/env python3
"""Offline skill creation with Full Auto and portable HTML questionnaires."""
from __future__ import annotations
import argparse
import json
import sys
import builder_core as core


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="command", required=True)
    names = ("init", "set-questions", "validate", "status", "answer", "recommend", "render", "import-answers",
             "resume", "restore", "brief", "reset-answers", "checkpoint", "resolve-input", "interpret-answer", "complete-input")
    for name in names:
        sub = commands.add_parser(name)
        sub.add_argument("--workspace", required=True, help="Task-owned run directory, separate from the installed skill")
        if name == "init":
            sub.add_argument("--goal", required=True)
            sub.add_argument("--mode", choices=sorted(core.MODES), default="questionnaire")
        elif name in {"set-questions", "import-answers", "restore", "resume"}:
            sub.add_argument("--input", required=name != "resume", help="Authored JSON or saved questionnaire HTML, depending on command")
            if name == "set-questions":
                sub.add_argument("--rebind-project", action="store_true", help="Bind an authored fixture to an empty run while preserving its selected mode")
                sub.add_argument("--presentation-only", nargs="+", metavar="QUESTION_ID", help="Preserve answers for explicitly reviewed cosmetic edits")
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
        if name == "init":
            result = core.init_workspace(args.workspace, args.goal, args.mode)
        elif name == "set-questions":
            result = core.set_questions(args.workspace, core.read_json(args.input), presentation_only=args.presentation_only, rebind_project=args.rebind_project)
        elif name == "validate":
            view = core.status(args.workspace, True)
            result = {"valid": True, "project_id": view["questionnaire"]["project_id"], "run_id": view["questionnaire"]["run_id"], "counts": view["counts"],
                      "checks": ["schema", "evidence references", "options", "dependency graph", "registered assets", "answer versions"],
                      "semantic_question_quality_tested": False}
        elif name == "status":
            view = core.status(args.workspace, include_workflow=args.json)
            result = view if args.json else {"project_id": view["questionnaire"]["project_id"], "run_id": view["questionnaire"]["run_id"],
                "mode": view["questionnaire"]["mode"], "revision": view["questionnaire"]["revision"], "answer_revision": view["answers"]["answer_revision"],
                "counts": view["counts"], "pending_input_ids": view["pending_input_ids"], "unresolved_branch_ids": view["unresolved_branch_ids"],
                "traversal_complete": view["traversal_complete"], "ready_to_build": view["ready_to_build"]}
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
        print(json.dumps(result, ensure_ascii=False, indent=2))
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
