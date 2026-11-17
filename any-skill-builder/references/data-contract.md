# Questionnaire and response data

Use `schema_version: 1` for the questionnaire, answer envelope, and Full Auto decision list. Canonical files are `questions.json`, `answers.json`, and, for Full Auto, `decisions.json`. Author question changes in a separate file and import them with `set-questions`; do not hand-edit history or versions to bypass validation.

## Minimal questionnaire

```json
{
  "schema_version": 1,
  "project_id": "paper-study",
  "revision": 1,
  "goal": "Create a paper analysis skill that develops testable ideas",
  "mode": "questionnaire",
  "locale": {"language": "en", "direction": "ltr"},
  "groups": [{"id": "scope", "label": "Goal and scope"}],
  "sources": [],
  "questions": [
    {
      "id": "q-scope",
      "version": 1,
      "group_id": "scope",
      "type": "single",
      "importance": "core",
      "title": "Which sources should the skill compare?",
      "help": "The scope determines which evidence the analysis can use.",
      "decision": "Choose the evidence scope of the generated skill",
      "origin": "proposal",
      "source_ids": [],
      "options": [
        {"id": "paper", "label": "Supplied papers", "effect": "Analyze supplied material and mark unverified external claims"},
        {"id": "related", "label": "Related research as well", "effect": "Compare relevant prior and subsequent research"}
      ],
      "recommendation": {
        "value": "related",
        "rationale": "Comparisons can reveal useful gaps; use supplied material when external access is unavailable.",
        "assumptions": ["External research is within the requested scope"]
      },
      "when": []
    }
  ]
}
```

This is original proposal text, not evidence that subject research happened. Link actual inspected sources for research-backed questions.

## Questionnaire fields

| Field | Meaning |
| --- | --- |
| `project_id` | Human-readable identifier matching the initialized run. A folder name alone does not establish identity. |
| `run_id` | Immutable UUID created by `init`. Authored questions may omit it; saved exports must retain it. |
| `revision` | Questionnaire revision managed by the helper. |
| `mode` | `auto` or `questionnaire`. A fixture rebound into an empty run retains the initialized mode. Ordinary updates must match the run; `set-questions --from-decisions` is the one switch, from a Full Auto decision list to a questionnaire. |
| `locale` | `{language,direction,messages?}`; see [language-support.md](language-support.md). |
| `groups` | Ordered `{id,label}` objects. Pagination does not limit total questions. |
| `sources` | Source records with ID, title, kind, access status, notes, and URL or user-material identifier. |
| Question `id` / `version` | Stable decision identity and helper-managed content version. |
| `type` | `single`, `multi`, `text`, or `image`. |
| `importance` | Optional `core` or `detail`. Core recommends direct input but does not require it. |
| `decision` | How the answer changes the finished skill. |
| `origin` | `source`, `inference`, `proposal`, or `user`. |
| `source_ids` | References to defined sources; empty is valid for original proposals or user preferences. |
| `recommendation` | Valid `value`, meaningful `rationale`, and explicit `assumptions`. This is not a user answer. |

Sources use `{id,title,url,kind,status,accessed_at,notes}`. Status is `read`, `partial`, or `unavailable`. HTTP(S) source URLs are supported. For user material without a URL, use a meaningful title, optional path, and notes. Record source versions when they affect interpretation. Unknown access is not a claim of reading.

Each ordinary option has an ID, label, behavioral effect, and optional description. A multi-select option such as "none" that cannot coexist with other choices must use `exclusive: true`. The helper does not infer that from the label:

```json
{"id": "none", "label": "No extra sections", "effect": "Return only the required output", "exclusive": true}
```

A sole explicitly exclusive option is a complete ordinary answer even when `min_choices` exceeds one. It cannot be combined with any other option or nonempty Other text. Ordinary selections still obey their minimum and maximum; the word "none" without `exclusive: true` has no special validation behavior.

Image options include `image: "assets/filename.png"` and optional `traits`. Use real run-owned files and meaningful captions. The helper records `image_sha256`; changing image bytes requires a new `set-questions` import so obsolete choices are invalidated. Do not forge image hashes or use arbitrary absolute paths.

## Ordinary and custom values

| Question | Ordinary value | Custom value |
| --- | --- | --- |
| Single / image | One option ID | `{"other":"Custom direction","selected":[]}` |
| Multi | List of distinct option IDs | `{"other":"Additional direction","selected":["option-id"]}` |
| Text | Nonempty text | The same text input; no duplicate Other field |

