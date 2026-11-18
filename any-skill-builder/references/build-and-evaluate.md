# Turn decisions into a usable skill

Only build the final package after current applicable design choices are resolved, including blanks assigned to AI and meaningful custom answers. `brief` enforces the state gate and writes the current evidence, answers, reasons, and assumptions. This text is input to the host AI, not an automatic replacement for implementation judgment.

Read `build-brief.md` with the latest user instructions, including constraints supplied after a form was saved. For choices that affect the same input, output or reader, trace what happens when their effects apply together. Include custom text, the user's selections in an AI-completed answer, and any implicit implementation defaults. For example, if a handoff must name the assignee while hiding contact details, scope masking to the contact fields. If a second default groups tasks by team, keep the named assignee beside each task after grouping. If the user requires anonymity, use only a permitted way to distinguish assignees that still works for the intended reader.

Keep the user's original answers. Narrow or replace the AI-owned part wherever needed to satisfy them, even when several defaults contribute to the loss. Record the resulting rule in the affected `design.json` feature's `behavior` before implementation. Link the contributing requirement and decision IDs, and identify the source of any newer constraint in that rule. On resume, update affected rules against the current choices. If two explicit requirements still conflict within the same scope, ask which should govern that specific output.

Summarize the main AI-selected directions, their reasons, and remaining assumptions in chat. Carry facts needed only at execution into the generated skill's runtime inputs; do not turn unknown accounts, equipment, or private resources into assumed facts.

At this planning stage, declare the evaluation tasks, actual inputs, and success criteria following [evaluation.md](evaluation.md). Keep criteria out of the executor's task packet. When improving an existing skill, snapshot the original runtime before editing so later comparisons use the actual old version.

## Design the smallest adequate package

Use `RUN/output/<skill-name>/`. Name the folder and skill consistently with lowercase letters, digits, and hyphens. When improving an existing skill, retain its identifier and matching folder/frontmatter name unless the user requests a rename; a separate revision directory does not require a new skill name. The required `SKILL.md` has YAML `name` and `description` followed by instructions. Its description must explain the actual capability and when it applies.

- Put purpose, important decisions, essential workflow, and links to conditional material in `SKILL.md`.
- Include a concise user-facing `README.md` with every newly created skill, following the checklist below. This guide is part of the installable runtime, not maintainer documentation.
- Add `references/` only for substantial task-specific information that changes decisions and is useful on demand.
- Add `assets/` for real output templates, chosen images, or other reusable deliverable resources.
- Add `scripts/` for repeatable operations where deterministic handling improves reliability. Do not generate code just to make the skill look sophisticated.
- Add host metadata only when the target environment uses it. Keep the standard instructions portable where possible, and state real dependencies or unsupported capabilities.

For image decisions, preserve the chosen candidate and translate its relevant properties into actionable instructions. A filename alone does not communicate layout density, information hierarchy, or the user's comments.

The references used while building do not all belong in the final skill. Keep full research logs, questionnaire history, and evaluation scaffolding in the run. Do not copy entire external manuals or install arbitrary dependencies as part of packaging.

Write reusable instructions, reference documents, README files, code comments, and package metadata in English by default. An explicit request for a different file language overrides this default. Keep original-language input, quotations, translation dictionaries, and multilingual regression fixtures intact. The generated skill's user-facing behavior still follows the conversation or explicitly requested output language.

When preparing a skill for distribution, use relative resource references, document actual runtime requirements, and remove personal paths and assumptions. Exclude run records, answers, generated user material, credentials, caches, and machine-specific verification output. Package runtime files separately from maintainer tests and documentation. Include the chosen license. An archive is optional unless distribution is requested; if supplied, verify its exact contents and a separately extracted copy as described below. Do not publish externally unless publication is authorized.

## Provide usage guidance at the right moment

Write the generated skill's `README.md` for someone who has not read the design conversation. Keep a simple skill's guide short; add detail only when its actual workflow needs it. Include:

- A plain-language sentence explaining what the skill helps the user accomplish.
- Required inputs or materials, plus optional preferences that actually change the result.
- One immediately usable starting request and, when useful, one or two distinct examples such as a refinement or continuation. Use the target host's supported invocation spelling rather than inventing slash commands or flags.
- What the user will receive and any real tool, permission, or capability limits needed to start successfully.
- How to ask for changes or resume when the implementation supports it.

