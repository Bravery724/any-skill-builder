# Review the current questions

Use this procedure after `set-questions` and before presenting a questionnaire or applying AI recommendations. The host performs the review. `review_questions.py` prepares a pending record and checks its binding, coverage, references, and recorded outcomes; it does not call a model or decide whether the questions are good. Both modes use the same review without adding HTML or a human approval step to Full Auto.

## Prepare, review, and accept

Resolve `SCRIPT` to this skill's `scripts/skill_builder.py` and `REVIEW_SCRIPT` to `scripts/review_questions.py`. `RUN` is the existing private run directory. Review the canonical file after import because `set-questions` manages identities, versions, and serialization.

```text
python -B SCRIPT set-questions --workspace RUN --input AUTHORED_QUESTIONNAIRE_JSON
python -B SCRIPT validate --workspace RUN
python -B REVIEW_SCRIPT prepare --questions RUN/questions.json --out RUN/question-review-draft.json
```

`prepare` writes `status: "pending"`, not a successful review. It refuses to overwrite an existing destination. Read the user's request, original requirements, inspected evidence, and every question and option. Complete the generated template in place or save a separate reviewed copy. Keep useful candidate reasoning in `RUN/question-review.md`; the accepted machine-readable record is `RUN/question-review.json`.

```text
python -B REVIEW_SCRIPT check --questions RUN/questions.json --review REVIEWED_JSON
python -B SCRIPT accept-review --workspace RUN --input REVIEWED_JSON
python -B SCRIPT status --workspace RUN --json
```

`check` exits `0` only for a passing record, `1` for a missing, pending, stale, invalid, or needs-revision record, and `2` when preparation or questionnaire reading fails. Inspect its findings. `accept-review` validates again against the current canonical file, stores the accepted JSON, and enables the review policy. A reported pass means the required judgments were recorded; it does not establish their truth.

New CLI `init` runs default to required review. Runs from earlier versions without a policy remain compatible. Enable the policy on an older run with `python -B SCRIPT require-review --workspace RUN`; this preserves its questions and answers. `init --review-policy legacy` is reserved for explicit structural fixture previews, not a shortcut around review for new authoring. CLI `restore` enables review on the recovered run; saved answers remain intact while the host reviews the recovered questions.

Required review gates `render`, `recommend`, and `brief`; status reports the review and does not call the run ready to build until it passes. Any change to `questions.json` bytes, including presentation or localization edits, makes the old SHA-bound record stale. Prepare a new template at a new path, review the changes and current coverage, then accept it. Do not paste in a new hash to imply a review occurred. Review operations do not reset answers; ordinary question-version and dependency rules still determine which answers a substantive edit invalidates.

## Complete the generated record

Preserve the generated field names and exact schema. Write explanatory statements, reasons, summaries, and finding text in the conversation's language; IDs and enum values remain unchanged. Reusable source documentation stays English unless requested otherwise.

| Field | Required review work |
| --- | --- |
| `questions_sha256` | Preserve the generated lowercase SHA-256 of the exact canonical questionnaire bytes. |
| `reviewer` | Set `identity` and `relationship`: `separate`, `self`, or `unknown`. A separate Agent call alone proves neither fresh context nor blind review. Record actual access and limits in the relevant reasons or review notes. |
| `requirements` | Preserve the one exact original `goal` invariant. Add every explicit constraint as `{id,statement,basis:{kind,reference,evidence}}`. `kind` is `goal`, `user`, or `source`; a source reference is a defined source ID. User references identify the supplied request or material. |
| `question_reviews` | Review every question once and list every authored option ID in `option_ids`; text questions use `option_ids: []`. Include every declared requirement ID exactly once in `requirement_ids`. Explain whether all offered choices preserve them; explain irrelevance in the reason rather than omitting a requirement. |
| `combinations` | For two or more questions, complete both `recommended` and `contrast` scenarios as described below. |
| `no_combinations_reason` | For one question, explain why a multi-decision combination does not apply and leave `combinations` empty. Otherwise leave this reason empty. An empty run may have a pending template, but a completed zero-question review cannot pass. |
| `localization` | Match the resolved locale `language`, retain the complete generated `fields` inventory, and review the actual text at every path. List only permitted original-language titles or quotations in `original_language_fields`. |
| `fair_alternatives` | Cover every question ID and assess whether viable alternatives receive fair, meaningful descriptions of effects and costs. |
| `unknown_private_facts` | Cover every question ID and verify that unknown accounts, budgets, equipment, permissions, and other private facts remain unknown or become required runtime inputs. |
| `findings` | Retain concrete issues and their resolutions. Each item has `id`, `status`, `area`, `question_ids`, `description`, and `resolution`. An open finding prevents a pass. |

