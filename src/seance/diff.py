from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from seance.gitops import run_git

# "@@ -old_start[,old_count] +new_start[,new_count] @@"; a missing count means 1
HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

SKIP_NAMES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "uv.lock",
    "Pipfile.lock", "Cargo.lock", "composer.lock", "go.sum",
}
SKIP_SUFFIXES = (".min.js", ".min.css", ".map", ".snap", "_pb2.py")


@dataclass
class Hunk:
    file: str  # path in the BASE commit, because blame runs on base
    old_start: int
    old_count: int
    removed: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)

    @property
    def old_end(self) -> int:
        return self.old_start + self.old_count - 1


def is_generated(path: str) -> bool:
    name = PurePosixPath(path).name
    return name in SKIP_NAMES or name.endswith(SKIP_SUFFIXES) or ".generated." in name


def _old_path(raw: str) -> str | None:
    raw = raw.split("\t")[0]  # git may append a tab after paths with spaces
    if raw == "/dev/null":  # file is new, so nothing was removed from it
        return None
    return raw[2:] if raw.startswith("a/") else raw


def parse_diff(text: str) -> list[Hunk]:
    hunks: list[Hunk] = []
    in_header = False
    old_path: str | None = None
    current: Hunk | None = None

    for line in text.splitlines():
        if line.startswith("diff --git "):
            in_header, old_path, current = True, None, None
        elif line.startswith("@@"):  # content lines never start with "@@"
            in_header = False
            m = HUNK_RE.match(line)
            current = None
            if m and old_path:
                count = int(m.group(2)) if m.group(2) is not None else 1
                current = Hunk(old_path, int(m.group(1)), count)
                hunks.append(current)
        elif in_header:
            if line.startswith("--- "):
                old_path = _old_path(line[4:])
        elif current is not None:
            if line.startswith("-"):
                current.removed.append(line[1:])
            elif line.startswith("+"):
                current.added.append(line[1:])
            # "\ No newline at end of file" is ignored

    # Keep only real removals: drops pure additions, blank-only removals, generated files
    return [
        h for h in hunks
        if any(line.strip() for line in h.removed) and not is_generated(h.file)
    ]


def removed_hunks(cwd: Path, base: str, head: str) -> list[Hunk]:
    out = run_git(
        [
            "-c", "core.quotepath=off",  # keep non-ASCII paths readable
            "diff", "--no-color", "--no-ext-diff",
            "--unified=0",  # no context lines, only the changed lines
            "-w",           # ignore whitespace changes
            f"{base}...{head}",
        ],
        cwd,
    )
    return parse_diff(out)