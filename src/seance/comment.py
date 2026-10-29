from __future__ import annotations

import httpx

from seance.github import API
from seance.render import MARKER

CLEARED = f"{MARKER}\n_git-seance: no risky removals flagged in the latest run._"
MAX_PAGES = 10


def _find_existing(http: httpx.Client, repo: str, pr: int) -> int | None:
    for page in range(1, MAX_PAGES + 1):
        resp = http.get(f"/repos/{repo}/issues/{pr}/comments",
                        params={"per_page": 100, "page": page})
        resp.raise_for_status()
        items = resp.json()
        for c in items:
            if MARKER in (c.get("body") or ""):
                return c["id"]
        if len(items) < 100:
            return None
    return None


def upsert_comment(
    repo: str, token: str, pr: int, body: str | None,
    transport: httpx.BaseTransport | None = None,
) -> str:
    """Create or update the single bot comment. Returns 'created', 'updated' or 'skipped'."""
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    with httpx.Client(base_url=API, headers=headers, timeout=15, transport=transport) as http:
        existing = _find_existing(http, repo, pr)
        if body is None:
            if existing is None:
                return "skipped"  # nothing to say and nothing to clear
            body = CLEARED
        if existing is not None:
            http.patch(f"/repos/{repo}/issues/comments/{existing}",
                       json={"body": body}).raise_for_status()
            return "updated"
        http.post(f"/repos/{repo}/issues/{pr}/comments", json={"body": body}).raise_for_status()
        return "created"