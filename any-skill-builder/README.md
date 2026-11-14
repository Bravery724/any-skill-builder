# Any Skill Builder

Create or improve a reusable skill through subject research, useful design questions, and actual evaluation.

[Project and installation](https://github.com/Bravery724/any-skill-builder) · [Example requests](https://github.com/Bravery724/any-skill-builder/blob/main/docs/usage.md) · [Releases](https://github.com/Bravery724/any-skill-builder/releases)

## Choose how to work

| Mode | What happens |
| --- | --- |
| **Full Auto** | AI researches the topic, prepares and answers the design questions, then creates and evaluates the skill. No HTML is generated. |
| **Questionnaire** | AI prepares an HTML questionnaire. Answer the parts you care about, save it, and return to chat. AI fills the remaining blanks and builds the skill. |

If your request already makes the choice clear, the agent starts directly. Otherwise it offers these two modes in chat. The host controls its skill picker and whether invocation uses `/`, `$`, or another interface.

**Full Auto:**

> Use any-skill-builder in Full Auto to create a skill that analyzes research papers from any field and develops testable research ideas.

**Questionnaire:**

> Use any-skill-builder to create a webtoon-making skill. Research the options and prepare an HTML questionnaire so I can choose the direction.

You can provide examples, source material, and constraints, but a rough idea is enough. These requests create a reusable skill; use the finished skill afterward to do its task.

## Save and continue

The questionnaire shows what skill is being made, the question count, and answered/unanswered status. Choose an option, use **Other — describe**, or leave a question blank. Core questions recommend direct input but can also be left for AI. Clear an answer if you want AI to decide it instead.

Choose **Save answers** on any page. It downloads an HTML file containing your answers; you do not need to visit the final page. Save it in the original location when practical. Browsers can choose another folder or append a suffix, so saving does not guarantee the original was overwritten.

Return to the same chat and say:

> Continue building from the saved HTML.

The agent checks the known questionnaire file, keeps meaningful answers, and decides the blanks. If you saved elsewhere, provide that path or the file. If a file is missing or ambiguous, the agent asks only for the information needed to find the right one. No server needs to remain running, and the HTML does not contact a model or automatically restart a closed chat.

Brief but meaningful answers such as "none" or "0" are respected. Clearly unusable input is reviewed in context by the agent, retained in the records, and replaced with a reasoned AI decision. An unusual preference is not discarded merely because it differs from the recommendation.

## Improve or resume

Provide the existing skill folder and describe what should improve. The agent preserves working behavior as a baseline and compares the revision on suitable cases. For an unfinished build, provide its saved run folder or continue in the existing conversation; it reuses valid decisions instead of starting over.

To request only a questionnaire, say so. The agent stops after delivering it and waits for your continuation.

## What you receive

A completed build includes the reusable skill, a concise usage guide, a starting request, and the checks and limits actually observed. Source files default to English; questions, chat, and task outputs follow your language unless you request otherwise.

For complex builds, consider a capable reasoning model and a higher reasoning-effort setting in your host. This can help with research and difficult decisions, but is not a guarantee or a measured success-rate claim for this builder. Reliable sources, useful examples, and actual tests still matter. The skill does not silently change your model, provider, or effort.

The host must support local file access and Python 3.10 or newer. Research and image candidates use its available tools; no separate model API key is required. See the [host-specific installation guide](https://github.com/Bravery724/any-skill-builder/blob/main/docs/installation.md#claude-code-and-antigravity).