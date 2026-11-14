# Any Skill Builder

Turn an idea into a reusable skill through subject research and guided design questions.

[Project and installation](https://github.com/Bravery724/any-skill-builder) · [Releases](https://github.com/Bravery724/any-skill-builder/releases)

## Start with your task

Tell your agent what you want the new skill to do. Add any examples, materials, or constraints you already have. You do not need a finished prompt or a technical specification.

> Use any-skill-builder to create a skill that analyzes research papers and suggests testable research ideas. Let me answer the design questions.

To delegate the design choices:

> Use any-skill-builder to create a webtoon-making skill. Research the options, recommend the answers, and continue through implementation.

To improve or resume work, provide the existing skill folder or saved run directory and explain the desired change. The agent preserves your recorded decisions and continues from the saved state.

## Answer or delegate

The agent researches the subject and prepares a questionnaire or asks in chat. You can answer, leave questions for AI, or defer a decision for later discussion. Core questions recommend your input but remain delegatable.

In the questionnaire, select **Let AI decide unanswered questions** if needed, then choose **Finish** on any page. Existing answers and deferrals stay protected. If Finish downloads a file, return it to the skill-building chat. A downloaded file does not restart a closed chat.

## What you receive

A completed build includes the reusable skill, a concise usage guide, a starting request, and the checks and limits actually observed. If you request only a questionnaire or another part, the agent completes that part.

The files use English by default. Conversation, questions, explanations, and task outputs follow your language unless you request otherwise.

## Getting help

Ask “How do I use any-skill-builder?” for guidance. When you invoke it without a task or earlier context, it briefly introduces itself and asks what you want to create. When the task is already clear, it starts the work.

The host may show a short description and starting prompt in its skill picker. The host controls whether invocation uses `/`, `$`, or another interface. It must support local file access and Python execution; the skill does not include its own model or API key.
