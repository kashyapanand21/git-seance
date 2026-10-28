from seance.evidence import Bundle, Evidence
from seance.score import score_bundle


def ev(i, kind, label, tags=None):
    return Evidence(id=f"E{i}", kind=kind, label=label, text=label, tags=tags or [])


def make(*items, removed=("x = 1",)):
    return Bundle(file="a.py", start=1, end=1, removed=list(removed), sha="a" * 40,
                  method="blame", items=list(items))


def test_bug_fix_commit_warns():
    s = score_bundle(make(ev(1, "commit", "fix: retry on 502")))
    assert s.worth_warning and (s.signals[0].name, s.signals[0].evidence_id) == ("fix", "E1")


def test_typo_fix_stays_silent():
    assert not score_bundle(make(ev(1, "commit", "fix: typo in docstring"))).worth_warning


def test_formatting_commit_stays_silent():
    s = score_bundle(make(ev(1, "commit", "style: reformat with prettier")))
    assert s.total == 0


def test_revert_warns():
    assert score_bundle(make(ev(1, "commit", 'Revert "add retry"'))).worth_warning


def test_linked_bug_issue_alone_warns():
    items = [ev(1, "commit", "update retry logic"), ev(2, "issue", "Duplicate charges", ["bug"])]
    s = score_bundle(make(*items))
    assert [x.name for x in s.signals] == ["linked_bug"] and s.worth_warning


def test_keep_comment_in_removed_code_warns():
    s = score_bundle(make(ev(1, "commit", "add helper"), removed=["# do not remove: gateway"]))
    assert s.worth_warning and s.signals[0].evidence_id is None


def test_plain_feature_commit_is_silent():
    assert score_bundle(make(ev(1, "commit", "add retry helper"))).total == 0