from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from seance.diff import Hunk
from seance.gitops import GitError, run_git

SHA_HEADER_RE = re.compile(r"^([0-9a-f]{40}) \d+ \d+")  # porcelain header per line
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
IGNORE_FILE = ".git-blame-ignore-revs"
MIN_KEY_LEN = 8  # shorter lines match too many commits to mean anything


@dataclass
class Origin:
    sha: str
    method: str  # "blame", "log-S", "log-G" or "log-L"; shown in the comment later
    hunk: Hunk


def merge_base(cwd: Path, base: str, head: str) -> str:
    # The diff was taken against the merge-base, so blame must run there too.
    return run_git(["merge-base", base, head], cwd).strip()


def key_line(hunk: Hunk) -> str | None:
    lines = [ln.strip() for ln in hunk.removed if len(ln.strip()) >= MIN_KEY_LEN]
    return max(lines, key=len, default=None)  # longest = most distinctive


def _ere_escape(text: str) -> str:
    # git -G takes a POSIX ERE; escape its special characters
    return re.sub(r"([.^$*+?()\[\]{}|\\])", r"\\\1", text)


def _shas(output: str) -> list[str]:
    # Full-line match only, so diff text from `log -L` is never mistaken for a sha
    return [ln for ln in output.splitlines() if SHA_RE.match(ln)]


def blame_origin(cwd: Path, hunk: Hunk, rev: str) -> str | None:
    args = ["blame", "-w", "--porcelain", "-L", f"{hunk.old_start},{hunk.old_end}"]
    ignore = cwd / IGNORE_FILE
    if ignore.is_file():  # blame errors if the file is missing, so check first
        args += ["--ignore-revs-file", str(ignore)]
    out = run_git([*args, rev, "--", hunk.file], cwd)
    counts = Counter(m.group(1) for ln in out.splitlines() if (m := SHA_HEADER_RE.match(ln)))
    return counts.most_common(1)[0][0] if counts else None


def pickaxe_s(cwd: Path, hunk: Hunk, rev: str) -> str | None:
    key = key_line(hunk)
    if key is None:
        return None
    out = run_git(["log", "--format=%H", f"-S{key}", "--follow", rev, "--", hunk.file], cwd)
    shas = _shas(out)
    return shas[-1] if shas else None  # newest-first, so last = oldest


def pickaxe_g(cwd: Path, hunk: Hunk, rev: str) -> str | None:
    key = key_line(hunk)
    if key is None:
        return None
    out = run_git(
        ["log", "--format=%H", f"-G{_ere_escape(key)}", "--follow", rev, "--", hunk.file], cwd
    )
    shas = _shas(out)
    return shas[-1] if shas else None


def log_l(cwd: Path, hunk: Hunk, rev: str) -> str | None:
    # -L takes no pathspec; the file goes inside the range argument
    spec = f"{hunk.old_start},{hunk.old_end}:{hunk.file}"
    shas = _shas(run_git(["log", "--format=%H", "-L", spec, rev], cwd))
    return shas[-1] if shas else None


def trace_hunk(cwd: Path, hunk: Hunk, rev: str) -> Origin | None:
    """Return the commit that introduced the removed lines, or None if untraceable."""
    # log -L is deliberately not in this chain: it walks back to the file's first commit,
    # which would be a confident wrong origin (see MISTAKES.md, P2).
    steps = [("blame", blame_origin), ("log-S", pickaxe_s), ("log-G", pickaxe_g)]
    for method, finder in steps:
        try:
            sha = finder(cwd, hunk, rev)
        except GitError:
            sha = None  # a failing step just hands over to the next one
        if sha:
            return Origin(sha, method, hunk)
    return None