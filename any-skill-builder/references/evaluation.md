# Evaluate questions and the generated skill

Use this guide after drafting a questionnaire or creating a skill. Evaluate the actual decisions and task results, not the number of files or questions. Keep evaluation records in the run directory, outside the installed skill. The host produces outputs and reviews them; `scripts/evaluate_skill.py` checks saved evidence and assembles a reproducible report. It does not call a model, launch another skill, execute commands from a manifest, or certify overall quality.

Use [evaluation-loop.md](evaluation-loop.md) to plan cases before implementation and conduct actual execution, separate review, evaluation-quality critique, correction, and rerun. This reference defines the saved evidence format and reporting behavior.

## Choose useful cases

Separate three kinds of evidence:

| Category | What to establish | Suitable evidence |
| --- | --- | --- |
| `mechanics` | The package, helper, or requested invocation works | Actual helper output, a host execution record, or a parsed result |
| `question_quality` | The questions discover material choices without needless repetition, and decisions affect the design | A review of the goal, inspected sources, questionnaire, answers, and resulting design |
| `skill_output` | The generated skill produces useful, accurate results under its selected constraints | Results from normal, failure, and alternative-decision cases |

For question quality, inspect whether important decisions are covered, whether the user already supplied an answer, whether each question changes a behavior, and whether evidence actually supports its recommendation. Check one important alternative answer against the resulting design or output. Record the relevant `question_ids`; these annotations help trace a judgment but do not prove coverage automatically. A text match or a large question count cannot pass a question-quality review.

For the finished skill, use a normal task, a relevant edge case, and a case affected by a material design choice. An independent agent can use the skill with only the request and raw input. Do not supply the expected answer to that agent. Review its actual outputs, preserve failures, make justified corrections, and run affected cases again in a new run record. Do not turn a demonstration into a claimed comparison against another tool.

If invocation matters, include relevant requests that should and should not select the skill. Exercise the actual host, preserve its invocation record, and record the observed result as a reviewed `mechanics` check. This helper does not optimize descriptions or simulate a host's skill selection.

## Save a small evaluation manifest

Use `evaluation.json` in a dedicated evaluation directory. All input and output references are relative to that directory, use `/` separators, and must remain inside it, including resolved symlinks. The helper reads UTF-8 text and JSON assertions; reviews may also reference inspected image or other binary artifacts. It never downloads a reference. Files are limited to 16 MiB each; there is no fixed case, check, or run count. For larger raw inputs, save a relevant excerpt or a separate inspection record and describe the omitted material.

