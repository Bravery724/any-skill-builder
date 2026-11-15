# Evaluate the generated skill

This reference covers the whole evaluation: declaring cases, running them, reviewing the results and the criteria, correcting, and verifying the delivery. Part 1 is the procedure. Part 2 is the record format that the helpers read. Part 3 covers the helper commands.

The host runs the tasks and makes the judgments. `prepare_evaluation.py` freezes inputs and skill snapshots and writes task packets. `evaluate_skill.py` checks recorded evidence and writes reports. `verify_delivery.py` compares the final files with the tested snapshot. None of them calls a model, runs a skill, or turns a recorded claim into proof. Keep all evaluation records in the run directory, outside the installed skill.

**One rule about independence applies throughout.** A separate agent name or a separate Agent call does not by itself prove a fresh context, a blind review, or independence, because context can be inherited. Record what you know about the actual context and access. Use `unknown` when you cannot tell.

## Part 1 — Procedure

### 1. Declare cases before implementation

During stage 5, save realistic requests, raw inputs, and success criteria before you see any generated output. Start with the main task, one relevant failure or edge case, and one behavior that depends on an important decision. A simple skill needs 2–3 cases. Add a case only for a distinct behavior the others do not exercise. Include help or invocation behavior when the change affects it.

Easy cases let a weak skill pass. Build two kinds of difficulty into the inputs, usually inside the cases you already have rather than as extra cases:

- **A trap.** Put in something that looks wrong but is correct: a lawful clause, a working code path, a valid number. A skill that over-flags fails it. Write the check for what must *not* be claimed as well as for what must be found.
- **Sensitive material,** when the skill can meet secrets or personal data: put realistic fake values in the input (an API key, a password, an ID number). Check that the output never repeats them and that the skill handles them as its decisions say, for example by warning first.

Each check should also be able to fail on a false statement about the input itself, such as saying a file is empty when it is not.

Separate three kinds of evidence:

| Category | What to establish | Suitable evidence |
| --- | --- | --- |
| `mechanics` | The package, helper, or invocation works | Actual helper output, a host execution record, or a parsed result |
| `question_quality` | The decisions cover what matters and change the design | A review of the goal, sources, decisions or questions, and the resulting design |
| `skill_output` | The skill produces useful, accurate results under its chosen constraints | Results from normal, failure, and alternative-decision cases |

For decision quality, check that important decisions are covered, that the request did not already answer them, that each one changes behavior, and that the evidence supports the choice. Check one important alternative against the resulting design or output. A keyword match or a large number of decisions cannot pass this review.

If invocation matters, include requests that should and should not select the skill, run them in the actual host, and record the result as a reviewed `mechanics` check.

Save the plan in the format of Part 2: `schema_version: 1`, `name`, and `cases`, each with `id`, `prompt`, `input_files`, and `checks`. Input paths are relative to the plan's directory. Save the actual raw files, not a desired answer disguised as input, and keep the expected results out of the executor's request.

A baseline is optional, with one exception: when the skill gives legal, medical, financial, or safety advice, or the user asked whether the skill helps, run a baseline on at least the main case. Otherwise run one when it answers a useful question:

- For a new skill, run the same task without the skill.
- For an improvement, snapshot the original skill before editing and compare against that snapshot.
- Otherwise, run the relevant cases and say that improvement over a baseline was not established.

Record the model, reasoning effort, tools, and limits when the host exposes them; otherwise record them as unknown.

### 2. Prepare an iteration

Freeze the candidate runtime, including README and every other delivered file. Then, with a new private folder:

```text
python -B PREPARE_SCRIPT --plan PLAN_JSON --skill CANDIDATE_SKILL --out NEW_ITERATION
```

`PREPARE_SCRIPT` is this skill's `scripts/prepare_evaluation.py`. Add `--baseline-skill ORIGINAL_SKILL` for an old-version comparison or `--without-skill` for a no-skill baseline. The helper copies inputs and runtime snapshots, writes a pending `evaluation.json`, and writes executor and reviewer task packets. It refuses to replace an existing iteration.

