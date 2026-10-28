from seance.diff import removed_hunks
from seance.trace import log_l, merge_base, pickaxe_g, pickaxe_s, trace_hunk

V1 = "def pay(x):\n    return x\n"
GUARDED = "def pay(x):\n    if x is None:\n        return 0\n    return x\n"
REINDENTED = "def pay(x):\n  if x is None:\n    return 0\n  return x\n"  # 2 spaces


def _scenario(repo):
    """initial -> fix (adds guard) -> reindent -> unrelated edit -> feature removes guard."""
    repo.commit("initial", {"pay.py": V1})
    fix = repo.commit("fix: retry guard (#212)", {"pay.py": GUARDED})
    reformat = repo.commit("style: reindent", {"pay.py": REINDENTED})
    repo.commit("add other()", {"pay.py": REINDENTED + "\n\ndef other():\n  return 1\n"})
    repo.git("switch", "-c", "feature")
    repo.commit("drop guard", {"pay.py": "def pay(x):\n  return x\n\n\ndef other():\n  return 1\n"})
    (hunk,) = removed_hunks(repo.path, "main", "feature")
    return fix, reformat, hunk, merge_base(repo.path, "main", "feature")


def test_blame_skips_whitespace_reformat(repo):
    fix, reformat, hunk, rev = _scenario(repo)
    # Control: plain blame is fooled by the reindent, so this test is meaningful
    plain = repo.git("blame", "--porcelain", "-L", "2,3", rev, "--", "pay.py")
    # Porcelain also prints a "previous <sha>" line, so check only who owns line 2
    assert plain.splitlines()[0].startswith(reformat)
    origin = trace_hunk(repo.path, hunk, rev)
    assert (origin.sha, origin.method) == (fix, "blame")


def test_ignore_revs_file_skips_non_whitespace_reformat(repo):
    head, tail = "def pay(x):\n", "    return x\n"
    guard = "    if x is None:\n"
    single = "        log('none')\n        return 'zero'\n"
    double = single.replace("'", '"')  # the "reformat": quote style only
    repo.commit("initial", {"pay.py": head + tail})
    fix = repo.commit("fix: guard", {"pay.py": head + guard + single + tail})
    quotes = repo.commit("style: double quotes", {"pay.py": head + guard + double + tail})
    repo.git("switch", "-c", "feature")
    repo.commit("drop guard", {"pay.py": head + tail})
    (hunk,) = removed_hunks(repo.path, "main", "feature")
    rev = merge_base(repo.path, "main", "feature")

    # 3 removed lines: 1 owned by the fix, 2 by the quotes commit, so quotes wins
    assert trace_hunk(repo.path, hunk, rev).sha == quotes  # known limit: unlisted reformat wins
    (repo.path / ".git-blame-ignore-revs").write_text(quotes + "\n", encoding="utf-8")
    assert trace_hunk(repo.path, hunk, rev).sha == fix


def test_fallbacks_find_the_same_origin(repo):
    fix, _, hunk, rev = _scenario(repo)
    assert pickaxe_s(repo.path, hunk, rev) == fix
    assert pickaxe_g(repo.path, hunk, rev) == fix
    # Documented limit: log -L walks back to the file's first commit, not the introducer
    assert log_l(repo.path, hunk, rev) == repo.git("rev-list", "--max-parents=0", "main")

def test_trace_follows_file_rename(repo):
    repo.commit("initial", {"pay.py": V1})
    fix = repo.commit("fix: guard", {"pay.py": GUARDED})
    repo.commit("rename", {"pay.py": None, "payments.py": GUARDED})
    repo.git("switch", "-c", "feature")
    repo.commit("drop guard", {"payments.py": "def pay(x):\n    return x\n"})
    (hunk,) = removed_hunks(repo.path, "main", "feature")
    assert trace_hunk(repo.path, hunk, merge_base(repo.path, "main", "feature")).sha == fix