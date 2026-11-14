#!/usr/bin/env python3
"""CLI for source-driven skill creation and resumable HTML questionnaires."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import builder_core as core


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="command", required=True)
    for name in ("init", "set-questions", "validate", "status", "answer", "recommend", "render", "serve", "import-answers", "brief", "delegate", "reset-answers", "submit", "acknowledge", "checkpoint"):
        sub = commands.add_parser(name)
        sub.add_argument("--workspace", required=True, help="Task-owned run directory; keep separate from the installed skill")
        if name == "init":
            sub.add_argument("--goal", required=True)
            sub.add_argument("--mode", choices=sorted(core.MODES), default="user")
        elif name in {"set-questions", "import-answers"}:
            sub.add_argument("--input", required=True)
            if name == "set-questions":
                sub.add_argument("--rebind-project", action="store_true", help="Bind an authored fixture without run identity to an empty initialized workspace")
                sub.add_argument("--presentation-only", nargs="+", metavar="QUESTION_ID", help="Preserve answers for explicitly reviewed cosmetic edits to these questions; meaning must remain unchanged")
        elif name in {"delegate", "reset-answers"}:
            sub.add_argument("--input", help="Optional guarded workflow request JSON; omit to use the workspace's current saved state")
        elif name == "status":
            sub.add_argument("--json", action="store_true", help="Print the full structured view")
        elif name == "acknowledge":
            sub.add_argument("--request-id", required=True, help="Exact accepted handoff read by the host")
            sub.add_argument("--revision", type=int, required=True)
            sub.add_argument("--answer-revision", type=int, required=True)
        elif name == "checkpoint":
            sub.add_argument("--stage", type=int, required=True, choices=range(1, 8))
            sub.add_argument("--revision", type=int, required=True, help="Question revision inspected by the host")
            sub.add_argument("--answer-revision", type=int, required=True, help="Answer revision inspected by the host")
            sub.add_argument("--summary", required=True, help="Work actually observed or completed")
            sub.add_argument("--next-action", required=True, help="Concrete next action, or an explicit completion statement")
            sub.add_argument("--remaining", action="append", default=[], help="Unfinished work; repeat for multiple items")
            sub.add_argument("--request-id", help="Acknowledged handoff this work continues")
        elif name == "answer":
            sub.add_argument("--question", required=True)
            values = sub.add_mutually_exclusive_group(required=True)
            values.add_argument("--value-json", help='JSON value, e.g. "yes" or ["a","b"]')
            values.add_argument("--value-file", help="UTF-8 JSON value file, avoiding shell quoting")
            values.add_argument("--defer", action="store_true")
            values.add_argument("--clear", action="store_true")
            sub.add_argument("--actor", choices=("user", "ai"), default="user")
            sub.add_argument("--rationale", default="")
        elif name == "serve":
            sub.add_argument("--timeout", type=float, default=3600)
            sub.add_argument("--port", type=int, default=0)
    sub = commands.add_parser("check-skill", help="Basic structural checks; does not evaluate skill behavior")
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
            result = view if args.json else {"project_id": view["questionnaire"]["project_id"], "run_id": view["questionnaire"]["run_id"], "revision": view["questionnaire"]["revision"],
                "answer_revision": view["answers"]["answer_revision"], "counts": view["counts"],
                "traversal_complete": view["traversal_complete"], "ready_to_build": view["ready_to_build"]}
        elif name == "answer":
            value = core.read_json(args.value_file) if args.value_file else json.loads(args.value_json) if args.value_json is not None else None
            result = core.answer_one(args.workspace, args.question, value, args.actor, args.rationale, args.defer, args.clear)
        elif name == "recommend":
            result = core.recommend(args.workspace)
        elif name == "render":
            result = core.render(args.workspace)
        elif name == "serve":
            from builder_server import serve
            serve(args.workspace, args.timeout, args.port)
            return 0
        elif name == "import-answers":
            result = core.import_answers(args.workspace, core.read_json(args.input))
        elif name == "delegate":
            result = core.request_ai(args.workspace, core.read_json(args.input) if args.input else None)
        elif name == "reset-answers":
            result = core.reset_answers(args.workspace, core.read_json(args.input) if args.input else None)
        elif name == "submit":
            result = core.submission(args.workspace)
        elif name == "acknowledge":
            result = core.acknowledge(args.workspace, args.request_id, args.revision, args.answer_revision)
        elif name == "checkpoint":
            result = core.checkpoint(args.workspace, args.stage, args.summary, args.next_action, args.remaining, args.request_id,
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
