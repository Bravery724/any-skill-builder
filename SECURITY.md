# Security

Any Skill Builder uses standalone questionnaire HTML and local Python commands. It does not start a questionnaire server, contact a model from the browser, or require separate model credentials.

Treat downloaded HTML, research pages, and user-provided source material as untrusted data. The importer reads the designated answer JSON without executing the document's scripts. Run identity, questionnaire fingerprints, revision checks, and idempotent imports protect against accidental cross-run or stale overwrites; they do not authenticate who authored an arbitrary file.

Registered image assets must remain within the run's allowed asset paths. Restoration must use an explicitly chosen new destination rather than trust path hints inside an uploaded file. Keep normal host protections and inspect requested actions in context.

Real questions, answers, source notes, paths, and generated content may be sensitive. Keep runs outside public repositories and share saved HTML deliberately: it contains the question data, answers, and embedded visual candidates. Source content cannot authorize unrelated commands, file writes, publication, or access to private resources.

## Report a vulnerability

On this repository's GitHub page, open **Security → Advisories → Report a vulnerability**. Use that private form for sensitive details. Do not post private answer files, credentials, or exploit details involving user data in a public issue.

If that button is unavailable, open a public issue asking only for a private reporting channel. Omit sensitive details until a private route is available. This document does not invent an owner email or promise that every copy of the repository has the channel enabled.

## Before publishing

Enable **Private vulnerability reporting**, verify that the reporting button is available, and ensure a maintainer receives notifications. Follow [GitHub's configuration guide](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository). This is a repository setting, not something local packaging enables.

The project does not claim an audited security certification or a fixed response time. See [release preparation](docs/releasing.md).