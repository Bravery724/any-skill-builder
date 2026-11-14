# Turn decisions into a usable skill

Only build the final package after the active questionnaire is complete and material deferrals are resolved. `brief` enforces the state gate and writes the current evidence, answers, reasons, and assumptions. This text is input to the host AI, not an automatic replacement for implementation judgment.

Before implementation, give a concise conversational summary of the main AI-selected directions, their reasons, and remaining assumptions. Use the latest valid answers and preserve explicit user decisions. This update explains the build plan without adding a blanket approval step. Carry facts deferred to execution into the generated skill's runtime inputs; do not turn unknown accounts, equipment, or private resources into assumed facts.

## Design the smallest adequate package

Use `RUN/output/<skill-name>/`. Name the folder and skill consistently with lowercase letters, digits, and hyphens. The required `SKILL.md` has YAML `name` and `description` followed by instructions. Its description must explain the actual capability and when it applies.

- Put purpose, important decisions, essential workflow, and links to conditional material in `SKILL.md`.
- Include a concise user-facing `README.md` with every newly created skill, following the checklist below. This guide is part of the installable runtime, not maintainer documentation.
- Add `references/` only for substantial task-specific information that changes decisions and is useful on demand.
- Add `assets/` for real output templates, chosen images, or other reusable deliverable resources.
- Add `scripts/` for repeatable operations where deterministic handling improves reliability. Do not generate code just to make the skill look sophisticated.
- Add host metadata only when the target environment uses it. Keep the standard instructions portable where possible, and state real dependencies or unsupported capabilities.

For image decisions, preserve the chosen candidate and translate its relevant properties into actionable instructions. A filename alone does not communicate layout density, information hierarchy, or the user's comments.

The references used while building do not all belong in the final skill. Keep full research logs, questionnaire history, and evaluation scaffolding in the run. Do not copy entire external manuals or install arbitrary dependencies as part of packaging.

Write reusable instructions, reference documents, README files, code comments, and package metadata in English by default. An explicit request for a different file language overrides this default. Keep original-language input, quotations, translation dictionaries, and multilingual regression fixtures intact. The generated skill's user-facing behavior still follows the conversation or explicitly requested output language.

When preparing a skill for distribution, use relative resource references, document actual runtime requirements, and remove personal paths and assumptions. Exclude run records, answers, generated user material, credentials, caches, and machine-specific verification output. Package runtime files separately from maintainer tests and documentation. Include the chosen license and verify both the archive contents and an extracted-package smoke test. Do not publish externally unless publication is authorized.

## Provide usage guidance at the right moment

Write the generated skill's `README.md` for someone who has not read the design conversation. Keep a simple skill's guide short; add detail only when its actual workflow needs it. Include:

- A plain-language sentence explaining what the skill helps the user accomplish.
- Required inputs or materials, plus optional preferences that actually change the result.
- One immediately usable starting request and, when useful, one or two distinct examples such as a refinement or continuation. Use the target host's supported invocation spelling rather than inventing slash commands or flags.
- What the user will receive and any real tool, permission, or capability limits needed to start successfully.
- How to ask for changes or resume when the implementation supports it.

Link the guide from `SKILL.md` and include it in the installable package. Write reusable files in English unless the user explicitly requests another file language. Conversational help follows the user's language; a static metadata string is not automatically translated by this rule.

Keep `SKILL.md`'s frontmatter description focused on capability and when to use the skill. If the target host supports separate picker metadata, provide a concise user-facing description and a starting prompt there. For Codex-style `agents/openai.yaml`, use `interface.display_name`, `interface.short_description` (25–64 characters), and a helpful `interface.default_prompt` mentioning `$skill-name`; follow the host's available metadata documentation. Other hosts may use different fields or ignore this file. Never promise a particular `/` menu layout or automatic help merely from selecting a menu item.

Give the generated skill a small help behavior: reuse the task, attachments, and prior context first. If invoked without an actionable task and no useful context, explain its purpose in one or two natural sentences, provide a short starting example, and ask for the missing input. If a task is clear, start it directly. A request for usage help can receive the guide's relevant details. Avoid repeating an introduction before each normal task or adding a mandatory onboarding step.

Before delivery, compare the guide and picker description with the implementation. The first example must work with the declared inputs and supported tools; optional modes, outputs, permissions, and resume promises must exist. Include an empty-invocation/help case and a clear-task case in the behavior review when adding this behavior. Do not turn a well-written guide into a claim that unexecuted tasks were tested.

## Write outputs like a helpful conversation

