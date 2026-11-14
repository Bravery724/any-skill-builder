# Design

The host agent makes semantic decisions. The runtime keeps those decisions consistent and reviewable. This split keeps the package useful across subjects without embedding a model API, a fixed domain questionnaire, or a second hidden agent.

| Component | Responsibility |
| --- | --- |
| SKILL.md and references | Research, question quality, recommendations, deferred discussion, implementation, and evaluation |
| Python core | Schema validation, run identity, dependency state, revisions, history, and build readiness |
| Loopback server | Versioned save/submit bridge to an active host task |
| HTML, CSS, JavaScript | Card form, pagination, images, composition-safe input, recovery, and progress |
| Host tools | Actual research, candidate generation, skill authoring, and behavior checks |
| Evaluation helper | Repeatable artifact checks, evidence-backed review records, and qualified baseline comparisons |

## Decisions and transitions

Each question has a stable ID, a decision it controls, meaningful alternatives, and an evidence origin. Sources distinguish inspected material, partial access, and unavailable material. Recommendations include reasons and assumptions; they are not user approvals.

Optional `importance` distinguishes core design directions from detail refinements without changing who may answer them. Core choices are recommended for direct answering and remain fully delegatable. The host separates these design choices from unknown user facts and runtime inputs, and reuses information already supplied. Core review records the strongest viable alternative, conditions that would change a recommendation, and conflicts with other answers. Semantic review stays with the host; a populated field is not a quality certificate.

An answer can be present, deferred, or absent. Dependency state is active, waiting, or inactive. An unanswered or deferred parent leaves children waiting. Relevant parent or question changes invalidate dependent answers while retaining history. Building requires all active answers and no unresolved material deferrals or waiting decisions.

Cosmetic corrections need an explicit host declaration and are limited to display fields. They keep answer validity while advancing the questionnaire revision and recording the edits. Default updates still invalidate changed meaning and affected descendants. A display field can change meaning; the helper cannot decide that linguistic question for the host.

The top AI toggle records a pending delegation preference in the browser draft. Finish sends an explicit request for unanswered decisions to the active host when that preference is selected, preserving current answers and deferrals. With unanswered questions and no preference selected, Finish presents an inline choice to delegate and finish or continue at the first unanswered question. A separate confirmed reset archives responses, empties the current answer set, and clears pending delegation without replacing questions. Offline Finish exports the user's edits and any explicit delegation/reset intent under the original version checks. Neither an HTML button nor this server runs a model on its own.

Questions must not offer dishonest reporting or ignoring a refusal as legitimate alternatives. Shared correctness requirements apply to every option. Inspect combinations too: a requirement to preserve exact wording may conflict with permission to rewrite it. Mechanical schema checks do not discover all such semantic conflicts.

## Questionnaire interaction

The questionnaire separates navigation from delivery. Finish is the filled primary action on every page. AI delegation uses one outlined toggle in the header, with its pending state shown without marking blanks as answered. Navigation follows previous, page selection, next in both DOM and visual order and may pass unanswered questions. On narrow screens Finish occupies a separate full-width row below navigation. The missing-answer prompt appears near Finish and offers delegation or continued editing. Reset sits in a separate row with explicit confirmation. Progress appears on the action actually running. Successful resets and image-dialog closure restore meaningful keyboard focus, and recovery messages have alert semantics without stealing focus from typing.

Core-question pages have one concise direct-answer recommendation, with explicit permission to delegate. The renderer retains authored order so importance does not break dependency sequencing. Accepted submissions have durable identities and separate host receipts. The browser cannot acknowledge on the host's behalf. Because the server returns and closes after submission, the active chat reports receipt and ongoing work. The completion panel offers a resume message containing local run context, never the server token, and a manual-copy fallback. Offline wording distinguishes downloaded files from accepted submissions.

The host saves versioned last-observed checkpoints with a stage, completed-work summary, remaining items, and next action. Each write supplies the questionnaire and answer revisions the host read, rejecting concurrent unseen changes. Old records remain available as history but must not be presented as current after a reset, replacement handoff, or incompatible revisions. Checkpoints support resumption without claiming process liveness. An AI-decision summary is a concise chat update, not a new approval gate.

## Language and persistence

English is the default source language, while runtime content follows the conversation. The host sets the form locale and supplies complete translations where needed. Translation keys and named placeholders remain stable. No fixed list of user languages is imposed.

New runs explicitly record English as the fallback. Existing explicit locales survive question updates that omit a locale. Legacy missing/null locale records retain Korean at read time without a migration of their stored questions or answers.

The browser preserves the active text editor during composition and unrelated save acknowledgements. It keeps drafts while typing and commits at meaningful boundaries such as blur, navigation, export, or submission. Run IDs and baseline revisions prevent unrelated or stale exports from silently overwriting current answers.

## Distribution boundary

Only reusable runtime files enter the installable archive. Source archives also contain explicitly reviewed public examples, their demonstration outputs, synthetic screenshots, tests, docs, and release tooling. Questions, answers, model outputs, screenshots, and machine paths from private projects remain excluded. `.agents/` and `.codex/` are excluded from Git discovery and forbidden by the package allowlist checker. The package does not change host model/effort settings or publish a repository automatically.
