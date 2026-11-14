---
name: any-skill-builder
license: MIT
compatibility: "Requires Python 3.10 or newer and a host agent with filesystem access. Research and visual candidates use the host's available tools."
description: "Use when a user wants to create or improve an agent skill from a rough idea, prompt, or existing skill, discover useful requirements through subject research, or resume an unfinished design questionnaire. Connect researched questions and recorded decisions to an implemented and evaluated skill."
---

# Any Skill Builder

Build the skill the user needs, using researched questions to discover and resolve meaningful choices. The host AI does the research, judgment, question writing, conversations, and final implementation. The bundled Python tool manages records, HTML, submission, and structural checks. It does not call another model or require an API key.

## Help the user get started

When invoked without an actionable task, first reuse any purpose, attachments, or existing run already supplied in the conversation. If the purpose is still missing, briefly explain in the user's language that this skill researches a topic, asks useful design questions, and creates a reusable skill. Offer one short example and ask what task they want the skill to handle. Do not initialize an empty project or display the full workflow just to show help. When a task is already clear, begin it directly; reserve a longer explanation for a request for help. See the packaged [user guide](README.md).

The host controls whether its skill picker shows the supplied short description and starting prompt. Do not claim that selecting a `/` or `$` menu item necessarily sends a message, opens a guide, or translates metadata. The stage updates below apply to actual creation, improvement, or resumption work, not a standalone help response.

## Show progress in chat

Make the current stage visible in the user's conversation language. Use these seven stages as a shared map of the work:

1. **Understand the goal**: identify the intended use, output, environment, constraints, and existing decisions.
2. **Research the subject**: inspect relevant materials and identify supported possibilities and evidence gaps.
3. **Design and review questions**: turn meaningful choices into questions, review their quality, and prepare the questionnaire.
4. **Resolve answers and deferrals**: collect user decisions or authorized AI recommendations, follow active branches, and revisit deferred choices after the full traversal.
5. **Prepare the build plan**: turn valid decisions into the build brief, file responsibilities, and evaluation criteria.
6. **Create the skill**: implement the instructions and any useful references, assets, or executable helpers.
7. **Verify and deliver**: exercise realistic tasks, correct observed problems, check the package, and deliver the requested artifacts with honest limits.

At the start or resume, name the current stage and the immediate work. On a stage transition or a meaningful development, send a short natural update such as "3/7 · Designing questions — I have grouped the key choices and am checking for missing decisions." Report observable work and useful findings, not private reasoning, repeated polling, or an invented completion percentage. The stage number indicates position in the workflow, not elapsed time or a fraction of total effort. Follow the host's progress-update requirements.

Use the same stages for user, auto, hybrid, and chat-only modes. AI delegation remains part of stage 4 and preserves existing answers and deferrals. Say when user input is needed; do not imply that waiting decisions are complete. Branches and revisions may revisit a stage, and verification may return to implementation. Resume from the actual saved state without replaying completed work. If the user requests only a questionnaire or another limited part, complete and deliver that requested part; do not continue into unrequested stages. Keep updates concise and avoid turning stage boundaries into extra approval gates.

After a run exists, save a checkpoint at meaningful stage changes and before a known handoff or interruption, following [references/workflow.md](references/workflow.md). Read the latest status and pass its questionnaire and answer revisions so an unseen concurrent edit cannot be labeled as reviewed progress. Record the observed work, remaining work, and next action. A checkpoint describes the last confirmed state; it is not proof that an agent is still running. Keep user-facing updates conversational and preserve the records needed to resume.

## Start or resume

1. Identify the requested skill's purpose, intended output, target environment, and already-stated constraints from the conversation and supplied materials. Reuse that information instead of asking again.
2. If a run directory was supplied, inspect its `questions.json`, `answers.json`, and `question-review.md` before doing new work. Run `status --workspace RUN --json`, inspect the current handoff and last checkpoint, and continue from the recorded decisions. Check which records are current or stale; a reset, new submission, or later decisions can supersede an earlier request. Inspect a saved `ai-request.json` when relevant. A resume must not replace the questionnaire or reset answers.
3. Choose a separate run directory following the user's storage preferences and available space. Keep run data and generated skills outside this reusable skill's directory and any repository intended for publication. Never replace an existing run merely because its name matches.
4. Use `user` mode by default. An explicit request to decide everything or proceed autonomously selects `auto`; a request for editable AI suggestions selects `hybrid`. Respect the user's selected mode. AI filling is not permission to overwrite user answers or deferrals.
5. Resolve `scripts/skill_builder.py` relative to this SKILL.md. Run Python with `-B` to avoid cache files. Call `init --workspace RUN --goal "..." --mode MODE`. For commands and the submission bridge, read [references/workflow.md](references/workflow.md).

