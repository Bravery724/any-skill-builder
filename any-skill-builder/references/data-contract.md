# Questionnaire and response data

Use `schema_version: 1`. The canonical files in a run are `questions.json` and `answers.json`. Author question input in a separate file; `set-questions` validates it and manages revisions. Do not hand-edit response history to bypass validation.

## Minimal questionnaire

```json
{
  "schema_version": 1,
  "project_id": "paper-study",
  "revision": 1,
  "goal": "Create a paper analysis skill that develops testable ideas",
  "mode": "user",
  "locale": {"language": "en", "direction": "ltr"},
  "groups": [{"id": "scope", "label": "Goal and scope"}],
  "sources": [],
  "questions": [
    {
      "id": "q-scope",
      "version": 1,
      "group_id": "scope",
      "type": "single",
      "title": "Which sources should the skill compare?",
      "help": "The research scope determines which evidence the analysis can use.",
      "decision": "Choose the evidence scope of the generated skill",
      "origin": "proposal",
      "source_ids": [],
      "options": [
        {"id": "paper", "label": "Supplied papers", "effect": "Analyze supplied sources and explicitly mark unverified external claims"},
        {"id": "related", "label": "Related research as well", "effect": "Search for and compare relevant prior and subsequent research"}
      ],
      "recommendation": {
        "value": "related",
        "rationale": "Comparisons may expose useful gaps for new ideas; use supplied material when external access is unavailable.",
        "assumptions": ["External research is within the requested scope"]
      },
      "when": []
    }
  ]
}
```

The example is original proposal text, not a claim that subject research has happened. Real research-backed questions should include inspected sources and an honest origin.

## Fields

- `project_id`: human-readable project identifier. Match the initialized run; use lowercase letters, digits, and hyphens for portability. Different directories may share this name.
- `run_id`: immutable UUID created by `init` in both canonical files. Authored questionnaire input may omit it; `set-questions` preserves the initialized value. Never copy another run's ID to make its answers importable. Exports and browser storage are bound to this ID, independently of the project name.
- `revision`: questionnaire revision, managed on import by `set-questions`.
- `mode`: `user`, `auto`, or `hybrid`.
- `locale`: `{language,direction,messages?}`. `language` is a language tag, `direction` is `ltr` or `rtl`. Korean and English UI dictionaries are bundled; other languages use a complete translated dictionary with the same message keys and named placeholders. See `language-support.md`. This sets the form language, independently of the generated skill's output language.
- `groups`: ordered `{id,label}` objects; the form splits long groups into pages without limiting total questions.
- `sources`: `{id,title,url,kind,status,accessed_at,notes}`. `status` is `read`, `partial`, or `unavailable`. If present, `url` must be an HTTP(S) URL. For user materials, omit `url` (or use an empty string) and put a meaningful identifier in optional `path`, `title`, or `notes`. Notes identify relevant evidence, source version when needed, and limitations.
- Question `id` and `version`: stable identity plus content version. Preserve ID when revising the same decision.
- `type`: `single`, `multi`, `text`, or `image`.
- `importance`: optional `core` or `detail`; omitted values behave as `detail`. Use `core` for decisions that materially change the skill's purpose, method, scope, or required resources. This controls concise guidance only, not validation, answer ownership, or permission to delegate. Every unanswered core question can be assigned to AI through the normal delegation flow. Order groups and questions deliberately; importance does not reorder them. When changing only this guidance on answered questions, use the explicit `set-questions --presentation-only` path to preserve their answers; unmarked changes use normal invalidation.
- `decision`: how the answer changes the eventual skill.
- `origin`: `source`, `inference`, `proposal`, or `user`.
- `source_ids`: references to defined source IDs. Empty is legitimate for user preferences/original proposals, not a substitute for required subject research.
- `options`: IDs, labels, optional descriptions, and behavioral `effect`. `single`/`image` answers are option IDs; `multi` answers are a nonempty list of valid distinct option IDs. Include an explicit "none" option when appropriate rather than treating blank as an answer.
- Image options add `image: "assets/filename.png"` and may add `traits: ["...", "..."]`. Use relative run-owned files and meaningful captions; do not pass arbitrary absolute paths. The backend records `image_sha256` on import. After changing image bytes, run `set-questions` again so the new image invalidates obsolete selections. Do not forge the stored hash.
- Text answers are actual nonempty text. The user can type no additional preference or defer instead of having emptiness silently counted as answered.
- `recommendation`: valid `value`, `rationale`, and explicit `assumptions`. Its presence is not a user choice.

## Conditions

`when` is an ALL list; empty means an unconditional question:

```json
[{"question_id":"q-scope","equals":"related"}]
```

