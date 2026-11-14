# Language support

This builder accepts Unicode subject material, questions, and answers. Reusable package files are written in English by default: instructions, references, README files, code comments, and metadata. Newly generated skills follow the same default unless the user explicitly requests another file language. Preserve intentional translations, examples used to test Unicode, and user-provided text.

Questionnaires, chat replies, and the generated skill's task outputs naturally follow the conversation's language. An explicit output-language request takes precedence. Do not ask the user to select a language, translate a dictionary, or configure anything. All metadata and translation mechanics below are the host's responsibility. Choose helper programming languages from the task environment; a source prose language does not prescribe a programming language.

New workspaces record an explicit English locale as a portable fallback. The host sets the actual form locale to match the conversation before rendering. Updating questions without a locale keeps the run's existing choice. Legacy saved workspaces that omit the locale retain their original Korean fallback without rewriting saved questions or answers. Set an explicit locale when intentionally changing a run's interface language.

## Localize the questionnaire

Set `questionnaire.locale`:

```json
{"language":"ar","direction":"rtl","messages":{"...":"complete translated message dictionary"}}
```

The `messages` above is explanatory, not valid production input. Read `assets/locales.json` relative to this skill and translate every English message key for a language without a bundled dictionary. Keep the keys and all named `{placeholders}` exactly intact. Supply the complete translated dictionary to `locale.messages`; never translate internal enum values, question IDs, option IDs, JSON keys, or API names. `set-questions` checks dictionary completeness and placeholders.

Korean (`ko`) and English (`en`) have bundled dictionaries; their regional variants can use the base dictionary. Other language tags are accepted with a complete translated dictionary. `language` uses a language tag such as `ja`, `ar`, `fr`, or `pt-BR`. Set `direction` to `rtl` for right-to-left UI and `ltr` otherwise. Do not infer direction from the presence of an English acronym in an otherwise right-to-left form. The form also supports automatic direction for entered text.

For compatibility with saved custom dictionaries, deferral-note, global-action, question-status, clear-selection, Finish, pending-delegation, core-question guidance, resume-copy, and browser-recovery messages are optional on read and use English fallbacks when absent. Recovery keys include `draft_exported`, `draft_imported`, `invalid_draft`, and `ai_request_import_notice`. Translate them with the other keys when authoring or intentionally refreshing a form. Keep recovery wording clear about unfinished selections and the need to return AI-request files to chat. Keep resume instructions in the conversation language while preserving the exact local workspace and run identifiers. Never insert a server token or authenticated URL into the copied message.

Translate question titles, help, option labels, descriptions, recommendation reasons, source summaries, and group labels into the questionnaire language. Preserve the actual meaning and tradeoffs. The source's original title, quoted technical term, or proper name may remain in its original language when useful. Recommendations and AI-created assumptions need the same language treatment as user-facing questions.

## Research and generate across languages

- Search relevant local-language material as well as primary sources in other languages when useful. Explain a translation or evidence gap rather than inventing a source.
- Keep units, dates, names, script, accents, and mixed-language text intact. Language preference alone does not reveal jurisdiction, location, budget, or software environment.
- For unfamiliar language-specific terminology, preserve the original term with an explanation or seek reliable evidence. Do not certify native quality from a mechanical check.
- A skill may be written in one language and accept multilingual input. Encode that intended behavior explicitly in its instructions and evaluation cases.
- Use portable ASCII skill names when the target host requires them; that does not require ASCII body text or answers.

## Verify without overstating coverage

Exercise the actual chosen language in the browser, including controls, notices, long text, and save/resume. For right-to-left languages inspect direction, choice alignment, mixed-direction numbers, and narrow screens. Test composition-based input when relevant. Export/import must preserve text exactly.

Bundled dictionaries and a flexible translation mechanism do not prove translation quality for every language. Record the languages and behaviors actually exercised. Retain the user's host model/effort; do not silently switch providers to obtain a translation.
