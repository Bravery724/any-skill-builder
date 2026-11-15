# Recorded offline workflow examples

These fictional examples were created on 2026-11-15 using the redesigned builder. Two separate execution agents read the current skill instructions and used the actual Python helper. They did not copy the earlier generated examples. Each agent authored and exercised its own resulting skill; these output reviews are not blinded or independent quality measurements. They were recorded with v0.3.0; since v0.5.0, Full Auto records a decision list (`decisions.json`) instead of resolving authored questions.

| Workflow | Actual build | Selected input and output |
| --- | --- | --- |
| Full Auto | Five researched design questions were resolved with AI recommendations. The helper reached build readiness and produced a brief. No HTML was generated. [Skill](full-auto/project-notes-brief/SKILL.md) · [Usage](full-auto/project-notes-brief/README.md) | [Fictional notes](full-auto/input.md) · [Produced brief](full-auto/output.md) |
| Saved HTML | The agent resumed from the known questionnaire path. It kept the custom request for outside readers, natural explanations, and no repetition; retained a lone period and the reason for treating it as unusable in history; and filled the remaining choices. [Skill](saved-html/clear-weekly-update/SKILL.md) · [Usage](saved-html/clear-weekly-update/README.md) | [Fictional notes](saved-html/input.md) · [Produced update](saved-html/output.md) |

The saved HTML was filled and downloaded through the real standalone browser UI by the test harness. The continuation agent received the ordinary instruction to continue using the saved file, the known run directory, and the builder instructions. It used `resume`, contextual input resolution, recommendations, the build brief, and package checks. No live service or defer state was involved.

Both packages include a usage guide and MIT license. Their original and extracted folders passed structural checks. The Full Auto author also exercised sparse notes, an alternative topic recap, and empty help; the saved-HTML author also exercised conflicting status, an alternative source layout, and empty help. Only one representative input/output pair per workflow is included here. These are actual authored outputs, with line endings and trailing blank lines normalized; their prose was not rewritten for publication.

The host model and reasoning effort were not exposed. No no-skill baseline, measured success rate, installed-host routing test, or new Claude Code/Antigravity IDE test was performed. The fictional `example.invalid` link tests preservation of supplied evidence, not live source retrieval. See [current validation](../../docs/offline-validation.md) for the mechanics, browser checks, and limits.
