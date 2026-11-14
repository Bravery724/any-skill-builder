# Historical host validation: v0.2.3

**Version boundary:** these observations cover the previous v0.2.3 workflow. v0.3.0 replaces its connected form with standalone saved HTML and Full Auto without HTML. This report is retained as historical evidence; it does not validate the new workflow or either IDE extension.

Recorded on 2026-11-14 on Windows. These were supervised runs of installed host applications, not simulations of their tools. The shared goal was a small English `meeting-action-list` skill: turn rough meeting notes into clear actions, retain supplied owners and deadlines, and flag missing or conflicting details. All meeting data was fictional.

The tests began with v0.2.2 and exercised the guidance corrections included in v0.2.3. The Python and browser runtime algorithms were unchanged. Research, questionnaire authoring, selected answers, handoff receipt, generated files, and fresh task outputs were inspected separately. These observations are not a head-to-head model benchmark or a guarantee for every skill.

Independent review used a separate AI reviewer/context with predefined criteria. It inspected the actual artifacts and responses without rewriting them.

## Results and boundaries

| Host | Observed execution | Fresh generated-skill cases |
| --- | --- | --- |
| Claude Code 2.1.322 | Native skill discovery, researched questionnaire, live Chrome submission, host acknowledgment, revisioned repairs, and completed skill | Normal, missing, and conflicting details: all three pass independent review |
| Antigravity CLI 1.5.9 | Researched and repaired questionnaire, live Chrome submission, supervised resume, host acknowledgment, completed skill, and readability refinement | Normal, missing, and conflicting details: all three retain substantive behavior after refinement |

Claude Code reported `claude-opus-5-5`. No model or reasoning-effort override was applied; effort was not exposed in the recorded run. This is CLI testing, not validation of the Claude Code IDE extension, Antigravity IDE/App, Claude web chat, every discovery path, or every host setting.

## What was actually done

1. Install the full builder into an isolated project using each host's skill directory. Ask the actual host to research the subject and prepare questions.
2. Review the authored questions against the original goal. Send concrete findings back to the actual authoring host and retain revisions and answer history.
3. Open the rendered questionnaire in Chrome through the bundled authenticated loopback server. Enter manual choices, delegate remaining questions, and finish. Verify accepted browser submission and host acknowledgment as separate events. Claude launched and waited on its server; the Antigravity test harness launched the same bundled server between CLI turns and resumed the actual host after submission. The latter is a supervised resume, not proof of automatic wakeup.
4. Have the actual host turn current decisions into a build plan, skill, usage guide, and its own evaluation artifacts.
5. Freeze the generated skill. Execute three inputs in separate fresh host contexts, without giving those contexts the review criteria or other cases. Independently judge the unchanged outputs against criteria written before the outputs existed.

The [published inputs, skills, and outputs](../examples/host-validation/README.md) are the evidence for the final behavior. Text line endings are normalized for Git; task responses were not rewritten to satisfy the review. Release manifests cover the published file hashes. Raw host transcripts, machine paths, authentication data, and local server URLs are excluded.

## Claude Code observations

The builder was invoked through Claude Code's native Skill tool. The host authored 18 candidates, of which 17 were initially active, and launched the live submission server. Two choices were entered in Chrome: rough bullet notes and a Markdown table. Finish was used on page 4 of 5, with the other 15 active questions delegated.

The browser submission was accepted at 13:15:37 UTC and read/acknowledged by the host at 13:16:09 UTC. The active host continued building. Independent review then found the authoring issues below. The actual Claude session revised questions through `set-questions`, retained both manual choices as user-owned answers, and refreshed the build. Because that revision superseded the earlier handoff, it recorded a new explicitly authorized delegation and receipt.

The final run had 17 candidates and 16 active answered decisions, at questionnaire revision 2 / answer revision 22, with a stage-7 checkpoint. The three-file package contains `SKILL.md`, `README.md`, and an on-request export reference. The selected bullet-input scope and table format are implemented explicitly.

All three fresh sessions used `/meeting-action-list`. The host's native slash expansion and injected installed skill body were verified; the skill was not manually pasted into the request. Both original and installed copies matched the pre-run hashes after execution. The author's own checks were kept separate from the independent three-case review.

## Antigravity CLI observations

Initial inspection reported CLI 1.5.8; later launches reported 1.5.9, without the test installing an update. Model/effort fields were not independently exposed by the CLI stream, so a model identity is not treated as verified. The default model and effort were left unchanged.

The Windows terminal sandbox was unavailable in this environment. `auto` fell back to a mode requiring review, and headless commands were denied until narrowly scoped session rules matched their exact Windows command forms. No global configuration or permission bypass was used. One attempt was interrupted while slow generation was buffered; later logs showed generation in progress, so that interruption is recorded as a test-harness recovery rather than a proven skill deadlock.

