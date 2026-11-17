# Korean shift handoff regressions

Use these two user tasks with a generated shift handoff skill. Its design brief calls for a Korean handoff with three sections in order (`미해결`, `다음 행동`, `완료`), `없음` in empty sections, ticket IDs beside related items, and source attribution for conflicting claims. Show only explicitly assigned owners and deadlines. Mask personal addresses as `[비공개]` and preserve explicitly shared mailboxes.

From the repository root, substitute the generated skill's directory and a fresh iteration directory outside it.

```text
python -B any-skill-builder/scripts/prepare_evaluation.py --plan tests/fixtures/field-preservation/plan.json --skill GENERATED_SKILL --out ITERATION
```

Give each executor its `ITERATION/tasks/execute-candidate-*.md` packet, the designated snapshot and its raw notes. Have a reviewer compare the actual handoff with those notes using the criteria in the manifest. Record the judgment, reason and quoted evidence in `ITERATION/evaluation.json`, then run the report.

```text
python -B any-skill-builder/scripts/evaluate_skill.py --manifest ITERATION/evaluation.json
```

## Calibrating a reviewer

Present the six outputs under `controls/` to the reviewer with neutral labels. Share only the corresponding case, its raw notes and the criteria. Compare the results with `calibration.json` after review. A new run can express the same facts in different words and a different order. The saved quotes identify evidence in the respective controls.

| Case | Output | Source | Expected observation |
| --- | --- | --- | --- |
| OPS | ops-aliases | Archived packet 2a9141ee71 | Two aliases obscure who reported recovery and who reported continued delay. |
| OPS | ops-attributed | Archived packet 308da34107 | Each named speaker is linked to the correct observation. |
| OPS | ops-swapped | Edited ops-attributed | Both names are present but the reports have traded speakers. |
| DB | db-unnamed | Archived packet a32452762f | 대호 appears under DB-086. DB-092 masks the address but omits the private recipient's name. |
| DB | db-addressed | Archived packet 2ac7c0ac5c | Both destinations are explicit and the private address is masked. |
| DB | db-wrong-recipient | Edited db-addressed | Both names appear but the action routes the private copy to 서윤. |

The source notes and four archived outputs come from the fictional November 2026 handoff evaluation. The offline test replays their evidence and the two edited controls. A fresh skill execution and reviewer judgment are needed to assess a new build. See the [evaluation workflow](../../../any-skill-builder/references/evaluation.md) for recording execution and review evidence.
