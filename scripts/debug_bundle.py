"""Trace the real pipeline on PR #3: python scripts\\debug_bundle.py"""
from pathlib import Path

from seance.cli import run
from seance.config import Settings
from seance.diff import removed_hunks
from seance.evidence import build_bundle
from seance.github import GitHubClient, linked_issue_numbers
from seance.gitops import commit_message
from seance.render import render_comment
from seance.score import score_bundle
from seance.trace import merge_base, trace_hunk

cwd = Path("..") / "demo-repo"
s = Settings.from_env()
gh = GitHubClient(s.repo, s.token)  # same default cache as the CLI
base, head = gh.pr_refs(3)
rev = merge_base(cwd, base, head)
hunk = removed_hunks(cwd, base, head)[0]
origin = trace_hunk(cwd, hunk, rev)
msg = commit_message(cwd, origin.sha)
print("origin:", origin.sha, origin.method)
print("message repr:", repr(msg))
print("linked issues:", linked_issue_numbers(msg))
ctx = gh.context_for(origin.sha, msg)
print("pr:", ctx.pr)
print("issues:", [(i.number, i.title) for i in ctx.issues])

bundle = build_bundle(origin, msg, ctx, s.repo)
print("bundle items:", [(e.id, e.kind) for e in bundle.items])
print("--- build_bundle + render, by hand ---")
print(render_comment([(bundle, score_bundle(bundle), None)]))
print("--- cli.run(), the real path ---")
print(run(cwd, base, head, s, GitHubClient(s.repo, s.token)))