For an existing skill, first inspect its instructions, resources, actual failures, and intended use. Preserve working behavior and the user's decisions. Ask only about material gaps or proposed changes, keep the original as the baseline, and build into a separate output folder. Do not replace the installed original until the update is verified and authorized. Existing run directories from the earlier `skill-builder` name remain valid; the rename does not change run IDs or answer formats.

Use English by default for reusable skill instructions, references, README files, code comments, and package metadata, including newly generated skills. An explicit request for another file language takes precedence. This source-language default does not force English conversation or questionnaires: naturally follow the user's conversation language for questions, choices, interface notices, chat replies, and task outputs. Preserve user-provided text and intentional translation data. Do not add a language-selection question or language picker. The host sets locale metadata and writes translated UI wording itself. Read [references/language-support.md](references/language-support.md) when preparing the form. There is no fixed language allowlist; do not claim that every language has been tested.

## Research the requested subject, then design questions

Read [references/question-design.md](references/question-design.md) before generating questions. Research the **subject of the skill**, not just how to write skills. Use available search, official documentation, primary papers, relevant professional sources, actual GitHub code/issues, and user-provided materials. Prefer a service's connected tool when it can do the job. Do not pretend to have read inaccessible material.

Build a short map of decisions and useful extensions. Include different methods, failure conditions, constraints, and possibilities the user may not have considered. A question needs an identifiable effect on the skill's behavior, inputs, output, constraints, or evaluation. Open-ended discovery questions are valid when their intended use is clear.

Separate decisions needed to design the skill from facts that only the user can supply and inputs that belong to the finished skill's execution. Reuse answers already given in the conversation. Mark decisions that materially change the purpose, method, scope, or required resources with `importance: core`; use `detail` for refinements. Ask core choices before their consequences while respecting dependencies. Core means direct answering is recommended, not required: the user may delegate every unanswered core and detail question to AI. Never infer delegation from a question's importance or invent private facts to complete an answer.

Author the questionnaire following [references/data-contract.md](references/data-contract.md). Maintain stable question IDs, sources, option effects, dependencies, and recommendations with reasons. Question quality is the primary deliverable at this stage:

- Research broadly enough to find important choices; never impose an arbitrary maximum question count.
- Review for missing decisions, redundant questions, leading wording, multiple decisions hidden in one question, implausible options, and facts already supplied.
- For every core decision, record the recommended choice and reason, strongest viable alternative, conditions that would change the recommendation, and conflicts with other choices plus their resolution. Describe how the alternatives change the resulting skill.
- Keep research facts, AI interpretations, proposals, and user-supplied facts distinct.
- Write the review in the run's `question-review.md`: decision coverage, adopted/reworked/merged/dropped candidates and reasons, evidence gaps, and representative answer-to-behavior comparisons. Do not certify quality with a self-assigned numerical score.
- Review core decisions in a separate pass using the goal, sources, and questionnaire, without presenting the author's recommendation as a proven answer. Use an independent agent when available; otherwise label the work as a separate review pass. Correct material omissions, unfair alternatives, or incompatible combinations before presenting the form. Record unresolved evidence gaps without inventing certainty.

Run `set-questions --workspace RUN --input QUESTIONNAIRE` and `validate --workspace RUN`. Fix structural errors before presenting the form. Validation cannot judge whether the questions are insightful.

## Present questions and collect decisions

Use the bundled card form: simple white cards, restrained colors, small counts, previous/next controls, and a page picker. Keep a single secondary AI-delegation toggle above the questions. Give Finish the strongest visual emphasis and make it available on every page; keep previous, page selection, and next as separate navigation controls, and separate reset from the main flow. Navigation may pass unanswered questions and does not submit the form. Do not add a hero, branding, large title, decorative dashboard, or a mandatory introduction. Related questions share pages; long/image questions use more space. Page size is a display choice, not a limit on the questionnaire.

