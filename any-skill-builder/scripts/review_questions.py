"""Check a review record's binding and coverage, not the truth of its judgments.

No model is called. A passing record means a reviewer recorded the required
judgments against these exact questionnaire bytes; it is not semantic proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

import builder_core as core


STATUSES = {"pending", "pass", "needs-revision"}
LIMITATION = "Checks binding, coverage, references, and recorded outcomes only; does not certify semantic quality or localization."


class ReviewError(core.BuilderError):
    """Invalid questionnaire or an unsafe/unavailable review destination."""


class _Invalid(Exception):
    def __init__(self, path, message):
        self.path, self.message = path, message
        super().__init__(message)


def _require(condition, path, message):
    if not condition:
        raise _Invalid(path, message)


def _object(value, keys, path):
    _require(isinstance(value, dict), path, "Must be an object.")
    _require(set(value) == set(keys), path,
             "Fields must be exactly: " + ", ".join(sorted(keys)) + ".")


def _text(value, path, *, empty=False):
    _require(isinstance(value, str) and (empty or bool(value.strip())), path,
             "Must be text." if empty else "Must be non-empty text.")


def _id(value, path):
    _require(isinstance(value, str) and core.ID.fullmatch(value), path, "Invalid identifier.")


def _list(value, path):
    _require(isinstance(value, list), path, "Must be a list.")


def _references(value, allowed, path, *, exact=False, nonempty=False):
    _list(value, path)
    _require(all(isinstance(item, str) for item in value), path, "References must be strings.")
    _require(len(value) == len(set(value)), path, "Duplicate references.")
    _require(set(value) <= set(allowed), path, "Unknown reference.")
    if exact:
        _require(set(value) == set(allowed), path, "Coverage must include every expected reference.")
    if nonempty:
        _require(bool(value), path, "At least one applicable requirement is needed.")


def _unique_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"Duplicate JSON key: {key}")
        value[key] = item
    return value


def _read(path):
    raw = Path(path).read_bytes()
    return raw, json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_unique_pairs)


def _questions(path):
    try:
        raw, data = _read(path)
        core.validate_questionnaire(data, allow_empty=True)
        return data, hashlib.sha256(raw).hexdigest()
    except (OSError, UnicodeError, ValueError, core.BuilderError) as exc:
        raise ReviewError(f"Cannot review questionnaire {path}: {exc}", "invalid_questionnaire") from exc


def visible_fields(questionnaire):
    """Inventory authored display/effect text; values remain in questions.json.

    Source titles and explicit quotations may retain their original language.
    The resolved locale covers built-in UI messages; authored overrides are
    included here. Paths use JSON Pointer escaping.
    """
    fields, originals = [], []

    def add(container, key, base, original=False):
        if key not in container:
            return
        value = container[key]
        path = base + "/" + str(key).replace("~", "~0").replace("/", "~1")
        if isinstance(value, str):
            fields.append(path)
            if original:
                originals.append(path)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, str):
                    fields.append(f"{path}/{index}")
                    if original:
                        originals.append(f"{path}/{index}")

    add(questionnaire, "goal", "")
    for index, group in enumerate(questionnaire["groups"]):
        add(group, "label", f"/groups/{index}")
    for index, source in enumerate(questionnaire["sources"]):
        for key in ("title", "notes", "accessed_at", "quote", "quotes"):
            add(source, key, f"/sources/{index}", key in {"title", "quote", "quotes"})
    for index, question in enumerate(questionnaire["questions"]):
        base = f"/questions/{index}"
        for key in ("title", "help", "decision", "placeholder"):
            add(question, key, base)
        for option_index, option in enumerate(question.get("options", [])):
            for key in ("label", "description", "effect", "traits"):
                add(option, key, f"{base}/options/{option_index}")
        recommendation = question.get("recommendation")
        if recommendation:
            for key in ("rationale", "assumptions"):
                add(recommendation, key, base + "/recommendation")
            if question["type"] == "text":
                add(recommendation, "value", base + "/recommendation")
            elif isinstance(recommendation.get("value"), dict):
                add(recommendation["value"], "other", base + "/recommendation/value")
    for key in questionnaire.get("locale", {}).get("messages", {}):
        add(questionnaire["locale"]["messages"], key, "/locale/messages")
    return fields, originals


def prepare(questions_path, out_path):
    """Write a pending review template; never overwrite an existing file."""
    questionnaire, digest = _questions(questions_path)
    destination = Path(out_path)
    if destination.resolve() == Path(questions_path).resolve() or destination.exists():
        raise ReviewError(f"Refusing to overwrite review destination: {destination}", "already_exists", 409)
    questions = questionnaire["questions"]
    question_ids = [question["id"] for question in questions]
    fields, _ = visible_fields(questionnaire)
    review = {
        "schema_version": 1,
        "questions_sha256": digest,
        "status": "pending",
        "reviewer": {"identity": "", "relationship": "unknown"},
        "requirements": [{"id": "goal", "statement": questionnaire["goal"],
                          "basis": {"kind": "goal", "reference": "goal", "evidence": questionnaire["goal"]}}],
        "question_reviews": [
            {"question_id": question["id"], "option_ids": [option["id"] for option in question.get("options", [])],
             "requirement_ids": ["goal"], "status": "pending", "reason": ""}
            for question in questions],
        "combinations": [
            {"kind": kind, "answers": [], "inapplicable_question_ids": [], "fewer_decisions_reason": "",
             "requirement_ids": ["goal"], "status": "pending", "reason": ""}
            for kind in ("recommended", "contrast")] if len(questions) > 1 else [],
        "no_combinations_reason": "",
        "localization": {"language": core.resolve_questionnaire_locale(questionnaire)["language"],
                         "fields": fields, "original_language_fields": [], "status": "pending", "reason": ""},
        "fair_alternatives": {"question_ids": question_ids, "status": "pending", "reason": ""},
        "unknown_private_facts": {"question_ids": question_ids, "status": "pending", "reason": ""},
        "findings": [],
    }
    try:
        core.atomic_json(destination, review)
    except OSError as exc:
        raise ReviewError(f"Cannot write review: {exc}", "review_io_error") from exc
    return review


def _same_value(question, left, right):
    if question["type"] != "multi":
        return left == right
    if isinstance(left, list) and isinstance(right, list):
        return set(left) == set(right)
    if isinstance(left, dict) and isinstance(right, dict):
        return left["other"] == right["other"] and set(left["selected"]) == set(right["selected"])
    return False


def _validate(review, questionnaire, findings):
    _object(review, {"schema_version", "questions_sha256", "status", "reviewer", "requirements", "question_reviews",
                     "combinations", "no_combinations_reason", "localization", "fair_alternatives",
                     "unknown_private_facts", "findings"}, "review")
    _require(type(review["schema_version"]) is int and review["schema_version"] == 1,
             "schema_version", "Unsupported review schema.")
    _require(isinstance(review["questions_sha256"], str)
             and re.fullmatch(r"[0-9a-f]{64}", review["questions_sha256"]),
             "questions_sha256", "Must be a lowercase SHA256 digest.")

    def outcome(value, path, reason=True):
        _require(isinstance(value["status"], str) and value["status"] in STATUSES,
                 path + ".status", "Status must be pending, pass, or needs-revision.")
        if reason:
            _text(value["reason"], path + ".reason", empty=value["status"] == "pending")
        if value["status"] != "pass":
            findings.append({"code": value["status"], "path": path,
                             "message": value.get("reason") or "Review has not been completed."})

    outcome(review, "review", reason=False)
    _object(review["reviewer"], {"identity", "relationship"}, "reviewer")
    _text(review["reviewer"]["identity"], "reviewer.identity", empty=review["status"] == "pending")
    _require(isinstance(review["reviewer"]["relationship"], str)
             and review["reviewer"]["relationship"] in {"separate", "self", "unknown"},
             "reviewer.relationship", "Relationship must state separate, self, or unknown; no isolation is inferred.")
    questions = {question["id"]: question for question in questionnaire["questions"]}
    sources = {source["id"] for source in questionnaire["sources"]}
    requirements, goal_ids = set(), set()
    _list(review["requirements"], "requirements")
    for index, requirement in enumerate(review["requirements"]):
        path = f"requirements[{index}]"
        _object(requirement, {"id", "statement", "basis"}, path)
        _id(requirement["id"], path + ".id")
        _require(requirement["id"] not in requirements, path, "Duplicate requirement ID.")
        requirements.add(requirement["id"])
        _text(requirement["statement"], path + ".statement")
        basis = requirement["basis"]
        _object(basis, {"kind", "reference", "evidence"}, path + ".basis")
        _require(isinstance(basis["kind"], str) and basis["kind"] in {"goal", "user", "source"},
                 path + ".basis.kind", "Basis must identify the original goal, user request, or source.")
        _text(basis["reference"], path + ".basis.reference")
        _text(basis["evidence"], path + ".basis.evidence")
        if basis["kind"] == "goal":
            _require(requirement["statement"] == questionnaire["goal"] and basis["reference"] == "goal"
                     and basis["evidence"] == questionnaire["goal"], path,
                     "Goal invariant must preserve the exact questionnaire goal and its evidence.")
            goal_ids.add(requirement["id"])
        elif basis["kind"] == "source":
            _require(basis["reference"] in sources, path + ".basis.reference", "Unknown source ID.")
    _require(len(goal_ids) == 1, "requirements", "Exactly one original goal invariant is required.")

    def applicable(value, path):
        _references(value, requirements, path, exact=True, nonempty=True)

    _list(review["question_reviews"], "question_reviews")
    _require(bool(questions) or review["status"] == "pending", "question_reviews",
             "A completed review needs at least one question to review the fixed requirements.")
    covered = set()
    for index, row in enumerate(review["question_reviews"]):
        path = f"question_reviews[{index}]"
        _object(row, {"question_id", "option_ids", "requirement_ids", "status", "reason"}, path)
        _require(isinstance(row["question_id"], str) and row["question_id"] in questions,
                 path + ".question_id", "Unknown question ID.")
        qid = row["question_id"]
        _require(qid not in covered, path, "Duplicate question review.")
        covered.add(qid)
        _references(row["option_ids"], [option["id"] for option in questions[qid].get("options", [])],
                    path + ".option_ids", exact=True)
        applicable(row["requirement_ids"], path + ".requirement_ids")
        outcome(row, path)
    _require(covered == set(questions), "question_reviews", "Every question needs an option-coverage review.")

    _list(review["combinations"], "combinations")
    _text(review["no_combinations_reason"], "no_combinations_reason", empty=len(questions) > 1 or review["status"] == "pending")
    if len(questions) <= 1:
        _require(not review["combinations"], "combinations", "Use no_combinations_reason for zero or one question.")
    else:
        _require(not review["no_combinations_reason"], "no_combinations_reason", "Multiple questions require explicit combinations.")
        by_kind = {}
        for index, combination in enumerate(review["combinations"]):
            path = f"combinations[{index}]"
            _object(combination, {"kind", "answers", "inapplicable_question_ids", "fewer_decisions_reason",
                                  "requirement_ids", "status", "reason"}, path)
            kind = combination["kind"]
            _require(isinstance(kind, str) and kind in {"recommended", "contrast"}, path + ".kind", "Unknown combination kind.")
            _require(kind not in by_kind, path + ".kind", "Duplicate combination kind.")
            applicable(combination["requirement_ids"], path + ".requirement_ids")
            outcome(combination, path)
            _list(combination["answers"], path + ".answers")
            answers, records = {}, {}
            for answer_index, answer in enumerate(combination["answers"]):
                answer_path = f"{path}.answers[{answer_index}]"
                _require(isinstance(answer, dict), answer_path, "Must be an answer object.")
                _require(set(answer) in ({"question_id", "value"},
                                        {"question_id", "value", "branch_value", "branch_rationale"}),
                         answer_path, "Answer needs question_id and value, optionally branch_value plus branch_rationale.")
                qid = answer["question_id"]
                _require(isinstance(qid, str) and qid in questions, answer_path + ".question_id", "Unknown question ID.")
                _require(qid not in answers, answer_path, "Duplicate question in combination.")
                try:
                    core.validate_value(questions[qid], answer["value"])
                except core.BuilderError as exc:
                    raise _Invalid(answer_path + ".value", str(exc)) from exc
                recommendation = questions[qid].get("recommendation")
                if kind == "recommended" and recommendation:
                    _require(_same_value(questions[qid], answer["value"], recommendation["value"]), answer_path,
                             "Recommended combination must use recorded recommendation values.")
                answers[qid] = answer["value"]
                records[qid] = {"status": "answered", "value": answer["value"]}
                if "branch_value" in answer:
                    _require(isinstance(answer["value"], dict), answer_path, "Branch interpretation needs a custom answer.")
                    _text(answer["branch_rationale"], answer_path + ".branch_rationale")
                    try:
                        core.validate_branch_value(questions[qid], answer["branch_value"], answer["value"])
                    except core.BuilderError as exc:
                        raise _Invalid(answer_path + ".branch_value", str(exc)) from exc
                    records[qid]["branch_value"] = answer["branch_value"]
            _references(combination["inapplicable_question_ids"], questions, path + ".inapplicable_question_ids")
            _text(combination["fewer_decisions_reason"], path + ".fewer_decisions_reason", empty=True)
            if combination["status"] != "pending":
                states = core.states_for(questionnaire, {"answers": records})
                _require(all(states[qid] == "active" for qid in answers), path + ".answers",
                         "Combination contains inactive or unresolved conditional questions.")
                inactive = {qid for qid, state in states.items() if state == "inactive"}
                _references(combination["inapplicable_question_ids"], inactive,
                            path + ".inapplicable_question_ids", exact=True)
                if len(answers) < 2:
                    _require(len(answers) == 1 and inactive == set(questions) - answers.keys(), path + ".answers",
                             "Review at least two decisions unless every other question is explicitly inactive.")
                    _text(combination["fewer_decisions_reason"], path + ".fewer_decisions_reason")
            by_kind[kind] = answers
        _require(set(by_kind) == {"recommended", "contrast"}, "combinations", "Both recommended and contrasting combinations are required.")
        if all(row["status"] != "pending" for row in review["combinations"]):
            shared = by_kind["recommended"].keys() & by_kind["contrast"].keys()
            _require(any(not _same_value(questions[qid], by_kind["recommended"][qid], by_kind["contrast"][qid]) for qid in shared),
                     "combinations", "Contrasting combination must change a shared decision from the recommended combination.")

    localization = review["localization"]
    _object(localization, {"language", "fields", "original_language_fields", "status", "reason"}, "localization")
    _require(localization["language"] == core.resolve_questionnaire_locale(questionnaire)["language"],
             "localization.language", "Review language must match the resolved questionnaire locale.")
    fields, originals = visible_fields(questionnaire)
    _references(localization["fields"], fields, "localization.fields", exact=True)
    _references(localization["original_language_fields"], originals, "localization.original_language_fields")
    outcome(localization, "localization")
    for name in ("fair_alternatives", "unknown_private_facts"):
        _object(review[name], {"question_ids", "status", "reason"}, name)
        _references(review[name]["question_ids"], questions, name + ".question_ids", exact=True)
        outcome(review[name], name)

    _list(review["findings"], "findings")
    finding_ids = set()
    for index, finding in enumerate(review["findings"]):
        path = f"findings[{index}]"
        _object(finding, {"id", "status", "area", "question_ids", "description", "resolution"}, path)
        _id(finding["id"], path + ".id")
        _require(finding["id"] not in finding_ids, path + ".id", "Duplicate finding ID.")
        finding_ids.add(finding["id"])
        _require(isinstance(finding["status"], str) and finding["status"] in {"open", "resolved"},
                 path + ".status", "Finding must be open or resolved.")
        _require(isinstance(finding["area"], str) and finding["area"] in {
            "requirements", "options", "combinations", "localization", "fair_alternatives", "unknown_private_facts"},
            path + ".area", "Unknown review area.")
        _references(finding["question_ids"], questions, path + ".question_ids")
        _text(finding["description"], path + ".description")
        _text(finding["resolution"], path + ".resolution", empty=finding["status"] == "open")
        if finding["status"] == "open":
            findings.append({"code": "open_finding", "path": path, "message": finding["description"]})


def check(questions_path, review_path):
    """Return a nonpassing report for missing, stale, pending, or invalid reviews."""
    questionnaire, digest = _questions(questions_path)
    report = {"schema_version": 1, "status": "invalid", "passed": False, "questions_sha256": digest,
              "review_path": str(Path(review_path).resolve()), "findings": [], "limitations": LIMITATION}
    findings = report["findings"]
    try:
        _, review = _read(review_path)
    except FileNotFoundError:
        report["status"] = "missing"
        findings.append({"code": "missing", "path": "review", "message": "Question review file is missing."})
        return report
    except (OSError, UnicodeError, ValueError) as exc:
        findings.append({"code": "invalid", "path": "review", "message": f"Cannot read review: {exc}"})
        return report
    try:
        _validate(review, questionnaire, findings)
    except _Invalid as exc:
        findings.append({"code": "invalid", "path": exc.path, "message": exc.message})
    if isinstance(review, dict) and review.get("questions_sha256") != digest:
        findings.append({"code": "stale", "path": "questions_sha256", "message": "Questionnaire bytes changed after review preparation."})
    codes = {finding["code"] for finding in findings}
    if "invalid" in codes:
        report["status"] = "invalid"
    elif "stale" in codes:
        report["status"] = "stale"
    elif codes & {"needs-revision", "open_finding"}:
        report["status"] = "needs-revision"
    elif "pending" in codes:
        report["status"] = "pending"
    else:
        report.update(status="pass", passed=True)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    make = commands.add_parser("prepare", help="Write a pending review template; does not perform a review.")
    make.add_argument("--questions", required=True)
    make.add_argument("--out", required=True)
    verify = commands.add_parser("check", help="Check binding, coverage, references, and recorded outcomes.")
    verify.add_argument("--questions", required=True)
    verify.add_argument("--review", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(args.questions, args.out)
            code = 0
        else:
            result = check(args.questions, args.review)
            code = 0 if result["passed"] else 1
    except ReviewError as exc:
        result, code = {"error": exc.code, "message": str(exc)}, 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
