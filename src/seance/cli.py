from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import httpx
import typer

from seance.comment import upsert_comment
from seance.config import Settings
from seance.diff import removed_hunks
from seance.evidence import Bundle, build_bundle
from seance.github import GitHubClient
from seance.gitops import commit_message
from seance.llm import LLMResult, summarise
from seance.render import render_comment
from seance.score import score_bundle
from seance.trace import merge_base, trace_hunk
from seance.verify import verify

app = typer.Typer(add_completion=False, help="Summon the reason a line of code was written.")


def run(
    cwd: Path,
    base: str,
    head: str,
    settings: Settings,
    gh: GitHubClient,
    summarise_fn: Callable[[Bundle], LLMResult] | None = None,  # None = no model (v0.1 mode)
) -> str | None:
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
            verified = None
            if summarise_fn is not None:
                result = summarise_fn(bundle)
                # Model failed twice -> verified stays None -> raw evidence only
                if result.summary is not None:
                    verified = verify(result.summary, bundle)
            findings.append((bundle, score, verified))
    return render_comment(findings)


@app.command()
def main(
    pr: int | None = typer.Option(None, "--pr", help="PR number (needs GITHUB_TOKEN)"),
    base: str | None = typer.Option(None, "--base", help="Base ref or sha"),
    head: str | None = typer.Option(None, "--head", help="Head ref or sha"),
    repo_dir: Path = typer.Option(Path("."), "--repo-dir", help="Path to the git repository"),
    no_model: bool = typer.Option(False, "--no-model", help="Skip the model; raw evidence only"),
    post: bool = typer.Option(False, "--post", help="Post/update the PR comment (needs --pr)"),
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
    fn = None if no_model else (lambda bundle: summarise(bundle, settings))
    comment = run(repo_dir, base, head, settings, gh, fn)
    if not post:
        if comment:
            typer.echo(comment)  # silent run prints nothing and exits 0
        return
    if pr is None or not settings.token or not settings.repo:
        typer.echo("--post needs --pr, GITHUB_TOKEN and GITHUB_REPOSITORY.", err=True)
        raise typer.Exit(2)
    try:
        typer.echo(f"comment {upsert_comment(settings.repo, settings.token, pr, comment)}")
    except httpx.HTTPError as exc:
        # Advisory bot: a failed post must never fail the PR's checks
        typer.echo(f"warning: could not post comment: {exc}", err=True)