Link the guide from `SKILL.md` and include it in the installable package. Write reusable files in English unless the user explicitly requests another file language. Conversational help follows the user's language; a static metadata string is not automatically translated by this rule.

Keep `SKILL.md`'s frontmatter description focused on capability and when to use the skill. If the target host supports separate picker metadata, provide a concise user-facing description and a starting prompt there. For Codex-style `agents/openai.yaml`, use `interface.display_name`, `interface.short_description` (25–64 characters), and a helpful `interface.default_prompt` mentioning `$skill-name`; follow the host's available metadata documentation. Other hosts may use different fields or ignore this file. Never promise a particular `/` menu layout or automatic help merely from selecting a menu item.

Give the generated skill a small help behavior: reuse the task, attachments, and prior context first. If invoked without an actionable task and no useful context, explain its purpose in one or two natural sentences, provide a short starting example, and ask for the missing input. If a task is clear, start it directly. A request for usage help can receive the guide's relevant details. Avoid repeating an introduction before each normal task or adding a mandatory onboarding step.

Before delivery, compare the guide and picker description with the implementation. The first example must work with the declared inputs and supported tools; optional modes, outputs, permissions, and resume promises must exist. Include an empty-invocation/help case and a clear-task case in the behavior review when adding this behavior. Do not turn a well-written guide into a claim that unexecuted tasks were tested.

## Write outputs like a helpful conversation

Make natural conversational explanation the default for chat and document prose, including HTML reports. Match the user's language and level of politeness; use natural phrasing in that language without hard-coding one language's sentence endings. An explicit request for academic prose, a formal submission, or another genre takes precedence.

Lead with what the result means, then connect the reasoning, examples, and implications in readable paragraphs. Explain necessary technical terms briefly. Use lists and tables when they aid comparison or navigation. Avoid dense noun fragments, administrative phrasing, and unnecessary jargon. Preserve source attribution, numerical precision, uncertainty, and useful depth; conversational writing is not permission to omit these. Keep schemas, identifiers, citations, and code unchanged.

When several requested sections use the same evidence, give each section a distinct job. A table can hold facts and short source quotes; explanation should add an implication the table does not convey; follow-up questions should ask for the missing decision. Do not repeat the full row, quote, or generic reason in every section. Refer to item numbers where useful and keep simple cases proportionately short. Preserve requested sections, flags, evidence, and uncertainty while removing repetition. Review an actual output for this distinction rather than assuming that separate headings make it readable.

Add a concise instruction with this behavior to the generated skill. Review a representative output passage by reading it as something said directly to the user. Revise the explanation itself when needed instead of mechanically swapping sentence endings. Do not copy stock transitions into every paragraph or introduce extra questions for a preference the user has already supplied.

For analytical outputs, always make the reasoning easy to follow, intuitive, and useful. Explain the finding's meaning and importance, the evidence that supports it and its limits, and what the reader can do with that understanding. A concrete input/output example or comparison can help before technical detail; label hypothetical examples and keep their limits clear. Do not force a fixed sequence into every paragraph. In review, ask whether a reader unfamiliar with the analysis can understand its main point and practical consequence without decoding unexplained labels or opening every citation. Clear explanation remains necessary even when the requested genre is formal.

## Record decision traceability

Write `RUN/design.json` as a compact record of what was built. Example shape:

```json
{
  "project_id": "paper-study",
  "questionnaire_revision": 2,
  "skill_path": "output/paper-idea-review",
  "features": [
    {
      "id": "related-work-comparison",
      "question_ids": ["q-scope"],
      "behavior": "Compare relevant prior/subsequent work before proposing a research gap",
      "files": ["SKILL.md", "references/comparison.md"],
      "evaluation_ids": ["case-related-work"]
    }
  ],
  "assumptions": [],
  "limitations": []
}
```

Record actual current decisions and files. For features specified entirely by fixed requirements, use their IDs in `requirement_ids` and leave `question_ids` empty. Inactive questions and obsolete candidates must not reappear as selected features. If a user changes an answer later, use this mapping to identify affected instructions, scripts, assets, and evaluations. Recheck shared behavior when the change affects it.

When one feature implements several rules, add `requirement_ids` and `question_ids` to the relevant **case** in the working evaluation plan. List all IDs that case exercises for the given field. For example, a newer-revision case could carry `"requirement_ids": ["latest", "identity"]`, while a cancellation case carries `"requirement_ids": ["conflict", "latest"]`. Use an empty list when a case exercises none of that kind. An omitted field means coverage is unknown. Existing IDs on individual checks provide additional positive links. Keep these annotations outside the executor's task and preserve the previous frozen plan.

