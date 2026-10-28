
# git-seance

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
