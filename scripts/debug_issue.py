"""Debug the issue lookup: python scripts\\debug_issue.py"""
import os
import tempfile
from pathlib import Path

from seance.github import GitHubClient

repo, token = os.environ.get("GITHUB_REPOSITORY"), os.environ.get("GITHUB_TOKEN")
gh = GitHubClient(repo, token, Path(tempfile.mkdtemp()))  # fresh cache dir: rules out stale cache
print("enabled:", gh.enabled, "| repo:", repo)

resp = gh._http.get(f"/repos/{repo}/issues/1")
print("issue #1 status:", resp.status_code)
print("has pull_request key:", "pull_request" in resp.json())

msg = "fix: retry once on 502 to stop duplicate charges (fixes #1)"
ctx = gh.context_for("e37ff14", msg)  # the sha only matters for the PR lookup
print("issues found:", [(i.number, i.title) for i in ctx.issues])