from __future__ import annotations

import re
from dataclasses import dataclass

from seance.evidence import Bundle
from seance.llm import Claim, Summary

MAX_CLAIMS = 3
MAX_CLAIM_TEXT = 300
MAX_QUOTE = 200

WS_RE = re.compile(r"\s+")
NUM_RE = re.compile(r"\d+")
EVIDENCE_ID_RE = re.compile(r"\bE\d+\b")  # "E1" must not count as the number 1
TICK_RE = re.compile(r"`([^`]+)`")
MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
URL_RE = re.compile(r"https?://\S+|www\.\S+")
HTML_RE = re.compile(r"<[^>]*>")
MENTION_RE = re.compile(r"@(?=\w)")  # removing the @ stops GitHub notifying the user
HASH_RE = re.compile(r"#(?=\d)")  # "#12" would become a cross-reference link on GitHub

@dataclass
class Dropped:
    claim: Claim
    reason: str  # kept for the run log and the replay report


@dataclass
class Verified:
    claims: list[Claim]  # sanitised, safe to render
    dropped: list[Dropped]


def norm(text: str) -> str:
    return WS_RE.sub(" ", text).strip()


def sanitize(text: str, limit: int) -> str:
    text = MD_LINK_RE.sub(r"\1", text)  # keep link text, drop the target
    text = URL_RE.sub("", text)
    text = HTML_RE.sub("", text)
    text = MENTION_RE.sub("", text)
    text = HASH_RE.sub("# ", text)
    return norm(text)[:limit]


def check_claim(claim: Claim, texts: dict[str, str]) -> str | None:
    """Return why the claim fails, or None if it is supported."""
    if not claim.evidence:
        return "no evidence cited"
    for eid in claim.evidence:
        if eid not in texts:
            return f"unknown evidence id {eid}"
    quote = norm(claim.quote)
    if not quote:
        return "empty quote"
    if len(quote) > MAX_QUOTE:
        return "quote too long"
    cited = [texts[eid] for eid in claim.evidence]
    if not any(quote in text for text in cited):
        return "quote not found in cited evidence"
    pool = " ".join(cited)
    pool_numbers = set(NUM_RE.findall(pool))
    claim_text = EVIDENCE_ID_RE.sub("", claim.text)
    for number in NUM_RE.findall(claim_text):
        if number not in pool_numbers:
            return f"number {number} not in cited evidence"
    for term in TICK_RE.findall(claim.text):
        if term not in pool:
            return f"term `{term}` not in cited evidence"
    return None


def verify(summary: Summary, bundle: Bundle) -> Verified:
    texts = {e.id: norm(e.text) for e in bundle.items}
    kept: list[Claim] = []
    dropped: list[Dropped] = []
    for claim in summary.claims:
        reason = check_claim(claim, texts)
        if reason is None:
            clean = Claim(
                text=sanitize(claim.text, MAX_CLAIM_TEXT),
                evidence=claim.evidence,
                quote=sanitize(claim.quote, MAX_QUOTE),
            )
            if not clean.text or not clean.quote:
                reason = "empty after sanitising"
            elif len(kept) >= MAX_CLAIMS:
                reason = "over the claim cap"
            else:
                kept.append(clean)
        if reason is not None:
            dropped.append(Dropped(claim, reason))
    return Verified(kept, dropped)