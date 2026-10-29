# import json  # noqa: E402  (keep with the other imports if you prefer)


from typer.testing import CliRunner  # noqa: E402

from seance.cli import (
    app,  # noqa: E402
    run,
)
from seance.config import Settings
from seance.github import GitHubClient
from seance.llm import Claim, LLMResult, Summary  # noqa: E402

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


def _fixed(quote):
    claim = Claim(text="The commit message says it retries.", evidence=["E1"], quote=quote)
    return lambda bundle: LLMResult(summary=Summary(claims=[claim]))


def _fence_repo(repo):
    repo.commit("initial", {"pay.py": V1})
    repo.commit("fix: retry once on 502 (bug)", {"pay.py": GUARDED})
    repo.git("switch", "-c", "feature")
    repo.commit("drop guard", {"pay.py": V1})


def test_verified_claim_appears_in_comment(repo, tmp_path):
    _fence_repo(repo)
    out = run(repo.path, "main", "feature", SETTINGS, _gh(tmp_path), _fixed("retry once on 502"))
    assert 'Quote: "retry once on 502"' in out and "[E1]" in out


def test_invented_quote_falls_back_to_raw_evidence(repo, tmp_path):
    _fence_repo(repo)
    out = run(repo.path, "main", "feature", SETTINGS, _gh(tmp_path), _fixed("always retry 5 times"))
    assert "Quote:" not in out and "E1 (commit)" in out  # evidence kept, model text dropped


def test_model_failure_falls_back_to_raw_evidence(repo, tmp_path):
    _fence_repo(repo)
    fail = lambda bundle: LLMResult(summary=None, error="boom")  # noqa: E731
    out = run(repo.path, "main", "feature", SETTINGS, _gh(tmp_path), fail)
    assert out is not None and "Quote:" not in out


def test_main_runs_end_to_end_without_model(repo):
    _fence_repo(repo)
    result = CliRunner().invoke(
        app, ["--base", "main", "--head", "feature", "--repo-dir", str(repo.path), "--no-model"]
    )
    assert result.exit_code == 0
    assert "<!-- git-seance -->" in result.output


def test_main_without_refs_exits_2():
    result = CliRunner().invoke(app, [])
    assert result.exit_code == 2