from __future__ import annotations

from pydantic import BaseModel

from seance.github import Context
from seance.trace import Origin

MAX_TEXT = 4000  # small local models choke on long history


class Evidence(BaseModel):
    id: str  # "E1", "E2"... the model must cite these
    kind: str  # "commit" | "pr" | "issue"
    label: str  # short title shown in the comment
    text: str  # full text; the verifier checks quotes against exactly this
    url: str | None = None
    tags: list[str] = []  # issue labels; kept out of `text` so we never invent quotable text


class Bundle(BaseModel):
    file: str
    start: int
    end: int
    removed: list[str]
    sha: str
    method: str
    items: list[Evidence]


def build_bundle(origin: Origin, message: str, ctx: Context, repo: str | None) -> Bundle:
    items: list[Evidence] = []

    def add(kind: str, label: str, text: str, url: str | None, tags: list[str] | None = None):
        text = text.strip()[:MAX_TEXT]
        if text:  # an empty PR body or commit message adds nothing
            items.append(
                Evidence(
                    id=f"E{len(items) + 1}",
                    kind=kind,
                    label=label,
                    text=text,
                    url=url,
                    tags=tags or [],
                )
            )

    subject = message.strip().splitlines()[0] if message.strip() else ""
    commit_url = f"https://github.com/{repo}/commit/{origin.sha}" if repo else None
    add("commit", subject, message, commit_url)
    if ctx.pr:
        pr = ctx.pr
        add("pr", f"PR #{pr.number}: {pr.title}", f"{pr.title}\n\n{pr.body}", pr.url)
    for issue in ctx.issues:  # outside the `if`: issues exist even when no PR does
        label = f"Issue #{issue.number}: {issue.title}"
        add("issue", label, f"{issue.title}\n\n{issue.body}", issue.url, issue.labels)

    h = origin.hunk
    return Bundle(
        file=h.file, start=h.old_start, end=h.old_end, removed=h.removed,
        sha=origin.sha, method=origin.method, items=items,
    )