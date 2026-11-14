# README demo

[Watch the GIF](assets/demo.gif) · [Static questionnaire](assets/questionnaire.jpg) · [Complete example](../examples/complete/README.md)

The GIF is an edited replay of the fictional weekly-update example with the current standalone questionnaire. Request, continuation, and result panels summarize the workflow; the questionnaire and saved HTML step use the actual renderer. Timing is condensed. It does not show a new model researching and building a skill in the animation's running time.

## What is shown

| Stage | Content and evidence |
| --- | --- |
| One request | “Create a skill that turns project notes into clear weekly updates.” |
| Questionnaire | The saved goal and related questions appear as cards. The example includes one conditional follow-up. |
| Answer and save | The recorded choices are entered, then Save answers downloads a standalone HTML containing them. |
| Continue in chat | A presentation panel explains returning with the saved HTML. It is not a claim that downloading wakes an agent. |
| Finished skill | Excerpts from the existing `weekly-team-update/SKILL.md` show audience context, uncertainty, and source links beside supported claims. |

The replay uses these recorded choices:

- Readers: teammates and cross-functional partners.
- Evidence: beside the relevant claim.
- Missing information: draft now and mark what is uncertain.

These match [the historical decisions](../examples/complete/decisions.json). The clarification-first branch remains inactive. The final skill excerpts come from the [actual existing skill](../examples/complete/weekly-team-update/SKILL.md).

The **nine recorded checks** are two automatic checks and seven reviewed judgments in [the existing evaluation report](../examples/complete/evaluation-report.md). They are not a fresh evaluation, nine automated model tests, or a quality comparison with another builder. Read [the execution note](../examples/complete/execution.md) for scope.

## Reproduce the questionnaire

Use the current [weekly-update questionnaire fixture](../examples/weekly-update-questionnaire.json). It copies the historical question content into the current Questionnaire mode while preserving the original evidence files. Follow [the walkthrough](../examples/complete/README.md#recreate-the-answered-questionnaire). Omit the recommendation-filling step if you want to answer it yourself.

The preview uses only reviewed fictional data. No user browser account, private research, real responses, or machine-specific paths should appear in the published media. The example's `example.invalid` source links are fixtures, not verified live sources.

The GIF loops. Use the static preview or written walkthrough if motion is inconvenient or the text is hard to read.

The refreshed recording is approximately 21 seconds, 900 × 990 pixels, and 542 KiB. Its actual saved HTML was inspected to confirm the three recorded choices. The current browser renderer produced the static screenshot; the surrounding request, continuation, and result panels are explicitly an edited illustration.
