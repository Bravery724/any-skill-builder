# Offline workflow validation — v0.3.0

Recorded on 2026-11-15. This page describes observed checks for the two-workflow redesign. Earlier [Claude Code and Antigravity CLI validation](host-validation.md) belongs to v0.2.3 and does not certify the new workflow or either IDE extension. Since v0.5.0, Full Auto records a decision list instead of authoring and reviewing questions; see the [v0.5.0 Full Auto validation](full-auto-validation.md).

## Creation and continuation

Two separate execution agents independently followed the builder instructions in isolated run directories:

- **Full Auto:** researched the subject, authored and reviewed five design questions, applied reasoned recommendations, reached build readiness, created the brief, and delivered `project-notes-brief` with a usage guide and license. No HTML was generated.
- **Saved HTML:** used `resume` on the known questionnaire location, preserved a meaningful custom audience/style answer, recorded why a lone period did not answer its question, filled missing choices, and delivered `clear-weekly-update` with a usage guide and license.

Both agents checked the original and extracted packages and exercised four small fictional tasks. Each author reviewed its own resulting outputs; these are scoped forward executions of the builder, not blinded assessments of the generated skills. Model and effort metadata were unavailable. [Representative artifacts](../examples/offline-workflows/README.md) include the actual skills, usage guides, inputs, and outputs.

## Browser and state handling

The standalone HTML was exercised in an isolated headless Chrome profile, with no HTTP(S) requests from the form:

- Saving on page one with unanswered questions; downloading HTML with questions, answers, identity, and embedded image candidates; reopening the saved file.
- Clearing an existing answer, saving, and reopening without an older browser draft restoring it.
- Custom Other text, image-candidate rejection, a partially selected multi-choice question, and exact preservation of a meaningful `0`.
- Korean, Japanese, Chinese, Arabic, accented characters, and combining marks through editing and saved-HTML import.
- Browser-level Korean composition simulation preserving the focused textarea and committed text. Native Windows IME operation was **not** tested.
- No horizontal overflow at 320, 390, 768, and 1280 CSS pixels; desktop and mobile screenshot inspection.

The real browser export was imported by the Python helper. Contextual resolution retained unusable original text in history; recommendation filling retained meaningful user choices and partial selections. Re-importing the same snapshot and resuming from the known path preserved subsequent AI decisions. A build brief was generated from the resolved state.

The shipped JavaScript regression suite also covers composition events, caret position, conditional branches, explicit selections alongside Other, blank/partial answers, answer provenance, exclusive choices, reset confirmation, RTL messages, HTML JSON escaping, download identity, and unsaved edits.

Python checks cover identity/revision conflicts, inert HTML parsing, duplicate exports, safe restoration, embedded image boundaries, contextual resolution, dependency behavior, history, checkpoints, source packaging, and installation protection. The [CI workflow](../.github/workflows/ci.yml) executes the suite on Ubuntu and Windows with Python 3.10 and 3.13, plus Node 24. Consult the [actual Actions results](https://github.com/Bravery724/any-skill-builder/actions/workflows/ci.yml) for a particular commit or tag; a configured job is not itself a passing result.

## Review and release limits

Independent source review found and prompted fixes for selected-branch handling, preservation of human descendant answers, restored history and ownership, portable export IDs, and safe path handling. Regression checks accompany the corrections. The project structural/package checks and the historical public example's nine recorded checks are separate from model behavior tests; historical outputs were not regenerated to improve their results.

The optional system skill-creator validator could not run in the local interpreter because PyYAML was absent. The project's own standard-library structural checker ran successfully. No new dependency was installed for that optional check.

These checks do not prove universal language support, native keyboard compatibility, host picker behavior, browser download-folder choices, security certification, or superiority over another builder. Saved HTML does not wake a closed conversation. Old connected-form runs are kept intact and require explicit, reviewed migration when their formats are incompatible.
