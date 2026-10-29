from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
from pydantic import BaseModel

from seance.config import Settings
from seance.evidence import Bundle

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "summarise.v1.txt"
TIMEOUT = 300  # seconds; the first call has to load the model
PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")


class Claim(BaseModel):
    text: str
    evidence: list[str]  # ids like "E1"; the verifier checks them
    quote: str  # must appear verbatim in the cited evidence


class Summary(BaseModel):
    claims: list[Claim]


@dataclass
class LLMResult:
    summary: Summary | None  # None = model failed twice; caller falls back to raw evidence
    prompt_tokens: int = 0
    output_tokens: int = 0
    seconds: float = 0.0
    error: str | None = None


def build_prompt(bundle: Bundle) -> str:
    items = [
        {"id": e.id, "kind": e.kind, "label": e.label, "text": e.text} for e in bundle.items
    ]
    values = {
        "SCHEMA": json.dumps(Summary.model_json_schema()),  # also in the prompt, per Ollama docs
        "FILE": bundle.file,
        "START": str(bundle.start),
        "END": str(bundle.end),
        "REMOVED": "\n".join(bundle.removed),
        "EVIDENCE": json.dumps(items, indent=2, ensure_ascii=False),
    }
    template = PROMPT_PATH.read_text(encoding="utf-8")
    # One pass: substituted text is never rescanned, so evidence can't inject placeholders
    return PLACEHOLDER.sub(lambda m: values.get(m.group(1), m.group(0)), template)


def summarise(
    bundle: Bundle, settings: Settings, transport: httpx.BaseTransport | None = None
) -> LLMResult:
    options: dict[str, int | float] = {"temperature": 0}
    if settings.num_gpu is not None:
        options["num_gpu"] = settings.num_gpu
    body = {
        "model": settings.model,
        "stream": False,
        "think": False,
        "messages": [{"role": "user", "content": build_prompt(bundle)}],
        "format": Summary.model_json_schema(),  # constrains the output to our schema
        "options": options,
    }
    result = LLMResult(summary=None)
    start = time.monotonic()
    with httpx.Client(base_url=settings.ollama_url, timeout=TIMEOUT, transport=transport) as http:
        for _ in range(2):  # one try plus one retry
            try:
                resp = http.post("/api/chat", json=body)
                resp.raise_for_status()
                data = resp.json()
                result.prompt_tokens += data.get("prompt_eval_count", 0)
                result.output_tokens += data.get("eval_count", 0)
                # Never trust the schema alone: validate in code too
                result.summary = Summary.model_validate_json(data["message"]["content"])
                result.error = None
                break
            except (httpx.HTTPError, ValueError, KeyError) as exc:
                # ValueError covers bad JSON and pydantic validation errors
                result.error = f"{type(exc).__name__}: {exc}"
    result.seconds = time.monotonic() - start
    return result