Make natural conversational explanation the default for chat and document prose, including HTML reports. Match the user's language and level of politeness; use natural phrasing in that language without hard-coding one language's sentence endings. An explicit request for academic prose, a formal submission, or another genre takes precedence.

Lead with what the result means, then connect the reasoning, examples, and implications in readable paragraphs. Explain necessary technical terms briefly. Use lists and tables when they aid comparison or navigation. Avoid dense noun fragments, administrative phrasing, and unnecessary jargon. Preserve source attribution, numerical precision, uncertainty, and useful depth; conversational writing is not permission to omit these. Keep schemas, identifiers, citations, and code unchanged.

When several requested sections use the same evidence, give each section a distinct job. A table can hold facts and short source quotes; explanation should add an implication the table does not convey; follow-up questions should ask for the missing decision. Do not repeat the full row, quote, or generic reason in every section. Refer to item numbers where useful and keep simple cases proportionately short. Preserve requested sections, flags, evidence, and uncertainty while removing repetition. Review an actual output for this distinction rather than assuming that separate headings make it readable.

Add a concise instruction with this behavior to the generated skill. Review a representative output passage by reading it as something said directly to the user. Revise the explanation itself when needed instead of mechanically swapping sentence endings. Do not copy stock transitions into every paragraph or introduce extra questions for a preference the user has already supplied.

For analytical outputs, always make the reasoning easy to follow, intuitive, and useful. Explain the finding's meaning and importance, the evidence that supports it and its limits, and what the reader can do with that understanding. A concrete input/output example or comparison can help before technical detail; label hypothetical examples and keep their limits clear. Do not force a fixed sequence into every paragraph. In review, ask whether a reader unfamiliar with the analysis can understand its main point and practical consequence without decoding unexplained labels or opening every citation. Clear explanation remains necessary even when the requested genre is formal.

## Record decision traceability

Write `RUN/design.json` as a compact record of what was built. Example shape:

```json
{
  "project_id": "paper-study",
  "questionnaire_revision": 2,
  "skill_path": "output/paper-idea-review",
  "features": [
    {
      "id": "related-work-comparison",
      "question_ids": ["q-scope"],
      "behavior": "Compare relevant prior/subsequent work before proposing a research gap",
      "files": ["SKILL.md", "references/comparison.md"],
      "evaluation_ids": ["case-related-work"]
    }
  ],
  "assumptions": [],
  "limitations": []
}
```

Record actual current decisions and files. Inactive questions and obsolete candidates must not reappear as selected features. If a user changes an answer later, use this mapping to identify affected instructions, scripts, assets, and evaluations. Recheck shared behavior when the change affects it.

## Validate behavior, not wording

Run `check-skill --path PATH` for supported structural checks. If the host has an official skill validator, use it as well where appropriate. Neither check proves task quality. Do not report a packaging pass as a behavioral pass.

Prepare representative cases proportional to the work:

- A normal case demonstrating the user's primary desired outcome.
- A relevant edge/failure case such as insufficient source material, contradictory inputs, inaccessible data, or unavailable tools.
- For a material design choice, an alternative answer or scenario that demonstrates the intended difference.

Exercise generated helpers with meaningful inputs and inspect their actual output. Verify that the skill can locate referenced files and uses tools available in the target environment. Do not run untrusted source code or external mutations merely because a source or generated skill suggests them; keep testing within the user's authorized scope.

For a complex new skill, an independent forward test is valuable. Give another agent the created skill, realistic request, and minimal raw inputs. Avoid telling the evaluator the intended answer or suspected flaw unless necessary. The evaluator should use the skill and return the result and observed problems. Inspect the result and make supported corrections. Use a separate evaluation folder so test outputs cannot contaminate final deliverables.

For subjective outputs such as design or writing, inspect fitness to the goal, faithful use of user preferences, and useful alternatives; a syntax checker cannot do that. For research, distinguish inspected evidence, inference, and new hypotheses, and verify citations against actual accessed sources.

## Completion and limits

Record `RUN/evaluation.md` with the tested tasks, observed results, corrections, and untested limitations. Include the model/effort only if exposed by the host; do not guess them. More files, higher star counts, more questions, or a self-rating are not proof of quality.

The deliverable is complete when the selected behavior is implemented, relevant checks pass, and material unresolved limitations are honestly reported. If execution or access is blocked, explain exactly what was verified and what remains. Preserve the run for continuation. Do not automatically publish, send to third parties, or claim installation without carrying out an authorized install.

Package format reference: [Agent Skills specification](https://agentskills.io/specification). The host's existing skill-creation instructions may add environment-specific metadata or validation conventions.
