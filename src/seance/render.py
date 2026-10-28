from __future__ import annotations

from seance.evidence import Bundle
from seance.score import Score

MARKER = "<!-- git-seance -->"  # P8 finds and updates the comment by this line


def render_finding(bundle: Bundle, score: Score) -> str:
    lines = [
        f"`{bundle.file}`, lines {bundle.start}-{bundle.end} removed",
        f"- The history shows these lines were added in `{bundle.sha[:7]}`"
        f" (found by {bundle.method}).",    ]
    for e in bundle.items:
        link = f"[{e.label}]({e.url})" if e.url else e.label
        lines.append(f"  - {e.kind}: {link}")
    names = ", ".join(s.name for s in score.signals)
    lines.append(f"- Signals: {names}. This may reintroduce an earlier problem; please check.")
    return "\n".join(lines)


def render_comment(findings: list[tuple[Bundle, Score]]) -> str | None:
    if not findings:
        return None  # silence is a valid answer
    n = len(findings)
    head = f"**Chesterton's Fence check: {n} removal{'s' if n > 1 else ''} may matter**"
    body = "\n\n".join(render_finding(b, s) for b, s in findings)
    foot = "_Advisory only. Generated from git history, not a verdict._"
    return f"{MARKER}\n{head}\n\n{body}\n\n{foot}"