from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel

API = "https://api.github.com"
# Same-repo keyword links only. A bare "#230" may be a PR number, so it is ignored.
LINK_RE = re.compile(r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s*:?\s+#(\d+)", re.IGNORECASE)
MAX_ISSUES = 3  # keeps the evidence bundle small for a local model


class PullRequest(BaseModel):
    number: int
    title: str
    body: str = ""
    url: str


class Issue(BaseModel):
    number: int
    title: str
    body: str = ""
    url: str
    labels: list[str] = []


@dataclass
class Context:
    pr: PullRequest | None = None
    issues: list[Issue] = field(default_factory=list)


def linked_issue_numbers(*texts: str | None) -> list[int]:
    numbers: list[int] = []
    for text in texts:
        for m in LINK_RE.finditer(text or ""):
            n = int(m.group(1))
            if n not in numbers:  # dedupe, keep first-seen order
                numbers.append(n)
    return numbers


class GitHubClient:
    def __init__(
        self,
        repo: str | None,
        token: str | None,
        cache_dir: Path = Path(".seance-cache"),
        transport: httpx.BaseTransport | None = None,  # tests inject a fake transport
    ):
        self.repo = repo
        self.enabled = bool(repo and token)  # False = git-only mode
        self.cache_dir = cache_dir
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._http = httpx.Client(base_url=API, headers=headers, timeout=10, transport=transport)

    def _get(self, path: str) -> Any | None:
        if not self.enabled:
            return None
        cached = self.cache_dir / (hashlib.sha256(path.encode()).hexdigest()[:16] + ".json")
        if cached.is_file():
            try:
                return json.loads(cached.read_text(encoding="utf-8"))
            except ValueError:
                pass  # corrupt cache file: fall through and refetch
        try:
            resp = self._http.get(path)
            data = resp.json() if resp.status_code == 200 else None
        except (httpx.HTTPError, ValueError):
            return None  # offline, rate-limited or bad JSON: degrade, never crash
        if data is not None:
            cached.parent.mkdir(parents=True, exist_ok=True)
            cached.write_text(json.dumps(data), encoding="utf-8")
        return data

    def context_for(self, sha: str, commit_message: str) -> Context:
        ctx = Context()
        pulls = self._get(f"/repos/{self.repo}/commits/{sha}/pulls")
        if isinstance(pulls, list) and pulls:
            # Prefer a merged PR; the endpoint can also return open ones
            raw = next((p for p in pulls if p.get("merged_at")), pulls[0])
            ctx.pr = PullRequest(
                number=raw["number"],
                title=raw.get("title") or "",
                body=raw.get("body") or "",
                url=raw["html_url"],
            )
        pr_text = (ctx.pr.title, ctx.pr.body) if ctx.pr else ()
        for n in linked_issue_numbers(commit_message, *pr_text)[:MAX_ISSUES]:
            raw = self._get(f"/repos/{self.repo}/issues/{n}")
            # The issues endpoint also returns PRs; those carry a "pull_request" key
            if not isinstance(raw, dict) or "pull_request" in raw:
                continue
            ctx.issues.append(
                Issue(
                    number=n,
                    title=raw.get("title") or "",
                    body=raw.get("body") or "",
                    url=raw["html_url"],
                    labels=[lb["name"] for lb in raw.get("labels", [])],
                )
            )
        return ctx

    
    def pr_refs(self, number: int) -> tuple[str, str] | None:
        """Return (base_sha, head_sha) for a PR, or None if it can't be fetched."""
        raw = self._get(f"/repos/{self.repo}/pulls/{number}")
        if not isinstance(raw, dict):
            return None
        return raw["base"]["sha"], raw["head"]["sha"]