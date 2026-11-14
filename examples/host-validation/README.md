# Host validation evidence

These fictional cases were executed by actual installed hosts on 2026-11-14. See the [validation report](../../docs/host-validation.md) for versions, supervision, question repairs, browser handoff, and limitations.

The [review criteria](criteria.md) were written before generated outputs existed. Each task ran in a fresh context with the frozen generated skill and its own input. The authoring host did not receive the hidden criteria. Public files preserve the recorded text with normalized line endings.

| Case | Input | Claude Code output | Antigravity CLI output |
| --- | --- | --- | --- |
| Normal assignments and a dependency | [Normal](inputs/normal.md) | [Actual output](claude/outputs/normal.md) | [Actual output](antigravity/outputs/normal.md) |
| Missing owners and dates | [Missing](inputs/missing.md) | [Actual output](claude/outputs/missing.md) | [Actual output](antigravity/outputs/missing.md) |
| Conflicting records and a cancelled deadline | [Conflicting](inputs/conflicting.md) | [Actual output](claude/outputs/conflicting.md) | [Actual output](antigravity/outputs/conflicting.md) |

Claude's generated package: [SKILL.md](claude/meeting-action-list/SKILL.md), [usage guide](claude/meeting-action-list/README.md), and [export reference](claude/meeting-action-list/references/export-schema.md). All three cases passed an independent review against the predefined criteria. The host's self-evaluation was recorded separately and is not counted as fresh behavioral evidence.

Antigravity's generated package: [SKILL.md](antigravity/meeting-action-list/SKILL.md) and [usage guide](antigravity/meeting-action-list/README.md). The linked final responses come from repeated fresh-context regressions after a targeted readability refinement; all three retain substantive behavior and manual choices. Independent review means a separate AI reviewer/context. See the report for remaining wording limitations.

For a before/after comparison, the [earlier missing-details response](antigravity/before-readability/missing.md) and [earlier conflicting-details response](antigravity/before-readability/conflicting.md) show the repetition that prompted the writing change. They belong to the previous instruction version and are not outputs of the final published skill.

To reproduce, install the generated package in a fresh project for the same host, invoke it with one input, and save the actual response. Keep the other inputs and criteria outside that execution context until review. Compare meaning and traceability rather than requiring identical wording. A different model, setting, or run may produce different results. These examples are evidence snapshots, not extra skills installed by the builder's Python installer.

Install one host's example variant at a time when reproducing: both use the name `meeting-action-list`. When installing the builder through the Skills CLI, retain `--skill any-skill-builder` to select only the builder.
