# Contributing

Keep reusable source files and documentation in English. Preserve intentional translations and multilingual input fixtures. User-facing questions and outputs should follow the conversation language rather than the source language.

Use Python's standard library for the runtime and Node's built-in modules for form regression tests. Avoid adding dependencies or mandatory services without a demonstrated need. Keep run data outside the repository.

Run the commands in [testing](docs/testing.md). Add behavioral coverage when changing dependencies, revisions, save/resume, imports, locale handling, or text composition. Tests should check observable outcomes such as preserved text and decisions, not merely repeat the implementation.

Keep runtime changes under `any-skill-builder/`. Update relevant references, public examples, and [CHANGELOG.md](CHANGELOG.md) when behavior changes. When adding a distributable file, update `tools/release-files.json` intentionally and review the resulting ZIP contents.

Describe the problem, changed behavior, relevant validation, and any untested limits in a pull request. Do not include personal run records, live form URLs, answer exports, generated user assets, credentials, or local screenshots containing private content.