The actual host researched and reviewed nine candidates, with eight active and one conditional question. Source records distinguish partial search-grounded summaries from full-page reads. After targeted question repairs, the host imported, validated, and rendered the form. In Chrome, the operator selected a separate tentative-items section and a source quote on every item, delegated six remaining decisions, and finished on page 1 of 3 without visiting later pages. The server accepted the request at 13:38:34 UTC. The resumed host read and acknowledged that exact submission at 13:41:00 UTC, at questionnaire revision 1 / answer revision 3.

The host preserved both manual choices, filled the six delegated decisions, built `SKILL.md` and `README.md`, and completed stage 7 at questionnaire revision 1 / answer revision 9. An independent review confirmed that all eight selected decisions materially appear in the instructions. The author recorded 16 passing self-evaluation checks before the later writing refinement; those checks were not rerun afterward and are separate from the final behavioral evidence.

A file-hash guard detected a final authoring edit after provisional task trials had begun. Those outputs were retained privately as provisional and excluded from the final result. The final two-file package was frozen again and the three cases were rerun in new contexts.

Those complete-package trials passed substantive checks but exposed repetitive explanations. The actual host then applied the targeted writing guidance below, kept all eight decisions, and passed structural validation again. The same three inputs were rerun in three new contexts against the updated frozen package. Each context actually read its supplied skill and case, and each saved response is the unchanged host result. Both generated files still matched their pre-execution snapshot hashes afterward.

The final repeated cases preserve owners, deadlines, unresolved conflicts, dependencies, and cancelled-date status, as well as the two manual features. These are regressions on the same cases, not a new unseen benchmark. Responses became 25%, 40%, and 43% shorter by Unicode character count in the normal, missing, and conflicting cases respectively; this describes these outputs only. Review also found less repeated quotation and explanation. [Earlier missing-details output](../examples/host-validation/antigravity/before-readability/missing.md) and [earlier conflicting-details output](../examples/host-validation/antigravity/before-readability/conflicting.md) are retained for comparison with the final outputs.

## Issues found and corrections

- **Contradictory multi-select choices:** Claude omitted `exclusive: true` from two "none" options. The runtime already enforced that flag, but the authoring contract did not explain it. The contract and question-review guidance now do, and the actual authored questions were repaired and checked with the existing validator.
- **Options that relaxed the supplied goal:** Claude offered role/topic-based owner inference despite the supplied-owner constraint. The authoring host removed it, and reusable guidance now treats explicit requirements as fixed across ordinary options. Baseline verification also belongs in the build plan rather than an optional question.
- **Presentation choices that could lose meaning:** Antigravity's draft made dependency preservation optional and did not sufficiently constrain ambiguous date conversion. Review required preservation of conditions and uncertainty, and clarified that conflict display order cannot establish authority. The reusable guidance now makes this distinction explicit.
- **Repetitive explanations:** Antigravity's first complete outputs passed substantive checks but repeated facts, quotes, and flags across several sections. The build guidance now gives tables, explanations, and questions distinct jobs, retaining selected features while removing repeated material. The actual host revised the skill, and repeated behavioral checks confirmed that required information and selected features survived.
- **Host permissions and session lifetime:** Windows headless commands required host-specific permissions. The workflow and [installation guide](installation.md#claude-code-and-antigravity) now distinguish file-edit approval from command approval, and explain scoped recovery and the need for an active server/host. A quiet or buffered stream is not sufficient evidence of a deadlock.

These were repaired, supervised runs. They do not show that initial authoring always produces correct questions without review. No global permission bypass was used.

## Behavioral scope

The fixed cases cover explicit assignments, missing owners/dates, unresolved relative dates, conflicting owner/date pairs, dependencies, discussion versus commitment, and a cancelled deadline. The criteria and full outputs are linked from the evidence directory.

The Claude missing-details response is verbose because the chosen design asks one clarification question per flag. Its held email stays in the action table but is explicitly marked on hold with the previous date cancelled. These are presentation tradeoffs, not failures of the predefined criteria.

Antigravity's final responses are shorter, but wording is not flawless: the normal case adds an unnecessary mobile-topic scheduling question and suggests a deadline after Theo's due date rather than simply after receiving findings; the conflict explanation adds speculative workload/reminder comments. None becomes an invented active assignment, owner, or deadline. Retain these limitations when interpreting the substantive pass; correctness checks do not certify uniformly concise prose.

This run does not certify native input methods, multilingual output, every date convention, image questions, exported CSV/JSON, empty invocation, or every host configuration. The general automated suites cover additional mechanics; they do not replace actual host or browser tests. See [testing](testing.md).
