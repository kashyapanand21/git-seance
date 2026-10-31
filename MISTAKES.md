# MISTAKES.md

Every failure: what happened, why, the fix.

## 2026-10-28: P0 venv creation failed

- **What:** `py -3.11 -m venv .venv` printed "No suitable Python runtime found". Activate then failed, and `pip install` ran against the global Python.
- **Why:** I assumed Python 3.11 was installed without checking.
- **Fix:** Run `python --version` and `py -0` first, then create the venv from a Python that is 3.11 or higher (3.12 here). Confirm the `(.venv)` prefix before installing anything.

## 2026-10-28: P2 test failures

- **Porcelain assertion:** `fix not in plain` failed because `blame --porcelain` prints a `previous <sha>` line. Fix: check only the first line's sha.
- **Tie in blame majority:** a 2-line hunk split 1:1 between fix and reformat, so the test did not exercise "reformat wins". Fix: 3-line hunk where the reformat owns 2 lines.
- **`git log -L` oldest = file creation:** `-L` walks back to the file's first commit, not the commit that added the lines. Decision: dropped from the fallback chain (R3 deviation, approved as option A). `log_l` is kept and tested only to document the limit.

## 2026-10-28: P6 Ollama crashed on GPU

- **What:** `gemma4:e4b` and `gemma3:12b` returned HTTP 500 (`CUDA error: shared object initialization failed`, exit 0xc0000409). My first guess (curl quoting) was wrong.
- **Why (likely, not proven):** RTX 4050 has 6 GB VRAM; both crashing models are larger. `qwen2.5:3b` fits and worked.
- **Fix:** `SEANCE_NUM_GPU=0` forces CPU. gemma4:e4b also "thinks" by default, so we send `think: false`.

## 2026-10-29: P7b misplaced `fn` assignment

- **What:** `UnboundLocalError: fn` when running the real CLI.
- **Why:** The `fn = ...` line was applied one indent too deep, under the `raise typer.Exit(2)`, so it never ran. Unit tests called `run()` directly and never exercised `main()`.
- **Fix:** De-indent the line. Added `CliRunner` tests that invoke `main` the way a user does.

## 2026-10-31: demo repo setup

- **What:** `git push` failed with "src refspec main does not match any", and PowerShell commands failed in Git Bash.
- **Why:** I ran `git init` in a new empty folder instead of using the script's repo, and pasted PowerShell commands into Git Bash (`Remove-Item` missing, `\` eaten as an escape).
- **Fix:** Build the demo repo with `scripts/make_demo_repo.py`, and use one shell (PowerShell) for all commands.

## 2026-10-31: `--post` said "Could not fetch the PR"

- **What:** Every `--pr` run failed with the same message.
- **Why:** `GITHUB_REPOSITORY` and `GITHUB_TOKEN` were empty. `$env:` values only live in the PowerShell window where they were set, so `GitHubClient` was in git-only mode.
- **Fix:** Set the variables in the same window and check them before running. The error message names both variables.

## 2026-10-31: PR numbers and descriptions

- **What:** PR #2 and #3 were the opposite of what the instructions assumed, and PR #3's description was pasted into the wrong PR.
- **Why:** I told you which PR would get which number, but GitHub numbers PRs in creation order.
- **Fix:** Read the numbers off the PR pages before running the bot, and edit the description.

## 2026-10-31: model text auto-linked on GitHub

- **What:** The quote `(fixes #1)` rendered with `#1` expanded into the issue title.
- **Why:** GitHub autolinks `#<number>` in comments, and sanitising only stripped URLs, `@mentions` and HTML. Model text containing `#123` could create cross-reference notices on real issues.
- **Fix:** Quotes are shown in a code span, and `#<digits>` is neutralised in all model text.


## 2026-10-31: issue evidence missing from the live comment

- **What:** The comment listed only E1 (commit); linked issue #1 was missing though `context_for` found it.
- **Why:** The `for issue in ctx.issues` loop in `build_bundle` was indented under `if ctx.pr:` after an edit, so issues were only included when a PR existed. My earlier guesses (token, regex, stale cache) were wrong. Tests missed it because every test supplied a PR.
- **Fix:** De-indent the loop; add a test with an issue and no PR.
