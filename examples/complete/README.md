# From notes to a weekly-update skill

This small public example follows the whole authoring path: a goal, inspected subject material, four design questions, selected decisions, a usable skill, and evaluation cases. All project inputs are fictional. The outputs and evaluation below are recorded historical evidence, not a fresh model run for each release or a benchmark against another builder.

1. Read the [goal, source notes, and question review](research.md).
2. Inspect the [questionnaire](questionnaire.json). The clarification question is conditional, so the selected path has three active questions.
3. Follow the [selected decisions and their effects](decisions.json) into the finished [weekly-team-update skill](weekly-team-update/SKILL.md).
4. Try the skill with the [routine notes](inputs/routine.md) and [contradictory notes](inputs/conflicting.md). Both include uncertainty that a polished draft must preserve.
5. Inspect [the observed evaluation report](evaluation-report.md), [its machine-readable form](evaluation-report.json), and [the evidence manifest](evaluation.json). `not_run` means no result has been supplied; it is never counted as success.

## Recreate the answered questionnaire

From the repository root, use a fresh directory for this historical preview. The `--review-policy legacy` flag lets you replay the example's recorded choices. For a new skill, keep the default review policy and follow the [question review procedure](../../any-skill-builder/references/question-review.md).

```sh
python -B any-skill-builder/scripts/skill_builder.py init --workspace ../example-runs/team-update --goal "Create a weekly team-update skill from supplied project notes" --mode questionnaire --review-policy legacy
python -B any-skill-builder/scripts/skill_builder.py set-questions --workspace ../example-runs/team-update --input examples/weekly-update-questionnaire.json --rebind-project
python -B any-skill-builder/scripts/skill_builder.py recommend --workspace ../example-runs/team-update
python -B any-skill-builder/scripts/skill_builder.py render --workspace ../example-runs/team-update
python -B any-skill-builder/scripts/skill_builder.py brief --workspace ../example-runs/team-update
```

The commands replay the recorded recommendations, render the form, and write `build-brief.md` in the run directory. To try your own answers, run only `init`, `set-questions`, and `render`. Open the HTML path printed by `render`, choose **Save answers**, and return to chat with the saved file. The agent imports your answers and fills the blanks before creating the brief.

For a Full Auto build, use `--mode auto` and record the choices with `set-decisions`. See the [Full Auto workflow](../../any-skill-builder/references/workflow.md#full-auto-decision-list).

The explicit `--rebind-project` option adapts this authored fixture to the new project's name and preserves the initialized mode. It must not rebind exported answers or an established run. The decisions in this folder are readable authoring evidence, not a canonical response export with a reusable run identity.

## Exercise the finished skill

Give a fresh agent only the skill and one raw input file. For example:

> Use `weekly-team-update/SKILL.md` to fulfill the request in `inputs/conflicting.md`. Return the draft itself.

Save its actual response in an evaluation workspace, then record the case result and evidence. A separate reviewer should inspect the response against the checks. Do not rewrite the output to fit expected assertions and call it an independent result. The [design review input](inputs/design-review.md) evaluates the questions and decision mapping separately from the skill's prose.

Copy this `complete` directory to an evaluation workspace outside the repository, for example `../example-runs/complete`. Keep the manifest, inputs, and output evidence together. The evaluator runs without a model call or extra dependencies:

```sh
python -B any-skill-builder/scripts/evaluate_skill.py --manifest ../example-runs/complete/evaluation.json --out ../example-runs/complete/evaluation-report
```

This example includes recorded independent forward outputs for the routine and conflicting requests, plus a separate design review. A fresh agent received only the finished skill and raw request files; it did not receive the assertions. Another agent inspected the resulting artifacts and recorded seven reviewed judgments. Two exact-link checks were then executed by the helper. All nine recorded checks passed; the [execution note](execution.md) states the limits. Model, effort, and budget fields remain unknown rather than guessed. There is no no-skill baseline, no executed alternate design, and no claim of general quality or superiority to another builder.
