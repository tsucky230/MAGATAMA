"""Tests for LoadCompIndexUseCase."""

import sqlite3
from pathlib import Path

import pytest

from magatama_core.application.usecases.comp_usecase import LoadCompIndexUseCase
from magatama_core.infrastructure.storage.networkx_graph import NetworkXKnowledgeGraph

SCHEMA = """
CREATE TABLE files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    hash TEXT NOT NULL,
    language TEXT NOT NULL,
    last_indexed INTEGER NOT NULL DEFAULT 0,
    char_count INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    line INTEGER NOT NULL,
    col INTEGER NOT NULL,
    scope TEXT,
    is_exported INTEGER DEFAULT 0,
    signature TEXT
);
CREATE TABLE edges (
    from_id INTEGER NOT NULL,
    to_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    PRIMARY KEY (from_id, to_id, kind)
);
CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT);
"""


@pytest.fixture
def comp_db(tmp_path: Path) -> Path:
    """Create workspace with 2 files + 4 nodes."""
    workspace = tmp_path / "myproject"
    comp_dir = workspace / ".comp"
    comp_dir.mkdir(parents=True)
    db_path = comp_dir / "index.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.executemany(
        "INSERT INTO files (id, path, hash, language) VALUES (?, ?, ?, ?)",
        [(1, "src/main.py", "abc", "python"), (2, "src/util.py", "def", "python")],
    )
    conn.executemany(
        "INSERT INTO nodes (id, file_id, name, kind, line, col, scope,"
        " is_exported, signature) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (1, 1, "main", "function", 10, 0, None, 1, "def main() -> None"),
            (2, 2, "Helper", "class", 5, 0, None, 1, None),
            (3, 2, "run", "method", 8, 4, "Helper", 0, "def run(self)"),
            (4, 2, "MAGIC", "constant", 1, 0, None, 1, None),
        ],
    )
    conn.executemany(
        "INSERT INTO edges (from_id, to_id, kind) VALUES (?, ?, ?)",
        [(1, 3, "function_call"), (1, 2, "type_reference")],
    )
    conn.commit()
    conn.close()
    return workspace


def make_usecase() -> tuple[LoadCompIndexUseCase, NetworkXKnowledgeGraph]:
    graph = NetworkXKnowledgeGraph()
    return LoadCompIndexUseCase(knowledge_graph=graph), graph


# ─── happy path ─────────────────────────────────────────────────────────────


def test_execute_success(comp_db: Path) -> None:
    uc, _ = make_usecase()
    result = uc.execute(comp_db)
    assert result.success is True
    assert result.entities_loaded == 6


def test_execute_entities_in_graph(comp_db: Path) -> None:
    uc, graph = make_usecase()
    uc.execute(comp_db)
    assert graph.entities.count() == 6


def test_execute_replace_idempotent(comp_db: Path) -> None:
    """Two replace-mode loads leave exactly 6 entities (no duplicates)."""
    uc, graph = make_usecase()
    uc.execute(comp_db, mode="replace")
    result = uc.execute(comp_db, mode="replace")
    assert result.success is True
    assert graph.entities.count() == 6
    assert result.entities_removed == 6


def test_execute_merge_no_duplicate_entities(comp_db: Path) -> None:
    """Merge mode upserts entities by ID — entity count stays at 6."""
    uc, graph = make_usecase()
    uc.execute(comp_db, mode="replace")
    result = uc.execute(comp_db, mode="merge")
    assert result.success is True
    assert graph.entities.count() == 6


# ─── error paths ─────────────────────────────────────────────────────────────


def test_execute_path_not_found(tmp_path: Path) -> None:
    uc, _ = make_usecase()
    result = uc.execute(tmp_path / "no_such_dir")
    assert result.success is False
    assert len(result.errors) > 0


def test_execute_corrupt_db(tmp_path: Path) -> None:
    """A text file masquerading as .db causes a graceful failure."""
    workspace = tmp_path / "proj"
    comp_dir = workspace / ".comp"
    comp_dir.mkdir(parents=True)
    fake_db = comp_dir / "index.db"
    fake_db.write_text("this is not a sqlite database")
    uc, _ = make_usecase()
    result = uc.execute(workspace)
    assert result.success is False
    assert len(result.errors) > 0


def test_execute_invalid_mode(comp_db: Path) -> None:
    uc, _ = make_usecase()
    result = uc.execute(comp_db, mode="invalid")
    assert result.success is False


# ─── graph traversal ─────────────────────────────────────────────────────────


def test_execute_get_neighbors(comp_db: Path) -> None:
    """After loading, Helper's neighbors include run (via scope CONTAINS)."""
    uc, graph = make_usecase()
    uc.execute(comp_db)
    helper_id = next(e.id for e in graph.entities.all() if e.id.value == "comp:myproject:n2")
    neighbors = graph.get_neighbors(helper_id, depth=1)
    neighbor_names = {n.name for n in neighbors}
    assert "run" in neighbor_names
