# Testing

Run these commands from the repository root. Runtime and Python tests use the standard library. Form tests use Node's built-in test runner and modules; no package installation or browser download is required.

```sh
python -B -m unittest discover -s tests -p "test_*.py"
node --test tests/test_form.mjs tests/test_form_notes.mjs tests/test_form_actions.mjs
python -B tools/check_release.py
python -B tools/check_example.py
```

Use Python 3.10+ and Node.js 22+ with the built-in test runner and `Blob`. Prefer a maintained Python 3.13+ release for new installations while retaining a separate minimum-version check.

Python tests use temporary directories. Set `SKILL_BUILDER_TEST_TMPDIR` to an existing writable parent outside the repository and user runs if another drive is preferred. The JavaScript harness does not launch a browser.

## Runtime and form coverage

The redesigned workflow needs behavioral checks for:

- Full Auto preserving research/decision records without creating HTML.
- Questionnaire structure, stable identity, source references, dependencies, revision invalidation, and image integrity.
- Saved HTML containing actual questions, answers, locale, assets, and baseline information.
- Import, known-path resumption, and fresh restoration without executing uploaded HTML.
- Rejection of stale, foreign, conflicting, or tampered exports before mutation.
- Idempotent repeated imports preserving AI work performed after the first import.
- User-owned ordinary choices, meaningful Other text, partial multi-select values, and explicit clearing/reset.
- AI filling eligible blanks while protecting useful human choices.
- Contextual custom-answer interpretation and retained raw input when unusable text is replaced.
- Locale keys, Unicode text, RTL presentation, and safe JSON/HTML embedding.
- Checkpoints, build readiness, installation preservation, explicit package contents, and evaluation evidence.

Form tests must execute the shipped JavaScript rather than a separate reimplementation. Exercise both common composition/input event orders, cancelled composition, middle edits, caret/focus retention, navigation, and saving the last typed characters. An empty Other input must remain unanswered. A saved file reopened after clearing an answer must not revive a stale browser draft.

The mock DOM has no layout engine and does not certify a real input method or file download. Record which cases actually ran in current validation notes; test intentions alone are not passed results.

## Browser and host checks

Use a separate task-owned browser profile and fictional data. Inspect desktop and narrow layouts, long content, image enlargement, keyboard navigation, the fixed save footer, and RTL rendering. Confirm:

1. Save answers is available before the last page and with blanks.
2. The downloaded HTML opens independently and restores exact answers and clears.
3. Registered images remain visible after moving the saved file.
4. Input is not lost during composition or page navigation.
5. Saving reports a download honestly and directs the user back to chat.
6. The host reads the matching saved file and continues without a running form server.

For native Korean, Japanese, and Chinese input-method coverage, use the actual OS input method and report that separately from simulated DOM composition events. A responsive screenshot does not certify touch-keyboard behavior.

Exercise actual host discovery and continuation when claiming support for a particular app or extension. Historical [v0.2.3 CLI runs](host-validation.md) do not certify the new offline workflow or either IDE extension.

## Question and skill quality

The [complete public example](../examples/complete/README.md) includes recorded forward outputs and separately reviewed criteria. Reusing those files checks evidence consistency, not a new model execution. A changed generated skill needs fresh relevant outputs before claiming its behavior improved.

Review useful decision coverage and answer-to-behavior mapping as well as final prose. The [evaluation helper](../any-skill-builder/references/evaluation.md) records artifact hashes and explicit untested results; it does not replace actually running tasks or reviewing judgment.

For the [execution loop](../any-skill-builder/references/evaluation-loop.md), test iteration preparation from outside the source directory, preserved skill/input snapshots, pending records, and refusal to reuse an existing destination. Executor packets must not disclose grading checks or expected answers. Check execution-provenance records, evidence-backed critiques, repeated-operation observations, and helper-validation references; missing reviews must not become passing results. Existing schema-1 examples without optional loop records must reproduce their historical reports unchanged.

Exercise a realistic host task separately from these unit checks. Keep the author, executor, and reviewer roles explicit, preserve actual outputs, and record why any correction or helper extraction was warranted. A synthetic fixture proves record handling, not independent model performance.

The CI matrix covers Ubuntu/Windows, Python 3.10/3.13, and Node 24. A configured job is not a passed check until it runs. Inspect current commit results and state untested environments honestly.