### Resume after one rule changes

Use the stable ID of the existing rule or answer. The read-only planner can include neighboring invariants the user singled out.

```text
python -B scripts/plan_change.py --run RUN --requirement conflict --keep-requirement latest
python -B scripts/plan_change.py --run RUN --question audience --keep-case confidential-handoff
```

Use `--keep-question ID` for a neighboring decision. Repeat the keep options as needed. The helper looks for `plan.json` or `evaluation-plan.json` directly in the run or its `plan/` folder. Supply `--plan PATH` to select the current working plan if it lives elsewhere or several match.

Read the JSON as an edit and retest checklist. Inspect the named feature rules and files, the cases tracing the change, and the regression cases for other features sharing those files. Keep every criterion of a selected case, including its unaffected assertions. Feature-only links retain all cases whose coverage is uncertain. A missing or inconsistent inventory broadens the plan to the full suite. Reconcile unmatched IDs, newly active branches, public examples and unmapped dependencies against the actual runtime before narrowing. File sharing and declared IDs cannot establish semantic coverage.

From the installed builder folder, prepare one revision form. Use `--question ID` for a questionnaire answer or Full Auto choice. Use `--requirement ID` for a fixed requirement in the Full Auto list or the accepted questionnaire review.

```text
python -B scripts/skill_builder.py revise-rule --workspace RUN --requirement conflict --prepare CHANGE.json
```

Read the selected features and checks. The preparation output lists every working-plan case in `case_features`, with its current feature owners, and lists its checks in `checks`. Inspect the inputs and expectations of cases that exercise the rule, including cases whose links are missing. Put the user's new rule in the generated form once, identify its source in `basis`, and select exact clauses or expectations to change. Keep the generated target, plan path, and fingerprint. For example, these are the editable fields of a form for a cancellation rule.

```json
{
  "rule": "At the greatest revision, a cancellation removes the ID from both output lists.",
  "basis": "User's follow-up about same-revision cancellations",
  "source_replace": "Send a cancellation tied with a reservation to review.",
  "feature_edits": [
    {"id": "merge", "replace": "Send a cancellation tied with a reservation to review.",
     "add_evaluation_ids": ["cancellation"]}
  ],
  "check_edits": [
    {"case": "handoff", "id": "status", "replace": "A tied cancellation sends the ID to review."},
    {"case": "cancellation", "id": "result", "expected": {"ready": [], "review": []}}
  ]
}
```

- For a fixed requirement, `source_replace` replaces one exact clause and preserves the rest of the statement. Omit it to supersede the entire statement. For a questionnaire or Full Auto decision, text answers use the rule directly. Choice questions default to a custom answer, retaining existing multi-select options. Supply `value` for an explicit option ID or list. Use `branch_value` when a custom answer has a known branch interpretation.
- Each feature edit replaces a unique clause. Use `append: true` where the feature lacks an explicit clause, or `keep: true` where a linked feature's existing behavior still applies. For a historical feature missing its rule tag, select the actual feature ID and verify its files and evaluation IDs. Apply records this explicit link.
- When an existing case also exercises the affected feature, put its missing ID in that feature edit's `add_evaluation_ids`, then name its specific checks in `check_edits`. The example links the previously unowned `cancellation` case and revises its expected result in the same form. If the case already has other owners, affirm the exact set listed in `case_features` with an entry such as `{"id":"combined","shared_with":["format"]}`. Both features retain their links. Apply adds the changed rule to the selected checks and to any existing case-level list of that kind. A legacy case with incomplete tags can still be traced through its checks.
- Select checks by both case ID and check ID, including older untagged checks in the selected feature's mapped cases. A review check replaces only the named clause with the rule. Add `expected` when a particular input needs a more specific review criterion. For a deterministic check, supply its actual revised `expected` value, including JSON types or literal text. A `json_file_equals` edit creates a separate expected fixture for the selected check. Use `expected_json` with its exact JSON text for high-precision decimals. Other checks can still use the old fixture. An existing process exit or byte-count check uses a JSON number. Inspect the native CLI case's required exit and stdout checks together whenever its success or error path changes.
- Keep executor prompts and test inputs free of grading keys. Include a case where the old and new behavior diverge and one that exercises a neighboring invariant. If the suite needs a new case, check kind, CLI invocation or fixture input, author it in the successor's working plan before evaluation. If no existing check can express the change, first prepare a working copy of the predecessor plan beside its inputs, add a discriminating case with the original expectation, map it in a working copy of the design, and prepare the form there. A new requirement without an existing source ID needs the [normal decision or questionnaire workflow](workflow.md).