Every choice/image question has a built-in **Other — describe** control. Do not add a fake image or a second conditional text question solely to create that control. An explicit ordinary "none" option remains a meaningful answer; a blank is different and is left for AI.

A multi-select custom value retains ordinary selections alongside the text. Respect selection limits and exclusive options. Incomplete choices remain inspectable rather than being silently discarded or counted as a completed valid decision. Use the supported `complete-input` workflow when AI must finish a partial selection while retaining human choices.

Older HTML files may have stored a sole exclusive selection as an incomplete draft. Import and reopening recover that unambiguous selection as a user answer. Conflicting answer records, invalid combinations, and stale answer baselines remain protected; this recovery does not replace a newer cleared answer. A valid exclusive answer is not pending work for `complete-input`.

The browser records text without deciding whether it is sensible. The host reviews meaning after import. Do not use text length or punctuation alone to reject it. Meaningful "none", `0`, specialist terms, unusual preferences, and rejection of the displayed choices must be honored.

## Conditions

`when` is an ALL list. Empty means unconditional:

```json
[{"question_id":"q-scope","equals":"related"}]
```

For a multi-select parent, use `includes` with an option ID. Referenced questions and option IDs must exist; cycles are invalid. Active answered parents can enable or disable a child. Unanswered parents leave children waiting rather than implying false.

Custom answers may need a host interpretation before a predefined branch can be evaluated. Use `interpret-answer` with a reason to record the applicable ordinary branch value or JSON `null` when none matches. Preserve the user's original custom text. Do not silently force custom preferences into a preset.

Parent changes can invalidate dependent answers. Inspect current status; a value remaining syntactically valid does not make its old context valid. Inactive answers do not control the final build.

## Answer envelope

```json
{
  "schema_version": 1,
  "project_id": "paper-study",
  "run_id": "<the initialized run_id>",
  "revision": 1,
  "answer_revision": 0,
  "answers": {
    "q-scope": {
      "status": "answered",
      "value": "related",
      "actor": "user",
      "rationale": "",
      "question_version": 1
    }
  },
  "history": []
}
```

Absence means unanswered. Active records identify their author as `user` or `ai`; AI decisions retain their rationale. The current format has no special defer answer. AI recommendation filling cannot overwrite meaningful user-owned choices.

The helper increments `answer_revision` when it accepts a change. Saved HTML carries its original baseline revision; it must not invent a newer revision. Imported files must match the run, project, question revision, and accepted answer baseline. Explicit clears and resets must remain clears, not be resurrected from browser storage or an older export.

For clearly unusable custom/text input, `resolve-input` retains the raw input and rationale in history before allowing the unresolved part to be decided by AI. Meaningful ordinary selections remain protected. This command requires host judgment; it is not an automatic language or content filter.

## Saved HTML

The standalone file contains a `<script id="skill-builder-data" type="application/json">` block. The importer reads that data without executing the document.

Its versioned wrapper includes:

- `format: "any-skill-builder-questionnaire"` and `format_version: 1`.
- `saved_at` and a unique `export_id` when Save answers creates an answered file. An untouched template is not a saved answer export.
- `base_answer_revision` and `questionnaire_sha256` for baseline/content checks.
- `view`, including the questionnaire and answer envelope.
- Resolved `locale` and registered `assets` embedded as data URLs.
- `resume` hints with the original workspace, HTML path, run ID, and project ID.

Path hints help locate known work; they are not permission to write to arbitrary paths. Restoration uses an explicit new destination. Text and JSON must be escaped safely when embedded. Image validation and safe relative asset paths still apply.

Reopening a saved HTML uses the state embedded in that file. It must not replace deliberately cleared answers with an older local browser draft. Saving can happen on any page; blank questions remain blank until the host resolves them.

`import-answers` validates a saved export before applying it. `resume` checks the known path and matching saved siblings without silently choosing conflicting versions. Re-importing the same export is idempotent and does not erase later AI decisions. Use [workflow.md](workflow.md) for commands and conflict handling.

## Status and progress

`status --json` exposes the questionnaire, canonical answers, dependency states, counts, and build readiness. Plain status is a compact summary.

- **Active** questions currently apply.
- **Waiting** questions need an unresolved parent or interpretation.
- **Inactive** questions are outside the current branch.
- **Ready to build** means the applicable design choices are valid and unresolved required decisions no longer block the build.

