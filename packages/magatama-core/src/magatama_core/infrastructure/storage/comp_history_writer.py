"""comP session history writer.

Appends records to .comp/history/log-YYYY-MM.jsonl in the same shape the
comP daemon (0.9.2) writes for its session_log tool:

    {"timestamp", "query", "outcome", "files", "symbols", "tokens", "stale"}

so comP's session_recall surfaces them alongside daemon-written records in
later sessions. (Older daemons wrote "request" instead of "query"; readers
in this codebase accept both.)
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path


def append_history_record(
    comp_dir: str | Path,
    query: str,
    outcome: str,
    files: list[str] | None = None,
    symbols: list[str] | None = None,
) -> Path:
    """Append one record to the current month's history JSONL.

    Creates .comp/history/ if needed. Returns the path written to.
    """
    history_dir = Path(comp_dir) / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    now_ms = int(time.time() * 1000)
    month = datetime.fromtimestamp(now_ms / 1000, tz=UTC).strftime("%Y-%m")
    log_file = history_dir / f"log-{month}.jsonl"

    record: dict[str, object] = {
        "timestamp": now_ms,
        "query": query,
        "outcome": outcome,
        "files": files or [],
        "symbols": symbols or [],
        "tokens": 0,
        "stale": False,
    }

    with log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return log_file
