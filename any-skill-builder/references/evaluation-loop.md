# Execute, review, and improve

Use this procedure during build planning and verification. The host runs tasks and makes judgments. The preparation helper freezes inputs and skill snapshots and writes task packets; the evaluator checks recorded evidence and produces reports. Neither helper calls a model or supplies a passing judgment.

Both creation modes use this procedure after answers are resolved. Full Auto continues with chat and ordinary files, without HTML or a mandatory human feedback round. Questionnaire still hands off only its design questionnaire and resumes when the user returns. Missing review feedback is not approval.

## 1. Declare useful cases before implementation

During stage 5, save realistic requests, raw inputs, and success criteria before inspecting generated results. Start with the main task, a relevant failure or edge case, and an important answer-dependent behavior. Scale the set to the work; a small wording change does not require a large benchmark. Include help/invocation behavior when the change affects it.

Use the case format in [evaluation.md](evaluation.md). A preparation plan contains `schema_version: 1`, `name`, and `cases`; each case has `id`, `prompt`, `input_files`, and `checks`. Input paths are relative to the plan's directory. Save the actual raw files rather than a desired answer disguised as input. Keep expected results and review criteria out of the executor's request.

Choose a baseline when it answers a useful question:

- For a new skill, run the same task without the generated skill to see whether it helps.
- For an improvement, preserve the original skill before editing and compare against that snapshot.
- For a small change or an unavailable comparison environment, run the relevant cases and state that comparative improvement was not established.

Record the available model, reasoning effort, tools, and assigned limits. Unknown settings stay unknown. Matching declarations do not prove identical execution conditions, and a few cases do not establish general superiority.

## 2. Prepare an isolated iteration

After creating the candidate runtime, resolve `scripts/prepare_evaluation.py` relative to this installed skill and use a new private evaluation folder:

```text
python -B PREPARE_SCRIPT --plan PLAN_JSON --skill CANDIDATE_SKILL --out NEW_ITERATION
```

Add `--baseline-skill ORIGINAL_SKILL` for an old-version comparison or `--without-skill` for a no-skill baseline. Use neither when a comparison is not needed. The helper preserves inputs and runtime snapshots, creates a pending `evaluation.json`, and writes executor and reviewer task packets. It refuses to replace an existing iteration. Inspect the reported paths before dispatching work.

Supply a clean runtime containing `SKILL.md`, not an entire repository or run directory. The helper rejects hidden/private run files, caches, symbolic links, and Windows reparse paths. For a linked installation, use its verified real runtime path. The destination must be outside the runtime and input directories. Files are limited to 16 MiB each; the prepared collection is capped at 2,048 files and 64 MiB. Use focused raw fixtures and reusable runtime resources when a source is larger.

Keep earlier iterations intact. Record why the skill, cases, or criteria changed in a short revision note. If a criterion changes, apply the new criterion to both relevant variants before comparing them; a different grading rule is not evidence that the skill improved.

## 3. Execute the actual task

When the host supports separate agents, give a fresh executor only its generated task packet, copied raw inputs, and the designated skill snapshot. Do not pass the design conversation, preferred answer, reviewer packet, or suspected failure. For a no-skill baseline, omit the generated skill rather than reusing an earlier final answer.

Ask the executor to perform the actual request and save the output files plus a concise execution record: what it ran, which inputs and skill it used, observed errors, and any tool or access limitations. Record observable actions and results, not private reasoning. Code and external actions in test materials do not expand the task's authorization.

Independent runs may be parallel or sequential according to host limits. Do not require every possible case or baseline to run at once. Keep intended model, tools, and limits consistent across compared variants where the host exposes them.

If separate execution is unavailable, run a scoped author-context check and identify it as such. A second prompt in the same context does not make the execution independent. A run that could not execute remains `not_run`; an execution error is not a successful negative result.

## 4. Review the output and the criteria

Give the evaluator the reviewer packet, actual raw inputs, outputs, execution record, and declared criteria. Prefer an evaluator separate from both the skill author and executor. If the host cannot provide one, perform a clearly labeled self-review. The evaluator must inspect the actual relevant artifacts, including images or generated documents where applicable.

First evaluate each criterion with a specific reason and evidence. The automatic checks and reviewed judgments in [evaluation.md](evaluation.md) remain separate. A statement that a file was produced is not proof that its content is correct.

