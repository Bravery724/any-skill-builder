# Usage examples and model settings

[Installation](installation.md) · [Project overview](../README.md) · [Complete worked example](../examples/complete/README.md)

Describe what you want a reusable skill to do. Bring examples, source material, or constraints if you have them; a rough idea is enough to start. Use `any-skill-builder` in your request, or `$any-skill-builder` if your host supports that spelling.

Source packages default to English. Questions, explanations, and task outputs follow your language unless you request another language.

## Choose a workflow

**Full Auto** researches the subject, lists the design decisions with the alternatives it considered, chooses each with a reason, checks the choices once, and builds and evaluates the skill. It creates no HTML. If you later want to answer the questions yourself, ask for the questionnaire; the agent converts the same decisions instead of writing new questions.

**Questionnaire** prepares a standalone HTML. You answer what matters, choose Save answers, and return to chat. AI keeps meaningful answers and resolves the blanks before building. If your request already selects one flow, the agent starts directly; otherwise it offers both in chat.

## 1. Full Auto for a research-paper skill

```text
Use any-skill-builder in Full Auto to create a skill that analyzes
research papers and develops testable ideas across disciplines.
Do not fix one paper topic. Research useful methods, record and explain
the main design choices, then implement and evaluate the skill.
Adapt analysis to each field and separate evidence from proposed ideas.
```

The result should include a usage guide and observed checks. A reusable method still needs to respect each field's evidence and the limits of the supplied paper.

## 2. A webtoon-making questionnaire

```text
Use any-skill-builder to create a skill for making short everyday-life
comedy webtoons. Research story structure, panel pacing, character
consistency, lettering, and revision workflows. Prepare an HTML
questionnaire so I can choose the important creative direction.
Use real image candidates when suitable tools are available.
```

Choose **Other — describe** to explain a different direction or reject the shown candidates. Image generation depends on available host tools; placeholders must not be presented as real candidates. This request creates a reusable production skill, not a finished episode.

## 3. A UI-design questionnaire

```text
Use any-skill-builder to create a skill for designing accessible
web-app interfaces. Research the topic and let me answer an HTML
card questionnaire. Show useful visual alternatives when tools allow.
Preserve my custom directions and decide the questions I leave blank.
```

Core questions recommend direct input without requiring it. The form has answered/unanswered states, answer clearing, Other text, and a Save answers button on every page.

## 4. Continue after saving

```text
Continue building from the saved HTML.
```

In the same conversation, the agent uses the known run and recorded file location. It checks that the file contains saved answers for that run. If you saved to another folder or the browser added a suffix, provide that file or path:

```text
Use the saved questionnaire at <saved-html-path>.
Keep my answers and fill the remaining blanks with your judgment.
```

Replace the placeholder with your actual file. You do not need a separate user-facing command such as `build_from_answers`. The saved file does not restart a closed conversation on its own.

Brief meaningful values such as "none", `0`, or a specialist term are respected. Clearly unusable text is judged in context by the host, retained in the record, and replaced with an explained decision. AI does not invent your real budget, accounts, equipment, or access.

## 5. Ask only for questions

```text
Use any-skill-builder to research and prepare an HTML questionnaire
for a skill that turns project notes into clear weekly updates.
Show the question count and the evidence behind meaningful choices.
Stop after delivering the questionnaire; I will return after saving it.
```

The agent completes that part and waits. It should not answer your blanks while you are still editing.

## 6. Improve an existing skill

```text
Use any-skill-builder in Full Auto to improve the skill in <skill-folder>.
Its explanations are too rigid and hard to follow. Inspect the
instructions and examples, preserve working behavior as a baseline,
and research useful improvements. Build the revision separately and
compare it with the original on the same tasks before replacing it.
```

Provide examples of useful and disappointing outputs when possible. They turn a broad preference into concrete checks.

## 7. Resume an interrupted build

```text
Use any-skill-builder to resume the run in <saved-run-folder>.
Read the questions, current answers, and last checkpoint.
Continue from the next unfinished stage without initializing again
or asking me to repeat valid decisions.
```

If only an answered HTML remains, provide it. The helper can restore its embedded questionnaire, answers, and assets into a new run. It cannot claim that research logs or output files absent from the HTML have also been recovered.

## Use the skill you receive

The builder delivers the skill folder, usage guide, starting request, and observed checks and limits. Follow that guide to install the complete folder where your host discovers skills, then refresh the host if needed.

For example, if the delivered skill is named `paper-research` and supports these actions:

```text
Use paper-research to analyze the attached paper. Explain its central
claim and evidence in plain language, identify important limitations,
and propose three research ideas with a test for each.
```

That name is illustrative, not another skill installed with this builder. Use the name and capabilities in your delivered guide.

## Model and reasoning settings

A capable reasoning model and enough reasoning effort can help with research synthesis, useful question design, conflicting requirements, and evaluation. This is a practical recommendation, not a guarantee that every increase in effort produces a better skill.

General [research on test-time compute](https://arxiv.org/abs/2408.03314) finds task- and method-dependent benefits. Applying that to skill creation is an inference: this project has not benchmarked the best model or effort setting for every skill.

| Work | Practical starting point |
| --- | --- |
| Unfamiliar subject or complex workflow | Consider a capable reasoning model and higher effort, if available. |
| Important choices and behavior review | Allow time to compare alternatives and test actual outcomes. |
| Small, well-defined wording change | The host's normal setting may be enough. |

Higher effort can increase time and cost. Useful examples, good sources, and real testing still matter; a long answer is not a quality measure. Choose model and effort in your host's controls. Asking “think harder” does not change the actual setting, and the builder does not silently change your provider or settings.