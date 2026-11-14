Atlas export service — weekly update, November 9–13, 2026

Maya merged the fix for retries when exporting newly changed data ([AT-214](https://example.invalid/atlas/issues/214)), and it is deployed to staging. All 12 previously failing replay fixtures passed there. These results cover only those test cases; we have no new production reliability measurement. Production rollout is still awaiting release approval.

- **Onboarding:** Luis completed the [onboarding checklist draft](https://example.invalid/atlas/docs/onboarding). Support identified two steps needing clarification. Luis plans to revise them next week; no specific date is committed.
- **Blocked test:** The nightly reconciliation test, which checks that data matches, needs its service account to access the staging snapshot. The access request has no recorded owner or agreed deadline. Manual staging checks continue and are unaffected by this blocker.
- **Proposed next step:** Request production approval after the release team reviews the staging results. Approval has not been granted in the supplied notes.

**Help needed:** Please confirm who will own the staging snapshot access request so the nightly reconciliation test can proceed.
