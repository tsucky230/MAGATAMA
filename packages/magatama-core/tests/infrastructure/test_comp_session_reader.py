"""Tests for CompSessionReader."""

import json
from pathlib import Path

import pytest

from magatama_core.domain.entities.base import EntityType
from magatama_core.infrastructure.storage.comp_session_reader import (
    CompSessionReader,
    CompSessionsNotFoundError,
    resolve_comp_dir,
)


def make_workspace(
    tmp_path: Path,
    memory: dict | None = None,
    history_lines: list[str] | None = None,
) -> Path:
    """Create a workspace with a .comp directory holding session data."""
    workspace = tmp_path / "proj"
    comp_dir = workspace / ".comp"
    comp_dir.mkdir(parents=True)
    if memory is not None:
        (comp_dir / "session-memory.json").write_text(
            json.dumps(memory, ensure_ascii=False), encoding="utf-8"
        )
    if history_lines is not None:
        history = comp_dir / "history"
        history.mkdir()
        (history / "log-2026-06.jsonl").write_text("\n".join(history_lines), encoding="utf-8")
    return workspace


SAMPLE_MEMORY = {
    "sessions": [
        {
            "id": "1780341799695",
            "timestamp": 1780341799978,
            "calls": [
                {
                    "query": "fix compilation errors",
                    "outcome": "fixed them",
                    "symbols": ["registerCommands"],
                    "files": ["src/ui/commands.ts", "README.md"],
                    "tokens": 100,
                    "timestamp": 1780341799978,
                }
            ],
        }
    ]
}

SAMPLE_HISTORY = ['{"timestamp":1782521356807,"request":"add session_log","outcome":"done"}']


class TestResolveCompDir:
    def test_workspace_root(self, tmp_path: Path) -> None:
        ws = make_workspace(tmp_path, memory=SAMPLE_MEMORY)
        assert resolve_comp_dir(ws) == ws / ".comp"

    def test_comp_dir_direct(self, tmp_path: Path) -> None:
        ws = make_workspace(tmp_path, memory=SAMPLE_MEMORY)
        assert resolve_comp_dir(ws / ".comp") == ws / ".comp"

    def test_history_only(self, tmp_path: Path) -> None:
        ws = make_workspace(tmp_path, history_lines=SAMPLE_HISTORY)
        assert resolve_comp_dir(ws) == ws / ".comp"

    def test_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(CompSessionsNotFoundError):
            resolve_comp_dir(tmp_path / "nowhere")

    def test_empty_comp_dir(self, tmp_path: Path) -> None:
        (tmp_path / "proj" / ".comp").mkdir(parents=True)
        with pytest.raises(CompSessionsNotFoundError):
            resolve_comp_dir(tmp_path / "proj")


class TestCompSessionReader:
    def test_reads_session_memory(self, tmp_path: Path) -> None:
        ws = make_workspace(tmp_path, memory=SAMPLE_MEMORY)
        data = CompSessionReader().read(ws)

        assert data.alias == "proj"
        assert data.sources == ["session-memory.json"]
        assert len(data.records) == 1
        record = data.records[0]
        assert record.entity.type == EntityType.SESSION
        assert record.entity.name == "fix compilation errors"
        assert record.entity.id.value == "comp-session:proj:1780341799695:0"
        assert "fixed them" in (record.entity.docstring or "")
        assert record.files == ["src/ui/commands.ts", "README.md"]
        assert record.symbols == ["registerCommands"]

    def test_reads_history_jsonl(self, tmp_path: Path) -> None:
        ws = make_workspace(tmp_path, history_lines=SAMPLE_HISTORY)
        data = CompSessionReader().read(ws)

        assert data.sources == ["history/log-2026-06.jsonl"]
        assert len(data.records) == 1
        record = data.records[0]
        assert record.entity.name == "add session_log"
        assert record.entity.id.value == "comp-session:proj:hist:log-2026-06:1"
        assert record.entity.location.line == 1
        assert record.files == []
        assert record.symbols == []

    def test_reads_both_sources(self, tmp_path: Path) -> None:
        ws = make_workspace(tmp_path, memory=SAMPLE_MEMORY, history_lines=SAMPLE_HISTORY)
        data = CompSessionReader().read(ws)
        assert len(data.records) == 2
        assert set(data.sources) == {"session-memory.json", "history/log-2026-06.jsonl"}

    def test_timestamp_in_docstring(self, tmp_path: Path) -> None:
        ws = make_workspace(tmp_path, history_lines=SAMPLE_HISTORY)
        data = CompSessionReader().read(ws)
        # 1782521356807 ms -> 2026-06-27 (UTC)
        assert (data.records[0].entity.docstring or "").startswith("[2026-06-27T")

    def test_skips_malformed_jsonl_lines(self, tmp_path: Path) -> None:
        lines = ["not json", "42", SAMPLE_HISTORY[0], ""]
        ws = make_workspace(tmp_path, history_lines=lines)
        data = CompSessionReader().read(ws)
        assert len(data.records) == 1
        assert data.skipped_lines == 2

    def test_corrupt_session_memory_is_skipped(self, tmp_path: Path) -> None:
        ws = make_workspace(tmp_path, history_lines=SAMPLE_HISTORY)
        (ws / ".comp" / "session-memory.json").write_text("{broken", encoding="utf-8")
        data = CompSessionReader().read(ws)
        # history record still read; corrupt memory counted as skipped
        assert len(data.records) == 1
        assert data.skipped_lines == 1

    def test_missing_request_gets_placeholder(self, tmp_path: Path) -> None:
        ws = make_workspace(tmp_path, history_lines=['{"timestamp": 1, "outcome": "x"}'])
        data = CompSessionReader().read(ws)
        assert data.records[0].entity.name == "(no request)"

    def test_long_request_truncated(self, tmp_path: Path) -> None:
        long_request = "x" * 500
        ws = make_workspace(
            tmp_path, history_lines=[json.dumps({"request": long_request, "outcome": ""})]
        )
        data = CompSessionReader().read(ws)
        assert len(data.records[0].entity.name) <= 120

    def test_non_string_files_and_symbols_filtered(self, tmp_path: Path) -> None:
        memory = {
            "sessions": [
                {
                    "id": "s1",
                    "timestamp": 1,
                    "calls": [
                        {
                            "query": "q",
                            "outcome": "o",
                            "files": ["ok.py", 42, None, ""],
                            "symbols": "not-a-list",
                        }
                    ],
                }
            ]
        }
        ws = make_workspace(tmp_path, memory=memory)
        data = CompSessionReader().read(ws)
        assert data.records[0].files == ["ok.py"]
        assert data.records[0].symbols == []