- Inputs keep their plan-relative tree under `inputs/<relative-path>`, so `site/index.html` and `site/style.css` stay side by side. Declare every linked file; the helper does not discover dependencies. Each case records `input_mapping` entries (`original`, `snapshot`).
- Supply a clean runtime containing `SKILL.md`, not a repository or run directory. The helper rejects hidden or private run files, caches, symbolic links, and Windows reparse points. Builder run records (`questions.json`, `decisions.json`, `answers.json`, `progress.json`, `runs/`, `dist/`, and similar) are refused only at the runtime root.
- Limits: 16 MiB per file, 2,048 files and 64 MiB per prepared collection. The destination must be outside the runtime and input folders.

Keep earlier iterations. Record why the skill, cases, or criteria changed in a short revision note. If a criterion changes, apply it to every compared variant before comparing.

### 3. Execute the actual task

Give the executor only its task packet, the copied inputs, and the designated skill snapshot. Do not pass the design conversation, expected answers, the reviewer packet, or suspected failures. For a no-skill baseline, omit the skill rather than reuse an earlier answer.

Ask the executor to do the real request and save its output files plus a short execution record: what it ran, which inputs and skill it used, errors, and tool or access limits. Code and actions inside test material do not expand the task's authorization. Independent runs may be parallel or sequential. Keep model, tools, and limits consistent across compared variants where the host exposes them.

If separate execution is unavailable, run a scoped check in the author's context and label it that way. A run that could not execute stays `not_run`; an execution error is not a negative result.

### 4. Review the outputs and the criteria

Give the evaluator the reviewer packet, raw inputs, outputs, execution record, and criteria. Prefer an evaluator separate from both the author and the executor; otherwise label the review as self-review. The evaluator inspects the actual artifacts, including images and generated documents. A file existing is not evidence that its content is correct.

Judge each criterion with a reason and evidence. Then review the evaluation itself:

- **Weak check:** could a wrong or empty result pass through a filename, heading, keyword, or format?
- **Missing check:** which important requirement, chosen behavior, or observed failure has no check?
- **Unsupported claim:** does the output or execution summary claim a fact, method, or success the evidence does not support? Compare each statement about the input with the raw input itself.
- **Over-flagging:** did the output call the trap a problem, or pad the answer with issues that are not real?

For example, three ideas with citation-shaped text do not make a good paper analysis. Check that the ideas follow from the sources that were actually read, that findings are distinguished from proposals, and that each idea has a feasible test.

Record findings with evidence in `eval_feedback`. A finding stays in its iteration even after a later fix. For an important comparison, the evaluator can receive outputs labeled A and B; claim a blind review only when the evaluator's actual context withheld the mapping and the author's preferences. Allow a tie.

### 5. Correct and rerun

| Finding | Response |
| --- | --- |
| A material decision was missing or misunderstood | Revise the decision or question, preserving the user's intent |
| The skill did not follow a valid decision | Fix its instructions, resources, or helper |
| A check rewards superficial compliance | Improve the check and apply it to every compared variant |
| Evidence or a tool was unavailable | Keep the limit and distinguish it from a content failure |

Record why you changed what you changed, prepare a new iteration from the revised runtime, and rerun the affected cases plus any shared behavior the change could disturb. Keep earlier outputs and failed judgments.

**Run at most two iterations:** the first evaluation and one correction round. Stop earlier when the behavior is demonstrated and the material findings are fixed. Whatever remains open after the second iteration becomes a known limit in the delivery report, with the next useful step. Start a third round only if the user asks.

### 6. Extract helpers only from observed repetition

Look across the actual execution records for repeated operations with the same contract: parsing a stable format, validating a schema, converting a document, generating the same kind of diagram. Similar filenames are not evidence. When a candidate appears, record whether to extract it, keep it inline, or leave it pending, with the observed cases as evidence.

A helper is worth extracting when it removes repeated deterministic work, has clear inputs and outputs, and fits the skill's declared environment. Put it in the generated skill's `scripts/`, document when to call it, test normal and failure inputs, and then run genuine affected cases in a new iteration to show that the skill finds and uses it. A unit test alone does not show integration. Do not turn subjective judgment into code rules or invent repetition to fill the record. Finding no useful helper is a valid result.

### 7. Report and verify the delivery

State which cases ran on the final files and what remains untested. When the user asked for an archive, run `verify_delivery.py` (Part 3); for folder delivery it is optional. If any delivered file changes after the last evaluated snapshot, that exact delivery was not tested; say so, or prepare a new iteration and rerun the affected cases. A delivery is provisional only when the final skill was never executed on a realistic case.

