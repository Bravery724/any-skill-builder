# Korean workshop handoff regressions

A facilitator wants a short Korean memo for their next class. Count distinct participant codes separately for each issue, then hide the codes and personal names in the memo. Put the headcount beside its issue and retain the workstation name. For an agreed action whose owner has not been assigned, put the exact text `담당 미정` in the action entry. Preserve assigned roles, delegated responsibilities, and the tentative status of proposals.

## Evaluate a generated skill

Run these commands from the repository root with the candidate skill directory and a new iteration directory. The executor needs its generated task packet, the designated skill snapshot and the raw notes listed in the packet.

```text
python -B any-skill-builder/scripts/prepare_evaluation.py --plan tests/fixtures/workshop-handoff/plan.json --skill GENERATED_SKILL --out ITERATION
```

Have the reviewer compare each count and action entry with the corresponding raw notes. Record their judgment, reason and an exact output quotation per review check in `ITERATION/evaluation.json`. Literal checks also scan the entire memo for supplied names, codes and the required owner phrase. See the [evaluation workflow](../../../any-skill-builder/references/evaluation.md).

```text
python -B any-skill-builder/scripts/evaluate_skill.py --manifest ITERATION/evaluation.json
```

## Replay the controls

The pottery and woodwork notes are the two fictional user inputs from the November 2026 workshop evaluation. Their four controls reproduce the first and revised memos. The dyeing case and its four controls were written for this regression. They can also serve as a held-out task for a new build when the builder and executor have not seen the criteria or controls.

| Case | Control | Observation |
| --- | --- | --- |
| Pottery | `pottery-first` (t17) | Reports “여러 참가자” where the two people contributed three cards. Paraphrases the owner label. |
| Pottery | `pottery-revised` (v37) | Reports two people and places `담당 미정` on bottle numbering. |
| Woodwork | `woodwork-first` (t82) | Correctly distinguishes three people from five cards. Mentions the next assignment meeting but omits the label. |
| Woodwork | `woodwork-revised` (v72) | Reports three people and places the label on installing a drawer. |
| Dyeing | `dyeing-card-counts` | Uses three, four and two cards as the headcounts for three issues. |
| Dyeing | `dyeing-swapped` | Contains the correct set of counts but assigns two of them to the wrong issues. |
| Dyeing | `dyeing-misplaced` | Places the literal on an assigned task, a delegated selection task and a proposal. Omits it from the agreed action that needs it. |
| Dyeing | `dyeing-correct` | Reports two, three and one contributors by issue. Only marking the water container receives the fallback. |

To calibrate reviewers, provide unlabeled controls with the matching raw notes and criteria. Compare their evidence with `calibration.json` after review. The offline suite runs the preparation and evaluation helpers, replays these saved judgments, and checks that leaking each source identity still fails an otherwise correct output. Evaluating a new skill requires fresh execution and review.

```text
python -B -m unittest discover -s tests -p test_workshop_handoff.py -v
```
