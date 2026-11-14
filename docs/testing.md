# Testing

Run the following commands from the repository root. Runtime and Python tests use the standard library. The form tests use Node's built-in test runner and modules; no package installation or browser download is required.

```sh
python -B -m unittest discover -s tests -p "test_*.py"
node --test tests/test_form.mjs tests/test_form_notes.mjs tests/test_form_actions.mjs
python -B tools/check_release.py
python -B tools/check_example.py
```

Use Python 3.10 or newer and a maintained Node.js release with the built-in test runner, `Blob`, and `Intl.Segmenter` (Node.js 22 or newer). Test reports go to the terminal. The JavaScript suite does not write files or start a browser.

The minimum-version check and the recommended interpreter for a new installation serve different purposes. Prefer a maintained Python 3.13+ release for daily use and retain a separate 3.10 compatibility job. The [installation guide](installation.md#verified-scope) distinguishes observed local environments from the configured GitHub matrix.

Python tests use isolated temporary directories. Set `SKILL_BUILDER_TEST_TMPDIR` to an existing writable parent directory to choose another location for test files. Keep this directory outside the repository and outside saved user runs.

## What the tests exercise

The backend suite covers questionnaire validation, dependencies, deferred decisions, AI recommendations, answer history, revision conflicts, registered assets, localization, storage, and the local HTTP bridge. Runtime regressions cover streaming image hashing, cosmetic edit declarations, fresh-fixture rebinding, and structural-checker examples. Release and installation tests cover archive contents and preservation of existing installations. Evaluation tests distinguish automatic assertions, supported review evidence, missing work, and incomparable runs.

Handoff regressions cover accepted submission identities, explicit host acknowledgment, stale and superseded records, last-observed checkpoints, and ordinary offline imports that remain drafts until submitted. Core-question importance must not restrict delegation or recommendation filling.

The form suite executes the shipped `any-skill-builder/assets/form.js` in a small deterministic DOM and HTTP acknowledgement harness. It verifies:

- Korean, Japanese, and Chinese composition across a background save acknowledgement.
- Both common final-input/composition-end event orders and cancelled composition.
- Caret position and selected text during middle edits and background saves.
- Final text commit on blur, navigation, export, and submission.
- Exact Unicode preservation through draft storage, resume, and JSON export.
- Optional deferral notes retaining their deferred status and text through composition and saves.
- A top-only AI delegation setting, any-page Finish, missing-answer confirmation, and navigation without premature delivery.
- Core-question guidance with unrestricted explicit delegation, accurate acceptance/download wording, and token-free resume messages with clipboard fallback.
- Explicit AI handoff and whole-answer reset across pending saves, offline exports, and conflict recovery, including conflicts arriving during Finish or reset.
- Recovery of unfinished multi-select drafts without treating them as answered, including validation and preserved reset intent.
- Accurate guidance when an AI-request download is imported into the form instead of returned to chat, without silently running the request.
- Grapheme-safe length limits, dependency changes, and conflict recovery.
- Explicit English and Korean interface dictionaries.

English is used for test names, comments, and general fixture labels. Non-English strings are intentional input and localization fixtures, not untranslated documentation.

The harness exposes existing form functions only to drive and observe the tests. It does not replace production editor behavior. Its DOM has no layout engine, and its HTTP acknowledgements are simulated rather than a full second backend implementation.

## Manual browser checks

Automated event tests are not native OS input-method tests. Before a release that changes text handling or layout, open a newly generated questionnaire in the target browser and check normal typing, composition, cursor movement, selection replacement, page navigation, save/resume, and exported answers. Use actual input methods where available, particularly Korean, Japanese, and Chinese.

Also inspect narrow screens, image choices and enlargement, deferred questions, long answers, and an RTL questionnaire. Confirm that an active server receives the submitted answers. A static HTML export cannot restart an inactive AI conversation.

Record the browser, OS, languages, and input methods actually exercised. Passing the mock DOM tests does not establish rendering quality, translation quality, accessibility, or compatibility with every browser and language.

## Skill and question outcomes

The [complete public example](../examples/complete/README.md) includes actual independent forward outputs and separately reviewed criteria. Reproduce it with fresh task outputs before making claims about a changed skill. Inspect question coverage and selected-answer-to-behavior mapping as well as final prose. The [evaluation helper](../any-skill-builder/references/evaluation.md) preserves artifact hashes and explicit untested results; it does not replace running the task or reviewing the evidence.

Run the supported minimum Python version, not only the locally newest interpreter. An Actions matrix is a plan until its jobs actually execute. Host discovery, operating-system input methods, and a repository-URL installer also need their own observed checks.

## Published example consistency

`python -B tools/check_example.py` checks the existing public artifacts, evidence, and stored reports without a model call or report overwrite. Run it from the source directory after Git has applied its text normalization, such as in a fresh checkout or the CI workspace. A passing working-directory check alone cannot rule out CRLF/LF differences in files Git will publish.

Keep this evidence consistency check separate from a fresh model evaluation. Changing a generated skill or its cases may require new forward outputs and a new independent review; merely updating report hashes does not supply that evidence.
