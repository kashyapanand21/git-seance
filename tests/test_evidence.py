from seance.diff import Hunk
from seance.evidence import build_bundle
from seance.github import Context, Issue, PullRequest
from seance.trace import Origin

HUNK = Hunk("pay.py", 2, 2, removed=["    if x is None:", "        return 0"])
SHA = "a" * 40


def test_ids_urls_and_order():
    ctx = Context(
        pr=PullRequest(number=230, title="Retry on 502", body="Fixes #212", url="https://x/pull/230"),
        issues=[Issue(number=212, title="Duplicate charges", body="Twice.", url="https://x/i/212",
                      labels=["bug"])],
    )
    b = build_bundle(Origin(SHA, "blame", HUNK), "fix: retry guard\n\nbody", ctx, "o/r")
    assert [e.id for e in b.items] == ["E1", "E2", "E3"]
    assert [e.kind for e in b.items] == ["commit", "pr", "issue"]
    assert b.items[0].url == f"https://github.com/o/r/commit/{SHA}"
    assert b.items[0].label == "fix: retry guard"
    assert b.items[2].tags == ["bug"]
    assert (b.start, b.end) == (2, 3)


def test_no_repo_no_context_gives_commit_only():
    b = build_bundle(Origin(SHA, "blame", HUNK), "fix: retry guard", Context(), None)
    assert len(b.items) == 1 and b.items[0].url is None