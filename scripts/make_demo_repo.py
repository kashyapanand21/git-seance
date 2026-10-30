"""Build a throwaway demo repo: python scripts/make_demo_repo.py demo-repo"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def commit(cwd: Path, message: str, files: dict[str, str]) -> None:
    for name, text in files.items():
        (cwd / name).write_text(text, encoding="utf-8", newline="\n")
    git(cwd, "add", "-A")
    git(cwd, "commit", "-m", message)


def main(target: Path) -> None:
    target.mkdir(parents=True, exist_ok=False)  # refuse to overwrite an existing folder
    git(target, "init", "-b", "main")
    git(target, "config", "user.name", "Demo")
    git(target, "config", "user.email", "demo@example.com")
    git(target, "config", "core.autocrlf", "false")
    git(target, "config", "commit.gpgsign", "false")

    commit(target, "feat: add charge helper", {
        "charge.py": "def charge(gateway, amount):\n    return gateway.post(amount)\n",
    })
    commit(target, "fix: retry once on 502 to stop duplicate charges (fixes #1)", {
                "charge.py": (
            "def charge(gateway, amount):\n"
            "    resp = gateway.post(amount)\n"
            "    if resp.status == 502:  # gateway timed out\n"
            "        resp = gateway.post(amount)\n"
            "    return resp\n"
        ),
    })
    commit(target, "chore: add logging helper", {
        "log.py": "def log(msg):\n    print(msg)\n\n\n# TODO: use logging module\nunused = 1\n",
    })

    # Branch 1: removes the retry guard (the fence)
    git(target, "switch", "-c", "remove-retry")
    commit(target, "refactor: simplify charge", {
        "charge.py": "def charge(gateway, amount):\n    return gateway.post(amount)\n",
    })

    # Branch 2: removes a harmless line (should stay silent)
    git(target, "switch", "main")
    git(target, "switch", "-c", "remove-unused")
    commit(target, "chore: drop unused variable", {
        "log.py": "def log(msg):\n    print(msg)\n\n\n# TODO: use logging module\n",
    })
    git(target, "switch", "main")
    print(f"Demo repo ready at {target}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))