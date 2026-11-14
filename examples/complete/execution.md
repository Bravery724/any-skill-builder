# Observed example execution

On 2026-11-14, an independent host agent read only `weekly-team-update/SKILL.md` and the raw `routine` and `conflicting` requests. It wrote the two files in `outputs/` directly. Those outputs were not rewritten to fit the checks.

A second agent inspected the actual outputs, source notes, questionnaire, selected decisions, and finished skill. It completed `inputs/design-review.md` and recorded seven reviewed judgments with exact evidence quotations. The artifact helper separately executed two exact-link assertions and validated the quoted evidence. The report records nine passing checks, separated by automatic and reviewed method.

This demonstrates these two fictional tasks and a design review. It does not establish a cross-domain success rate, deployment safety, trigger accuracy, or superiority over another builder. The alternate `clarify-first` path was inspected as a design consequence, not independently executed. No no-skill baseline was run. The host did not expose sufficient model, reasoning-effort, or budget metadata for a controlled comparison; those fields remain null.

The fictional `example.invalid` references are source-preservation fixtures, not live material that was verified. The design review identifies recipient authorization for mixed-access updates as an unaddressed scope decision. Source research and original proposals are separated in `research.md`; this small example is not an exhaustive requirements analysis.

During release preparation, existing text artifacts and the evaluation manifest were normalized to LF line endings to match Git's checkout policy. The helper regenerated the saved report from the same outputs and review evidence so its byte counts and hashes match the distributed files. This was an artifact consistency correction, not a new model run or a new independent review.
