# Changelog

## Unreleased

- Plan single-rule changes from the existing feature, file and evaluation records. The planner lists relevant cases and flags missing coverage.
- Run a generated Python CLI against predeclared inputs and expected JSON in one command. The evidence records actual output, exit codes and file hashes.
- For choices that are hard to judge from labels, questionnaires can show one realistic input and the outcomes of choosing different options.
- Tabbing past a text or Other answer preserves its author, rationale and branch interpretation when the offline form is saved and imported. Editing the answer records the user's new choice.
- Full Auto reports which decisions are waiting on a custom choice. Record the branch interpretation and its rationale to preserve the original choice and include the applicable decisions in the build brief.
- Switching from Full Auto to Questionnaire checks the proposed form against the saved decisions. Authors can translate the form while keeping its choices, behavioral effects, recommendations and dependencies intact.
- Single-choice, multiple-choice and image cards show the behavioral effect beside each option. Repeated wording is shown once.

## 0.5.4 — 2026-11-18

- Full Auto and Questionnaire build briefs now identify active AI decisions to review together. The builder checks their combined effects against the user's explicit choices and records how it scoped any conflicting default.
- When a skill masks or transforms information, the evaluation plan and reviewer instructions now check both the change and the relationship the reader still needs to follow in the output.
- Added two repeatable handoff regressions covering conflicting reports attributed to the wrong or unnamed speaker and a masked email that loses its intended recipient.

## 0.5.3 — 2026-11-18

- Prepared evaluations and delivery verification now check the cases, prompts, input mappings, and grading criteria against the saved plan. A change to those definitions requires a new evaluation iteration.
- Full Auto can build a fully specified skill from its fixed requirements with zero design decisions. The existing review checks still apply.

## 0.5.2 — 2026-11-16

- Questionnaire build briefs take their fixed requirements from the accepted question review only. In 0.5.1 the brief also added any decision-list requirement the review lacked, so a requirement released on purpose when a Full Auto run was converted could reappear as fixed and contradict the user's answer.

## 0.5.1 — 2026-11-16

- Questionnaire build briefs now include a **Fixed requirements** section, taken from the accepted question review. Before, only Full Auto briefs listed them, so a constraint the review had recorded could be missed during the build.
- When a Full Auto run is converted with `set-questions --from-decisions`, the question review template from `prepare` lists the decision list's fixed requirements and attaches them to every question and combination. The brief also adds any decision-list requirement the review lacks.
- `docs/full-auto-validation.md` records a re-check of the harder evaluation rules: a new Full Auto build wrote a trap case and a fake-secret case, and both skill versions ran five times on the held-out input that had exposed the earlier error.

## 0.5.0 — 2026-11-15

- Commands that change a run (`set-questions`, `answer`, `recommend`, `import-answers`, `resume`, `reset-answers` and similar) print a short summary instead of the full questionnaire and answer records, which were 40-60 KB per call. `--full` restores the old output, `--out FILE` saves it, and `status --json` is unchanged.
- `check-skill` now matches the official skill validator: it rejects unknown frontmatter fields, angle brackets in `description`, and `compatibility` over 500 characters.
- `prepare_evaluation.py` rejects builder run records (`answers.json`, `questions.json`, `progress.json`, `runs/`, `dist/`, and similar) only at the runtime root, accepts `.gitignore`, `.gitkeep`, `.gitattributes` and `.editorconfig`, and names the refused path in its error.
- Full Auto records its decisions in a short decision list (`decisions.json`: question, alternatives with tradeoffs, choice, reason, assumptions, sources) with a single check (fixed requirements kept, no ruled-out choice, no invented private facts) instead of a questionnaire with a SHA-bound review. New commands: `set-decisions` validates and stores the list and `brief` builds from it; `decisions-to-questions` writes a questionnaire skeleton from the same fields, and `set-questions --from-decisions` switches the run to Questionnaire mode. Existing Full Auto runs with `questions.json` keep working.
- Iteration caps: one revision after the first question review (remaining non-requirement findings can be marked `accepted` and are reported), and at most two evaluation iterations with 2-3 cases for a simple skill; a no-skill baseline is optional except for legal, medical, financial or safety advice, or when the user asks whether the skill helps.
- Harder evaluation inputs: cases include a trap (something that looks wrong but is correct, so over-flagging fails) and, when the skill can meet secrets or personal data, fake sensitive values the output must not repeat. Reviewers compare each statement about the input with the raw input and check for over-flagging. This follows a blind comparison in which the builder's own checks passed but a held-out case still exposed an error.
- `verify_delivery.py` is required for archive delivery and optional for folder delivery. A delivery is provisional only when the final skill was never executed on a realistic case.
- The agent states the expected scope and rough duration when the work starts.
- `set-questions` fills omitted `schema_version`, `project_id`, `mode` and `revision` from the run and reports which it filled; identity and revision errors now show the expected and supplied values.
- Questionnaire: up to four questions per page (an image question counts as two), a Recommended badge on the recommended option, and a saved filename of `questionnaire-<project_id>-r<revision>-answers.html`, which `resume` still finds.
- After delivery the agent offers to install the skill, naming the destination, and installs only after the user agrees.
- Instructions tightened: SKILL.md states each rule once with fewer repeated disclaimers (about 2,350 words, down from 2,930), and the evaluation procedure (`evaluation-loop.md`) and record format are merged into one `references/evaluation.md`.
- Research rule: facts the skill depends on in legal, medical, financial or safety matters, and figures that change over time, are checked in the primary source (statute, official notice, vendor documentation); a source counts as `read` only if it was opened, and unreachable primary sources are recorded as known limits.
- New skill description: it names both modes and claims plain skill creation, Full Auto and improvement requests, while leaving description-only trigger tuning and benchmark-only requests to skill-creator. In an isolated A/B test (3 runs per case) those requests went from 0/9 to 9/9, and skill-creator's own cases stayed 6/6.
- Evaluation findings take an optional `severity` (`blocking` by default, or `minor`); minor findings are reported but no longer block `evaluate_skill.py` or `verify_delivery.py`.

