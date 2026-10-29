import json

import httpx

from seance.comment import CLEARED, upsert_comment
from seance.render import MARKER


def server(comments):
    """In-memory PR comment list; returns (transport, log)."""
    log = []

    def handler(req: httpx.Request) -> httpx.Response:
        log.append((req.method, req.url.path))
        if req.method == "GET":
            return httpx.Response(200, json=comments)
        if req.method == "POST":
            comments.append({"id": 99, "body": json.loads(req.content)["body"]})
            return httpx.Response(201, json={})
        cid = int(req.url.path.rsplit("/", 1)[1])
        for c in comments:
            if c["id"] == cid:
                c["body"] = json.loads(req.content)["body"]
        return httpx.Response(200, json={})

    return httpx.MockTransport(handler), log


def test_creates_then_updates_one_comment():
    comments = [{"id": 1, "body": "someone else"}]
    t, _ = server(comments)
    assert upsert_comment("o/r", "tok", 7, f"{MARKER}\nv1", t) == "created"
    assert upsert_comment("o/r", "tok", 7, f"{MARKER}\nv2", t) == "updated"
    ours = [c for c in comments if MARKER in c["body"]]
    assert len(ours) == 1 and ours[0]["body"].endswith("v2")


def test_no_findings_and_no_old_comment_is_skipped():
    t, log = server([])
    assert upsert_comment("o/r", "tok", 7, None, t) == "skipped"
    assert all(m == "GET" for m, _ in log)  # never wrote anything


def test_no_findings_clears_a_stale_warning():
    comments = [{"id": 5, "body": f"{MARKER}\nold warning"}]
    t, _ = server(comments)
    assert upsert_comment("o/r", "tok", 7, None, t) == "updated"
    assert comments[0]["body"] == CLEARED