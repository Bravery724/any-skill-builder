# README demo

[Watch the GIF](assets/demo.gif) · [Static questionnaire preview](assets/questionnaire.jpg) · [Complete example](../examples/complete/README.md)

The 21.3-second GIF is an edited replay of the fictional weekly-update example. Its request and result are presentation panels; the questionnaire is the actual browser-rendered form. Timing is condensed. It does not show a new model generating and evaluating a skill in 21 seconds.

## What is shown

| Stage | Content and evidence |
| --- | --- |
| One request | “Create a skill that turns project notes into clear weekly updates.” This expresses the goal in the public questionnaire. |
| Questionnaire | The current renderer displays the saved goal, three active questions, and one conditional question. Recorded pointer clicks select the same three values as the public decisions. |
| Finish | The standalone form downloads its answers. Its actual notice explains that the file must return to the skill-building chat. |
| Finished skill | Excerpts from the existing `weekly-team-update/SKILL.md` show audience context, visible uncertainty, and source links beside supported claims. |

The choices are:

- **Readers:** teammates and cross-functional partners.
- **Evidence:** beside the relevant claim.
- **Missing information:** draft now and mark what is uncertain.

These match [the recorded decisions](../examples/complete/decisions.json). The clarification-first follow-up remains inactive. The final screen quotes the [actual skill](../examples/complete/weekly-team-update/SKILL.md), rather than inventing an output or additional files.

The **nine recorded checks** are two automatic checks and seven reviewed judgments from [the existing evaluation report](../examples/complete/evaluation-report.md). They are not nine automated model tests, a fresh evaluation, or a comparative quality benchmark. See [the execution note](../examples/complete/execution.md) for scope and limits.

## Recording and accessibility

The form was rendered with the project's own Python helper and exercised in an isolated headless Chrome profile. The saved answers were checked against the public decisions, and browser exceptions were checked during the replay. Captions and a visible pointer were added around the form; the request and skill panels summarize the public artifacts. The GIF is 900 × 900 pixels, 10 frames per second, and approximately 366 KB.

No personal browser sessions, credentials, live server URLs, private research, or user responses appear in the recording. The example uses fictional public data. Its supplied `example.invalid` links are fixtures, not verified live sources.

The GIF loops. Use the static preview and the written walkthrough if animation is inconvenient or the small text is hard to read. To reproduce the questionnaire without the presentation panels, follow the commands in [the complete example](../examples/complete/README.md#recreate-the-answered-questionnaire), omitting `recommend` when you want to answer it yourself.
