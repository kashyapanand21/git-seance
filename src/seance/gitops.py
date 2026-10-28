from __future__ import annotations

import subprocess
from pathlib import Path


class GitError(RuntimeError):
    """git exited with a non-zero status."""


def run_git(args: list[str], cwd: Path) -> str:
    # List form, no shell=True: args are never interpreted by a shell.
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",  # never crash on odd bytes in commit text
    )
    if result.returncode != 0:
        raise GitError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout



def commit_message(cwd: Path, sha: str) -> str:
    # %B = raw body: subject plus message, exactly as written
    return run_git(["log", "-1", "--format=%B", sha], cwd).strip()