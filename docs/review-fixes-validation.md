# Review fixes and validation — v0.4.1

This release preserves Full Auto without HTML and Questionnaire with explicit saved-HTML continuation. It addresses the v0.4.0 review findings without adding a server, a third mode, or a human approval round.

## What changed

| Finding | Change |
| --- | --- |
| Ordinary options could violate fixed requirements | New CLI authoring requires a hash-bound question review covering every option and declared requirement before render, recommendation application, or the build brief. |
| Individually plausible answers could conflict | Reviews include recommended and contrasting applicable combinations. Conflicts must be corrected in the actual options, conditions, or visible precedence; a review explanation cannot silently override an option. Numerical limits must state what they count. |
| Final files could differ from the last tested files | `verify_delivery.py` requires a completed, reviewed selected run and exact snapshot/runtime equality, including README. Optional archive and extracted copies must also match. |
| A sole “none” could not satisfy an ordinary minimum of two choices | An explicitly exclusive sole option is complete. Ordinary answers still obey their minimum; incompatible combinations are rejected. Saved drafts and later explicit clears retain their intended precedence. |
| Copied evaluation inputs lost relative links | Preparation preserves declared input paths and records the original-to-snapshot mapping. Traversal, aliases, and path collisions are rejected. |
| Korean disclosure text contained authored English prose | The review inventory covers visible explanations, decisions, source notes, placeholders, and recommendation text as well as primary labels. Original source titles and quotations may retain their language. |
| A concurrent change could separate rendered content from export metadata | Render uses one captured questionnaire state for both. |

Existing runs without a review policy remain compatible and explicitly report legacy status. Review acceptance or enablement does not reset answers. Restored runs retain saved answers while requiring review before continuation.

## Mechanical checks

On Windows, the staged, LF-normalized source was tested with Python 3.15.2 and Node 25.2.1:

- Python: 230 tests, 227 passed and 3 skipped because this local environment did not permit creating symbolic links.
- JavaScript: 58 passed, including exclusive selection, saved drafts/clears, composition, Unicode, navigation, and save state.
- Release allowlist, UTF-8, local links, skill structure, packaging, and existing public-example consistency checks passed. Existing example checks did not invoke a model.
- Anthropic's original minimal `quick_validate.py`, pinned at `1780c5e5a552fd4d1c9d6a7b0cab26b0c2bef064`, passed. This is a format check, not Anthropic certification.

The first full Python run exposed two old tests comparing the whole status object with a mutation result. The new read-only review metadata made that comparison obsolete. The tests were corrected to verify the unchanged questionnaire, answers, readiness, legacy review state, and exact persisted bytes. The full suite above was then rerun successfully.

## Actual host and browser trials

Both tasks used Claude Code 2.1.322 with the primary model reported as `claude-opus-5-5`. The host's reasoning-effort value was not exposed. Tools used scoped file/command permissions; ordinary denied-command retries remain in the private execution record. No model API key or new dependency was required by the builder.

The initial runtime was frozen before the trials. Independent artifact review then found two residual alternative-combination defects despite accepted question reviews:

