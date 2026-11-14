# Security

The form server binds to loopback and requires the run's token. Keep tokenized URLs private. It accepts versioned questionnaire data, not commands to execute. Registered image assets must stay within the run directory. These boundaries do not replace careful handling of untrusted source material by the host agent.

Real answers, research, and generated content may be sensitive. Store them outside public repositories. The offline form uses browser storage; exporting an answer file is an explicit handoff, not automatic submission to a stopped agent.

## Report a vulnerability

On this repository's GitHub page, open **Security → Advisories → Report a vulnerability**. Use that private form for sensitive details. Do not put live tokens, private answer files, or exploit details involving user data in a public issue.

If the button is unavailable, the owner has not enabled the private channel for that copy of the repository. Open a public issue asking only for a private reporting channel; omit vulnerability details, tokens, and user data until a private route is available. This document does not imply that a channel exists before the repository has been configured, and it does not invent an owner email address.

## Before publishing a repository

The owner must enable **Private vulnerability reporting** in the repository's security settings and verify that the reporting button is available. Follow [GitHub's configuration guide](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository). Ensure a maintainer receives the resulting notifications. This is a repository setting, not something the local release tools can enable.

This project does not promise an audited security certification or a fixed response time. See [release preparation](docs/releasing.md) for the remaining publication checks.
