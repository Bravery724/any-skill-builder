# Predetermined review criteria

Recorded on 2026-11-14 before inspecting any generated skill or host response for this validation. These inputs are fictional and are shared across hosts. The reviewer will judge actual outputs, not require one exact template or wording.

## Common checks

- The output follows the supplied meeting-action-list skill and gives a concise, readable action list.
- Each listed active action can be traced to a commitment or agreed action in the notes.
- Owners and dates come from the notes. Missing or conflicting values remain visible and are not silently invented.
- Discussion topics and settled decisions are distinguished from newly assigned actions when relevant.
- The output is usable as a draft without requiring an extra conversation when the input asks for a draft now.

## Normal case

- Mira's onboarding checklist is due 2026-11-18; Theo's keyboard test is due 2026-11-20.
- Mira's accessibility summary depends on Theo's findings, and its date remains unspecified.
- Keeping button labels and discussing a mobile version do not become invented tasks.

## Missing case

- CSV export checking appears as an action with an unknown owner and an unresolved "before the next demo" timing.
- Lio owns the setup instructions, with an unspecified date.
- Sending the survey has an unknown owner. "Next Friday" is retained or explicitly unresolved because the meeting date is missing, rather than converted to a guessed calendar date.
- Dark mode does not become a committed action.

## Conflicting case

- The release checklist is represented once with the conflicting owner/date pairs visible, or with both records clearly marked as a single unresolved conflict.
- Neither Rina/2026-11-19 nor Pavel/2026-11-21 is silently chosen as authoritative.
- Pavel's link check retains its 2026-11-18 due date.
- The pilot email is cancelled or on hold pending checklist approval. The former 2026-11-20 date is not presented as an active confirmed deadline, and no replacement date is invented.

## Evidence boundaries

Review the authored questionnaire, recorded answers, build brief, completed SKILL.md and usage instructions, and actual host-generated outputs. Record whether selected answers materially affect the generated skill. Report host version/model only from observed evidence. A structural checker result does not establish behavioral success. A successful browser submission does not establish host receipt until the accepted record is inspected and acknowledged. Native input methods and every possible host configuration remain outside these three cases.
