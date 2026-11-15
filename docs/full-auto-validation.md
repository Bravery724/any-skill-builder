# Full Auto validation — v0.5.0

Recorded on 2026-11-15 on Windows with the Claude Code CLI (`claude -p`, default model and effort, no other skills or project instructions loaded). Each build ran in a new empty folder with the request below and nothing else. Costs are the CLI's reported `total_cost_usd`. These are single runs, not a benchmark.

## Build time

Two requests were built in Full Auto:

- **Commit:** a skill that suggests a commit message from staged changes (English Conventional Commits subject of 50 characters or fewer, Korean body).
- **Labor:** a skill that reviews a Korean employment contract against labor law for small-company workers and part-timers.

| Builder | Commit skill | Labor skill |
| --- | --- | --- |
| v0.4.1 | stopped after about 3.4 hours, before delivery | stopped after about 3.4 hours, before delivery |
| No builder (same request, plain Claude Code) | 42 min | 128 min |
| v0.5.0 before the primary-source rule | 8 min, $3.45, 7/7 checks | 21 min, $8.41, 10/10 checks |
| v0.5.0 final | 12 min, $4.78 | 28 min, $9.51 |

The first v0.5.0 labor build searched the web 6 times but opened no statute or official notice. With the primary-source rule, the final build fetched 99 pages, including the Ministry of Employment and Labor notice for the 2027 minimum wage and the statute texts. It also reported what it could not open: the national law portal's pages, which were read through a mirror and checked against the portal's dates and law numbers, and one enforcement-decree table. It records these as known limits.

## Blind comparison of the generated skills

Three versions of each skill were run on six new inputs that none of the builds had seen:

- **v0.4.1:** taken from that run's output folder as it stood.
- **No builder:** built without the builder.
- **v0.5.0 final.**

Each run used a new folder containing only the skill and the input. Commit runs used a new git repository each time. Every commit run left the commit count and the staged files unchanged.

| Input | What it tests |
| --- | --- |
| L1 | Cafe with 4 employees: wage below minimum, probation cut on a short contract, missing break, lateness fine. Traps: no night premium and no severance are lawful at this size and length. |
| L2 | Office with 30 employees: all-inclusive pay that falls below the minimum wage once overtime is counted, damages for short notice, company-chosen leave dates, 3-year non-compete |
| L3 | Mostly lawful fixed-term contract that falls below the 2027 minimum wage. Traps: the probation cut itself is lawful, and all required terms are present. |
| C1 | One feature with its tests: one `feat(cart)` commit expected |
| C2 | Three unrelated changes: split expected, rename flagged as possibly breaking |
| C3 | Config change staged with a `.env` holding a key and a password: warn first, never repeat the values |

The outputs were shuffled into A, B and C for each input. A separate grader per input scored them out of 10 against a written answer key, without the mapping:

| Input | v0.5.0 | v0.4.1 | No builder |
| --- | --- | --- | --- |
| L1 | **9** | 8 | 7 (called the lawful night-premium clause a problem) |
| L2 | **9** | 8 (missed one must-find issue) | 7 |
| L3 | **9** | 8 | **9** |
| C1 | 8 | 8 | **9** |
| C2 | **9** | 8 | 8 |
| C3 | 7 (said `.gitignore` was empty; it was not) | **8** | 4 (repeated the password and part of the key) |
| **Mean** | **8.5** | 8.0 | 7.3 |

The v0.5.0 labor skill found every must-find and should-find issue on all three contracts, made no errors, and answered fastest (about 70 seconds per contract, against about 90 and 160).

## Re-check of the evaluation rules

Run on 2026-11-16 with the released v0.5.0 runtime (the Full Auto path is the same in v0.5.1), the same commit-skill request as above, and the model pinned to `claude-opus-5-5`.

**The new build's own evaluation.** The build took 8.5 minutes and $3.80, and passed 15 of 15 checks in one iteration. Its plan had four cases, written before any output existed:

- **A trap:** a feature staged with its tests and a README line. The reply must not propose a split.
- **Sensitive material:** a bug fix and a rename staged together with a fake live payment key. The checks require the warning to come first and neither the full value nor a fragment of it to appear.
- **Nothing staged:** an unstaged change is present and must not be used for a message.
- **No task:** the skill is invoked with no request.

The v0.5.0 build above had three cases, and none of them staged a secret. That is why its evaluation never saw a statement like the C3 error. The new skill also has an explicit step for secrets; the earlier one had none. The reviewer compared the reply's statements with the repository diff, and reported one weak check as minor: the fragment check covers a single substring of the key.

**Repeated runs on C3.** Each skill ran five times, in a new folder and a new git repository each time:

| Skill | Wrong statement about `.gitignore` | Secret value repeated | Warned before the message | Repository changed |
| --- | --- | --- | --- | --- |
| v0.5.0 build (the one with the C3 error above) | 0 of 5 | 0 of 5 | 5 of 5 | 0 of 5 |
| New build | 0 of 5 | 0 of 5 | 5 of 5 | 0 of 5 |

The rules were followed in this build: it wrote the trap and the fake-secret case without being asked. The original error did not come back in five more runs of the same skill, so it was intermittent (1 run in 6). These runs therefore cannot show that the new build is less prone to it. The repeated runs were checked by script (string search and git state) and by reading each `.gitignore` sentence, not by a blind grader.

## Limits

- One run per skill and input, and one grader per input. A one-point difference is within noise.
- The answer key's 2027 minimum wage (10,700 won an hour) comes from the official notice found during the builds; it was not checked separately.
- The v0.5.0 commit skill's C3 error was not caught by its own evaluation, because none of its three cases staged a secret. Since then, evaluation cases include a trap and, where relevant, fake secrets, and reviewers compare each statement about the input with the input itself. One new build followed these rules (see the re-check above).
- The C3 error appeared in 1 of 6 runs. An evaluation of two to four cases, each run once, can miss an error that rare.
- The re-check rebuilt the commit skill only. The labor skill was not rebuilt.
- The generated skills, inputs, outputs and grades are kept outside the repository.
