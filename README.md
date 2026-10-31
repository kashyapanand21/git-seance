# git-seance

Summon the reason a line of code was written.

When a pull request deletes or rewrites code, `git-seance` traces the removed lines
through git history to the commit (and, with a token, the PR and issue) that added
them, and posts **one** comment with the original reason and links. Chesterton's Fence,
as a bot: don't tear down a fence until you know why it was built.

Built for DEV's Hacktoberfest Open-Source AI Challenge, Week 4 ("Ghost in the Machine").

## How it works

1. Parse the PR diff and keep removed or rewritten hunks (whitespace-only changes,
   lockfiles and generated files are skipped).
2. Trace each hunk with `git blame -w` on the merge-base (honouring
   `.git-blame-ignore-revs`), falling back to `git log -S` then `-G`.
3. Collect the origin commit message, the merged PR and linked issues (GitHub API).
4. Score the evidence with plain rules (fix, revert, hotfix, workaround, linked bug,
   a "do not remove" comment). No signal means **no comment**.
5. A local open-weight model (Gemma through Ollama) writes up the evidence as
   schema-constrained JSON, at temperature 0.
6. A verifier drops every claim that cites unknown evidence or quotes text that is not in
   the cited evidence. If nothing survives, the comment shows raw evidence links only.
7. One comment is created, or updated in place, on the PR.

**Git finds the evidence. The model never decides what the origin commit is.**

## Trust design

- Commit messages, PR bodies and issue text are untrusted. The model has no tools.
- Cite or drop: claims must list evidence ids and quote text found verbatim in them.
- Model text is sanitised (links, `@mentions`, HTML and `#123` references removed) and
  wrapped in fixed, hedged wording.
- Advisory only: it never blocks a merge, and a failed post never fails the run.
- The only action the bot takes is creating or updating one PR comment.
- Needs a token with: Contents (read), Issues (read), Pull requests (read and write).

## Install

Requires Python 3.11+, git, and [Ollama](https://ollama.com) with a model pulled.

```powershell
git clone https://github.com/kashyapanand21/git-seance
cd git-seance
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
ollama pull gemma4:e4b
```

On macOS or Linux, activate with `source .venv/bin/activate`.

## Use

Run it inside a clone of the repository whose PR you want to check.

```powershell
# Compare two refs locally, printing the comment (no GitHub needed)
git-seance --base main --head my-branch

# Skip the model: raw evidence only
git-seance --base main --head my-branch --no-model

# Check a real PR and post or update the comment
$env:GITHUB_REPOSITORY = "owner/repo"
$env:GITHUB_TOKEN = "<fine-grained token>"
git-seance --pr 42 --post
```

A run that finds nothing risky prints nothing and exits 0.

### Settings (environment variables)

| Variable              | Default                    | Meaning                                                         |
| --------------------- | -------------------------- | --------------------------------------------------------------- |
| `SEANCE_MODEL`      | `gemma4:e4b`             | Any Ollama model tag. Swap it with one setting.                 |
| `SEANCE_OLLAMA_URL` | `http://localhost:11434` | Ollama server                                                   |
| `SEANCE_NUM_GPU`    | unset                      | `0` forces CPU. Needed on a 6 GB GPU where the model crashed. |
| `GITHUB_TOKEN`      | unset                      | Without it, git-only mode: commit evidence only                 |
| `GITHUB_REPOSITORY` | unset                      | `owner/name`; set automatically in GitHub Actions             |

## Demo

[`kashyapanand21/seance-demo`](https://github.com/kashyapanand21/seance-demo) has two open
PRs. One deletes a retry guard that was added to fix a real bug, and the bot warns. The
other deletes an unused variable, and the bot stays silent. Rebuild the demo repo with
`python scripts/make_demo_repo.py <folder>`.

## GitHub Action (untested example)

Written but **not yet run** on a self-hosted runner, so treat it as a starting point.
The model is local, so the runner must be too. Use it only on repositories you own.

```yaml
name: git-seance
on:
  pull_request:
    types: [opened, synchronize, reopened]
permissions:
  contents: read
  pull-requests: write
jobs:
  seance:
    if: github.event.pull_request.head.repo.full_name == github.repository  # skip forks
    runs-on: self-hosted
    timeout-minutes: 10
    env:
      SEANCE_MODEL: gemma4:e4b
      SEANCE_NUM_GPU: "0"
      GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # blame and log need full history
      - run: python -m pip install -e .
      - run: git-seance --pr ${{ github.event.pull_request.number }} --post
```

- `git log -L` is not used: it walks back to the file's first commit, not the commit that
  added the lines (see `MISTAKES.md`).

## Results (replay, gemma4:e4b on CPU)

| Metric                                    | Result                       |
| ----------------------------------------- | ---------------------------- |
| Origin hit rate                           | 7/7                          |
| Quiet on harmless deletions               | 3/3                          |
| Planted injection leaked into the comment | 0/1                          |
| Unsupported claims posted                 | 0 (enforced by the verifier) |
| Claims proposed / dropped by the verifier | 7 / 0                        |
| Slowest case                              | 30 s                         |

Full per-case table: [`eval/report.md`](eval/report.md).

## Known limits

- A non-whitespace reformat commit that is not listed in `.git-blame-ignore-revs` can
  still win blame.
- The verifier checks grounding, not intent. An accurately quoted injected sentence passes
  it. The limits are no tools, one action, sanitised output and fixed wording.
- Squash merges collapse history; the PR text is then the main source of the reason.
- Same-repo PRs only. Fork PRs are not supported.
- GitHub responses are cached on disk and can go stale if a PR or issue is edited.
- The replay (`python eval/replay.py`) uses 10 scripted cases in temporary repos, not real
  public PRs, and runs in git-only mode. Treat the numbers below as a pipeline check, not a
  benchmark.

## Develop

```powershell
ruff check .
pytest -q
```

Tests build real temporary git repos; GitHub and Ollama are faked with `httpx.MockTransport`.

## License

M

Summon the reason a line of code was written.

When a pull request deletes or rewrites code, `git-seance` traces the removed
lines through git history to the commit, PR and issue that added them, and
posts one comment with the original reason and links. Git finds the evidence;
a local open-weight model (Ollama) only writes it up, and a verifier drops any
claim the evidence does not support.

> Status: work in progress for DEV's Hacktoberfest Week 4 ("Ghost in the Machine").

## Install (development)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
ruff check .
pytest
```

## License

MIT