Counts must distinguish active questions from all defined candidates and waiting branches. Saving an incomplete HTML is valid; it does not make all of its questions answered.

A checkpoint records the last observed stage, work, remaining items, next action, time, and exact question/answer revisions. It is not a heartbeat or quality certificate. Research, raw answers, paths, histories, and checkpoints are private run material, not reusable skill package contents.

## Full Auto decision list

Full Auto records its decisions in `RUN/decisions.json` instead of a questionnaire. It keeps the judgment (question, alternatives, choice, reason, evidence) and drops the text a person needs to choose on screen. Import it with `set-decisions`; do not hand-edit the stored copy.

```json
{
  "schema_version": 1,
  "language": "en",
  "requirements": [
    {"id": "staged-only", "statement": "Write the message from staged changes only", "basis": "user request"}
  ],
  "sources": [
    {"id": "git-diff", "title": "git diff documentation", "url": "https://git-scm.com/docs/git-diff",
     "kind": "official documentation", "status": "read", "accessed_at": "2026-11-15",
     "notes": "--cached shows only staged changes"}
  ],
  "decisions": [
    {
      "id": "empty-staging",
      "question": "What should happen when nothing is staged?",
      "affects": "The skill's behavior when the staging area is empty",
      "importance": "core",
      "origin": "source",
      "source_ids": ["git-diff"],
      "options": [
        {"id": "stop", "label": "Say so and stop", "tradeoff": "No risk of a wrong message; the user reruns after staging"},
        {"id": "suggest", "label": "Also suggest what to stage", "tradeoff": "Convenient, but reads unstaged files that may hold secrets"}
      ],
      "choice": "stop",
      "reason": "The message must match what will actually be committed",
      "assumptions": []
    }
  ],
  "check": {
    "reviewer": "self",
    "requirements_preserved": {"status": "pass", "reason": "Every choice reads staged changes only"},
    "no_forbidden_choices": {"status": "pass", "reason": "The option that reads unstaged files was considered, not chosen"},
    "no_invented_private_facts": {"status": "pass", "reason": "No account, budget, or private resource is assumed"},
    "revisions": 0,
    "known_limits": []
  }
}
```

| Field | Meaning |
| --- | --- |
| `language` | Optional language tag of the explanatory text; defaults to the run's locale. |
| `requirements` | What the request already fixes, one line each, with its `basis` (user request, supplied material, or a source ID). These are not decisions. |
| `decisions` | Use an empty array when the fixed requirements settle every material choice. Include at least one fixed requirement with its basis. The three checks still apply. |
| `sources` | Same records as questionnaire sources. |
| `decisions[].type` | `single` (default), `multi`, or `text`. Image choices need a questionnaire. |
| `decisions[].options` | At least two genuinely considered alternatives for choice types, each with `id`, `label`, and `tradeoff`. `exclusive`, `min_choices`, and `max_choices` work as in questions. |
| `decisions[].choice` | A value with the same shape as a questionnaire answer, including `{"other":"...","selected":[]}` for a direction outside the listed options. Required for every active decision. |
| `decisions[].when` | Optional conditions on other decisions, as in questions. An inactive decision needs no choice. |
| `check` | The single check. Each of the three items has `status` (`pending`, `pass`, `needs-revision`) and a `reason`. `revisions` counts revision rounds (Full Auto allows one). `known_limits` lists concerns left open, to report at delivery. |

`set-decisions` reports `ready_to_build` only when every active decision has a choice and all three checks pass. A recorded `revisions` above one adds a note; it is not an error.

If the decision list is empty, conversion reports `no_questions_to_convert` and keeps the run in Full Auto. If the user reopens a choice, update the requirements and record the choice with `set-decisions` before converting.

The fields map one to one onto the questionnaire, so `decisions-to-questions` can build a questionnaire without new judgment:

| Decision list | Questionnaire |
| --- | --- |
| `question` | question `title` |
| `affects` | question `decision` |
| `options[].tradeoff` | `options[].effect` |
| `choice`, `reason`, `assumptions` | `recommendation.value`, `.rationale`, `.assumptions` |
| `id`, `type`, `importance`, `origin`, `source_ids`, `when`, `group_id`, `groups`, `sources` | same names |
| `requirements` | printed by `decisions-to-questions` and copied into the question review's `requirements` by `prepare` |

Only display text is added after conversion: question `help`, option descriptions where the effect is unclear, and group labels.
