from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    model: str
    ollama_url: str
    token: str | None
    repo: str | None  # "owner/name"

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            model=os.environ.get("SEANCE_MODEL", "gemma4:e4b"),
            ollama_url=os.environ.get("SEANCE_OLLAMA_URL", "http://localhost:11434"),
            token=os.environ.get("GITHUB_TOKEN") or None,
            repo=os.environ.get("GITHUB_REPOSITORY") or None,  # set by Actions
        )