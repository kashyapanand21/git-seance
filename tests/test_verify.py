from seance.evidence import Bundle, Evidence
from seance.llm import Claim, Summary
from seance.verify import MAX_CLAIM_TEXT, MAX_CLAIMS, sanitize, verify


def make_bundle():
    items = [
        Evidence(id="E1", kind="commit", label="fix",
                 text="fix: retry once on 502\n\nStops duplicate charges (issue 212)."),
        Evidence(id="E2", kind="issue", label="Issue #212",
                 text="Customers were charged twice\nwhen the gateway timed out."),
    ]
    return Bundle(file="a.py", start=1, end=2, removed=["x"], sha="a" * 40,
                  method="blame", items=items)


def claim(text="The commit message says it retries on 502.", evidence=("E1",),
          quote="retry once on 502"):
    return Claim(text=text, evidence=list(evidence), quote=quote)


def run(*claims):
    return verify(Summary(claims=list(claims)), make_bundle())


def test_grounded_claim_is_kept():
    v = run(claim())
    assert len(v.claims) == 1 and not v.dropped


def test_unknown_evidence_id_is_dropped():
    v = run(claim(evidence=("E9",)))
    assert not v.claims and "E9" in v.dropped[0].reason


def test_no_evidence_cited_is_dropped():
    assert run(claim(evidence=())).dropped[0].reason == "no evidence cited"


def test_invented_quote_is_dropped():
    v = run(claim(quote="always retry three times"))
    assert not v.claims and "quote not found" in v.dropped[0].reason


def test_quote_may_differ_in_whitespace():
    v = run(claim(text="The issue says customers were hit.", evidence=("E2",),
                  quote="charged   twice when the\ngateway timed out"))
    assert len(v.claims) == 1


def test_quote_from_uncited_evidence_is_dropped():
    v = run(claim(evidence=("E1",), quote="charged twice"))  # that text is only in E2
    assert not v.claims


def test_invented_number_is_dropped():
    v = run(claim(text="It retries 3 times."))
    assert not v.claims and "number 3" in v.dropped[0].reason


def test_number_from_evidence_is_fine():
    assert len(run(claim(text="It retries on 502.")).claims) == 1


def test_evidence_ids_are_not_counted_as_numbers():
    assert len(run(claim(text="See E1 for the reason.")).claims) == 1


def test_invented_backtick_term_is_dropped():
    v = run(claim(text="It adds `max_retries`."))
    assert not v.claims and "max_retries" in v.dropped[0].reason


def test_sanitize_strips_links_mentions_and_html():
    dirty = "See [the PR](https://x.io/1) @alice <b>now</b> https://evil.io"
    assert sanitize(dirty, 300) == "See the PR alice now"


def test_kept_claim_is_stored_sanitised():
    v = run(claim(text="Added by @bob in [PR](http://x.io)."))
    assert v.claims[0].text == "Added by bob in PR."


def test_claims_are_capped():
    v = run(*[claim() for _ in range(5)])
    assert len(v.claims) == MAX_CLAIMS and len(v.dropped) == 2


def test_long_claim_text_is_truncated():
    v = run(claim(text="x" * 500))
    assert len(v.claims[0].text) == MAX_CLAIM_TEXT

def test_sanitize_neutralises_issue_references():
    assert sanitize("fixes #12 and PR #3", 300) == "fixes # 12 and PR # 3"