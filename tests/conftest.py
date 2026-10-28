from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


class Repo:
    def __init__(self, path: Path):
        self.path = path

    def git(self, *args: str) -> str:
        res = subprocess.run(
            ["git", *args], cwd=self.path, capture_output=True,
            text=True, encoding="utf-8", check=True,
        )
        return res.stdout.strip()

    def commit(self, message: str, files: dict[str, str | None]) -> str:
        """Write files (None deletes), commit everything, return the new sha."""
        for name, text in files.items():
            p = self.path / name
            if text is None:
                p.unlink()
            else:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(text, encoding="utf-8", newline="\n")  # force LF
        self.git("add", "-A")
        self.git("commit", "-m", message)
        return self.git("rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path: Path) -> Repo:
    r = Repo(tmp_path)
    r.git("init", "-b", "main")
    r.git("config", "user.name", "Test")
    r.git("config", "user.email", "test@example.com")
    r.git("config", "core.autocrlf", "false")  # no CRLF surprises on Windows
    r.git("config", "commit.gpgsign", "false")
    return r