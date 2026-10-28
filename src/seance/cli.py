from __future__ import annotations

from pathlib import Path

import typer

from seance.config import Settings
from seance.diff import removed_hunks
from seance.evidence import build_bundle
from seance.github import GitHubClient
from seance.gitops import commit_message
from seance.render import render_comment
from seance.score import score_bundle
from seance.trace import merge_base, trace_hunk

app = typer.Typer(add_completion=False, help="Summon the reason a line of code was written.")


def run(cwd: Path, base: str, head: str, settings: Settings, gh: GitHubClient) -> str | None:
    rev = merge_base(cwd, base, head)
    findings = []
    for hunk in removed_hunks(cwd, base, head):
        origin = trace_hunk(cwd, hunk, rev)
        if origin is None:
            continue  # untraceable: stay silent rather than guess
        message = commit_message(cwd, origin.sha)
        bundle = build_bundle(origin, message, gh.context_for(origin.sha, message), settings.repo)
        score = score_bundle(bundle)
        if score.worth_warning:
            findings.append((bundle, score))
    return render_comment(findings)


@app.command()
def main(
    pr: int | None = typer.Option(None, "--pr", help="PR number (needs GITHUB_TOKEN)"),
    base: str | None = typer.Option(None, "--base", help="Base ref or sha"),
    head: str | None = typer.Option(None, "--head", help="Head ref or sha"),
    repo_dir: Path = typer.Option(Path("."), "--repo-dir", help="Path to the git repository"),
) -> None:
    settings = Settings.from_env()
    gh = GitHubClient(settings.repo, settings.token)
    if pr is not None:
        refs = gh.pr_refs(pr)
        if refs is None:
            typer.echo("Could not fetch the PR. Check GITHUB_TOKEN and GITHUB_REPOSITORY.",
                       err=True)
            raise typer.Exit(2)
        base, head = refs
    if not base or not head:
        typer.echo("Give --pr, or both --base and --head.", err=True)
        raise typer.Exit(2)
    comment = run(repo_dir, base, head, settings, gh)
    if comment:
        typer.echo(comment)  # silent run prints nothing and exits 0