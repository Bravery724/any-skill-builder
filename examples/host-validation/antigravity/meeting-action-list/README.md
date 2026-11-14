# Meeting Action List (`meeting-action-list`)

`meeting-action-list` turns rough meeting notes, live scratchpads, chat dumps, or transcript excerpts into a structured, auditable Markdown action-item table—preserving explicit owners, deadlines, prerequisites, and verbatim source quotes while flagging missing, ambiguous, or conflicting details.

## What to provide

- **Required**: Rough meeting notes, bullet fragments, chat messages, or a transcript excerpt.
- **Optional details that improve output**:
  - **Meeting or reference date** (for example, `Meeting date: 2026-05-05, Tuesday`) so unambiguous relative phrases like `"by this Thursday"` can be paired with an exact `YYYY-MM-DD` date.
  - **Layout or sorting preference** if you want a `- [ ]` task checklist, mobile-friendly bullet blocks, or owner-grouped sorting instead of the default source-ordered Markdown table.
  - **Follow-up clarifications** in a second turn (such as naming a single primary owner or resolving a conflicted date) to produce a clean updated table.

## Quick start & examples

All examples below are fictional. Paste your notes directly in chat using your normal skill invocation or plain request:

### 1. Starting request (rough notes with gaps and conflicts)
```text
Use meeting-action-list to extract action items from these notes:

Beacon Release Sync — 2026-06-02 (Tuesday)
- Devon: I'll publish the v2 webhook retry guide by this Thursday.
- Kira and Owen to run failover drills after Infra finishes the subnet migration (due next Wednesday).
- Rotate staging API tokens ASAP.
- Line 9: Talia to send customer migration FAQ on 2026-06-08.
- Line 18: Marcus to send customer migration FAQ on 2026-06-08.
- Maybe prototype a usage-alert digest in Q3?
```

### 2. Follow-up refinement (resolving flagged items)
```text
Update the action list: Kira is the primary owner on failover drills (due 2026-06-10), Devon owns rotating staging tokens by 2026-06-04, and Talia owns the FAQ (Marcus is only reviewing).
```

### 3. Requesting an alternate layout on the fly
```text
Format that updated action list as a Markdown "- [ ]" checklist grouped by owner so I can paste it into our issue tracker.
```

## What you will receive

By default, the skill returns:
1. **A short conversational summary** of confirmed commitments, tentative follow-ups, and key items needing confirmation.
2. **`Action Items` table** ordered as items appear in your notes, with columns for `#`, `Action Item` (including any stated prerequisites), `Owner`, `Deadline`, `Source Quote` (a short verbatim snippet on every item), and `Flags & Notes`.
3. **`Tentative / Needs Confirmation` table** (when brainstorming or unconfirmed prompts appear) so loose ideas stay separate from firm commitments.
4. **`Missing & Conflicting Details`** highlighting the practical implications and ambiguities behind flagged items by `#ID` (without repeating full table rows or source quotes).
5. **`Blockers & Dependencies`** calling out upstream bottlenecks and task sequencing by `#ID`, plus **`Clarification Questions`** asking directly for the missing decisions whenever flags exist.

## Honest limits & scope

- **No silent guessing**: The skill will not invent owners, convert unanchored deadlines (`"by Friday"` with no meeting date), guess across multi-meaning dates (`"next Wednesday"` or locale-ambiguous `"04/05/2026"`), or pick a winner when notes contradict themselves without an explicit revision cue.
- **No external tracker mutations**: This skill requires no API keys, packages, or network access; it generates clean Markdown/text output for you to review and paste into your docs, chat, or issue tracker rather than creating tickets directly via external APIs.