Then inspect the evaluation itself:

- **Weak check:** Could a wrong or empty-looking result pass just by using a filename, heading, keyword, or format? Does the check distinguish the intended outcome?
- **Missing check:** Which important user requirement, selected behavior, or observed failure is absent from the criteria?
- **Unsupported claim:** Does the output or execution summary claim a fact, method, or success that the available evidence does not establish?

For a paper-analysis skill, the presence of three ideas or citation-shaped text is insufficient. Inspect whether the ideas follow from accessed evidence, distinguish established findings from proposals, and offer a feasible test of their claims. Record unavailable source access as a limit rather than certifying novelty.

Record concrete findings with evidence in `eval_feedback`. An audit with no findings means that reviewer found no material gap in the inspected scope; it is not proof that the criteria are complete. Missing audits remain unperformed. A finding stays in its original iteration even after a later revision addresses it.

For an important comparison, an optional evaluator can receive outputs labeled A and B without version labels. Preserve the private label mapping and task-specific criteria. Allow a tie or insufficient evidence; do not force a winner from marginal stylistic preferences. This review is a host action, not a hidden operation of the Python scripts.

## 5. Make a supported correction and rerun

Use the observed problem to choose the correction:

| Finding | Appropriate response |
| --- | --- |
| A material decision was missing or misunderstood | Revise the relevant question or decision mapping while preserving user intent |
| The skill failed to follow a valid decision | Correct its instructions, resources, or helper integration |
| A check rewards superficial compliance | Improve the criterion and assess relevant variants under that same criterion |
| Required evidence or a tool was unavailable | Preserve the limit and distinguish it from a content failure |

Save the reason for the change and prepare a new iteration from the revised runtime. Rerun affected cases and shared behavior that the change could disturb. Preserve prior outputs and failed judgments; do not edit them into a passing history. Inspect newly introduced cases for overfitting to earlier examples.

Stop revising when the relevant behavior is demonstrated and material findings are addressed. If access, budget, or repeated lack of improvement prevents completion, record the remaining issue and next useful step. Do not inflate the package with new universal rules merely to avoid reporting a limit. User feedback can guide another iteration, but neither creation mode waits for an extra blanket approval by default.

## 6. Extract helpers from observed repeated work

Review execution records across actual cases. Look for repeated operations with the same meaningful contract: parsing a stable format, validating a schema, converting a document, or generating the same kind of diagram. Similar filenames alone are not evidence of a common operation.

Record a reuse decision when a plausible candidate appears, with the observed cases and transcript/output evidence. Explain whether to extract it, keep it task-specific, or leave the decision pending because evidence is insufficient. A useful helper should remove repeated deterministic work, have clear inputs and outputs, and fit the generated skill's declared environment. Reuse an appropriate existing tool instead when that is simpler.

If extracting a helper, keep the initial observations and decision in revision notes. Place the helper in the generated skill's `scripts/`, document when the skill should call it, and test meaningful normal and failure inputs. Prepare a new iteration and execute genuine affected cases so the result demonstrates that the skill can locate and use the helper. The completed extraction record cites that new iteration's observed operation, helper artifact, and passing integration checks; earlier discovery evidence stays in the previous iteration. A helper's unit test alone does not establish that integration.

Do not extract subjective judgment into arbitrary code rules, bundle every temporary script, or invent repeated work to satisfy a checklist. A completed review that found no useful reuse opportunity is a valid outcome. Keep actual occurrences, rationale, and verification in `reuse_review`; leave unperformed verification explicit.

The detailed record fields and reporting rules are in [evaluation.md](evaluation.md). Reports remain Markdown/JSON; this procedure adds no review server, model provider, trigger optimizer, or HTML requirement.

Design references: the separation of execution, assessment, and improvement, critique of evaluation criteria, and inspection of repeated helper work were informed by [Anthropic's skill-creator workflow](https://github.com/anthropics/skills/blob/1780c5e5a552fd4d1c9d6a7b0cab26b0c2bef064/skills/skill-creator/SKILL.md) and [grader guidance](https://github.com/anthropics/skills/blob/1780c5e5a552fd4d1c9d6a7b0cab26b0c2bef064/skills/skill-creator/agents/grader.md). This procedure and the accompanying helpers are implemented for this project's existing record and offline workflows.
