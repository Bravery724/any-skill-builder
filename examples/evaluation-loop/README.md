# An evaluation finding and a fresh rerun

These are actual outputs and Markdown reports from the v0.4.0 workflow check on 2026-11-15. Each iteration used a fresh-context executor for two tasks and a separate fresh-context reviewer. Only selected public artifacts are included here; machine-specific task packets and execution logs remain outside the release.

Both iterations used the same historical [weekly-update skill](../complete/weekly-team-update/SKILL.md) and fictional raw [routine](../complete/inputs/routine.md) and [conflicting](../complete/inputs/conflicting.md) inputs. The executor received the task, skill, and raw input without the grading criteria. These are new outputs, not the earlier recorded example outputs.

| Iteration | Actual outputs | Recorded review |
| --- | --- | --- |
| 1 | [Routine](iteration-1/routine.md), [conflicting](iteration-1/conflicting.md) | [Report](iteration-1/report.md): seven task checks passed, but the reviewer identified two missing outcome checks. Workflow remained `needs_attention`. |
| 2 | [Routine](iteration-2/routine.md), [conflicting](iteration-2/conflicting.md) | [Report](iteration-2/report.md): nine checks passed after strengthening coverage; no material critique findings in this scope. Workflow was `reviewed`. |

The missing checks concerned retention of the onboarding workstream and the completed progress indicator. The first outputs already contained those facts; the problem was that omission would not reliably fail the criteria. The second iteration adds explicit coverage and executes the tasks again. The skill is unchanged, so the increased check count is **not** a measured quality improvement. The public [preparation plan](../evaluation-plan.json) includes the strengthened criteria.

Reports and outputs are copied with normalized line endings, without rewriting their prose. Report titles retain the initial plan label “unexecuted”; execution status and actual results are recorded in their rows. The public preparation plan now uses a neutral title so it remains appropriate after execution.

Both reuse inspections found contextual writing work, with no useful repeated deterministic operation that warranted a helper. No extraction was invented for this example. Code tests separately cover evidence and validation required for an extraction record.

Model and effort were unknown; there was no no-skill baseline or cross-builder comparison. Review independence was observed through separate agent dispatch, while the helper checks supplied evidence rather than authenticating agents. See [validation scope](../../docs/evaluation-validation.md).
