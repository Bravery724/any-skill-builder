# Design

The host agent makes semantic decisions. The runtime keeps those decisions consistent and reviewable. No model API, fixed domain questionnaire, or background agent is embedded.

| Component | Responsibility |
| --- | --- |
| SKILL.md and references | Subject research, question review, answer interpretation, implementation, and evaluation |
| Python core | Schema validation, identity, dependencies, revisions, history, saved-file import/restoration, and build readiness |
| HTML, CSS, JavaScript | Standalone cards, pagination, image choices, composition-safe input, and answered-HTML export |
| Host tools | Actual research, image generation, skill authoring, and task execution |
| Evaluation helper | Artifact checks, evidence-backed reviews, and qualified baseline comparisons |

## Two workflows

Full Auto performs research, records its decisions in a short decision list (question, alternatives with tradeoffs, choice, reason, sources) with a single check, and builds the skill without rendering HTML. The list maps field for field onto the questionnaire, so a run can be converted when the user wants to answer.

Questionnaire performs the same research and question review, then exports a self-contained HTML. The user answers, saves, and returns to chat. The host finds the matching saved file, imports meaningful answers, decides blanks, and builds. There is no live connection to keep open and no special defer state.

Both flows preserve the original request and constraints. Mode selection is conversational when needed; a skill does not control every host's native slash picker.

## Decisions and transitions

Questions have stable IDs, implementation effects, sources, alternatives, and reasoned recommendations. Core choices recommend direct answers while remaining fully available to AI. A core review compares viable alternatives, conditions that change a recommendation, and conflicting combinations.

An answer is present or absent. Custom values retain free text and, for multi-select, any ordinary selections. Clearly unusable text is a host judgment, with the original retained and the reason recorded; length or unfamiliar wording is not a rejection rule. Meaningful rejection of the candidates remains a constraint.

Dependencies are active, waiting, or inactive. Unknown parents wait. Custom answers can receive an explicit host interpretation for predefined branches without losing their original words. Parent changes invalidate affected dependent answers while retaining history. Only current valid decisions drive the build.

Cosmetic edits require an explicit declaration and are restricted to display fields. They preserve answer validity while advancing the questionnaire revision. Changing a display field can still change meaning, so the host must review the edit before using that exception.

## Questionnaire interaction

A small request summary and counts precede restrained question cards. Each card shows answered/unanswered status, relevant choices, Other text where appropriate, a clear-answer action, and expandable reasoning/evidence.

Navigation is separate from saving. Previous, page selection, and next may pass unanswered questions. Save answers remains available on every page in a small persistent footer. Its nearby note explains that blank questions will be decided in chat. A confirmed reset clears current inputs without changing the questionnaire.

Saving exports a complete HTML with its actual answer state embedded. Reopening that file restores those answers and clears without allowing an older browser draft to replace them. The saved file carries registered images, so a moved file does not depend on broken relative image links. The browser reports a download request honestly rather than claiming a confirmed overwrite of the original file.

The form preserves the active editor during input and composition. Question rendering must not recreate a focused textarea merely because answer counts change. Keep keyboard focus visible, controls reachable, and the fixed footer clear of the final editable content.

## Resume and integrity

The host starts from the generated path recorded for this run. The helper checks matching saved files by run identity, question content, and revisions. It rejects stale or foreign state and does not guess between conflicting saves. A user who saved elsewhere supplies that path or file.

A saved HTML is data, not authority to execute its scripts or write to paths it names. The importer reads the dedicated JSON block. A restore uses an explicit fresh destination and validates assets before reconstructing it. Repeated import of the same export is idempotent, protecting subsequent AI work.

A saved file cannot wake a closed conversation. Returning to chat starts continuation. Checkpoints describe the last observed stage and remaining work, not a continuously running process.

## Language and distribution

Reusable source prose defaults to English. Questions, interface messages, chat, and task outputs follow the user's language, with explicit requests taking precedence. The host supplies translation dictionaries where needed; users are not asked to configure localization.

Only reusable runtime files enter the installable archive. Source archives add reviewed public examples, evidence, synthetic screenshots, tests, and maintainer tools. Private runs, answers, credentials, machine paths, and user assets stay outside the public repository. The package does not change model settings or publish a repository by itself.