## 0.4.1 — 2026-11-15

- Require version-bound question-review records for new CLI authoring, with fixed requirement coverage, contrasting applicable answer combinations, fair alternatives, private-fact handling and complete visible-text localization.
- Resolve conflicting choices in their actual wording or conditions, with explicit output-count units; review prose cannot invent hidden overrides.
- Preserve existing saved answers and legacy runs; stale or incomplete reviews block rendering, recommendations and build briefs without adding human approval or HTML to Full Auto.
- Verify delivered runtime bytes against a completed reviewed execution snapshot, including README, optional ZIP and extracted files; do not treat post-test edits as tested.
- Preserve evaluation inputs' relative directory structure and record original-to-snapshot path mappings.
- Accept a sole explicit exclusive choice even when ordinary options require several selections; recover that choice from older saved drafts without resurrecting cleared/newer answers.
- Keep render metadata and embedded HTML bound to the same captured state.
- Preserve skill identifiers on improvements and distinguish separate-agent evidence from unverified blind-context claims.

## 0.4.0 — 2026-11-15

- Make execution, separate assessment, correction, and re-execution a concrete part of the existing seven-stage build workflow.
- Prepare isolated evaluation iterations with skill/input snapshots, executor and reviewer packets, and pending records; the host still runs tasks and makes judgments.
- Record execution provenance and critique weak checks, missing outcomes, and unsupported claims alongside evidence-backed results.
- Review repeated operations across actual execution records before extracting reusable helpers, and retain the validation of extracted code.
- Preserve Full Auto without HTML, saved-HTML Questionnaire continuation, and existing evaluation reports when the new optional records are absent.
- Update usage and release documentation for the original implementation inspired by Anthropic's evaluation workflow.

## 0.3.0 — 2026-11-15

- Offer two creation workflows: Full Auto completes researched decisions without generating HTML; Questionnaire exports an editable standalone form and resumes from its saved HTML.
- Apply the restrained card layout with the original request, answer counts and states, per-question clearing, custom Other answers, page navigation, and Save answers on every page.
- Store the questionnaire, answers, image candidates, and run/version identity in saved HTML so answers can be read without executing the document or running a local service.
- Resolve unanswered questions through the host AI when building resumes, preserving meaningful user choices and recording the reasons for AI decisions.
- Remove the connected server, submission polling, separate delegation controls, hybrid mode, and deferred-choice workflow.
- Update installation and usage guidance, current screenshots and demo, and validation coverage for the offline workflow. Earlier host validation remains clearly labeled as historical evidence.

## 0.2.3 — 2026-11-14

- Record actual supervised Claude Code and Antigravity CLI workflows, with fictional inputs, generated skills, fresh-context outputs, independent AI review, and explicit limitations.
- Document host-specific installation paths and execution permissions for Claude Code and Antigravity CLI.
- Make multi-select exclusivity explicit in the authoring contract, including localized "none" choices.
- Keep supplied requirements fixed across questionnaire options and preserve conditions, uncertainty, and conflicts when offering output-format choices.
- Give tables, explanations, and follow-up questions distinct roles so generated outputs preserve evidence without repeating it across sections.
- Clarify safe recovery from host permission denials and quiet or buffered headless sessions without resetting saved runs.

## 0.2.2 — 2026-11-14

- Add a lightweight README GIF showing one request, the actual questionnaire, and the recorded finished skill, with a static alternative and documented evidence.
- Show the saved goal at the top of the questionnaire; long requests expand from a two-line summary without changing answers or the current page.
- Add English and Korean goal labels while preserving compatibility with existing custom locale dictionaries.
- Accept GIF assets in release validation and verify their file signatures.

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