Review outcome fields use `pending`, `pass`, or `needs-revision`. Every completed section needs a substantive `reason`; the overall `status` has no reason field. A finding uses `open` or `resolved`, with area `requirements`, `options`, `combinations`, `localization`, `fair_alternatives`, or `unknown_private_facts`. A resolved finding needs a nonempty resolution grounded in the actual correction. Keep earlier review files when revisions require a new template. Do not change every status to pass merely to satisfy the gate.

Keep fixed requirements outside the selectable options. A prohibited choice must not appear as an ordinary alternative, even "for transparency" or labeled not recommended. For example, if owners must come from supplied notes, alternatives may differ in how they represent a missing owner, but cannot offer to infer one from the topic. A meaning-preserving paraphrase is a viable alternative to a direct quote when conditions, dependencies, uncertainty, and attribution survive. Keep limits at their actual scope: a maximum per note is not a maximum across an entire batch.

The checker ensures referenced coverage, but cannot discover omitted user requirements, judge a paraphrase, or prove that the reviewer inspected the text. The host must perform those checks before recording pass.

## Review combinations and language

Each combination contains `kind`, `answers`, `inapplicable_question_ids`, `fewer_decisions_reason`, `requirement_ids`, `status`, and `reason`. Every combination must reference every declared fixed requirement exactly once; explain a requirement's lack of effect in the reason instead of skipping it. An answer is `{question_id,value}`. A custom value may add both `branch_value` and `branch_rationale` when needed to resolve its conditional branches. Values must obey ordinary answer rules, including minimums, maximums, and exclusivity.

Use recorded recommendation values for the `recommended` scenario wherever a recommendation exists. The `contrast` scenario must change at least one shared decision and remain useful under the same fixed requirements. Inspect interactions among decisions, not just each answer separately. Cover at least two active decisions in each scenario; if only one can be active, every other question must be explicitly inactive and `fewer_decisions_reason` must explain why. `inapplicable_question_ids` must exactly identify the inactive questions for that scenario. Do not count a waiting branch as inactive or include an answer to an inactive question. Prefer complete, coherent scenarios covering the relevant active path, with clear reasons for the chosen tradeoffs.

Read the exact effects of every selected option together. A passing reason must describe behavior those questions actually allow; it cannot introduce a hidden override or exception. If one option says "artifact only" and another says "warnings only in chat", moving the warning into the artifact in the review is not a correction. Revise the canonical questions to state a consistent destination, condition the conflicting option, or make the precedence visible in the affected options. Repeat review against the new bytes before accepting it. Check applicable alternatives beyond the two recorded scenarios when their output channels, formats, scope, or provenance rules interact; the minimum recorded scenarios are not exhaustive combination coverage.

For numerical limits, state the unit and transformation explicitly. A source note, an exported note record, and the cards generated from that record are different units; a format that produces a pair cannot silently satisfy a one-card limit by counting it as one record. Keep per-source and per-batch limits distinct, and expose any exception or priority in the affected question's wording before accepting the combination.

The localization inventory uses JSON Pointer paths into the canonical questionnaire. Inspect the goal, group labels, source notes and `accessed_at`, question titles/help/decision/placeholder text, option labels/descriptions/effects/traits, recommendation rationale/assumptions and text/custom values, and authored locale messages. Preserve precise dates and timestamps while checking their displayed context. Source titles and explicit `quote`/`quotes` fields may remain in their original language and should be identified in `original_language_fields`; invented exemptions for authored explanations are not allowed. Preserve exact source quotations and user text. See [language-support.md](language-support.md) for UI dictionary and composition checks.

A populated inventory establishes which fields were covered, not that they were translated accurately. Inspect the final generated wording and layout when relevant, and report unperformed browser or native input checks separately.
