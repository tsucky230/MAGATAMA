"""comP session history reader.

Reads comP session records from a workspace's .comp directory and converts
them into SESSION entities. Two sources are supported (both optional):

- ``.comp/session-memory.json``: ``{"sessions": [{"id", "timestamp",
  "calls": [{"query", "outcome", "symbols": [...], "files": [...], ...}]}]}``
- ``.comp/history/*.jsonl``: one JSON object per line, at minimum
  ``{"timestamp", "request", "outcome"}``; ``files``/``symbols`` keys are
  honored when present.

Each record becomes one SESSION entity; the ``files``/``symbols`` lists are
returned alongside so the caller can link them to code entities already in
the knowledge graph (DISCUSSED relationships).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from magatama_core.domain.entities.base import Entity, EntityType
from magatama_core.domain.value_objects.ids import EntityId
from magatama_core.domain.value_objects.location import Location

_NAME_MAX_LEN = 120
_DOCSTRING_MAX_LEN = 500


class CompSessionsNotFoundError(FileNotFoundError):
    """Raised when neither session-memory.json nor history/*.jsonl exists."""


@dataclass
class SessionRecord:
    """One session record plus the file/symbol names it mentions."""

    entity: Entity
    files: list[str] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)
    timestamp_ms: int | None = None
    outcome: str = ""


@dataclass
class CompSessionData:
    """Result of reading comP session history."""

    alias: str
    comp_dir: str
    records: list[SessionRecord] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    skipped_lines: int = 0


def resolve_comp_dir(path: str | Path) -> Path:
    """Resolve a user-supplied path to the .comp directory.

    Accepts the workspace root or the .comp directory itself. Raises
    CompSessionsNotFoundError if the directory holds no session data.
    """
    p = Path(path)
    comp_dir = p if p.name == ".comp" else p / ".comp"
    memory = comp_dir / "session-memory.json"
    history = comp_dir / "history"
    has_history = history.is_dir() and any(history.glob("*.jsonl"))
    if memory.is_file() or has_history:
        return comp_dir
    raise CompSessionsNotFoundError(
        f"No comP session data found at {path!r} (looked for {memory} and {history}/*.jsonl)"
    )


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _timestamp_prefix(timestamp_ms: object) -> str:
    # bool is an int subclass but never a valid epoch; strings and other
    # types from hand-edited/third-party JSONL must not crash the reader.
    if (
        isinstance(timestamp_ms, bool)
        or not isinstance(timestamp_ms, (int, float))
        or not timestamp_ms
    ):
        return ""
    try:
        dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)
        return f"[{dt.strftime('%Y-%m-%dT%H:%M:%SZ')}] "
    except (OverflowError, OSError, ValueError):
        return ""


def _str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [v for v in value if isinstance(v, str) and v]


class CompSessionReader:
    """Reads comP session history into SESSION entities."""

    def read(self, path: str | Path) -> CompSessionData:
        comp_dir = resolve_comp_dir(path)
        alias = comp_dir.parent.name.lower()
        data = CompSessionData(alias=alias, comp_dir=str(comp_dir))

        memory_file = comp_dir / "session-memory.json"
        if memory_file.is_file():
            self._read_session_memory(memory_file, alias, data)

        history_dir = comp_dir / "history"
        if history_dir.is_dir():
            for jsonl in sorted(history_dir.glob("*.jsonl")):
                self._read_history_jsonl(jsonl, alias, data)

        return data

    def _read_session_memory(self, memory_file: Path, alias: str, data: CompSessionData) -> None:
        try:
            payload = json.loads(memory_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data.skipped_lines += 1
            return
        sessions = payload.get("sessions") if isinstance(payload, dict) else None
        if not isinstance(sessions, list):
            data.skipped_lines += 1
            return

        data.sources.append(memory_file.name)
        for session in sessions:
            if not isinstance(session, dict):
                data.skipped_lines += 1
                continue
            session_id = str(session.get("id", "unknown"))
            calls = session.get("calls")
            if not isinstance(calls, list):
                continue
            for i, call in enumerate(calls):
                if not isinstance(call, dict):
                    data.skipped_lines += 1
                    continue
                query = call.get("query") or "(no request)"
                outcome = call.get("outcome") or ""
                timestamp = call.get("timestamp") or session.get("timestamp")
                entity = Entity(
                    id=EntityId(value=f"comp-session:{alias}:{session_id}:{i}"),
                    name=_truncate(str(query), _NAME_MAX_LEN),
                    type=EntityType.SESSION,
                    location=Location(file=memory_file.name, line=1, column=0),
                    docstring=_truncate(
                        _timestamp_prefix(timestamp) + str(outcome), _DOCSTRING_MAX_LEN
                    )
                    or None,
                    scope="public",
                )
                data.records.append(
                    SessionRecord(
                        entity=entity,
                        files=_str_list(call.get("files")),
                        symbols=_str_list(call.get("symbols")),
                        timestamp_ms=timestamp if isinstance(timestamp, int) else None,
                        outcome=str(outcome),
                    )
                )

    def _read_history_jsonl(self, jsonl: Path, alias: str, data: CompSessionData) -> None:
        try:
            lines = jsonl.read_text(encoding="utf-8").splitlines()
        except OSError:
            data.skipped_lines += 1
            return

        data.sources.append(f"history/{jsonl.name}")
        for lineno, line in enumerate(lines, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                data.skipped_lines += 1
                continue
            if not isinstance(record, dict):
                data.skipped_lines += 1
                continue
            request = record.get("request") or record.get("query") or "(no request)"
            outcome = record.get("outcome") or ""
            entity = Entity(
                id=EntityId(value=f"comp-session:{alias}:hist:{jsonl.stem}:{lineno}"),
                name=_truncate(str(request), _NAME_MAX_LEN),
                type=EntityType.SESSION,
                location=Location(file=f"history/{jsonl.name}", line=lineno, column=0),
                docstring=_truncate(
                    _timestamp_prefix(record.get("timestamp")) + str(outcome),
                    _DOCSTRING_MAX_LEN,
                )
                or None,
                scope="public",
            )
            ts = record.get("timestamp")
            data.records.append(
                SessionRecord(
                    entity=entity,
                    files=_str_list(record.get("files")),
                    symbols=_str_list(record.get("symbols")),
                    timestamp_ms=ts if isinstance(ts, int) else None,
                    outcome=str(outcome),
                )
            )