On pages containing core questions, use the form's short guidance encouraging direct answers while explicitly allowing AI delegation. Keep detailed tradeoffs inside the existing recommendation/evidence disclosure. Do not add a required-core-answer gate, per-question warning banners, or an extra approval step.

Use `render` to create a standalone fallback and `serve` for the preferred live form. Open the local URL with an available app/browser tool. While the user answers, keep the serving process and the host task alive and wait in short bounded polls. A submitted form returns an event to **this active host task**, allowing it to continue. Do not claim a static HTML file can wake a closed conversation.

Distinguish saved input, accepted submission, and host receipt. After a submission event or an explicitly imported final file, read the current records and verify the submission identity and versions before acknowledging it through the host CLI. Then tell the user in chat what was received and which stage comes next. The server's acceptance alone does not mean the AI has read or reviewed the answers. The server ends after submission, so continuing progress belongs in chat, not a falsely live HTML indicator. Follow the receipt and resume procedure in [references/workflow.md](references/workflow.md).

The top AI toggle selects a cancellable preference to delegate unanswered questions; it does not send a request or fill answers. Finish sends the current answers and, when selected, an explicit delegation request. If unanswered questions remain without delegation selected, show an inline choice to let AI decide and finish or to continue answering at the first unanswered question. Users do not need to visit the last page. Show delegated blanks as awaiting AI decisions, never as answered. On `ai_requested`, inspect the current record and `ai-request.json`, research any remaining gaps, author reasoned recommendations, and fill eligible missing answers, including newly active branches. Preserve existing answers and deferrals. Do not interpret the request as permission to guess private facts or choose the largest scope. Continue to implementation when ready; unresolved deferrals still require the normal chat discussion. The submitted request asks this active host to work; it does not run a model inside the HTML.

The separate reset action clears all answers, deferrals, and the pending delegation preference while retaining the questions and prior responses in history. It does not automatically delegate to AI. A user who wants AI to decide everything can reset, select delegation, and finish. Never reset merely because a run is incomplete or an AI suggestion is inconvenient.

Use a chat-only path when the user prefers it, the decisions fit comfortably in a short conversation, or a browser is unavailable. Keep the same research, question IDs, conditions, recommendations, counts, and saved records. Present a manageable group of active questions, save each answer or explicit deferral through the CLI, and inspect `status` before choosing the next group. Do not reduce decision coverage to fit the interface. Revisit deferrals only after the full active traversal. See the chat workflow in [references/workflow.md](references/workflow.md).

For `auto` mode, first author genuine recommended answers from the user's goal and research, including rationale and explicit assumptions. Then run `recommend`, inspect the result, and continue to the build if ready. Render the answered form as an inspectable record. In `hybrid` mode, fill suggestions before opening the editable form. Missing recommendations or personal facts are not an excuse to fabricate values.

After completing delegated or automatic decisions, briefly explain the main chosen directions, why they fit the goal, and any remaining assumptions in the user's language. Use the current valid decisions only; preserve user answers and deferrals. This is a progress update, not a request to approve every AI answer. Continue with the authorized work when ready.

For visual decisions, provide actual candidate assets before showing an image question. Use suitable image-generation, search, or UI-rendering tools available in the host. Copy chosen assets into the run's `assets/`, record their provenance, and make comparisons meaningful. Read the image-specific guidance in [references/question-design.md](references/question-design.md). Never substitute unlabeled placeholders for real candidates.

## Resolve deferrals after the full traversal

Every active question permits deferral. Keep unanswered, deferred, and AI delegation distinct. A user deferral cannot be resolved by automatic recommendation filling.

1. Do not interrupt the current questionnaire to revisit deferrals. Wait until all **currently active** questions across all pages are answered or deferred.
2. On `deferred_review`, read the deferred IDs and existing choices. In the chat, ask about desired direction, disliked aspects, missing alternatives, and relevant constraints. Group closely related items to keep the conversation manageable. Do not ask the user to re-enter existing answers.
3. Use that feedback to revise the question or create genuinely new image/other candidates. Explain what changed. Keep old candidates and decisions as history; do not reuse the same unchanged set while calling it regenerated.
4. Import the revised questionnaire with `set-questions`. Preserve stable IDs. The tool invalidates changed questions and affected dependent answers, retaining history. Inspect `status`, reopen the updated form, and let the user select or defer again.
5. A decision may activate further questions. Present them in the next traversal and update the count. Do not answer them by guessing what a deferred parent means.

