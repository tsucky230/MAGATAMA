"""Tests for CompIndexReader."""

import sqlite3
from pathlib import Path

import pytest

from yata_core.domain.entities.base import EntityType
from yata_core.domain.entities.relationships import RelationshipType
from yata_core.infrastructure.storage.comp_index_reader import (
    CompIndexNotFoundError,
    CompIndexReader,
    resolve_db_path,
)

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
    """Create <tmp>/myproject/.comp/index.db and return workspace root."""
    workspace = tmp_path / "myproject"
    comp_dir = workspace / ".comp"
    comp_dir.mkdir(parents=True)
    db_path = comp_dir / "index.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.executemany(
        "INSERT INTO files (id, path, hash, language) VALUES (?, ?, ?, ?)",
        [
            (1, "src/main.py", "abc123", "python"),
            (2, "src/util.py", "def456", "python"),
        ],
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
        [
            (1, 3, "function_call"),
            (1, 2, "type_reference"),
            (999, 1, "function_call"),  # orphan edge — should be skipped
        ],
    )
    conn.execute("INSERT INTO metadata (key, value) VALUES ('version', '2')")
    conn.commit()
    conn.close()
    return workspace


# ─── resolve_db_path ────────────────────────────────────────────────────────

def test_resolve_db_path_workspace(comp_db: Path) -> None:
    """resolve_db_path accepts workspace root."""
    result = resolve_db_path(comp_db)
    assert result == comp_db / ".comp" / "index.db"


def test_resolve_db_path_comp_dir(comp_db: Path) -> None:
    """resolve_db_path accepts .comp directory."""
    result = resolve_db_path(comp_db / ".comp")
    assert result == comp_db / ".comp" / "index.db"


def test_resolve_db_path_direct(comp_db: Path) -> None:
    """resolve_db_path accepts direct .db file path."""
    direct = comp_db / ".comp" / "index.db"
    assert resolve_db_path(direct) == direct


def test_resolve_db_path_not_found(tmp_path: Path) -> None:
    """resolve_db_path raises CompIndexNotFoundError for missing path."""
    with pytest.raises(CompIndexNotFoundError):
        resolve_db_path(tmp_path / "nonexistent")


# ─── CompIndexReader.read() ──────────────────────────────────────────────────

def test_read_entity_count(comp_db: Path) -> None:
    """read() produces 6 entities: 2 files + 4 nodes."""
    data = CompIndexReader().read(comp_db)
    assert len(data.entities) == 6
    assert data.files_count == 2
    assert data.nodes_count == 4


def test_read_kind_mapping(comp_db: Path) -> None:
    """nodes.kind values map to correct EntityType."""
    data = CompIndexReader().read(comp_db)
    by_id = {e.id.value: e for e in data.entities}
    assert by_id["comp:myproject:n1"].type == EntityType.FUNCTION
    assert by_id["comp:myproject:n2"].type == EntityType.CLASS
    assert by_id["comp:myproject:n3"].type == EntityType.METHOD
    assert by_id["comp:myproject:n4"].type == EntityType.VARIABLE  # constant -> VARIABLE


def test_read_unknown_kind_fallback(tmp_path: Path) -> None:
    """Unknown kind falls back to VARIABLE without raising."""
    workspace = tmp_path / "proj"
    comp_dir = workspace / ".comp"
    comp_dir.mkdir(parents=True)
    db_path = comp_dir / "index.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.execute("INSERT INTO files (id, path, hash, language) VALUES (1, 'f.py', 'h', 'python')")
    conn.execute(
        "INSERT INTO nodes (id, file_id, name, kind, line, col) VALUES (1, 1, 'x', 'weird', 1, 0)"
    )
    conn.commit()
    conn.close()
    data = CompIndexReader().read(workspace)
    node = next(e for e in data.entities if e.id.value == "comp:proj:n1")
    assert node.type == EntityType.VARIABLE


def test_read_entity_id_format(comp_db: Path) -> None:
    """Entity IDs follow comp:{alias}:n{id} / f{id} pattern."""
    data = CompIndexReader().read(comp_db)
    ids = {e.id.value for e in data.entities}
    assert "comp:myproject:n1" in ids
    assert "comp:myproject:f1" in ids
    assert "comp:myproject:f2" in ids


def test_read_location(comp_db: Path) -> None:
    """node1 location is correctly mapped."""
    data = CompIndexReader().read(comp_db)
    by_id = {e.id.value: e for e in data.entities}
    loc = by_id["comp:myproject:n1"].location
    assert loc.file == "src/main.py"
    assert loc.line == 10
    assert loc.column == 0