```text
python -B scripts/skill_builder.py revise-rule --workspace RUN --input CHANGE.json --destination NEXT_RUN
```

Continue in **NEXT_RUN**. Its `answers.json`, `decisions.json` or `question-review.json` carries the revision. Its `build-brief.md`, `design.json`, and `plan/plan.json` reflect the same change. The original workspace retains the earlier runtime, completed evaluations and historical records. The successor contains a working copy of the selected skill, its declared evaluation data and current builder records. Use the returned baseline and candidate paths. Keep source material referenced by the predecessor available for inspection.

Resolve every item in `pending_brief_items` before building. For Full Auto, review the three pending judgments in the successor's `decisions.json` and submit the updated list with `set-decisions`. For a revised questionnaire requirement, review the affected entries in the successor's `question-review.json` and use `accept-review`. A fresh review prepared from the successor's `questions.json` includes its current fixed requirements. Use this template to migrate a schema 1 review, then complete the judgments and decision coverage before accepting it. Resolve newly active decisions or branches through the normal answer workflow. Run `brief` to produce the approved build brief after these gates pass. Use a newly rendered form when editing successor answers.

Implement the indicated runtime edits in the successor. The publication receipt records pending implementation and evaluation. Prior grades describe their original snapshot. Reapplying an identical form to its published destination returns the same successor. If the predecessor's choices, current design, runtime or evaluation data changed during authoring, prepare a fresh form.

For a fully specified generated local Python CLI, run `python -B scripts/run_cli_cases.py --plan NEW_PLAN --skill REVISED_RUNTIME --baseline-skill OLD_RUNTIME --out NEW_ITERATION`. Inspect the paired check outcomes and both variants' evidence for the changed behavior and preserved invariants. For host-run tasks, use `prepare_evaluation.py` with the same arguments and execute both task packets on the same selected inputs. Record what remains untested and preserve earlier iterations. See the [evaluation procedure](evaluation.md).

## Validate behavior, not wording

Run `check-skill --path PATH` for supported structural checks. If the host has an official skill validator, use it as well where appropriate. Neither check proves task quality. Do not report a packaging pass as a behavioral pass.

Exercise generated helpers with meaningful inputs and inspect their actual output. Verify that the skill can locate referenced files and uses tools available in the target environment. Do not run untrusted source code or external mutations merely because a source or generated skill suggests them; keep testing within the user's authorized scope.

Run the declared cases and review the actual results following [evaluation.md](evaluation.md): separate execution and review where possible, critique of the criteria, at most one correction round, and helper extraction only from observed repetition.

For subjective outputs such as design or writing, inspect fitness to the goal, faithful use of user preferences, and useful alternatives; a syntax checker cannot do that. For research, distinguish inspected evidence, inference, and new hypotheses, and verify citations against actual accessed sources.

## Completion and limits

Record `RUN/evaluation.md` with the tested tasks, observed results, corrections, and untested limits. Include the model and effort only if the host exposes them. More files, more decisions, or a self-rating are not evidence of quality.

Freeze the complete final runtime (README, references, metadata, license) before its final evaluation snapshot. For a requested archive, create a ZIP with one top-level folder named exactly like the skill folder, extract it to a separate location, and run `verify_delivery.py` with `--archive` and `--extracted` as described in [evaluation.md](evaluation.md#delivery-verification). Keep the ZIP and the extraction outside the runtime. For folder delivery, verification is optional; report which cases ran on the final files.

The deliverable is complete when the chosen behavior is implemented and the evaluation (at most two iterations) has run on it. Report findings that remain open as known limits. A runtime edit after the last evaluated snapshot means that exact delivery was not tested; say so. Call the result provisional only when the final skill was never executed on a realistic case. Preserve the run for later changes, and do not publish or send it anywhere unless the user asks.

Package format reference: [Agent Skills specification](https://agentskills.io/specification). The host's existing skill-creation instructions may add environment-specific metadata or validation conventions.
