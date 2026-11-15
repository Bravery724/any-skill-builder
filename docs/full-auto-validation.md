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

## Limits

- One run per skill and input, and one grader per input. A one-point difference is within noise.
- The answer key's 2027 minimum wage (10,700 won an hour) comes from the official notice found during the builds; it was not checked separately.
- The v0.5.0 commit skill's C3 error was not caught by its own evaluation. Since then, evaluation cases include a trap and, where relevant, fake secrets, and reviewers compare each statement about the input with the input itself. This change has not been run on a new build yet.
- The generated skills, inputs, outputs and grades are kept outside the repository.
