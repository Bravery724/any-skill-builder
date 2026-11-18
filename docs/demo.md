# Weekly-update questionnaire demo

[Watch the GIF](assets/demo.gif) · [Static questionnaire](assets/questionnaire.jpg) · [Complete example](../examples/complete/README.md)

The GIF follows the fictional weekly-update example. The questionnaire and saved HTML come from the standalone renderer. Edited panels summarize the request, continuation, and finished skill. The [narrated walkthrough in the project README](../README.md#demo) follows a packing-list skill from the initial request through installation.

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

In the current questionnaire, open **Incomplete notes** to compare two responses to the same conflicting CSV release notes. One option shows the sentence the team would receive in a draft. The other shows the question the writer would ask before drafting. [Questionnaire fixture](../examples/weekly-update-questionnaire.json) · [Fictional project notes](../examples/complete/inputs/conflicting.md) · [Steps to render the questionnaire](../examples/complete/README.md#recreate-the-answered-questionnaire)

The preview uses only reviewed fictional data. No user browser account, private research, real responses, or machine-specific paths should appear in the published media. The example's `example.invalid` source links are fixtures, not verified live sources.

The GIF loops. Use the static preview or written walkthrough if motion is inconvenient or the text is hard to read.

One loop lasts 26.2 seconds. The GIF is 900 × 990 pixels and approximately 542 KiB. The saved HTML was inspected to confirm the three recorded choices. The static screenshot shows the form rendered in the browser.