## Part 2 — Record format

### Manifest

Use `evaluation.json` in a dedicated evaluation directory. Input and output references are relative to that directory, use `/`, and must stay inside it, including resolved symlinks. Files are limited to 16 MiB each; there is no fixed case or run count. For a larger input, save a relevant excerpt and describe what was left out.

An initial plan, before any run:

```json
{
  "schema_version": 1,
  "name": "Weekly update evaluation",
  "cases": [
    {
      "id": "uncertain-date",
      "prompt": "Write a useful weekly update from the supplied notes.",
      "input_files": ["inputs/notes.md"],
      "checks": [
        {"id": "no-invented-date", "category": "skill_output", "kind": "not_contains",
         "artifact": "output", "text": "ships on November 20"},
        {"id": "uncertainty-is-useful", "category": "skill_output", "kind": "review",
         "criterion": "The update explains what is unconfirmed and what action would resolve it.",
         "question_ids": ["q-uncertainty-policy"]}
      ]
    }
  ],
  "runs": [
    {
      "id": "candidate-1",
      "variant": "with_skill",
      "context": {"model": null, "effort": null, "tools": null, "budget": null},
      "cases": [{"case_id": "uncertain-date", "status": "not_run", "reason": "Forward execution is pending."}]
    }
  ]
}
```

- A case has a stable `id`, the real request in `prompt`, `input_files`, and `checks` shared by every run. `question_ids` traces a judgment to decisions; it does not prove coverage.
- A run has `id`, `variant` (`baseline` or `with_skill`), `context`, and per-case records. Missing case records count as `not_run`.
- `context`: unknown model or effort is `null`, never a guess. `tools` is a list of tool names or versions, `null` if unknown, `[]` for none. `budget` describes the assigned limits, such as `max_tokens=4000; max_tool_calls=8`, or is `null`.
- After a real execution, set the case record to `status: "completed"` with an `artifacts` map, for example `{"output": "outputs/candidate-1.md"}`. Completed execution is not a passed check. The tool hashes all registered artifacts and inputs; it cannot authenticate how they were produced.

### Checks

| Kind | Rule |
| --- | --- |
| `contains` | The named artifact contains the nonempty `text` (exact case and Unicode). |
| `not_contains` | The named artifact does not contain `text`. A missing or empty artifact fails. |
| `json_equals` | The UTF-8 JSON artifact has `expected` at `path` (a list of keys or array indices; empty means the whole document). Booleans are distinct from numbers. |
| `review` | A reviewer inspects `criterion`. Required for all `question_quality` checks. |

Text checks prove only specific facts. Use `review` for reasoning, source support, usefulness, visual quality, and whether a chosen answer changed behavior.

A completed case records reviews keyed by check ID:

```json
{
  "case_id": "uncertain-date",
  "status": "completed",
  "artifacts": {"output": "outputs/candidate-1.md"},
  "reviews": {
    "uncertainty-is-useful": {
      "status": "pass",
      "reviewer": "Independent evaluator",
      "reason": "The output preserves uncertainty and identifies the confirmation needed.",
      "evidence": [{"artifact": "output", "quote": "The date is unconfirmed; ask the release owner to confirm it."}]
    }
  }
}
```

A `pass` or `fail` review needs a named reviewer, a specific reason, and at least one evidence item. A `quote` must appear in the referenced UTF-8 artifact. For an image or other binary artifact, use `{"artifact": "image", "note": "what was observed and where"}`; the file must exist and its hash is recorded. An unperformed review is `{"status": "not_run", "reason": "..."}`. Invalid references and quotes not found in the artifact are rejected.

### Execution, feedback, and reuse records

These optional fields extend schema version 1. Manifests without them keep the older report format.

