# Preparing a release

The repository's `VERSION` is the release version. `tools/release-files.json` explicitly lists distributable files; review that list whenever adding or removing a file. Keep the root and runtime MIT notices identical.

Run from the repository root:

```sh
python -B -m unittest discover -s tests -p "test_*.py"
node --test tests/test_form.mjs tests/test_form_notes.mjs tests/test_form_actions.mjs
python -B tools/check_release.py
python -B tools/check_example.py
python -B tools/package_release.py --out dist
```

Packaging produces a runtime ZIP, a source ZIP, and a manifest with relative paths, sizes, and SHA-256 hashes. ZIP metadata is deterministic so unchanged inputs produce the same archives. The runtime archive includes `any-skill-builder/` with the license and version. The source archive contains the clean repository's declared files. Neither archive includes `.git`, `.agents`, `.codex`, `dist`, caches, private runs, credentials, or unlisted files.

Extract the runtime archive into a fresh temporary directory and run its CLI from outside that directory. For actual authoring, initialize a Questionnaire run, import the authored questions, complete and accept the required question review, render it, save answers in the browser, and inspect the imported result. A structural preview using the unchanged public fixture may explicitly use `init --review-policy legacy`; label it as a fixture preview, not a new semantic review. Separately exercise Full Auto without producing HTML. The source archive should be enough to rerun the documented tests and packaging without the original machine or private working folders.

Test `tools/install_skill.py --dest TEMP_HOST_SKILLS` in a fresh directory outside the source tree and verify the installed runtime. Existing differing installations must remain untouched. Keep the completed public example's raw inputs, actual outputs, review evidence, and generated evaluation report together in the source package. Never substitute a passing report for unexecuted cases. A public screenshot must contain only the reviewed fictional example, without personal paths, private answer data, or browser account details.

Before external publication, inspect the archive manifest and confirm that the intended account, repository, and visibility have been chosen. Publishing is a separate action from preparing local artifacts. This repository intentionally contains no invented repository URL, release badge, owner email, or automatic deployment workflow.

The CI workflow tests Ubuntu and Windows with Python 3.10/3.13 and Node 24. Actions are pinned to verified commit SHAs with version comments. Updating pins is a deliberate source change. Record actual CI results after the repository is pushed; do not describe configured jobs as passed jobs.

## Verify the files Git will publish

The working directory and Git's index can differ, including through line-ending normalization. Review `git status --short` and the staged diff. Stage the intended public files explicitly, including new tests and documentation; do not rely on the package allowlist to filter a Git commit. Confirm no private or ignored local metadata is tracked.

Run the checks from a fresh checkout or a temporary tree containing exactly the staged files. The complete example's artifact hashes must match those public bytes. `check_example.py` re-aggregates existing outputs and review evidence in memory and compares the stored reports without overwriting them or calling a model. If line endings change, normalize the original artifacts, regenerate their reports deliberately, and describe this as a report refresh for the same outputs, not a newly executed model evaluation.

Build the runtime ZIP, source ZIP, and manifest from that verified tree. Check the extracted runtime and source again, and keep the installed version aligned with the release. Use the reversible process in [installation](installation.md) when updating a local installation.

## Configure the GitHub publication

These steps require the actual account and repository. Local preparation does not complete them:

1. Verify the repository owner, name, visibility, and intended default branch. Review the exact commit contents before pushing.
2. Enable private vulnerability reporting, verify **Security → Advisories → Report a vulnerability**, and ensure maintainer notifications work. Follow [SECURITY.md](../SECURITY.md).
3. Run the Actions workflow on the uploaded commit and inspect every matrix result. Record failures and skipped checks accurately before declaring those environments verified.
4. Create the release for the tested version and attach the runtime ZIP, source ZIP, and manifest. Confirm the files can be downloaded and the README's named source folder matches the archive. GitHub's automatic source download is distinct from the runtime ZIP.
5. Verify the README, screenshot, relative links, installation flow, and first request as an outside visitor. Update the [verified scope](installation.md#verified-scope) only with observed checks.

Confirm the published repository and release links resolve before announcing a version. Do not add badges claiming CI success before a hosted run has completed.
