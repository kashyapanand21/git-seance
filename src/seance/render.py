from __future__ import annotations

from seance.evidence import Bundle
from seance.score import Score
from seance.verify import Verified, sanitize

MARKER = "<!-- git-seance -->"  # P8 finds and updates the comment by this line


def _label(text: str) -> str:
    # Labels come from commit subjects and PR titles: untrusted. Strip links, @mentions, HTML,
    # and brackets so a label cannot break out of its own link.
    return sanitize(text, 120).replace("[", "(").replace("]", ")")


def render_finding(bundle: Bundle, score: Score, verified: Verified | None = None) -> str:
    lines = [
        f"`{bundle.file}`, lines {bundle.start}-{bundle.end} removed",
        f"- The history shows these lines were added in `{bundle.sha[:7]}`"
        f" (found by {bundle.method}).",
    ]
    for e in bundle.items:
        label = _label(e.label)
        link = f"[{label}]({e.url})" if e.url else label
        lines.append(f"  - {e.id} ({e.kind}): {link}")
    if verified and verified.claims:
        lines.append("- What that history says (each point checked against the quoted text):")
        for c in verified.claims:
            lines.append(f'  - {c.text} Quote: "{c.quote}" [{", ".join(c.evidence)}]')
    names = ", ".join(s.name for s in score.signals)
    lines.append(f"- Signals: {names}. This may reintroduce an earlier problem; please check.")
    return "\n".join(lines)


def render_comment(findings: list[tuple[Bundle, Score, Verified | None]]) -> str | None:
    if not findings:
        return None  # silence is a valid answer
    n = len(findings)
    head = f"**Chesterton's Fence check: {n} removal{'s' if n > 1 else ''} may matter**"
    body = "\n\n".join(render_finding(b, s, v) for b, s, v in findings)
    foot = "_Advisory only. Generated from git history, not a verdict._"
    return f"{MARKER}\n{head}\n\n{body}\n\n{foot}"