# Usage examples and model settings

[Installation](installation.md) · [Project overview](../README.md) · [Complete worked example](../examples/complete/README.md)

Tell your agent what you want a reusable skill to do. These requests start the creation or improvement of that skill; use the delivered skill afterward to carry out its task. You can bring examples and source material, but a rough idea is enough to begin.

Use `any-skill-builder` in your request, or `$any-skill-builder` if your host supports that spelling. Write naturally in your own language. Reusable files default to English, while questions, explanations, and task outputs follow the conversation's language. An explicit language request overrides the relevant default.

## Model and reasoning settings

**For a complex skill, a capable reasoning model and higher reasoning effort can help with research synthesis, useful question design, conflicting requirements, and evaluation.** Treat this as a practical recommendation, not a guarantee that every increase in effort produces a better skill.

General [research on test-time compute](https://arxiv.org/abs/2408.03314) finds that the benefits depend on the problem and how the extra computation is used. Applying that finding to skill creation is an inference: this project has not benchmarked which model or effort setting produces the best skills.

| Work | Practical starting point |
| --- | --- |
| Exploring a difficult subject or designing a complex workflow | Use a capable reasoning model and consider a higher effort setting, if your host offers one. |
| Reviewing important choices or checking a generated skill | Allow enough reasoning and time to compare alternatives and test actual behavior. |
| Fixing wording or making a small, well-defined change | Start with the host's usual setting; maximum effort is usually unnecessary. |

Higher effort can take longer and may cost more, depending on the host. Clear goals, reliable sources, useful examples, and real tests still matter. A longer answer does not by itself show better analysis.

Choose the model and effort in your host's controls. Asking the agent to "think harder" does not change the actual setting. Any Skill Builder preserves your selected model, provider, and effort; it does not silently change global settings.

## 1. Let AI design a research-paper skill

```text
Use any-skill-builder to create a skill that analyzes research papers
and develops testable research ideas across disciplines, without fixing
one paper topic. Research the relevant methods, recommend and record
the design answers, explain the main assumptions, and continue through
implementation and evaluation. Adapt the analysis to each field and
distinguish the paper's evidence from proposed ideas.
```

This delegates the design choices to AI. The builder should explain its main decisions and deliver a skill with a usage guide and observed checks. A reusable method still needs to respect the field and limits of each paper.

## 2. Create a webtoon-making skill

```text
Use any-skill-builder to create a skill for making short everyday-life
comedy webtoons. Research story structure, panel pacing, character
consistency, lettering, and revision workflows. Let me choose the visual
direction using real image candidates if the host has suitable tools.
If those tools are unavailable, explain the limitation and discuss the
direction in chat. Ask me about important creative preferences.
```

Image generation and visual comparisons depend on the host's available tools. This request creates a reusable production workflow; it does not ask the builder to draw a finished episode immediately.

## 3. Answer UI design questions yourself

```text
Use any-skill-builder to create a skill for designing accessible web-app
interfaces. Research the topic and let me answer a card-style questionnaire.
Show meaningful visual alternatives when tools are available. If I defer
a choice, finish the active questionnaire first, then discuss what I
disliked, create revised candidates, and let me choose again. Preserve
the answers I already gave.
```

You can leave a question unanswered for AI or explicitly defer it for later discussion. Those are different decisions: delegating unanswered questions does not resolve a deferral for you.

## 4. Ask only for the questionnaire

```text
Use any-skill-builder to research and design a questionnaire for a skill
that turns project notes into clear weekly updates. Show the active
question count, recommendations, and the evidence behind the choices.
Stop after delivering the questionnaire; do not build the skill yet.
```

The builder should respect this limited scope. Ask it to continue when you are ready, using the same saved run and decisions.

## 5. Improve an existing skill

```text
Use any-skill-builder to improve the existing skill in <skill-folder>.
It currently produces explanations that are too rigid and hard to follow.
Inspect the instructions and examples, preserve working behavior as a
baseline, and research useful improvements. Ask only about meaningful
gaps. Build the revision separately and compare it with the original
on the same tasks and available model settings before replacing anything.
```

Replace `<skill-folder>` with the actual path. Include examples of both useful and disappointing outputs when you have them; they help turn a broad preference into concrete evaluation criteria.

## 6. Resume an unfinished build

```text
Use any-skill-builder to resume the saved run in <saved-run-folder>.
Read its current status, recorded answers, deferrals, and last checkpoint.
Continue from the next unfinished step without reinitializing the run
or asking me to repeat decisions that are still valid.
```

Replace `<saved-run-folder>` with the existing run path. If an offline questionnaire downloaded a Finish file, also give that file to the agent. A saved HTML form cannot restart a closed conversation by itself.

## Use the skill you receive

The builder delivers the skill folder, its usage guide, a starting request, and the checks and limitations it actually observed. Follow that guide to install the complete folder in the location your host discovers, then refresh the host if necessary.

For example, if the delivered skill is named `paper-research` and supports these actions, you might ask:

```text
Use paper-research to analyze the attached paper. Explain its central
claim and evidence in plain language, identify the most important
limitations, and propose three research ideas with a test for each.
```

`paper-research` is an illustrative generated name here, not an additional skill installed with Any Skill Builder. Use the actual name and capabilities in your delivered guide. For a recorded end-to-end example, see the [weekly-update walkthrough](../examples/complete/README.md).
