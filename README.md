# Any Skill Builder

Turn a recurring task into a reusable Agent Skill. Describe the job and the choices that matter to you. Your agent researches the task, writes a skill folder, and tries the finished skill on sample inputs before handing it back. [Agent Skills format](https://agentskills.io)

For example, if you write a team update every Friday, decide once what to do when two sources disagree. Next Friday, give the finished skill the new notes. In v0.5.4 the builder also checks how its own defaults interact with your choices. If you ask it to hide email addresses, it checks whether the reader can still tell who should receive a message. [v0.5.4 release and downloads](https://github.com/Bravery724/any-skill-builder/releases/tag/v0.5.4)

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

This 82-second narrated walkthrough follows a packing-list skill that checks items against airline rules, from the initial request through design choices, testing, and installation. For a closer look at saving and resuming a questionnaire, see the [weekly-update walkthrough and still image](docs/demo.md).

## Quick start

Use an agent that can load Agent Skills, read and write local files, and run Python 3.10 or later. The Python helper uses the standard library. The builder uses your host agent's model and research tools, so it needs no separate API key.

From your project directory, install v0.5.4 with the Skills CLI (Node.js 22.20+). To use the latest questionnaire and Full Auto fixes on `main`, replace `@v0.5.4` with `@main`. [Changes since v0.5.4](CHANGELOG.md#unreleased)

```sh
npx skills add Bravery724/any-skill-builder@v0.5.4 --skill any-skill-builder
```

Select your agent and refresh its skills or start a new session. The explicit skill name selects the builder from a repository that also contains example skills. If you prefer a Python-only install, download the **source ZIP** from the release and run its included installer. [Python installation instructions](docs/installation.md#install-from-source)

**Try this in your agent**

> Use any-skill-builder in Questionnaire mode to create a skill that turns project notes into a weekly team update. Let me choose who it is for and what the skill should do when two sources disagree.

Open the HTML form the agent gives you. Answer the questions that matter to you, choose **Save answers**, then return to the same chat and say **Continue from my saved answers**. If the browser downloaded the file elsewhere, give the agent that file or its path. The agent keeps your answers, resolves the blanks, and builds the skill.

## Choose a build mode

| Mode | Choose it when | What happens |
| --- | --- | --- |
| **Full Auto** | You have a complete specification or want to delegate the remaining decisions. | The agent records fixed requirements and any choices it makes, then builds and tests the skill. When the requirements settle everything, it proceeds with zero design decisions. |
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

Before implementation the builder records the test inputs and success criteria. It runs the resulting skill and compares its actual answers with the source. If a criterion needs to change, it prepares a new evaluation iteration and retains the earlier evidence. For the weekly update, a draft that declares the launch complete would fail the check for conflicting reports. [Evaluation procedure](any-skill-builder/references/evaluation.md) · [Weekly-update results](examples/complete/evaluation-report.md)

Two regression cases shipped in **v0.5.4** show what it means to preserve information when transforming it.

| User requirement | What the reviewer looks for |
| --- | --- |
| Keep two conflicting reports unresolved and attributable. | Can the next shift tell who reported recovery and who still saw the delay? A draft that contains both names but swaps their claims fails. |
| Mask a personal email address and keep the shared mailbox. | Can the next shift tell who receives the private copy as well as where to send the shared copy? A person's name appearing elsewhere in the document is insufficient. |

The fixtures include source notes, passing outputs, and plausible mistakes. From the repository root or the extracted source ZIP, replay the recorded judgments and check their evidence with Python:

```sh
python -B -m unittest discover -s tests -p "test_field_preservation.py"
```

To evaluate a newly generated handoff skill, run it on the supplied notes and have a reviewer assess its fresh outputs. [Inputs, controls, and instructions](tests/fixtures/field-preservation/README.md)

<details>
<summary>Historical comparison of v0.5.0 with other ways to build a skill</summary>

In a **v0.5.0 trial**, graders evaluated generated skills on three previously unseen employment contracts and three sets of staged code changes. They scored the answers without knowing how each skill had been built.

| How the skill was created | Average score across the six inputs |
| --- | ---: |
| With Any Skill Builder v0.5.0 | 8.5 / 10 |
| With Any Skill Builder v0.4.1 (using the files available when those builds were stopped) | 8.0 / 10 |
| By asking the same agent to create a skill without a builder | 7.3 / 10 |

Each skill version ran once per input, and one grader scored the three answers for that input. On a straightforward commit, the skill built without a builder scored 9/10 and the v0.5.0 skill scored 8/10. On the staged-credentials case, the v0.5.0 skill incorrectly said `.gitignore` was empty. [Case-by-case scores, build times, and follow-up runs](docs/full-auto-validation.md)

</details>

## Guides and examples

| If you want to… | Start here |
| --- | --- |
| Install, update, or troubleshoot the builder | [Installation guide](docs/installation.md) |
| Improve an existing skill or resume from a saved form | [Usage guide](docs/usage.md) · [Recorded saved-form example](examples/offline-workflows/README.md) |
| Inspect the instructions your agent loads | [Builder entry point](any-skill-builder/SKILL.md) · [Workflow references](any-skill-builder/references/) |
| Compare a finished skill with its inputs and outputs | [Public examples](examples/README.md) · [Complete weekly-update example](examples/complete/README.md) |
| Work on the builder or verify a distribution | [Tests](docs/testing.md) · [Install and packaging tools](tools/) · [CI workflow](.github/workflows/ci.yml) |

[Release history](CHANGELOG.md) · [Contributing](CONTRIBUTING.md) · [MIT license](LICENSE)