This is an initial plan, not a passing result. Save the actual `inputs/notes.md` before running it:

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
        {
          "id": "no-invented-date",
          "category": "skill_output",
          "kind": "not_contains",
          "artifact": "output",
          "text": "ships on November 20"
        },
        {
          "id": "uncertainty-is-useful",
          "category": "skill_output",
          "kind": "review",
          "criterion": "The update explains what is unconfirmed and what action would resolve it.",
          "question_ids": ["q-uncertainty-policy"]
        }
      ]
    }
  ],
  "runs": [
    {
      "id": "candidate-1",
      "variant": "with_skill",
      "context": {"model": null, "effort": null, "tools": null, "budget": null},
      "cases": [
        {"case_id": "uncertain-date", "status": "not_run", "reason": "Forward execution is pending."}
      ]
    }
  ]
}
```

Each case has a stable `id`, the real request in `prompt`, input files, and checks shared by every run. A run has an `id`, `variant` (`baseline` or `with_skill`), execution context, and per-case records. Missing case records remain `not_run`; they are not silently dropped. Record unavailable model or effort information as `null`, never a guessed value. `tools` is a list of the available tool names/versions, or `null` if unknown; an empty list means no tools. `budget` is a precise text description of assigned limits, such as `max_tokens=4000; max_tool_calls=8`, or `null`.

After an actual execution, replace the case record with `status: "completed"`, an `artifacts` map of names to saved paths, and any reviewed judgments. A completed execution is different from a passed check. For example, a real output could be saved as `artifacts: {"output": "outputs/candidate-1.md"}`. Keep the executed skill/version and host transcript with the artifacts when they matter to reproducibility. The tool hashes all registered artifacts and case inputs. It cannot independently authenticate how they were produced.

## Checks and reviews

Automatic assertion kinds are deliberately small:

- `contains`: a named artifact must contain nonempty `text`, with exact case and Unicode.
- `not_contains`: the named artifact must not contain `text`. A missing or empty artifact fails, so an absent answer cannot pass a negative assertion.
- `json_equals`: the named UTF-8 JSON artifact must have an exact value at `path`, a list of object keys or nonnegative array indices. Set `expected` to the required JSON value. An empty path checks the whole document. Booleans are distinct from numbers.
- `review`: the host or an independent reviewer inspects the `criterion`. It is recorded separately from automatic checks. All `question_quality` checks must use this kind.

Text assertions establish only specific facts about an artifact. A paragraph containing the right phrase can still be misleading or unhelpful. Use reviewed criteria for reasoning, source support, question usefulness, visual quality, and whether a selected answer changed behavior as intended.

A completed case may supply reviews keyed by check ID:

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
      "evidence": [
        {"artifact": "output", "quote": "The date is unconfirmed; ask the release owner to confirm it."}
      ]
    }
  }
}
```

The quoted passage above is illustrative. Use only a passage present in the actual saved output. A `pass` or `fail` review requires a named reviewer, a specific reason, and at least one evidence item. Quotes must be found in the referenced UTF-8 artifact. For visual or other non-text evidence, use `{ "artifact": "image", "note": "What the reviewer actually observed and where" }`; the file must exist and its hash is recorded. An inspection note remains a reviewer claim, not automated image analysis. Do not record a review as passed merely because its evidence file exists.

Use `status: "not_run"` with a reason for an unperformed review. Missing reviews remain untested. Invalid references or fabricated quotations are rejected rather than converted into passing evidence. Include failed judgments and corrections; a report should explain what still needs attention.

## Execution, evaluation critique, and reuse records

The following fields extend schema version 1 without changing older manifests. Use them for the prepared evaluation loop in [evaluation-loop.md](evaluation-loop.md). Older manifests that omit them retain their existing report format and do not retroactively acquire evidence of independent review.

A completed case may add `execution` with `executor`, `relationship`, and `transcript`. The transcript value names a registered entry in that case's `artifacts` map. Save an actual execution record before referencing it. The relationship is `independent`, `self`, or `unknown`: for execution, independent means a fresh context separate from the skill author; self means the author's context. Names alone do not establish independence.

The same case may add `eval_feedback`:

| State | Fields |
| --- | --- |
| Not inspected | `status: "not_run"`, `reason` |
| Inspected | `status: "completed"`, `reviewer`, `relationship`, `summary`, `findings` |

For feedback, `independent` means separate from both the author and executor; `self` means the author or executor reviewed the results; `unknown` means that relationship is unavailable. Record the actual relationship rather than copying the preferred label from a task packet.

Each finding contains `kind` (`weak_check`, `missing_check`, or `unsupported_claim`), a specific `reason`, and nonempty `evidence` using the existing artifact-plus-quote or artifact-plus-note format. An optional `check_id` must refer to a check in that case. Findings describe unresolved issues in that iteration; do not erase them after a later fix. An empty findings array requires an actual completed review and summary. It means no material issue was found in that review's scope, not that the criteria are universally sufficient.

At the manifest root, `reuse_review` records inspection of repeated operations. It is either `{ "status": "not_run", "reason": "..." }` or a completed record containing `reviewer`, `relationship`, `summary`, `inspected_runs`, and `items`. Use actual run IDs in `inspected_runs`; each must include a completed case. Empty `items` is valid when the completed inspection found no useful reusable operation.

