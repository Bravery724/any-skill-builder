# Any Skill Builder

Create a reusable [Agent Skill](https://agentskills.io) for a task you do repeatedly. Describe the job once, give the builder an example if you have one, and it will research the task, work through the design choices, write the skill, and try it on sample inputs.

For example, if you write a team update every Friday, you can decide once how to handle conflicting notes, missing dates, and links to evidence. Next Friday, give the finished skill the new notes.

## Contents

- [Demo](#demo)
- [Quick start](#quick-start)
- [Choose a build mode](#choose-a-build-mode)
- [A weekly update from conflicting notes](#a-weekly-update-from-conflicting-notes)
- [What you get](#what-you-get)
- [How the skills are tested](#how-the-skills-are-tested)
- [Guides and examples](#guides-and-examples)

## Demo

https://github.com/user-attachments/assets/3d10f534-74e7-4cd4-a69c-369cc3844fce

In 80 seconds, the narrated walkthrough follows a packing-list skill that checks items against airline rules, from the initial request through design choices, testing, and installation.

## Quick start

Use an agent that can load Agent Skills, read and write local files, and run Python 3.10 or later. The Python helper uses the standard library. The builder uses your host agent's model and research tools, so it needs no separate API key.

From your project directory, install the builder with the Skills CLI (Node.js 22.20+).

```sh
npx skills add Bravery724/any-skill-builder --skill any-skill-builder
```

Select your agent and refresh its skills or start a new session. The explicit skill name selects the builder from a repository that also contains example skills. You can also [install with Python](docs/installation.md#install-from-source).

**Try this in your agent**

> Use any-skill-builder in Questionnaire mode to create a skill that turns project notes into a weekly team update. Let me choose who it is for and what the skill should do when two sources disagree.

Open the HTML form the agent gives you. Answer the questions that matter to you, choose **Save answers**, then return to the same chat and say **Continue from my saved answers**. If the browser downloaded the file elsewhere, give the agent that file or its path. The agent keeps your answers, resolves the blanks, and builds the skill.

## Choose a build mode

| Mode | Choose it when | What happens |
| --- | --- | --- |
| **Full Auto** | You know the job and want the agent to decide how the skill should work. | The agent records its choices and reasons, writes the files, and evaluates the result in one run. |
| **Questionnaire** | Audience, format, or handling of tricky cases is a matter of preference. | The agent researches the options first. You can accept a recommendation, describe another choice, or leave a question for the agent. The form works offline and can be saved partway through. |

For a **Full Auto** build, include a boundary the agent can test.

> Use any-skill-builder in Full Auto to create a skill that suggests a commit message from staged changes. Keep a feature and its tests together, suggest a split for unrelated changes, and leave my repository untouched.

You can write either request in your own language. The questionnaire follows the conversation language. Reusable skill files default to English unless you request another language.

You can also give the builder an **existing skill folder** and an example of a result you want to improve. It builds the revision separately so you can compare it with the original. [More example requests](docs/usage.md)

## A weekly update from conflicting notes

The repository includes a finished skill, its design choices, and the drafts it produced from fictional project notes. One choice changed how the writer handled uncertainty. When asked *“What should happen when the notes leave a material gap?”*, the recorded choice was *“Draft now and mark what is uncertain.”* [Questionnaire](examples/complete/questionnaire.json) · [Recorded choices](examples/complete/decisions.json)

| In the notes | In the resulting update |
| --- | --- |
| The meeting notes say CSV export is live for everyone. The release tracker says the feature is disabled and awaits approval. | The draft opens with **“CSV export availability is unresolved.”** It gives both accounts and asks which source is authoritative. |
| A colleague suggests Wednesday for rollout. No approver accepts the date. | The draft describes Wednesday as a proposal and asks who owns the release. |

To try the finished skill, open this repository in your agent and ask it to draft the update.

> Use `examples/complete/weekly-team-update/SKILL.md` to draft the update requested in `examples/complete/inputs/conflicting.md`.

[Read the input](examples/complete/inputs/conflicting.md) · [Inspect the generated skill](examples/complete/weekly-team-update/SKILL.md) · [Compare the recorded output](examples/complete/outputs/conflicting.md)

## What you get

The builder delivers a skill folder you can install in your host. This example turns project notes into a brief. [Open the skill folder](examples/offline-workflows/full-auto/project-notes-brief)

```text
project-notes-brief/
├── SKILL.md    Instructions the agent follows on future requests
├── README.md   Inputs, example requests, and expected results
└── LICENSE     Terms for reuse
```

Skills can also include scripts, references, or assets when the task needs them. The build workspace keeps the research notes, decisions, and evaluation records separately. Keep that workspace if you want to revisit a choice later. [Sample input](examples/offline-workflows/full-auto/input.md) · [Brief written by the finished skill](examples/offline-workflows/full-auto/output.md)

## How the skills are tested

Before writing the skill, the builder defines realistic inputs and what a successful result should do. It then exercises the finished skill and reviews the actual outputs. For the weekly update, a useful check is whether the draft preserves the disagreement about the release. A well-formatted update that declares a launch would fail that check. You can inspect the [recorded evaluation and its limits](examples/complete/evaluation-report.md).

In a **v0.5.0 trial**, graders evaluated generated skills on three previously unseen employment contracts and three sets of staged code changes. They scored the answers without knowing how each skill had been built.

| How the skill was created | Average score across the six inputs |
| --- | ---: |
| With Any Skill Builder v0.5.0 | 8.5 / 10 |
| With Any Skill Builder v0.4.1 (using the files available when those builds were stopped) | 8.0 / 10 |
| By asking the same agent to create a skill without a builder | 7.3 / 10 |

Each skill version ran once per input, and one grader scored the three answers for that input. On a straightforward commit, the skill built without a builder scored 9/10 and the v0.5.0 skill scored 8/10. On the staged-credentials case, the v0.5.0 skill incorrectly said `.gitignore` was empty. [Case-by-case scores, build times, and follow-up runs](docs/full-auto-validation.md)

## Guides and examples

- [Installation and updates](docs/installation.md) for host paths, release downloads, and troubleshooting.
- [Usage guide](docs/usage.md) for research, visual workflows, and improving an existing skill.
- [Saved questionnaire example](examples/offline-workflows/README.md) for a build resumed from a downloaded HTML file.
- [Releases](https://github.com/Bravery724/any-skill-builder/releases) · [Contributing](CONTRIBUTING.md) · [MIT license](LICENSE)
