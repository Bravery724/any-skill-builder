Atlas export service — November 9–13, 2026

Maya’s [export retry fix (AT-214)](https://example.invalid/atlas/issues/214) is merged and deployed to staging, the pre-production test environment. All 12 previously failing test cases passed when replayed there. This result covers those test cases only; we have no new production reliability measurement, and production rollout still awaits release approval.

- Luis completed the [onboarding checklist draft](https://example.invalid/atlas/docs/onboarding). Support identified two steps needing clarification. Luis plans to revise them next week; no specific date is committed.
- The nightly reconciliation test is blocked because its service account lacks access to the staging snapshot. Manual staging checks are continuing and are not blocked by this access issue.

Next, the proposed release step is to request production approval after the release team reviews the staging results. Approval has not been confirmed.

Help needed: assign an owner to the staging access request and arrange the access needed to unblock the nightly reconciliation test. The request owner and deadline are unconfirmed.
