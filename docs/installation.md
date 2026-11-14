# Install, update, and remove

Install the complete `any-skill-builder` directory in a location your agent host discovers. The host must read local files and execute Python. Uploading a ZIP to an ordinary chat interface does not by itself provide those capabilities.

## Choose a download

Open [GitHub Releases](https://github.com/Bravery724/any-skill-builder/releases):

| File | Use |
| --- | --- |
| `any-skill-builder-0.3.0-source.zip` | Recommended for the verified installer; includes tests, examples, and maintainer tools |
| `any-skill-builder-0.3.0.zip` | Smaller runtime for manual installation; contains `any-skill-builder/` and all its resources |
| `any-skill-builder-0.3.0-manifest.json` | File sizes and SHA-256 hashes for release verification |

You can also use **Code → Download ZIP** or clone [the repository](https://github.com/Bravery724/any-skill-builder). That download is source, not the runtime-only ZIP. Extract it into a normal working directory with enough space, outside the host's skills directory and existing questionnaire runs.

Use a maintained Python release, preferably 3.13 or newer, for a new installation. Python 3.10 is the minimum compatible version. Check `python --version`; if your system provides `python3`, use it consistently below. No `pip install`, API-key setup, or Node installation is needed to use the skill.

## Install with the Skills CLI

The optional [Skills CLI](https://github.com/vercel-labs/skills) requires Node.js 22.20+. Run it from the project where you want the skill available:

```sh
npx skills add Bravery724/any-skill-builder --skill any-skill-builder
```

Select your host in the interactive installer. For a project-local Codex installation without prompts:

```sh
npx skills add Bravery724/any-skill-builder --skill any-skill-builder --agent codex --copy --yes
```

The default source follows the repository's default branch. To install the published release instead:

```sh
npx skills add Bravery724/any-skill-builder@v0.3.0 --skill any-skill-builder
```

Keep the explicit skill name: this repository also contains generated example skills. Add `-g` only if you want a global installation. The CLI chooses paths according to its supported hosts; confirm the reported path and refresh the host before using the skill. Installing files does not certify another host's behavior.

The CLI has its own update and removal commands; see its [command reference](https://github.com/vercel-labs/skills/blob/main/docs/commands.md). Its documented `DISABLE_TELEMETRY=1` or `DO_NOT_TRACK=1` setting disables its telemetry and security-audit requests. These settings belong to that installer, not to this skill. Use the Python installer below if you prefer no Node.js dependency. Python remains necessary for the builder with either installation route.

## Install from source

The source root is the extracted directory containing `README.md`, `tools/`, and `any-skill-builder/`. The named source release creates `any-skill-builder-0.3.0-source/`; a GitHub source download uses the repository/branch name instead.

Open a terminal in its parent folder. For the named source release, these commands work in PowerShell and common POSIX shells. If the terminal already opens inside the source root, omit the `cd` line:

```sh
cd any-skill-builder-0.3.0-source
python -B tools/install_skill.py --dest "~/.agents/skills"
```

The example uses the `~/.agents/skills` convention. Replace it with the directory documented by your host. Quote paths containing spaces. The installer creates the final `any-skill-builder/` component; do not add it to `--dest`.

On macOS/Linux where the interpreter is named `python3`, use:

```sh
python3 -B tools/install_skill.py --dest "~/.agents/skills"
```

The installer reports JSON containing `installed`, `changed`, `version`, and the absolute `path`. It verifies copied files and does not alter host settings. An identical repeated installation returns `changed: false`. A different installation is preserved and installation stops; use the update procedure below.

### Claude Code and Antigravity

From the extracted source root, choose the host and installation scope:

| Host | In one project | Across your projects |
| --- | --- | --- |
| Claude Code | `python -B tools/install_skill.py --dest "PROJECT/.claude/skills"` | `python -B tools/install_skill.py --dest "~/.claude/skills"` |
| Antigravity CLI | `python -B tools/install_skill.py --dest "PROJECT/.agents/skills"` | `python -B tools/install_skill.py --dest "~/.gemini/config/skills"` |

Replace `PROJECT` with the intended project's absolute path. The installer copies the complete runtime, not just `SKILL.md`. Open that project in the host afterward.

Claude Code supports `/any-skill-builder`; refresh with `/reload-skills` or start a new session if needed. Antigravity CLI also exposes skills as slash commands; use `/skills reload` or a new conversation. These paths and commands follow the [Claude Code skill documentation](https://code.claude.com/docs/en/skills) and [Antigravity skill documentation](https://antigravity.google/docs/skills). The latter also documents IDE and legacy locations; CLI testing does not certify the IDE interface.

An interactive first run is the easiest way to grant the required local Python and file permissions. The host researches, writes its private run directory, and either completes Full Auto or renders a standalone questionnaire. No questionnaire server or active host task is needed while you answer the saved HTML. A successful install does not grant execution permissions.

For headless automation, configure the necessary project-scoped permissions explicitly. Claude Code's `--permission-mode acceptEdits` and Antigravity CLI's `--mode=accept-edits` are different flags; neither promises approval of every command. Antigravity's `auto` mode also depends on a supported terminal sandbox and account. If it is unavailable on Windows, it can fall back to a mode that still needs approvals, which a headless run cannot display. Follow the host's [Claude Code permission modes](https://code.claude.com/docs/en/permission-modes) or [Antigravity execution modes](https://antigravity.google/docs/cli/modes/) instead of disabling protections globally.

## Install the runtime ZIP manually

1. Extract the runtime ZIP into a staging directory outside the host's discovery directory.
2. Inspect `any-skill-builder/`. It must contain `SKILL.md`, `scripts/`, `references/`, `assets/`, the license, and version.
3. Copy that complete directory into the host's skills directory, giving the final path `<host-skills>/any-skill-builder/SKILL.md`. Do not nest another `any-skill-builder/` inside it.
4. If the target already exists, stop and use the update procedure. Do not merge old and new resource directories.

The runtime ZIP does not contain `tools/install_skill.py`. Use the source ZIP for that installer.

## Confirm installation and first use

Refresh the host's skill list or open a new session according to its discovery rules. Confirm **Any Skill Builder** is listed. Then ask:

> Use any-skill-builder to create a skill for writing weekly project updates. Let me answer the design questions.

The host should read the installed skill, show its stage, and choose a separate run directory. This request selects Questionnaire mode: it researches the subject and delivers standalone HTML. To skip HTML, request Full Auto. If the mode is unclear, the agent offers those two choices in chat; no native slash submenu is assumed.

For a structural check, replace `INSTALLED_SKILL` below with the absolute installed path printed by the installer. For example, the first argument is the script inside that folder, and the second is the folder itself:

```sh
python -B "INSTALLED_SKILL/scripts/skill_builder.py" check-skill --path "INSTALLED_SKILL"
```

Keep quotes around both paths. On Windows, use the printed drive-letter path, with forward slashes or backslashes as appropriate for your shell. This check verifies files and references; it does not prove the host discovered or executed the skill.

## Update with a reversible backup

Use this procedure for a source-installer installation or a manually copied runtime. The installer deliberately has no force-overwrite or automatic-update option.

1. Finish or pause any task using the installed skill. Keep its **run directory** and exported answers where they are; they are independent of the runtime.
2. Download and extract the new release into a separate staging directory. Check its version and run the structural check against that staged runtime.
3. In your file manager, inspect the **absolute path** of the current installation. Confirm it is exactly `any-skill-builder` inside the intended host skills directory. If any installation path is a symbolic link or junction, follow the separate instructions below.
4. Choose a new, uniquely named backup location **outside every directory scanned by the host**, such as a dated folder under a separate `skill-backups` directory. Move the complete installed `any-skill-builder` folder there. Keep it until the update works. Do not leave a second copy named `any-skill-builder-old` inside a discovery directory.
5. Install from the new source root using the same `--dest`, or copy the staged runtime into the now-empty target. The final folder must again be `<host-skills>/any-skill-builder/`.
6. Check the installed `VERSION`, run the structural check, refresh the host, and invoke the skill. To resume a project, give the host its existing run directory; do not call `init` for it again.

Use Explorer, Finder, or your file manager for the folder move and replacement, checking exact paths before each operation. Updating the skill does not rewrite old HTML or migrate saved runs automatically. v0.3.0 replaces the previous connection and answer-handoff formats. Keep legacy files intact; inspect them and migrate meaningful decisions explicitly into a new run if the current helper rejects their format. Never erase unresolved intent merely to make an old file importable. For a compatible current run, rerender only after preserving any unsaved browser answers.

### Roll back a failed update

Stop the task using the new version. Move the new runtime out of the discovery directory into a separate diagnostic folder. Move the preserved old runtime back to its original `any-skill-builder` path, refresh the host, and confirm the restored version. Leave run records untouched. If the new version changed a run's data format, inspect its release notes and the run's history before resuming with the old version.

### Symbolic links and junctions

The source installer rejects symbolic-link destinations. Some systems use a junction or another link to keep runtime files on a different drive. Determine both the discovery path and its real target before updating. Keep the link in place when its target is the intended installation, and use the host's link-aware installation method or manually replace the verified target after making a separate backup. Do not recursively remove a discovery link as an update shortcut. If you cannot identify its real target, leave it unchanged until you can.

## Remove the skill

Stop tasks using the skill. Verify the absolute installed path, then move the complete `any-skill-builder` runtime out of the discovery directory into a separate backup location. Refresh the host and confirm it is no longer listed. You can later delete that verified backup through your file manager if you no longer need it.

For a linked installation, remove only the verified discovery link through the host's link-aware workflow and decide separately whether to retain its target. Removing the skill does **not** require deleting questionnaire runs, exported answers, generated skills, or research. Keep or remove those user files separately according to your retention needs.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| `python` is not found | Install a maintained Python version or use the available `python3` command. Check its version before retrying. |
| `tools/install_skill.py` is missing | Open the source root. A runtime-only ZIP has no installer. |
| A different installation already exists | Preserve it and use the reversible update procedure. Do not merge directories or delete it just to bypass the check. |
| The installer rejects a symbolic link | Resolve the actual target and use the link-aware manual procedure. |
| Installation succeeds but the host cannot find the skill | Verify the host's directory, exact `any-skill-builder/SKILL.md` nesting, and whether discovery needs a refresh or new session. |
| Save answers downloads HTML but nothing happens in chat | Return to the skill-building chat and say “continue”. The agent checks the recorded path; if you saved elsewhere, give that path or file. HTML does not wake a closed chat. |
| The agent finds only an unanswered template | Use the questionnaire's Save answers button, then provide the downloaded file's location if the browser saved elsewhere or added a suffix. |
| Multiple saved files conflict | Identify which version you intend. The helper does not silently choose an arbitrary newest file or overwrite newer decisions. |
| An old release's run is rejected | Keep it intact and inspect its version. Use a reviewed migration into a new run, or the previous runtime to read its decisions. |

## Verified scope

The following observations were recorded on 2026-11-14 for earlier releases through **v0.2.3**. They are historical evidence, not a claim that the redesigned v0.3.0 workflow was rerun in those hosts or IDE extensions:

| Environment or capability | Evidence |
| --- | --- |
| Windows, Python 3.10.11 | Backend suite run from a freshly extracted source ZIP; minimum-version compatibility exercised |
| Windows, Node 25.2.1 | Form regression suite executed; Node is optional for end users choosing the Skills CLI route |
| Windows, Python 3.15.2 | Installer, runtime ZIP commands, fresh-source checks, and reproducible packaging exercised |
| Existing Codex desktop session | Installed skill is exposed in its skill catalog; this does not prove every host or every fresh-session discovery flow |
| Claude Code 2.1.322, Windows | Actual native discovery, authored questionnaire, live browser handoff, revisioned repairs, generated skill, and three fresh-context task cases; see [host validation](host-validation.md) |
| Antigravity CLI 1.5.9, Windows | Actual authored questionnaire, browser submission, supervised CLI resume/receipt, generated skill, and three fresh-context regression cases after readability refinement; the IDE was not tested; see [host validation](host-validation.md) |
| Chrome, Windows | Recorded checks cover 320/390/768/1100px layouts and live submission; native OS input methods and every language were not certified |
| GitHub Actions | [All four Ubuntu/Windows and Python 3.10/3.13 jobs passed with Node 24](https://github.com/Bravery724/any-skill-builder/actions/runs/43591884294), including Python tests, form tests, release checks, example evidence, and packaging; consult current runs for later commits |
| Skills CLI 1.8.1, Windows | Installed from the public repository with explicit `--skill any-skill-builder --agent codex --copy --yes`; all 18 runtime source files matched, only the builder was installed, and init/import/validation/render commands passed |
| Other hosts and installer modes | These observations do not cover other host variants, every global installation path, or every host-specific behavior |

For current work, choose Full Auto or the standalone Questionnaire flow. See [testing](testing.md) for the checks required for a new version. Neither historical CLI run certifies the Claude Code IDE extension or Antigravity IDE.
