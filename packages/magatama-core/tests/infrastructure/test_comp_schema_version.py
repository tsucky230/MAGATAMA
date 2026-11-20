"""comP の index.db の形式の版(metadata.schema_version)を確かめ、ずれていれば警告を返す。

comP 0.12.3 から、comP は metadata に schema_version を書く。MAGATAMA は読み込みを止めず、
LoadCompIndexResult.warnings に理由を入れる。どちらを更新すればよいかがユーザーに分かることが目的。
"""

import sqlite3
from pathlib import Path

import pytest

from magatama_core.application.usecases.comp_usecase import LoadCompIndexUseCase
from magatama_core.infrastructure.storage.comp_schema import (
    SUPPORTED_COMP_SCHEMA_VERSIONS,
    check_comp_schema_version,
)
from magatama_core.infrastructure.storage.networkx_graph import NetworkXKnowledgeGraph

TABLES = """
CREATE TABLE files (id INTEGER PRIMARY KEY, path TEXT NOT NULL UNIQUE, hash TEXT NOT NULL,
                    language TEXT NOT NULL, last_indexed INTEGER NOT NULL DEFAULT 0);
CREATE TABLE nodes (id INTEGER PRIMARY KEY, file_id INTEGER NOT NULL, name TEXT NOT NULL,
                    kind TEXT NOT NULL, line INTEGER NOT NULL, col INTEGER NOT NULL, scope TEXT,
                    is_exported INTEGER DEFAULT 0, signature TEXT);
CREATE TABLE edges (from_id INTEGER NOT NULL, to_id INTEGER NOT NULL, kind TEXT NOT NULL);
"""


def test_supported_versions_contains_current_comp_format() -> None:
    assert frozenset({"1"}) == SUPPORTED_COMP_SCHEMA_VERSIONS


def test_supported_version_has_no_warning() -> None:
    assert check_comp_schema_version({"schema_version": "1"}) == []


@pytest.mark.parametrize(
    "metadata",
    [
        {},  # metadata 表がない、または古い comP(版を書かない)
        {"version": "2"},  # 移行の番号だけがある古い comP
        {"schema_version": None},  # 値が NULL
    ],
)
def test_missing_version_warns_to_update_comp(metadata: dict) -> None:
    warnings = check_comp_schema_version(metadata)
    assert len(warnings) == 1
    assert "comP" in warnings[0]
    assert "0.12.3" in warnings[0]


@pytest.mark.parametrize("found", ["2", "0", "abc", "", " 1", "1.0"])
def test_unsupported_version_warns_to_update_magatama(found: str) -> None:
    warnings = check_comp_schema_version({"schema_version": found})
    assert len(warnings) == 1
    assert "MAGATAMA" in warnings[0]
    assert repr(found) in warnings[0]


def _make_db(tmp_path: Path, metadata_sql: str | None) -> Path:
    workspace = tmp_path / "proj"
    (workspace / ".comp").mkdir(parents=True)
    conn = sqlite3.connect(workspace / ".comp" / "index.db")
    conn.executescript(TABLES)
    if metadata_sql is not None:
        conn.executescript(metadata_sql)
    conn.execute("INSERT INTO files (id, path, hash, language) VALUES (1, 'a.py', 'h', 'python')")
    conn.commit()
    conn.close()
    return workspace


def _load(workspace: Path):
    return LoadCompIndexUseCase(knowledge_graph=NetworkXKnowledgeGraph()).execute(workspace)


def test_load_without_metadata_table_succeeds_with_warning(tmp_path: Path) -> None:
    result = _load(_make_db(tmp_path, None))
    assert result.success is True
    assert result.entities_loaded >= 1
    assert len(result.warnings) == 1
    assert "comP" in result.warnings[0]


def test_load_with_current_version_has_no_warning(tmp_path: Path) -> None:
    sql = (
        "CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT);"
        "INSERT INTO metadata VALUES ('schema_version', '1');"
    )
    result = _load(_make_db(tmp_path, sql))
    assert result.success is True
    assert result.warnings == []


def test_load_with_newer_version_still_loads_and_warns(tmp_path: Path) -> None:
    sql = (
        "CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT);"
        "INSERT INTO metadata VALUES ('schema_version', '2');"
    )
    result = _load(_make_db(tmp_path, sql))
    assert result.success is True
    assert result.entities_loaded >= 1
    assert len(result.warnings) == 1
    assert "MAGATAMA" in result.warnings[0]


def test_failed_load_has_no_schema_warning(tmp_path: Path) -> None:
    result = _load(tmp_path / "missing")
    assert result.success is False
    assert result.warnings == []
