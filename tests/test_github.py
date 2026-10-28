import httpx

from seance.github import GitHubClient, linked_issue_numbers

PR = {
    "number": 230,
    "title": "Retry on 502 from gateway",
    "body": "Fixes #212",
    "html_url": "https://github.com/o/r/pull/230",
    "merged_at": "2024-01-01T00:00:00Z",
}
ISSUE = {
    "number": 212,
    "title": "Duplicate charges on timeout",
    "body": "Customers were charged twice.",
    "html_url": "https://github.com/o/r/issues/212",
    "labels": [{"name": "bug"}],
}


def make_client(tmp_path, token="tok"):
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path == "/repos/o/r/commits/abc/pulls":
            return httpx.Response(200, json=[PR])
        if request.url.path == "/repos/o/r/issues/212":
            return httpx.Response(200, json=ISSUE)
        return httpx.Response(404)

    client = GitHubClient("o/r", token, tmp_path / "cache", transport=httpx.MockTransport(handler))
    return client, calls


def test_linked_issue_parsing():
    assert linked_issue_numbers("Fixes #212", "closes #3 and resolved: #4") == [212, 3, 4]
    assert linked_issue_numbers("Retry on 502 (#230)") == []  # bare #n is a PR, not a link
    assert linked_issue_numbers("fix #5", "Fix #5") == [5]  # deduped


def test_pr_and_issue_are_parsed(tmp_path):
    client, _ = make_client(tmp_path)
    ctx = client.context_for("abc", "Retry on 502 (#230)")
    assert ctx.pr.number == 230 and ctx.pr.url.endswith("/pull/230")
    (issue,) = ctx.issues  # "Fixes #212" came from the PR body
    assert (issue.number, issue.labels) == (212, ["bug"])


def test_no_token_is_git_only_mode(tmp_path):
    client, calls = make_client(tmp_path, token=None)
    ctx = client.context_for("abc", "fixes #212")
    assert ctx.pr is None and ctx.issues == [] and calls == []  # no error, no requests


def test_http_failures_degrade_quietly(tmp_path):
    def server_error(request):
        return httpx.Response(500)

    def offline(request):
        raise httpx.ConnectError("offline")

    for handler in (server_error, offline):
        client = GitHubClient("o/r", "tok", tmp_path / "c", transport=httpx.MockTransport(handler))
        ctx = client.context_for("abc", "fixes #212")
        assert ctx.pr is None and ctx.issues == []


def test_second_lookup_uses_disk_cache(tmp_path):
    client, calls = make_client(tmp_path)
    client.context_for("abc", "")
    first = len(calls)
    client.context_for("abc", "")
    assert len(calls) == first  # nothing refetched