For a multi-select parent use `includes` with an option ID. Referenced questions and expected values must exist; cycles are invalid. Active answered parents can enable or disable the question. An unanswered or deferred parent leaves it waiting, not implicitly false.

Changing a parent may invalidate dependent answers. Inspect the returned state rather than reusing a previously selected value because it still looks syntactically valid. Waiting and inactive questions are not included in active completion counts or generated design decisions.

## Answers

```json
{
  "schema_version": 1,
  "project_id": "paper-study",
  "run_id": "<copy the initialized run_id>",
  "revision": 1,
  "answer_revision": 0,
  "answers": {
    "q-scope": {
      "status": "answered", "value": "related", "actor": "user",
      "rationale": "", "question_version": 1
    }
  },
  "history": []
}
```

`status` is `answered` or `deferred`; absence is unanswered. Deferral has no active value. `actor` is `user` or `ai`. AI answers retain their rationale. No AI recommendation operation may overwrite user answers or user deferrals.

For a deferred answer, `rationale` may hold an optional user-provided reason. An "Other" choice is a normal stable option ID followed by a conditional text question; it is not a deferral and must not silently select a preset.

The backend increments `answer_revision` when it accepts a change. Browser/offline edits carry their loaded revision as the baseline; they must not invent a newer revision. Imports require matching `run_id`, project, questionnaire revision, and baseline answer revision. History is maintained by the backend. A live clear action sends `{question_id: null}` in the `changes` map, using the actual ID as the key.

## Handoff and last progress

`handoff.json` records an accepted normal submission or AI-delegation request with its `request_id`, run/project identity, questionnaire revision, answer revision, and timestamp. A host receipt is added only by the explicit `acknowledge` command after the host reads that exact accepted state. Browser storage, downloading, and HTTP acceptance do not imply acknowledgment. Imported ordinary answer files remain drafts until an explicit `submit` registers the completed traversal; delegated request files use `delegate`.

`progress.json` records the host's last observed stage, summary, remaining work, next action, time, and versions. Creating a checkpoint requires the exact questionnaire and answer revisions the host just read; a concurrent change rejects the write instead of attaching an old summary to unseen answers. A checkpoint may refer to an acknowledged handoff. These records retain prior history and are private run data; do not place them in the generated skill or public package. Read the `workflow` portion of `status --json` to distinguish records that are current from those superseded by later edits, resets, or submissions. Neither a receipt nor a checkpoint certifies quality or proves an agent is still running. See [workflow.md](workflow.md) for commands and resumption rules.

## View and transition

CLI `status --json` and the live server return `questionnaire`, canonical `answers`, per-question `states` (`active`, `waiting`, `inactive`), counts, `traversal_complete`, and `ready_to_build`. Plain `status` returns a concise summary instead of the full view.

- `traversal_complete`: no unanswered active questions, including all pages.
- `ready_to_build`: traversal complete, no active deferrals, and no unresolved waiting decisions.
- `deferred_review`: full traversal completed but user decisions still need chat discussion.

Validate the latest view before building. Display current active totals honestly; do not represent all potential branches as currently unanswered or assume that the currently known total can never change.

## Explicit workflow requests

AI delegation is a workflow request, not an answer status or an implicit recommendation click. Its scope is `unanswered`: answered and deferred records remain protected. The live server returns `ai_requested` to the active host. An offline form exports an explicit request for the host CLI to validate and apply; a downloaded file cannot wake a closed conversation.

Reset is a separate explicit user action. It removes current answer/deferral records, preserves the questionnaire and run identity, and archives previous responses. Stale and foreign requests must fail before changing records. Reset alone does not imply delegation. The form's pending changes and offline reset intent are part of the import protocol, not permission to bypass baseline revision checks. See [workflow.md](workflow.md) for the CLI handoff.

## Browser recovery drafts

When unfinished multi-select choices exist, a recovery download uses `{action: "restore_draft", answers: <canonical answer envelope>, partial_multi: {<question_id>: [<option_id>, ...]}, reset_pending: <boolean>}`. These selections are browser drafts, not valid answers or permission to delegate. The form validates identity, versions, question types, option IDs, and incomplete selection counts before restoring them. Existing reset intent remains explicit; recovery does not authorize a new reset by itself.

Load this file through the matching standalone/offline questionnaire's import control to continue editing, then use Finish to create the normal completed-answer or delegation-request file. The live form does not expose that import control. If necessary, the host can render an offline copy of the existing run, without resetting it. Identity and revision checks still apply; never bypass them or silently merge a stale draft over newer decisions.

Do not pass a browser recovery file to `import-answers`, `submit`, or `delegate` as a completed handoff. Ordinary Finish downloads and AI-request formats remain unchanged. If a user tries to import a `delegate_unanswered` request into the form, direct them to the skill-building chat without executing the request or replacing current answers.
