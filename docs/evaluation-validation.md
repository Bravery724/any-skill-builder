# Evaluation workflow validation — v0.4.0

Recorded on 2026-11-15. This update adds iteration preparation, execution provenance, critique of evaluation criteria, and review of repeated operations. It does not change the two creation modes or questionnaire UI. The earlier [offline browser validation](offline-validation.md) remains versioned evidence rather than a new browser run.

## Mechanics and evidence

Regression checks exercise new iteration preparation, old-skill and no-skill baseline packets, withholding criteria from executor packets, preservation of snapshots and raw inputs, and refusal to overwrite an iteration. The evaluator distinguishes output assertions from pending reviews, missing execution records, and critique findings. It checks cited artifacts and rejects invalid repeated-work references, unsupported extraction validation, changed snapshots, and attempts to overwrite evidence with reports.

An independent source reviewer reproduced nine focused boundaries, including changed copied inputs, missing execution provenance, weak-check findings, report-write protection, and malformed record identifiers. Passing these checks does not authenticate an agent's declared identity or prove semantic quality.

The existing public example's nine recorded checks and reports remain unchanged when the new optional fields are absent. The existing form and two-mode regressions run alongside the new tests. See [GitHub Actions](https://github.com/Bravery724/any-skill-builder/actions/workflows/ci.yml) for the actual Ubuntu/Windows and Python 3.10/3.13 results on a commit or tag.

## Actual host execution

The preparation helper was used with the public two-case weekly-update plan. One fresh-context executor received only the generated executor packets, the preserved skill, and raw inputs. It completed both tasks sequentially and saved actual outputs and observable execution logs. A different fresh-context reviewer inspected those artifacts and the declared criteria, recorded reviewed checks and criteria feedback, and inspected the logs for useful repeated operations.

The executor did not fetch the fictional example links. Model identity and reasoning effort were unavailable and were not invented. No no-skill or old-version comparison was executed in this host check, and no benchmark-superiority claim follows from it. Baseline preparation and extraction-validation boundaries are covered separately by deterministic fixtures.

The first reviewer passed all seven original task checks but identified two missing coverage criteria. The report correctly remained `needs_attention` with exit code 1. The plan was revised and both tasks executed again by a different fresh-context executor. A separate fresh-context reviewer then passed nine checks with no material critique finding in that scope; the second report was `reviewed` with exit code 0. Earlier evidence was preserved. Both reuse inspections found no useful deterministic helper to extract. [Selected actual outputs and reports](../examples/evaluation-loop/README.md) show the distinction between passing checks and adequate evaluation coverage.

The host run was initially prepared before copied-input hashes were added during review. That record is preserved as created; the final helper's input-inventory behavior is checked by fresh preparation and mutation regressions. Earlier task outputs were not relabeled as new execution evidence.

## Limits

This is a focused execution-and-review check, not a new end-to-end research-to-skill build or a Claude Code/Antigravity IDE certification. No additional browser, model provider, trigger optimizer, or external service was introduced. A useful helper is extracted only when actual repetition warrants it; an empty completed reuse review is a valid outcome.

The optional system skill-creator validator was unavailable because the local interpreter has no PyYAML. The project's standard-library structure, evidence, release, and package checks remain the applicable validation. No dependency was installed for that optional validator.
