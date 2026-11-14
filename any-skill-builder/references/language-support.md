# Language support

The builder accepts Unicode subject material, questions, and answers. Reusable package files default to English: instructions, references, README files, comments, and metadata. Newly generated skills follow that default unless the user explicitly requests another file language. Preserve original user text, intentional translations, and multilingual test material.

Questionnaires, chat replies, and the generated skill's task outputs naturally follow the conversation's language. An explicit output-language request takes precedence. Do not ask the user to select a language or translate a dictionary. Localization is the host's responsibility; source prose language does not dictate the programming language of generated helpers.

## Set the questionnaire locale

New runs record an explicit English fallback. Before rendering, set the actual form language to the conversation language through `questionnaire.locale`:

```json
{"language":"ar","direction":"rtl","messages":{"...":"complete translated message dictionary"}}
```

The example's `messages` value is explanatory, not valid production input. Read `assets/locales.json` and translate every English message key when no bundled dictionary is suitable. Preserve internal keys and all named `{placeholders}`. Do not translate IDs, option values, enum names, or JSON field names.

English (`en`) and Korean (`ko`) dictionaries are bundled; regional variants can use the base dictionary. Other valid language tags use a complete host-authored dictionary. Set `direction` to `rtl` for a right-to-left interface and `ltr` otherwise. The presence of an English acronym does not change the form's reading direction.

Current dictionaries include the request summary, Other input, answered/unanswered states, core guidance, blank-to-AI explanation, Save answers, download feedback, resume guidance, and reset confirmation. Use the current catalog as the authority. The offline redesign removed the old connected-form and special-state messages; an older custom dictionary must be reviewed and translated against the new keys rather than silently mixed with English fragments.

Updating a questionnaire without a locale preserves its existing choice. Do not rewrite old saved user data merely to refresh translations. If an incompatible legacy run needs migration, preserve its answers and original language explicitly in a new reviewed run.

## Preserve natural wording

Keep the request summary in the conversation language and display it as text. Use short, ordinary labels for saving and continuing; avoid making users learn internal export IDs or command names.

The download notice must say what actually happened. It should explain that the answered HTML is being downloaded, the browser may choose another location or filename, and the user should return to chat. Do not translate this into a claim that the original file was overwritten or that an AI has already received it.

Use the same language for questions, options, help, recommendation reasons, and completion guidance. Preserve exact paths and IDs when they are necessary, but do not expose them as decorative interface content.

## Research across languages

- Consult relevant local-language material and primary sources in other languages when useful. Explain translation or evidence gaps.
- Preserve names, units, dates, accents, and mixed-script text. Language alone does not establish jurisdiction, location, budget, or environment.
- For unfamiliar specialist terminology, retain the original term with an explanation or consult a reliable source.
- A skill written in English may accept multilingual input; state that behavior in its instructions and tests.
- Use portable ASCII skill names when a host requires them, without imposing ASCII on questions or answers.

## Verify without overstating coverage

Exercise the actual chosen language, including long text, Other inputs, save, reopening, and host import. For RTL, inspect layout, mixed-direction numbers, choice alignment, and narrow screens. Composition-based input requires both relevant event regressions and, when claiming native IME coverage, the actual operating-system input method.

Saved HTML and import must retain Unicode exactly. Tests of a flexible translation mechanism do not certify every language, translation, or keyboard. Record what was actually exercised. Preserve the user's host model and effort rather than silently switching providers for translation.