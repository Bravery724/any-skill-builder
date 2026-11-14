# Changelog

## 0.2.1 — 2026-11-14

- Put copyable requests for AI-led creation, interactive design, and existing-skill improvement near the start of the README.
- Add a practical usage guide with questionnaire-only, visual, and resume examples, and clarify when to use the resulting skill.
- Make model and reasoning-effort guidance visible in both public and installed user guides, including task-dependent benefits, time/cost tradeoffs, and the role of sources and testing.
- Keep model selection under host control; no runtime logic or questionnaire behavior changes.

## 0.2.0 — 2026-11-14

- Publish installation and release links, add an explicit Skills CLI installation path, and retain the dependency-free Python installer.
- Resolve the hosted CI temporary directory at step scope, where the runner context is available.
- Include user-facing usage guides with newly generated skills, add brief help for otherwise empty invocations, and clarify the builder's own picker description.
- Complete download, installation, update, rollback, and removal guidance with explicit host requirements and publication checks.
- Preserve incomplete multi-select choices in browser recovery files and explain how to return AI request files to the host.
- Reject browser-only recovery files as host submissions without changing saved answers or reset state.
- Normalize the public example's line endings and verify its recorded artifacts and reports in CI without rerunning a model.
- Strengthen core-question review with viable alternatives, recommendation-changing conditions, and conflicting-choice resolutions; distinguish design decisions from runtime inputs and explain AI-selected directions in chat.
- Recommend direct answers for core questions while preserving AI delegation for every unanswered question.
- Separate submission acceptance from host acknowledgment and retain versioned progress checkpoints with token-free resume guidance.
- Show seven skill-building stages in chat, with concise updates that respect saved progress, AI delegation, deferrals, and limited-scope requests.
- Show each question’s answer status and let users clear a single or image selection before delegating unanswered decisions.
- Keep AI delegation as a cancellable top-only preference and add Finish on every page, with an inline choice for unanswered questions and separate navigation controls.
- Restore keyboard focus after reset and image enlargement; announce recovery details and show progress on the action actually running.
- Rename the skill and distribution to `any-skill-builder`; preserve existing run formats and browser draft keys.
- Fix Python 3.10 image hashing and structural-checker false positives for code examples and multiline descriptions.
- Preserve answers for explicitly declared cosmetic corrections while retaining normal invalidation for changed decisions.
- Bind public questionnaire fixtures to fresh workspace names without weakening saved-answer identity checks.
- Add chat-only and existing-skill improvement guidance, an evidence-based evaluation helper, and a complete public example.
- Add explicit handoff of unanswered questions to the host AI and confirmed whole-answer reset with history preservation, including offline request files.
- Add a conservative local installer, private-metadata exclusions, and a real questionnaire screenshot.

## 0.1.0 — 2026-11-14

Initial distribution prepared for public review.

- English-first reusable files and package metadata, with conversation-language questionnaires and outputs.
- Explicit English defaults for new runs and preserved locale behavior for existing and legacy runs.
- Subject research, conditional design questions, image choices, AI recommendations, and deferred-choice review.
- Versioned decisions, run identities, conflict checks, local submission, and offline export/import.
- Editor preservation during composition and asynchronous acknowledgements, with portable regression tests.
- MIT licensing, maintainer documentation, explicit release allowlists, and reproducible runtime/source archives.

Historical private runs and machine-specific verification records are not part of this source distribution.
