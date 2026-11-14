Atlas export service — November 9–13, 2026

Maya merged the incremental export retry fix, [AT-214](https://example.invalid/atlas/issues/214). It is deployed to staging, the pre-production test environment; production rollout still awaits release approval. All 12 previously failing test cases passed in the staging replay. This evidence covers only those replay cases; we have no new production reliability measurement.

Luis completed the [onboarding checklist draft](https://example.invalid/atlas/docs/onboarding). Support identified two steps that need clarification. Luis plans to revise them next week; no specific date is committed.

Next actions and help needed:

- The proposed release step is to request production approval after the release team reviews the staging results. Approval has not been granted in the supplied notes.
- The nightly reconciliation test is blocked because its service account lacks access to the staging snapshot, a saved copy of test-environment data. Please identify an owner to request that access so the test can proceed. The access-request owner is unconfirmed, and no deadline was agreed. Manual staging checks are continuing and are not blocked by this access issue.
