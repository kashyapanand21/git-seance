from __future__ import annotations

import re
from dataclasses import dataclass, field

from seance.evidence import Bundle

THRESHOLD = 3  # a proposal; the P10 replay is where this gets tuned

# (signal name, points, pattern) applied to commit and PR text
RULES = [
    ("revert", 4, re.compile(r"\brevert(?:s|ed|ing)?\b", re.I)),
    ("hotfix", 4, re.compile(r"\bhot-?fix(?:es)?\b", re.I)),
    ("workaround", 3, re.compile(r"\bwork-?arounds?\b", re.I)),
    ("fix", 3, re.compile(r"\b(?:fix(?:es|ed)?|bug-?fix)\b", re.I)),
]
# A commit/PR whose title says it is cosmetic never counts as a "fix"
NOISE_RE = re.compile(
    r"\b(?:typos?|whitespace|formatting|reformat(?:ted)?|lint(?:ing)?|prettier|style|spelling|docs?)\b",
    re.I,
)
BUG_RE = re.compile(r"\b(?:bug|defect|regression|crash)\b", re.I)
# A comment in the removed code itself warning not to touch it
KEEP_RE = re.compile(r"do(?: not|n't)\s+(?:remove|delete|change)|must keep|\bhack\b", re.I)


@dataclass
class Signal:
    name: str
    points: int
    evidence_id: str | None  # None when the signal came from the removed code itself


@dataclass
class Score:
    signals: list[Signal] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(s.points for s in self.signals)

    @property
    def worth_warning(self) -> bool:
        return self.total >= THRESHOLD


def score_bundle(bundle: Bundle) -> Score:
    signals: list[Signal] = []
    fired: set[str] = set()  # one signal per name; the first matching item gets the credit

    def fire(name: str, points: int, evidence_id: str | None) -> None:
        if name not in fired:
            fired.add(name)
            signals.append(Signal(name, points, evidence_id))

    for item in bundle.items:
        if item.kind in ("commit", "pr"):
            if NOISE_RE.search(item.label):
                continue
            for name, points, pattern in RULES:
                if pattern.search(item.text):
                    fire(name, points, item.id)
        elif item.kind == "issue":
            if BUG_RE.search(item.label) or any(BUG_RE.search(t) for t in item.tags):
                fire("linked_bug", 3, item.id)

    if KEEP_RE.search("\n".join(bundle.removed)):
        fire("keep_comment", 3, None)
    return Score(signals)