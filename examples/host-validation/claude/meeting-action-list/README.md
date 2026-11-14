# meeting-action-list

Turns rough meeting notes into a clean table of action items: who does what, by when. It keeps any owners and dates you wrote exactly as given, and points out what's missing, vague, or contradictory, with a ready-to-send question for each gap.

## What to provide

- **Your notes** (required): paste them or attach a text file. Terse bullets, initials, and fragments are fine.
- **Meeting date** (optional, recommended): lets "Fri" or "next week" be converted into calendar dates. A date in the notes header works too.
- **Attendee list** (optional): helps match initials to people.

## Try it

> Turn these notes from our 2026-03-10 launch sync into action items:
> - PK send rev. deck to Acme Fri
> - pricing page copy — Dana: I'll draft
> - maybe revisit onboarding emails?
> - Decided: beta stays invite-only

Other things you can ask:

- "Same notes, but group the items by owner."
- "Lee confirmed the vendor call is due 03-17 — update the list."
- "Also give me a CSV I can import."

## What you get

1. A one-line summary.
2. A Markdown table with the columns #, Action, Owner, Due, Flags, and Source. Rows follow the order of your notes.
3. **Needs clarification**: each problem explained, with a short question you can send to the right person.
4. **Possible action items — confirm**: soft suggestions that nobody committed to yet.
5. **Decisions**: agreed outcomes that aren't tasks.

## What it will and won't do

- It never invents owners or dates. Owners come only from your notes. A line like "Sam: I'll check the backups" gives owner `Sam (inferred)`. An unnamed "I'll do it", or a role or topic mentioned nearby, leaves the owner `missing`.
- It never quietly picks between conflicting statements. Both values are shown, and the row is flagged.
- If the notes contain no action items, it says so instead of making some up.
- It is designed for typed or bullet notes. Long verbatim transcripts and email threads aren't specifically handled.
- It doesn't connect to task trackers. Ask for CSV/JSON and import that yourself.
