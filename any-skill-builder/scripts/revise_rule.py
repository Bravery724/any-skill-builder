"""Publish a successor workspace for one explicitly scoped rule revision."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import shutil
import tempfile
import uuid

import builder_core as core
import evaluate_skill as evaluation
import plan_change
from prepare_evaluation import cli_definition, excluded_part, portable_relative, register_path, safe_source


def rows(document, name):
    return evaluation.unique_records(document.get(name, []), name, allow_empty=True)


def fields(row, allowed, label):
    evaluation.object_value(row, label)
    evaluation.require(set(row) <= set(allowed), f"Unknown {label} fields: {sorted(set(row) - set(allowed))}")


def read(path):
    return plan_change.read_document(safe_source(path))


def read_change(path):
    blob = evaluation.read_bytes(safe_source(path))
    change = evaluation.object_value(evaluation.strict_json(blob, "Change form"), "Change form")
    serialized = json.dumps(change, ensure_ascii=False)
    core.require(evaluation.strict_json(blob, "Change form", exact_numbers=True) ==
                 evaluation.strict_json(serialized, "Re-encoded change form", exact_numbers=True),
                 "For an exact decimal in a JSON fixture, put its full JSON text in expected_json.")
    return change


def inventory(root, plan_path):
    """Only carry current authoring records, selected runtime, and declared evaluation data."""
    plan = read(plan_path)
    evaluation.require(set(plan) == {"schema_version", "name", "cases"} and type(plan["schema_version"]) is int
                       and plan["schema_version"] == 1, "Supply a working evaluation plan with schema_version 1.")
    evaluation.text(plan["name"], "Plan name")
    design = read(root / "design.json")
    question = read(root / "questions.json")
    core.validate_questionnaire(question, root, allow_empty=True)
    files, spellings = {}, {}

    def add(name, path):
        relative = str(name).replace("\\", "/")
        register_path(relative, spellings)
        path = safe_source(path)
        evaluation.require(path.is_file(), f"Missing current source file: {path}")
        evaluation.require(relative not in files or files[relative] == path, f"Collision at {relative}")
        files[relative] = path

    for name in ("questions.json", "answers.json", "design.json", "decisions.json", "review-policy.json",
                 "question-review.json"):
        if (root / name).exists():
            add(name, root / name)
    evaluation.require("answers.json" in files, "This workspace needs its answers.json.")
    for q in question.get("questions", []):
        for option in q.get("options", []):
            if "image" in option:
                core.safe_asset(root, option["image"])
                add(option["image"], root / option["image"])

    runtime = safe_source(root / evaluation.text(design.get("skill_path"), "design.skill_path"))
    evaluation.require(runtime != root and (runtime.is_relative_to(root) or runtime.parent == root.parent / "output")
                       and (runtime / "SKILL.md").is_file(),
                       "design.skill_path must name a skill in this workspace or its sibling output/ folder.")
    runtime_name = Path("output") / runtime.name
    pending = [runtime]
    while pending:
        for entry in pending.pop().iterdir():
            relative = entry.relative_to(runtime)
            if excluded_part(relative.parts) or entry.suffix.lower() in {".pyc", ".pyo", ".key", ".pem"}:
                raise core.BuilderError(f"Prepare a clean runtime first. It contains {relative}.")
            safe_source(entry)
            if entry.is_dir():
                pending.append(entry)
            else:
                add(runtime_name / relative, entry)

    add("plan/plan.json", plan_path)
    inputs, expectations = set(), set()
    cases = evaluation.unique_records(plan["cases"], "Cases")
    for case in cases.values():
        evaluation.text(case.get("prompt"), "Case prompt")
        for check in evaluation.unique_records(case.get("checks"), "Case checks").values():
            evaluation.check_definition(check)
            if check["kind"] == "json_file_equals":
                expectations.add(portable_relative(check["expected_file"]).as_posix())
        if "cli" in case:
            cli_definition(case)
        for path in evaluation.sequence(case.get("input_files", []), "Case inputs", allow_empty=True):
            inputs.add(portable_relative(path).as_posix())
    evaluation.require(not inputs & expectations, "Keep expected fixtures separate from task inputs.")
    for relative in inputs | expectations:
        evaluation.require(relative.casefold() != "plan.json", "A fixture conflicts with the successor plan name.")
        add("plan/" + relative, plan_path.parent / relative)
        if relative in expectations:
            evaluation.strict_json(evaluation.read_bytes(files["plan/" + relative]), relative)
    return files, design, plan, runtime


def snapshot(files):
    return core.json_digest({name: core.image_digest(path) for name, path in sorted(files.items())})


def source_binding(root, plan_path, target, digest):
    return core.json_digest([str(root), str(plan_path), target, digest])


def current_target(root, target):
    fields(target, {"kind", "id"}, "target")
    kind, ident = target.get("kind"), target.get("id")
    core.require(kind in ("question", "requirement"), "Choose a question or requirement.")
    core.valid_id(ident, "changed rule ID")
    q = read(root / "questions.json")
    if core.decision_list_in_use(root, q):
        source = read(root / core.DECISIONS_FILE)
        family = "requirements" if kind == "requirement" else "decisions"
    elif kind == "question":
        source, family = q, "questions"
    else:
        core.require((root / "question-review.json").is_file(),
                     "This run has no fixed-requirement record. Select an existing question or establish a reviewed requirement first.")
        source, family = read(root / "question-review.json"), "requirements"
    record = rows(source, family).get(ident)
    core.require(record is not None, f"No existing {kind} with ID {ident} in the authoritative {family}.")
    if family == "requirements" and isinstance(record.get("basis"), dict):
        core.require(record["basis"].get("kind") != "goal", "Revising the project goal requires reviewing the whole questionnaire.")
    return family


def prepare(root, target, plan_path, destination):
    current_target(root, target)
    files, design, plan, runtime = inventory(root, plan_path)
    trace = target["kind"] + "_ids"
    impact = plan_change.plan_change(root, trace, target["id"], plan=plan_path)
    template = {"schema_version": 1, "source_sha256": source_binding(root, plan_path, target, snapshot(files)), "plan": str(plan_path),
                "target": target, "rule": "", "basis": "",
                "feature_edits": [{"id": fid, "replace": ""} for fid in impact["features_to_change"]],
                "check_edits": []}
    destination = safe_source(destination)
    core.require(not destination.is_relative_to(runtime), "Keep the change form outside the predecessor skill runtime.")
    core.require(not destination.exists(), f"Change form already exists: {destination}", "already_exists", 409)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8") as stream:
        json.dump(template, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    features = rows(design, "features")
    return {"event": "change_form_created", "path": str(destination), "impact": impact,
            "features": {fid: feature.get("behavior") for fid, feature in features.items()},
            "case_features": case_features(features, rows(plan, "cases")),
            "checks": {c["id"]: {k["id"]: k["kind"] for k in c["checks"]} for c in plan["cases"]}}


def revised_text(old, edit, rule, *, append=False):
    evaluation.text(old, "Current clause")
    if append and edit.get("append") is True and "replace" not in edit:
        return old + " " + rule
    core.require("append" not in edit, "Choose either an exact replace clause or append: true.")
    clause = evaluation.text(edit.get("replace"), "Exact clause to replace")
    core.require(old.count(clause) == 1, "The selected clause must occur exactly once in its field.")
    core.require(clause != rule, "The replacement must change the selected clause.")
    return old.replace(clause, rule, 1)


def case_features(features, cases):
    owners = {cid: [] for cid in cases}
    for fid, feature in features.items():
        for cid in plan_change.identifiers(feature, "evaluation_ids"):
            if cid in owners:
                owners[cid].append(fid)
    return owners


def add_case_links(feature, additions, owners, cases, trace, ident):
    """Keep existing owners and require an explicit shared link when a case already has one."""
    for item in evaluation.sequence(additions, "add_evaluation_ids", allow_empty=True):
        shared = []
        if isinstance(item, str):
            cid = evaluation.text(item, "Case ID")
        else:
            fields(item, {"id", "shared_with"}, "shared case link")
            cid = evaluation.text(item.get("id"), "Case ID")
            shared = evaluation.sequence(item.get("shared_with"), "shared_with")
            for name in shared:
                evaluation.text(name, "Existing feature ID")
        core.require(cid in cases, f"Unknown evaluation case {cid}. Choose an existing case from case_features.")
        links = feature.setdefault("evaluation_ids", [])
        core.require(cid not in links, f"Duplicate evaluation link: {feature['id']}/{cid}.")
        core.require(sorted(shared) == sorted(owners[cid]),
                     f"Case {cid} has existing features {owners[cid]}. Affirm those exact IDs in shared_with to add a shared link.")
        links.append(cid)
        # Only a previously declared case-level inventory claims complete coverage.
        if trace in cases[cid] and ident not in plan_change.identifiers(cases[cid], trace):
            cases[cid][trace].append(ident)


def revise_mappings(stage, design, plan, change):
    trace, ident = change["target"]["kind"] + "_ids", change["target"]["id"]
    features = rows(design, "features")
    cases = rows(plan, "cases")
    owners = case_features(features, cases)
    edits = evaluation.unique_records(change.get("feature_edits"), "feature_edits")
    direct = {fid for fid, feature in features.items() if ident in plan_change.identifiers(feature, trace)}
    core.require(direct <= edits.keys(), "Review every feature linked to the changed ID; use keep: true for an unaffected rule.")
    affected, mapped_cases = [], set()
    for fid, edit in edits.items():
        fields(edit, {"id", "replace", "append", "keep", "add_evaluation_ids"}, "feature edit")
        core.require(fid in features, f"Unknown feature {fid}.")
        feature = features[fid]
        if edit.get("keep") is True:
            core.require(set(edit) == {"id", "keep"} and fid in direct, "keep applies only to an unchanged linked feature.")
            continue
        core.require("keep" not in edit, "Use keep: true only for an unchanged feature.")
        feature["behavior"] = revised_text(feature.get("behavior"), edit, change["rule"], append=True)
        if fid not in direct:
            feature.setdefault(trace, []).append(ident)
        add_case_links(feature, edit.get("add_evaluation_ids", []), owners, cases, trace, ident)
        affected.append(fid)
        mapped_cases.update(plan_change.identifiers(feature, "evaluation_ids"))
    core.require(affected, "At least one feature needs a revised behavior.")
    seen = set()
    for edit in evaluation.sequence(change.get("check_edits"), "check_edits"):
        fields(edit, {"case", "id", "replace", "expected", "expected_json"}, "check edit")
        cid, kid = evaluation.text(edit.get("case"), "Case ID"), evaluation.text(edit.get("id"), "Check ID")
        core.require(cid in cases and (cid, kid) not in seen, f"Unknown case or duplicate check edit: {cid}/{kid}.")
        seen.add((cid, kid))
        check = rows(cases[cid], "checks").get(kid)
        core.require(check is not None, f"Unknown check {cid}/{kid}.")
        core.require(cid in mapped_cases or ident in plan_change.identifiers(cases[cid], trace)
                     or ident in plan_change.identifiers(check, trace), f"Check {cid}/{kid} is outside the selected feature cases. "
                     "If this case exercises the changed rule, name it in that feature edit's add_evaluation_ids. "
                     "See case_features for any existing owners.")
        kind = check["kind"]
        if kind == "json_file_equals":
            core.require(("expected" in edit) != ("expected_json" in edit) and "replace" not in edit,
                         f"Supply the explicit expected result for {cid}/{kid} as expected or expected_json.")
            content = (evaluation.text(edit["expected_json"], "Expected JSON text") if "expected_json" in edit
                       else json.dumps(edit["expected"], ensure_ascii=False, indent=2))
            old = evaluation.read_bytes(stage / "plan" / check["expected_file"])
            core.require(evaluation.strict_json(old, "Old fixture", exact_numbers=True) !=
                         evaluation.strict_json(content, "New fixture", exact_numbers=True),
                         f"The expected result for {cid}/{kid} did not change.")
            path = Path("revision-expectations") / (core.json_digest([cid, kid, content]) + ".json")
            resource = stage / "plan" / path
            core.require(not resource.exists(), f"New expected fixture path already exists: {path}")
            core.atomic_text(resource, content + "\n")
            check["expected_file"] = path.as_posix()
        elif kind == "review":
            core.require("expected_json" not in edit, "expected_json applies only to a JSON fixture.")
            criterion = evaluation.text(edit.get("expected", change["rule"]), "Revised criterion")
            check["criterion"] = revised_text(check["criterion"], edit, criterion)
        else:
            core.require("expected" in edit and "replace" not in edit and "expected_json" not in edit,
                         f"Supply the explicit expected result for {cid}/{kid} ({kind}).")
            expected = edit["expected"]
            key = "expected" if kind == "json_equals" else "text"
            old, check[key] = check[key], expected
            core.require(core.json_digest(old) != core.json_digest(expected), f"The expected result for {cid}/{kid} did not change.")
        evaluation.check_definition(check)
        if ident not in plan_change.identifiers(check, trace):
            check.setdefault(trace, []).append(ident)
    for case in cases.values():
        if "cli" in case:
            cli_definition(case)
    core.atomic_json(stage / "design.json", design)
    core.atomic_json(stage / "plan/plan.json", plan)
    return sorted({path for fid in affected for path in plan_change.identifiers(features[fid], "files")})


def new_answer(question, previous, change):
    rule = change["rule"]
    if "value" in change:
        value = change["value"]
    elif question["type"] == "text":
        value = rule
    else:
        selected = previous.get("selected", []) if isinstance(previous, dict) else previous
        value = {"selected": selected if question["type"] == "multi" and isinstance(selected, list) else [], "other": rule}
    text = change["basis"] if value == rule or isinstance(value, dict) and value.get("other") == rule else rule + " (" + change["basis"] + ")"
    record = {"status": "answered", "actor": "user", "value": value, "rationale": text}
    if "branch_value" in change:
        record.update(branch_value=change["branch_value"], branch_rationale=change["basis"])
    return core.normalize_record(question, record)


def change_requirement(requirement, change):
    if "source_replace" in change:
        statement = revised_text(requirement["statement"], {"replace": change["source_replace"]}, change["rule"])
    else:
        statement = change["rule"]
    core.require(statement != requirement["statement"], "The fixed requirement statement did not change.")
    basis = change["basis"]
    if isinstance(requirement["basis"], dict):
        basis = {"kind": "user", "reference": basis, "evidence": change["rule"]}
    requirement.update(statement=statement, basis=basis)


def revise_source(stage, change):
    core.recover_workspace(stage)  # Migrate any legacy run identity only on the successor.
    q, answers = core.load_workspace(stage)
    revision = copy.deepcopy(q.get("rule_revision", {}))
    revision["id"] = str(uuid.uuid4())
    answers["workspace_revision_id"] = revision["id"]
    target, ident = change["target"], change["target"]["id"]
    family = current_target(stage, target)
    if family == "requirements":
        core.require(not {"value", "branch_value"}.intersection(change), "A fixed requirement has no answer value.")
    else:
        core.require("source_replace" not in change, "source_replace applies only to a fixed requirement.")
    if core.decision_list_in_use(stage, q):
        decisions = read(stage / core.DECISIONS_FILE)
        before = core.validate_decisions(decisions, q, stage)
        item = rows(decisions, family)[ident]
        if family == "requirements":
            change_requirement(item, change)
            protected_fields = ("statement", "basis")
        else:
            core.require(before["states"][ident] == "active", "The selected Full Auto decision is inactive or waiting.")
            question = rows(before["mapped"], "questions")[ident]
            record = new_answer(question, item.get("choice"), change)
            for key in ("branch_value", "branch_rationale", "assumptions"):
                item.pop(key, None)
            item.update(choice=record["value"], reason=record["rationale"], choice_actor="user")
            for key in ("branch_value", "branch_rationale"):
                if key in record:
                    item[key] = record[key]
            protected_fields = ("choice", "choice_actor", "reason", "branch_value", "branch_rationale")
        revision.setdefault("auto_rules", {}).setdefault(family, {})[ident] = {
            key: item[key] for key in protected_fields if key in item}
        q["rule_revision"] = revision
        decisions["workspace_revision_id"] = revision["id"]
        core.atomic_json(stage / "questions.json", q)
        # The previous run's review speaks only to its original decisions.
        for name in core.DECISION_CHECKS:
            decisions["check"][name] = {"status": "pending"}
        decisions["check"]["reviewer"] = "unknown"
        decisions["check"]["revisions"] = 0
        core.atomic_json(stage / core.DECISIONS_FILE, decisions)
        after = core.validate_decisions(decisions, q, stage)
        lines = core.decision_brief_lines(stage, q, draft=True)
        pending = list(after["pending_checks"]) + after["unchosen_ids"] + after["waiting_ids"]
    else:
        review = core.question_review_state(stage, q)
        core.require(not review["required"] or review["passed"],
                     "The predecessor questionnaire needs its current accepted review before revising its rules.")
        if family == "requirements":
            core.require(review["passed"], "A questionnaire fixed requirement needs its accepted review.")
            record = read(stage / "question-review.json")
            change_requirement(rows(record, family)[ident], change)
            record["status"] = "pending"
            for row in record["question_reviews"] + record["combinations"]:
                if ident in row["requirement_ids"]:
                    row.update(status="pending", reason="")
        else:
            question = rows(q, "questions")[ident]
            previous = answers["answers"].get(ident)
            core.require(previous is not None and core.states_for(q, answers)[ident] == "active",
                         "Only a current active answer can be superseded.")
            record = new_answer(question, previous["value"], change)
            core.require(core.apply_changes(q, answers, {ident: record}, "user", preserve_active_branches=True),
                         "The selected answer did not change.")
        # The questionnaire fingerprint identifies the successor even when question text
        # and answer numbers agree with an older run. Keep accepted fixed rules available
        # to a fresh review template and to restoration from the portable form.
        if review["passed"]:
            if family != "requirements":
                record = read(stage / "question-review.json")
            revision["requirements"] = [row for row in record["requirements"] if row["basis"]["kind"] != "goal"]
        q["rule_revision"] = revision
        core.atomic_json(stage / "questions.json", q)
        if review["passed"]:
            record["questions_sha256"] = core.image_digest(stage / "questions.json")
            core.atomic_json(stage / "question-review.json", record)
        view = core.make_view(q, answers)
        view["question_review"] = core.question_review_state(stage, q)
        pending = [qid for qid, state in view["states"].items() if state == "waiting" or state == "active" and qid not in answers["answers"]]
        if view["question_review"]["required"] and not view["question_review"]["passed"]:
            pending.append("question-review")
        lines = core.questionnaire_brief_lines(stage, view, draft=bool(pending))
    core.atomic_json(stage / "answers.json", answers)
    if pending:
        lines[0:1] = ["# Draft skill build brief", "", "Pending review or answers: " + ", ".join(pending),
                      "Resolve these items and run brief again before building."]
    core.atomic_text(stage / "build-brief.md", "\n".join(lines))
    return pending


def apply(root, change, destination):
    fields(change, {"schema_version", "source_sha256", "plan", "target", "rule", "basis", "value", "source_replace",
                    "branch_value", "feature_edits", "check_edits"}, "change form")
    core.require(type(change.get("schema_version")) is int and change["schema_version"] == 1, "Unsupported change form.")
    for key in ("rule", "basis", "source_sha256", "plan"):
        evaluation.text(change.get(key), key)
    current_target(root, change.get("target"))
    request = core.json_digest({"source": str(root), "change": change})
    destination = safe_source(destination)
    core.require(not destination.is_relative_to(root), "Publish the successor outside the predecessor workspace.")
    receipt_name = "rule-revision.json"
    if destination.exists():
        receipt = destination / receipt_name
        core.require(receipt.is_file() and read(safe_source(receipt)).get("request_sha256") == request,
                     "Destination already exists with different contents. Choose a fresh directory.", "already_exists", 409)
        return {"event": "already_published", "workspace": str(destination), "receipt": str(receipt)}
    plan_path = safe_source(change["plan"])
    files, design, plan, runtime = inventory(root, plan_path)
    core.require(not destination.is_relative_to(runtime), "Publish outside the predecessor runtime.")
    digest = snapshot(files)
    core.require(source_binding(root, plan_path, change["target"], digest) == change["source_sha256"],
                 "Source data or target changed. Prepare a new change form against the current files.",
                 "stale_revision", 409)
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".revise-rule-", dir=destination.parent))
    try:
        for name, path in files.items():
            copy = stage / name
            copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, copy)
        (stage / "assets").mkdir(exist_ok=True)
        core.require(snapshot({name: stage / name for name in files}) == digest, "Source changed while copying. Prepare again.")
        runtime_path = Path("output") / runtime.name
        design, plan = read(stage / "design.json"), read(stage / "plan/plan.json")
        design["skill_path"] = runtime_path.as_posix()
        pending = revise_source(stage, change)
        changed_files = revise_mappings(stage, design, plan, change)
        impact = plan_change.plan_change(stage, change["target"]["kind"] + "_ids", change["target"]["id"], plan=stage / "plan/plan.json")
        receipt = {"event": "rule_revision_published", "request_sha256": request, "source": str(root),
                   "workspace": str(destination), "rule": change["rule"], "target": change["target"],
                   "previous_plan": str(plan_path), "plan": str(destination / "plan/plan.json"),
                   "baseline_runtime": str(runtime), "runtime": str(destination / runtime_path),
                   "runtime_files_to_edit": changed_files, "pending_brief_items": pending,
                   "retest_scope": impact["scope"], "retest_cases": impact["retest_cases"],
                   "runtime_status": "awaiting_implementation_and_evaluation"}
        core.atomic_json(stage / receipt_name, receipt)
        current_files, _, _, _ = inventory(root, plan_path)
        core.require(snapshot(current_files) == digest, "Source changed while preparing the successor. Prepare again.")
        core.require(not destination.exists(), "The successor destination appeared during preparation.", "already_exists", 409)
        stage.rename(destination)
        return receipt
    finally:
        if stage.exists():
            core.require(stage.parent.resolve() == destination.parent and stage.name.startswith(".revise-rule-"), "Unexpected staging path.")
            shutil.rmtree(stage)


def run(args):
    try:
        root = safe_source(args.workspace)
        with core.workspace_lock(root):
            if (root / ".pending-state.json").is_file():
                core.recover_workspace(root)
            if args.prepare:
                core.require((args.question or args.requirement) and not args.destination,
                             "--prepare needs --question or --requirement. Use --destination with --input.")
                plan_path = args.plan or plan_change.find_plan(root)
                core.require(plan_path, "Supply --plan pointing to the current working evaluation plan.")
                target = {"kind": "question" if args.question else "requirement", "id": args.question or args.requirement}
                return prepare(root, target, safe_source(plan_path), args.prepare)
            core.require(args.destination and not (args.plan or args.question or args.requirement),
                         "--input needs --destination. The prepared form identifies the rule and working plan.")
            return apply(root, read_change(args.input), args.destination)
    except evaluation.EvaluationError as error:
        raise core.BuilderError(str(error)) from error