def test_read_line_zero_clamped(tmp_path: Path) -> None:
    """line=0 in DB is clamped to 1 to satisfy Location validation."""
    workspace = tmp_path / "proj"
    comp_dir = workspace / ".comp"
    comp_dir.mkdir(parents=True)
    db_path = comp_dir / "index.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.execute("INSERT INTO files (id, path, hash, language) VALUES (1, 'f.py', 'h', 'python')")
    conn.execute(
        "INSERT INTO nodes (id, file_id, name, kind, line, col) VALUES (1, 1, 'x', 'function', 0, 0)"
    )
    conn.commit()
    conn.close()
    data = CompIndexReader().read(workspace)
    node = next(e for e in data.entities if e.id.value == "comp:proj:n1")
    assert node.location.line == 1


def test_read_is_exported_scope(comp_db: Path) -> None:
    """is_exported maps to scope public/private."""
    data = CompIndexReader().read(comp_db)
    by_id = {e.id.value: e for e in data.entities}
    assert by_id["comp:myproject:n1"].scope == "public"   # is_exported=1
    assert by_id["comp:myproject:n3"].scope == "private"  # is_exported=0


def test_read_edge_kind_mapping(comp_db: Path) -> None:
    """Edge kinds map to correct RelationshipType."""
    data = CompIndexReader().read(comp_db)
    rel_map = {
        (r.source_id.value, r.target_id.value): r.type
        for r in data.relationships
        if r.metadata.get("origin") == "comp"
    }
    assert rel_map[("comp:myproject:n1", "comp:myproject:n3")] == RelationshipType.CALLS
    assert rel_map[("comp:myproject:n1", "comp:myproject:n2")] == RelationshipType.REFERENCES


def test_read_unknown_edge_kind_fallback(tmp_path: Path) -> None:
    """Unknown edge kind falls back to DEPENDS_ON."""
    workspace = tmp_path / "proj"
    comp_dir = workspace / ".comp"
    comp_dir.mkdir(parents=True)
    db_path = comp_dir / "index.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.execute("INSERT INTO files (id, path, hash, language) VALUES (1, 'f.py', 'h', 'python')")
    conn.executemany(
        "INSERT INTO nodes (id, file_id, name, kind, line, col) VALUES (?, 1, ?, 'function', 1, 0)",
        [(1, "a"), (2, "b")],
    )
    conn.execute("INSERT INTO edges (from_id, to_id, kind) VALUES (1, 2, 'mystery')")
    conn.commit()
    conn.close()
    data = CompIndexReader().read(workspace)
    edge_rels = [
        r for r in data.relationships
        if r.metadata.get("origin") == "comp" and r.type != RelationshipType.CONTAINS
    ]
    assert len(edge_rels) == 1
    assert edge_rels[0].type == RelationshipType.DEPENDS_ON


def test_read_skipped_orphan_edge(comp_db: Path) -> None:
    """Orphan edge (from_id=999 not in nodes) is skipped and counted."""
    data = CompIndexReader().read(comp_db)
    assert data.skipped_edges == 1


def test_read_file_contains_relationships(comp_db: Path) -> None:
    """Files produce CONTAINS relationships to their nodes."""
    data = CompIndexReader().read(comp_db)
    contains = {
        (r.source_id.value, r.target_id.value)
        for r in data.relationships
        if r.type == RelationshipType.CONTAINS and r.metadata.get("origin") == "comp"
    }
    assert ("comp:myproject:f2", "comp:myproject:n2") in contains
    assert ("comp:myproject:f2", "comp:myproject:n3") in contains
    assert ("comp:myproject:f2", "comp:myproject:n4") in contains


def test_read_parent_scope_contains(comp_db: Path) -> None:
    """Helper CONTAINS run is created via scope resolution (origin=comp-scope)."""
    data = CompIndexReader().read(comp_db)
    scope_contains = [
        r for r in data.relationships
        if r.type == RelationshipType.CONTAINS
        and r.metadata.get("origin") == "comp-scope"
    ]
    assert len(scope_contains) == 1
    assert scope_contains[0].source_id.value == "comp:myproject:n2"
    assert scope_contains[0].target_id.value == "comp:myproject:n3"


def test_read_metadata(comp_db: Path) -> None:
    """metadata table is read into CompIndexData.metadata."""
    data = CompIndexReader().read(comp_db)
    assert data.metadata == {"version": "2"}


def test_read_readonly(comp_db: Path) -> None:
    """read() does not mutate the DB (connection closed after read)."""
    db_path = comp_db / ".comp" / "index.db"
    before = db_path.read_bytes()
    CompIndexReader().read(comp_db)
    after = db_path.read_bytes()
    assert before == after
