from seance.cli import run
from seance.config import Settings
from seance.github import GitHubClient

SETTINGS = Settings(model="m", ollama_url="u", token=None, repo=None)
V1 = "def pay(x):\n    return x\n"
GUARDED = "def pay(x):\n    if x is None:\n        return 0\n    return x\n"


def _gh(tmp_path):
    return GitHubClient(None, None, tmp_path / "cache")  # git-only mode


def test_bug_fix_deletion_prints_a_comment(repo, tmp_path):
    repo.commit("initial", {"pay.py": V1})
    fix = repo.commit("fix: guard against None (retry bug)", {"pay.py": GUARDED})
    repo.git("switch", "-c", "feature")
    repo.commit("drop guard", {"pay.py": V1})
    out = run(repo.path, "main", "feature", SETTINGS, _gh(tmp_path))
    assert out is not None and out.startswith("<!-- git-seance -->")
    assert fix[:7] in out and "pay.py" in out and "fix" in out


def test_harmless_deletion_is_silent(repo, tmp_path):
    repo.commit("initial", {"pay.py": V1})
    repo.commit("add helper", {"pay.py": GUARDED})  # not a fix: no signal
    repo.git("switch", "-c", "feature")
    repo.commit("drop guard", {"pay.py": V1})
    assert run(repo.path, "main", "feature", SETTINGS, _gh(tmp_path)) is None