- Full Auto offered “artifact only” alongside “explain only in chat”; its contrast review invented an override not present in the options.
- Questionnaire offered one card per source memo alongside a reverse pair in Anki. An exported note and the cards generated from it are different units. See the [Anki Manual](https://docs.ankiweb.net/templates/generation.html).

Both findings were retained. Only `SKILL.md` and `references/question-review.md` changed afterward, adding explicit guidance against hidden overrides and ambiguous counting units. Executable Python, JavaScript, assets, and the remaining runtime files stayed byte-identical to the mechanically tested candidate. Follow-up correction uses that final frozen runtime, preserves the initial attempts, and checks the affected behavior again. It is a feedback-driven correction, not a blind benchmark or two entirely new end-to-end trials.

The initial Full Auto host performed four evaluation iterations. Its last four runtime files matched the tested snapshot, but seven review findings remained, including weak evaluation criteria and a possible AI-derived hint inside the issue draft. Delivery verification returned `unmet`, and the host explicitly delivered a provisional result. Nominal passing checks were not reported as a clean final verification. The follow-up targets the actual question conflict and remaining unsupported draft content instead of discarding the failed attempts.

The first Full Auto correction resolved the question conflict and removed the earlier page-count hint. Its three focused cases had 26 passing checks and 2 failing checks; all four runtime files matched the executed snapshot, but verification correctly remained `unmet`. An unreported `--chunk` diagnostic example still appeared in body follow-up information. A separate criterion also proved ambiguous about ordinary missing-input requests versus proposed diagnostic actions. The host disclosed an additional gap between the sensitive-data choice and the generated instruction. These outcomes were retained rather than reclassified as a successful autonomous build.

Questionnaire's initial continuation used six iterations on the same three fixtures. The sixth tightened criteria without changing runtime bytes; it is not new breadth of coverage. Its final three runtime files matched the executed snapshot, and all 20 checks plus the required review records passed delivery verification. The feedback-driven correction then fixed the actual card-count wording and reaccepted the canonical questions. The custom cloze direction and Markdown choice remained exact user-owned values at the current question version, with their original saved entries retained in history. All 16 completed answer values were preserved. The generated runtime stayed byte-identical, and the copied delivery passed the same 20-check verification without claiming another model execution. Counts now visibly distinguish one content item, a two-card reverse pair, and one exported TSV record.

A second Full Auto correction was authored by a Codex agent under the final builder guidance. It revised the AI-owned helper decision rather than silently overriding it, and added a small standard-library renderer after the repeated failures. The renderer permits defined missing-field kinds and exact sanitized-source quotations, rejects arbitrary diagnostic/example prose, and supplies the complete section used verbatim in the draft. The skill also explicitly forbids re-exposing removed values in user guidance. Nine meaningful helper checks passed before the complete six-file runtime was frozen.

Three new Claude Code CLI processes then executed the vague report, split-problem report, and credential-containing report. All four resulting draft bodies matched their actual renderer outputs. Independent review found the previous unreported diagnostic absent and the original credential/name/email absent from the final response. The final evaluation passed 26 checks (21 reviewed and 5 automatic), and `verify_delivery` exited successfully with all six delivered files identical to the executed snapshot. This was a Codex-assisted mechanism correction with focused Claude execution, not an untouched first-pass autonomous success or a comparison under unchanged criteria. Earlier failures and the rationale for distinguishing ordinary missing-input requests from invented diagnostic tests remain recorded.

One nonblocking editorial observation remains: the credential case's chat says uncertain deployment timing appeared only in the hypotheses section, although it also appears explicitly uncertain in the environment and a quoted clarification. No source fact, confidence level, or proposed action changed; the declared behavior checks pass. The exact wording was retained in the review observations, with no output edits, new criteria, or extra run to seek perfect incidental wording. These results establish the inspected behavior, not error-free prose in every future output.

The final frozen runtime, source export, runtime ZIP, fresh extraction, and fresh test installation matched the same 23-file inventory. The runtime ZIP SHA-256 was `c1b25cacd416de5c10552effba2f07a24bff188ca13222d1fcd8560a4498518b`. CLI commands ran from outside those directories. An identical repeat install was a no-op; a different disposable installation was rejected without modification. Both new modes blocked render/recommend/brief without a required review even when the synthetic fixture was fully answered. The explicitly labeled legacy fixture preview could render. These smoke checks did not run a model or replace the actual host trials.

The browser trial entered two predeclared fixture answers through actual headless Chrome/CDP clicks and text insertion, not a human typing session. Save answers downloaded an 80,684-byte HTML file; the download-completed event and reopened embedded data confirmed the exact values and `actor: user` metadata: Markdown export and a custom source-term cloze-only direction. Seven core questions remained blank. There were no observed browser runtime errors. All nine initially visible pages were captured with recommendation/source disclosures expanded. This is browser save/reopen evidence, not a native operating-system IME test.

After the question correction, a separate final render produced the actual revision-4 form. Chrome inspection at 1440×1100 and 390×844 confirmed the corrected count wording, expanded Korean explanations, both exact user answers, and no observed horizontal overflow or runtime exceptions. The previous HTML and original download were preserved. The host's technical follow-up ended with an English chat response; that transcript was retained, so this trial does not certify Korean chat continuity across the English follow-up harness. The cloze skill's interpretation of “recognition” without multiple-choice distractors also remains an explicit assumption.

## What these results do not establish

A machine-readable review proves binding, coverage, and recorded judgments; it cannot prove those judgments are correct. The residual defects in the initial trials demonstrate why actual artifact review still matters. Two recorded scenarios are not exhaustive combination coverage. Delivery verification proves equality with a completed reviewed snapshot, not universal correctness.

Reviewers were separate from the executing host, but some knew the builder implementation and test goals. Separate agent calls alone do not establish blind or fresh-context isolation. No broad quality ranking, success-rate improvement, or speed advantage is claimed.

The tasks used explicit local skill paths in Claude Code CLI. They do not newly verify native picker triggering, Claude Code IDE, Antigravity IDE, every language, native Korean/Japanese/Chinese composition, or image-choice authoring. The [GitHub Actions workflow](https://github.com/Bravery724/any-skill-builder/actions/workflows/ci.yml) runs Ubuntu/Windows, Python 3.10/3.13, and Node 24; inspect the published commit's run for hosted results.

Private run records, browser profiles, raw model streams, and local absolute paths are excluded from the public packages. The release manifest provides public file and archive hashes.
