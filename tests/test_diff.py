from seance.diff import removed_hunks

ORIGINAL = "def pay(x):\n    if x is None:\n        return 0\n    retry(x)\n    return x\n"


def _branch(repo):
    repo.commit("base", {"pay.py": ORIGINAL})
    repo.git("switch", "-c", "feature")


def test_removed_lines_become_a_hunk(repo):
    _branch(repo)
    repo.commit("drop guard", {"pay.py": "def pay(x):\n    retry(x)\n    return x\n"})
    (h,) = removed_hunks(repo.path, "main", "feature")
    assert h.file == "pay.py"
    assert (h.old_start, h.old_count, h.old_end) == (2, 2, 3)
    assert h.removed == ["    if x is None:", "        return 0"]
    assert h.added == []


def test_rewritten_line_has_removed_and_added(repo):
    _branch(repo)
    repo.commit("rewrite", {"pay.py": ORIGINAL.replace("retry(x)", "retry(x, 3)")})
    (h,) = removed_hunks(repo.path, "main", "feature")
    assert h.removed == ["    retry(x)"]
    assert h.added == ["    retry(x, 3)"]


def test_whitespace_only_change_gives_no_hunks(repo):
    _branch(repo)
    repo.commit("reindent", {"pay.py": ORIGINAL.replace("    ", "  ")})
    assert removed_hunks(repo.path, "main", "feature") == []


def test_pure_addition_gives_no_hunks(repo):
    _branch(repo)
    repo.commit("add", {"pay.py": ORIGINAL + "# new\n"})
    assert removed_hunks(repo.path, "main", "feature") == []


def test_blank_line_removal_is_ignored(repo):
    repo.commit("base", {"a.py": "x = 1\n\ny = 2\n"})
    repo.git("switch", "-c", "feature")
    repo.commit("tidy", {"a.py": "x = 1\ny = 2\n"})
    assert removed_hunks(repo.path, "main", "feature") == []


def test_lockfile_changes_are_skipped(repo):
    repo.commit("base", {"package-lock.json": '{"a": 1}\n'})
    repo.git("switch", "-c", "feature")
    repo.commit("bump", {"package-lock.json": '{"a": 2}\n'})
    assert removed_hunks(repo.path, "main", "feature") == []


def test_deleted_file_reports_old_path(repo):
    repo.commit("base", {"old.py": "a = 1\nb = 2\nc = 3\n"})
    repo.git("switch", "-c", "feature")
    repo.commit("remove file", {"old.py": None})
    (h,) = removed_hunks(repo.path, "main", "feature")
    assert (h.file, h.old_start, h.old_count) == ("old.py", 1, 3)