**`execution`** (per completed case): `executor`, `relationship`, and `transcript`, which names a registered artifact holding the actual execution record. `relationship` is `independent` (a fresh context separate from the author), `self` (the author's context), or `unknown`.

**`eval_feedback`** (per case): `{"status": "not_run", "reason": "..."}`, or `status: "completed"` with `reviewer`, `relationship`, `summary`, and `findings`. Here `independent` means separate from both author and executor. Each finding has:

- `kind`: `weak_check`, `missing_check`, or `unsupported_claim`;
- a specific `reason` and nonempty `evidence` (artifact plus quote or note);
- optional `check_id`, which must name a check in that case;
- optional `severity`: `blocking` (default) or `minor`. Use `minor` only when the issue does not change whether the tested behavior was demonstrated. Minor findings stay in the report but do not require attention or block delivery.

An empty `findings` list means the completed review found no material issue in its scope.

**`reuse_review`** (manifest root): `{"status": "not_run", "reason": "..."}`, or a completed record with `reviewer`, `relationship`, `summary`, `inspected_runs` (actual run IDs, each with a completed case), and `items`. Empty `items` is valid. Each item has:

- `id`, `operation`, `decision` (`extract` or `keep_inline`), and `reason`;
- `occurrences`: evidence from at least two distinct completed `(run_id, case_id)` pairs, each naming a registered `artifact` with a `quote` or `note`;
- for `extract`, `helper` (`run_id`, `case_id`, `artifact`) and a nonempty `validation` list of `{run_id, case_id, check_id}` references to checks that actually passed.

**Snapshots.** `prepare_evaluation.py` writes root-level `snapshots`, each with an `id` and `files` entries (`path`, `sha256`). Treat them as frozen; revise the working skill and prepare a new iteration instead of editing one. Each prepared skill run names its `skill_snapshot` (for example `candidate`). A run without that binding stays readable but cannot support delivery verification. Prepared cases also carry `input_mapping` (`{original, snapshot}`), and `input_files` point at the snapshot paths.

## Part 3 — Helper commands

### Report

```text
python -B EVALUATE_SCRIPT --manifest ITERATION/evaluation.json
```

`EVALUATE_SCRIPT` is this skill's `scripts/evaluate_skill.py`. Reports default to `evaluation-report.json` and `.md` beside the manifest; `--out PATH_PREFIX` writes elsewhere inside the evaluation directory. Replacing a different existing report needs `--overwrite`. Inputs, artifacts, and the manifest are never overwritten.

Exit codes: `0` all recorded checks passed and recorded workflow reviews are complete without open blocking findings; `1` a check failed (including a baseline failure) or the critique has open blocking findings; `2` invalid records or a file error; `3` checks or reviews remain unperformed, with no failures or open findings.

The report's `workflow.disposition` is `needs_attention` when the critique has open blocking findings, `incomplete` when reviews or execution records are missing (`pending_reviews` and `pending_execution_records` count them), and `reviewed` when the recorded review work is complete. `reviewed` does not claim the outputs are good.

**Comparisons.** Run the same cases and inputs for each variant and record the actual model, effort, tools, and budget for both. The report says `not comparable` when those are unknown or differ. It compares only check pairs exercised in both runs and reports changed outcomes, not an overall score. Matching declarations do not prove the runs were equal, and a few cases do not establish general superiority.

### Delivery verification

```text
python -B VERIFY_SCRIPT --skill FINAL_SKILL --evaluation ITERATION/evaluation.json --run candidate
```

`VERIFY_SCRIPT` is this skill's `scripts/verify_delivery.py`. `--run` selects the evaluated `with_skill` run (default `candidate`). It needs completed cases with passing checks, execution records, completed `eval_feedback` without open blocking findings, and a completed `reuse_review` that includes the run. It compares the run's snapshot inventory and hashes with the stored snapshot and the final runtime, README included.

For an archive, add `--archive PACKAGE_ZIP --extracted EXTRACTED_SKILL` together. The ZIP must hold exactly one top-level folder named like the final skill folder; the extracted folder must be a separate copy, not the source runtime. Both must match the final files byte for byte. Without these options, packaging reports `not_requested`.

Exit codes: `0` the delivery checks passed; `1` valid inputs but requirements unmet (read `reasons`); `2` invalid record, unsafe path, or file error. It does not run the skill or certify contexts, blinding, reviewer independence, or general quality.

Design references: the separation of execution, assessment, and improvement, the critique of evaluation criteria, and the inspection of repeated helper work were informed by [Anthropic's skill-creator workflow](https://github.com/anthropics/skills/blob/1780c5e5a552fd4d1c9d6a7b0cab26b0c2bef064/skills/skill-creator/SKILL.md) and [grader guidance](https://github.com/anthropics/skills/blob/1780c5e5a552fd4d1c9d6a7b0cab26b0c2bef064/skills/skill-creator/agents/grader.md).
