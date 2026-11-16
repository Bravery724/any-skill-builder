# Any Skill Builder

Turn a rough idea into a reusable agent skill. The builder helps your agent research the task, make design choices, and test the resulting skill on example tasks.

## Quick start

Use an agent that supports Agent Skills, can access local files, and can run Python 3.10+. The installer below requires Node.js 22.20+. [Install without Node.js](docs/installation.md#install-from-source).

From your project directory:

```sh
npx skills add Bravery724/any-skill-builder --skill any-skill-builder
```

Choose your agent in the installer, then refresh its skills or start a new session. Ask:

> Use any-skill-builder in Questionnaire mode to build a weekly update skill from project notes. Ask me what should appear first and how to handle missing details.

Save your answers in the HTML questionnaire, then return to chat and say `continue`. You’ll get a `SKILL.md` you can reuse. If your agent can’t find the saved HTML, give it the file path.

## Demo

https://github.com/user-attachments/assets/3d10f534-74e7-4cd4-a69c-369cc3844fce

## Two ways to build

- **Full Auto:** Let the agent make and explain the design choices.
- **Questionnaire:** Choose the details that matter to you and let the agent fill in the rest.

## Learn more

- [Usage guide](docs/usage.md) · [Complete weekly-update example](examples/complete/README.md)
- [Installation and updates](docs/installation.md) · [Releases](https://github.com/Bravery724/any-skill-builder/releases)
- [v0.5.0 validation](docs/full-auto-validation.md) · [Contributing](CONTRIBUTING.md) · [MIT license](LICENSE)