Each reuse item has:

- `id`, `operation`, `decision` (`extract` or `keep_inline`), and `reason`.
- `occurrences`: evidence from at least two distinct completed `(run_id, case_id)` pairs. Each entry names `run_id`, `case_id`, and a registered `artifact`, with either an exact `quote` or an inspection `note`.
- For `extract`, `helper`: the `run_id`, `case_id`, and registered `artifact` of the actual helper, plus a nonempty `validation` list of references containing `run_id`, `case_id`, and `check_id`. Every referenced check must have actually passed.

Use `keep_inline` when the observed operation should remain task-specific. If inspection or verification has not occurred, use a pending review and preserve the prospective decision in revision notes rather than recording a completed extraction. After extraction, prepare a new candidate iteration, execute genuine affected cases, and cite that iteration's observed helper use and integration checks. Earlier discovery records remain in the previous iteration. The minimum structural evidence does not prove that the helper was useful or integrated correctly; the reviewer must inspect the operation and relevant results.

`prepare_evaluation.py` also writes root-level `snapshots`: each snapshot has an `id` and `files` entries containing a relative `path` and SHA-256 value in `sha256`. The evaluator verifies these bytes and protects them from report overwrite. Treat snapshots as frozen execution inputs; revise the working skill and prepare a new iteration instead of editing an old snapshot.

The extended report separates its `workflow` summary from ordinary output checks. `workflow.disposition` is `needs_attention` when the evaluation critique reports issues, `incomplete` when recorded reviews remain unperformed or a completed case lacks its execution record, or `reviewed` when the recorded review work is complete. `pending_execution_records` counts missing provenance separately from `pending_reviews`. `reviewed` is not a claim of successful outputs or independently authenticated execution. Read both the ordinary results and workflow findings. CLI failure or incomplete status includes the workflow disposition; a legacy manifest remains governed by its original checks.

## Run and compare

From the repository root, for a run stored in a sibling directory:

```sh
python -B any-skill-builder/scripts/evaluate_skill.py --manifest ../runs/example/evaluation/evaluation.json
```

From an installed skill, resolve `scripts/evaluate_skill.py` relative to its `SKILL.md`. The default reports are `evaluation-report.json` and `evaluation-report.md` beside the manifest. Use `--out PATH_PREFIX` for another prefix inside that evaluation directory. An existing different report requires `--overwrite`; input files, artifacts, and the manifest can never be overwritten by report generation.

Exit codes: `0` means all recorded checks passed and any recorded workflow reviews are complete without open findings; `1` means at least one check failed, including a baseline failure, or an evaluation critique has unresolved findings; `2` means invalid records or a file error prevented evaluation; `3` means checks or requested workflow reviews remain unperformed and there are no failures or open findings. Reports retain failures and pending work. A deliberate baseline failure is evidence to inspect, not a broken evaluator. An earlier iteration keeps its findings even when a later iteration records a successful correction.

For a comparison, run the same shared case requests and inputs with and without the skill. Record the actual available model, reasoning effort, tools, and assigned budget in both run contexts. The helper reports `not comparable` if those fields are unknown or differ. It compares only check pairs exercised in both runs; missing reviews and unrun cases never count as wins. It reports changed assertion outcomes, not a general quality score or statistical claim. Inspect both outputs, preferably without revealing which version produced them to the reviewer.

Matching declared context does not prove that execution was fair: the host still needs to preserve the actual prompts, skill version, execution records, and relevant environmental constraints. Reusing a final answer as a baseline, guessing unavailable metadata, or writing a desired output into an evidence file does not establish an improvement. Several small successful cases do not establish superiority across subjects or against another tool.

Use the report to choose the next correction. If the issue is an omitted decision, revise the questions; if it is a wrong implementation of a selected answer, revise the generated skill; if it is unavailable evidence or a host limitation, keep that limit explicit. Preserve both the earlier and corrected run records so later changes can be assessed against the same cases.
