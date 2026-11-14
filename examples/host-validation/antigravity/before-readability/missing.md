I extracted **3 action items** and **1 tentative discussion item** for **Project Lantern**. None of the items are fully ready to track yet: every item is missing either an accountable owner, a concrete calendar deadline, or both, and because the meeting date was not recorded, relative deadlines like `"next Friday"` cannot be tied to a calendar date.

## Action Items

| # | Action Item | Owner | Deadline | Source Quote | Flags & Notes |
|---|---|---|---|---|---|
| 1 | Check the broken CSV export for Lantern (before the next demo) | `[Missing owner]` | `before the next demo` | `"Someone should check the broken CSV export before the next demo."` | `[Missing owner]`, `[Milestone deadline — no calendar date]` — `"Someone"` leaves ownership unassigned, and no calendar date is recorded for the next demo. |
| 2 | Draft the setup instructions for Lantern | Lio | `[Missing deadline]` | `"Lio volunteered to draft the setup instructions. No due date was given."` | `[Missing deadline]` — Owner is clear (`Lio`), but no target date was set. |
| 3 | Send the Lantern usage survey | `[Missing owner]` | `next Friday` | `'"Send the usage survey next Friday" was agreed, but the notes do not say who will send it.'` | `[Missing owner]`, `[Anchor date needed]`, `[Ambiguous date — confirm]` — Agreed task has no assignee; `"Meeting date: not recorded."` prevents resolving `"next Friday"`, which also needs confirmation of upcoming Friday vs. the following week's Friday. |

## Tentative / Needs Confirmation

| # | Action Item | Owner | Deadline | Source Quote | Flags & Notes |
|---|---|---|---|---|---|
| 1 | Add dark mode to Lantern (if approved) | `[Missing owner]` | `[Missing deadline]` | `"We discussed adding dark mode but made no decision."` | `[Needs decision]`, `[Missing owner]`, `[Missing deadline]` — Discussed only; confirm whether to pursue, defer, or drop before assigning work. |

## Missing & Conflicting Details

- **Unrecorded meeting date (`"Meeting date: not recorded."`)**: Without a reference date for the meeting, relative date expressions cannot be converted safely into `YYYY-MM-DD` calendar dates. Recording the meeting date—or replacing relative phrases with explicit calendar dates—is needed to anchor schedules.
- **CSV export check (#1 — missing owner & unanchored milestone)**: The note states `"Someone should check the broken CSV export before the next demo."` Using `"Someone"` leaves no single accountable person to investigate a broken feature ahead of a demo, and `"before the next demo"` has no attached calendar date. Confirm one primary owner, clarify whether `"check"` means diagnose-only or fix before the demo, and attach the demo's target `YYYY-MM-DD` date.
- **Setup instructions (#2 — missing deadline)**: `"Lio volunteered to draft the setup instructions. No due date was given."` Lio's ownership is explicit, but without a due date it is unclear whether the draft is needed before the next demo, alongside the usage survey, or on another timeline. Confirm a concrete `YYYY-MM-DD` deadline with Lio.
- **Usage survey (#3 — missing owner & doubly ambiguous deadline)**: The note confirms agreement (`'"Send the usage survey next Friday" was agreed, but the notes do not say who will send it.'`), so no one is accountable for sending it. In addition, `"next Friday"` both lacks a meeting anchor date and is inherently ambiguous between the immediately upcoming Friday and the following week's Friday. Assign one owner and confirm the exact `YYYY-MM-DD` send date.
- **Dark mode discussion (Tentative #1 — no decision made)**: `"We discussed adding dark mode but made no decision."` No commitment, owner, or timeline exists yet. Attendees need to decide whether dark mode is in scope now (with an owner and due date), parked for a future milestone, or dropped.

*(No cross-task blockers or explicit prerequisites between items were stated in the notes; there were no direct contradictions.)*

## Clarification Questions

You can copy and share these directly with the Lantern attendees to close the open gaps:

1. **Meeting reference date**: What date did this Lantern meeting take place (so relative dates in the notes have a clear baseline)?
2. **CSV export (#1)**: Who owns checking the broken CSV export, should it be fixed (not just checked) before the next demo, and what is the calendar date (`YYYY-MM-DD`) of the next demo?
3. **Setup instructions (#2)**: What target due date (`YYYY-MM-DD`) should we set for Lio's draft of the setup instructions?
4. **Usage survey (#3)**: Who will own sending the usage survey, and which exact `YYYY-MM-DD` Friday was meant by `"next Friday"`?
5. **Dark mode (Tentative #1)**: Do we want to take any follow-up action on dark mode right now (and if so, who owns it and by when), or keep it deferred?