Repeat as needed. If the user's desired direction is still unclear, narrow the chat discussion rather than silently choosing or removing the feature. Independent parts may be drafted, but material unresolved deferrals do not become final decisions.

## Build the actual skill and demonstrate its behavior

When `status` reports `ready_to_build`, run `brief --workspace RUN`. Use the resulting `build-brief.md` and source records; inactive or obsolete answers must not affect the implementation. Read [references/build-and-evaluate.md](references/build-and-evaluate.md).

Create `RUN/output/<skill-name>/SKILL.md` and a concise user-facing `README.md`, plus only the useful references, assets, and executable helpers. Every newly generated skill must include its usage guide in the installable package. Explain what to provide, how to ask, and what to expect, using examples that match the implemented capabilities. Include short picker metadata only when supported by the target host, and teach the generated skill to give brief help on an otherwise empty invocation while starting clear tasks directly. Follow the usage-guidance checklist in [references/build-and-evaluate.md](references/build-and-evaluate.md). Use the target environment's actual tools and supported skill format. Do not include scripts just because this creator contains scripts. Use compact shared instructions and load substantial subject-specific references only when needed.

Write the created reusable files in English unless the user explicitly requests another file language. In those instructions, require natural, conversational task outputs that mirror the user's language and level of politeness, explain judgments in connected prose, and preserve evidence and uncertainty. Apply that behavior to chat replies and prose inside generated documents or HTML. Follow an explicitly requested output language or formal genre when present. Read the writing guidance in `references/build-and-evaluate.md`; do not turn this distinction into a language picker or another questionnaire question. Choose any helper's programming language from the task and available runtime; this builder's Python implementation is not a requirement for the skills it creates. Keep format keys and command identifiers intact when translating prose.

Whenever a generated skill includes analysis, require its explanations to be easy to read, intuitive, and useful. Connect what a finding means, why it matters, its evidence and limits, and the decision or next action it informs. Use concrete examples when they clarify a difficult idea. Preserve useful depth and accuracy without relying on dense jargon or a mechanical list of findings.

Record `RUN/design.json` mapping selected question IDs to features, generated files, and evaluation cases. Run the structural `check-skill` command and execute any new helper scripts with meaningful inputs. Test the created skill on realistic tasks and relevant failure cases, including whether different answers produced the intended differences. Make corrections supported by observed failures. Report what was and was not exercised.

For repeatable checks and comparison reports, read [references/evaluation.md](references/evaluation.md) and use `scripts/evaluate_skill.py`. Keep question quality, selected-answer-to-behavior checks, and final task outcomes distinct from code mechanics. This helper checks recorded artifacts and evidence; the host still performs the tasks and reviews judgment-dependent outcomes. Compare an earlier skill or no-skill baseline only under matched conditions. Existing evaluation tools may be used when available, without making another skill or a particular model provider a requirement.

Before packaging, remove user-specific assumptions from reusable instructions. Use relative resource paths and configurable work directories; keep answers, research logs, credentials, generated user assets, and machine-specific paths out of public packages. Include only useful runtime files and the selected license; keep tests and maintainer documentation in the source repository. Verify archive contents and test the extracted package.

Deliver the skill folder, a link to its usage guide, a copyable starting request, validation result, and any remaining material limitation. Preserve the run so the user can request changes later. Installation or publication is separate from generating a package; follow the user's existing authorization and host conventions. Never imply that untested features, unavailable sources, or a merely rendered form prove the final skill works.

## Judgment and execution settings

Use substantial reasoning for subject synthesis, question design, contradiction checks, and difficult implementation/evaluation. Model effort is controlled by the host; writing "think deeply" in a skill does not change that setting. Preserve the user's selected model/effort and never silently edit global settings or switch to another provider. If the host can expose actual model/effort, record it for meaningful comparisons; otherwise record that it was not exposed.

Research and revision should stop when important decisions have adequate support and further work is not adding useful information. A time/tool limit ends a run segment, not the user's decision: record the completed work and gaps so it can resume. Do not translate a limit into invented evidence, hidden question deletion, or automatic resolution of user deferrals.
