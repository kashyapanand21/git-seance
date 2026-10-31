from __future__ import annotations

import json
import time
from pathlib import Path

LOG = Path("runs") / "log.jsonl"  # runs/ is git-ignored


def log_run(record: dict, path: Path = LOG) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), **record}) + "\n")