---
name: meeting-action-list
description: Turn rough bullet-style meeting notes into a clear action-item table that keeps supplied owners and due dates exactly, separates possible items and decisions, and flags missing, vague, duplicate, or conflicting details with ready-to-send clarifying questions. Use when someone pastes or attaches meeting notes and wants action items, follow-ups, or a to-do list from them.
---

# Meeting action list

Turn rough meeting notes into a short, trustworthy action list. The user should be able to see at a glance who does what by when, and exactly which details still need confirming. Usage guide: [README.md](README.md).

## Getting started

- If the request already includes notes, start right away. Don't introduce the skill first.
- If the skill is invoked with no notes and no useful earlier context, explain in one or two sentences that it turns rough meeting notes into an action table and flags gaps. Give a short example request, such as "Here are my notes from Tuesday's 2026-03-10 planning sync: …". Then ask for the notes, and the meeting date if they have one.
- Inputs:
  - **Required:** the notes text.
  - **Optional:** the meeting date, which is used to resolve relative dates. An explicit date in the notes header counts.
  - **Optional:** an attendee list. It is only used to resolve initials. It does not trigger extra checks.
  - **Optional:** a request for CSV or JSON export.
- Never ask questions before producing the list. Gaps go in the output as flags.

## Core rules

1. **Never invent.** Every owner, date, and task must trace back to the notes. If something is unknown, write `missing`. Don't guess.
2. **Keep supplied values exactly as written.** Copy owner names, initials, and date wording verbatim. You may add a resolved calendar date next to a relative date, but never replace the original wording.
3. **Ownership:**
   - A name explicitly attached to a task (`PK to send deck`, `Owner: Dana`, `@Lee`) is the owner.
   - A first-person commitment counts only when the same line explicitly names the person making it (`Dana: I'll draft the FAQ`). Write the owner as `Dana (inferred)`, and quote the line in Source.
   - An unattributed first-person line (`I'll draft the FAQ`, or `we'll handle it`) leaves the owner `missing`.
   - Never infer an owner from someone's role, the topic, their expertise, who raised the item, or who "usually" does the work.
   - If several people or a team are named (`PK + JL`, `design team`), keep them as written and flag `no single accountable owner`. Suggest naming one lead.
4. **Due dates:**
   - Keep the original wording.
   - If the meeting date is known and the phrase is relative (`tomorrow`, `Fri`, `next Friday`, `end of next week`), add the resolved ISO date after an arrow: `next Fri → 2026-03-20`.
   - For `next <weekday>`, use the weekday in the following calendar week. Flag it as `ambiguous relative date` and state the other reading, because people use the phrase both ways.
   - If the meeting date is unknown, keep the wording and add one note in the clarification section: "Meeting date unknown — relative dates were not converted". Still flag `next <weekday>` as ambiguous. Other relative dates get no per-row flag.
   - Explicit dates without a year (`03-12`) take the meeting date's year.
   - Vague timing (`ASAP`, `soon`, `before next sync`, `when possible`) is kept but flagged `no specific date`.
   - A blank date is `missing`.
5. **What counts as an action item:**
   - The table holds only clear commitments or assignments: someone agreed, or was asked, to do something.
   - An imperative or "needed" task line with no name (`update the runbook`, `revised forecast needed by 03-20`) counts as an assignment to the group. Put it in the table with owner `missing`, even if a role or presenter is mentioned nearby.
   - Soft suggestions (`maybe revisit pricing?`, `should we…`, `worth looking at`) go in **Possible action items — confirm**, quoted. They never appear in the table.
   - Agreed outcomes with no follow-up work (`Decided: launch stays in April`) go in **Decisions**. Don't turn them into tasks.
6. **Repeated tasks and conflicts:**
   - When two lines clearly describe the same deliverable, merge them into one row, placed at the first mention. Cite both lines in Source (`lines 1, 4`).
   - If the merged lines agree, keep the value. Note the agreement only if the wording differed, for example `03-16 / Mon → 2026-03-16`.
   - If they give different owners or dates, don't pick one. Write `conflicting: PK (line 2) vs JL (line 7)` in that cell and flag it.
   - When it's only likely, not clear, that two lines are the same task, keep separate rows and flag both `possible duplicate`.
7. **Other checks on every item:**
   - **Required checks:** missing owner, missing date, conflicting owner or date.
   - **Vague action:** no clear deliverable (`look into pricing`). Flag it, and suggest a sharper wording in the clarification entry.
   - **Possible duplicate:** see rule 6.
   - **Suspicious date:** before the meeting date, a non-existent date such as Feb 30, or a weekday that doesn't match the date (`Thu 2026-03-20` when that is a Friday).
   - Run no other checks unless the user asks.

## Output

Write the parts in this order. Skip any section that would be empty, except the action table. If there are no action items, say so plainly in a sentence instead of the table.

1. **One-line summary:** how many items, and how many need clarification.
2. **Action table**, with rows in the order they appear in the notes:

   | # | Action | Owner | Due | Flags | Source |
   |---|---|---|---|---|---|

   - **Action** starts with a verb and names the deliverable (`Send revised pricing deck to Acme`). Rewrite fragments clearly, but don't add scope.
   - **Flags** holds short markers only, such as `⚠ owner`, `⚠ date`, `⚠ conflict`, `⚠ vague`, `⚠ duplicate?`, `⚠ date check`, or `—` when there is nothing to flag.
   - **Source** holds a short quote (about 8 words, use `…` to trim) or a line reference, so each row can be checked against the notes.
3. **Needs clarification**: one entry per flag, numbered by item. Each entry gives:
   - what is missing or conflicting, and why it matters;
   - a ready-to-send question addressed to the likely person, or to "the group" if nobody is known.

   For example: `Item 3 — two due dates were given (Tue vs 03-20). → "Lee, is the vendor call due Tuesday 03-17 or Friday 03-20?"`
4. **Possible action items — confirm**: quoted suggestions, each with a one-line note on what would make it a real item (an owner and a date).
5. **Decisions**: one line each, quoted or closely paraphrased.

Keep the response compact. Don't repeat the whole table in prose.

## Export (only when asked)

If the user asks for CSV, JSON, or "something I can import", add the export after the normal output, following [references/export-schema.md](references/export-schema.md). Use the same values as the table, including `missing`, `conflicting`, and `(inferred)` markers. Don't resolve them for the export.

## Writing style

- Write chat and summary prose naturally, mirroring the user's language and tone. Copy names, quotes, and date wording from the notes exactly, even if they are in another language.
- Explain each flag in a plain sentence that says why it matters (`nobody is named, so this is likely to slip`) rather than a bare code.
- When converting a date, state the assumption once rather than hiding it.
- If the user asks for a different order (by owner or by date), a different layout, or a follow-up with corrections, apply it and keep all the rules above. When the user resolves a flag, update that row and drop the flag.
