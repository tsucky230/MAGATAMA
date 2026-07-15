"""Tests for LoadCompIndexUseCase."""

import json
import sqlite3
from pathlib import Path

import pytest

from magatama_core.application.usecases.comp_usecase import (
    EntityHistoryUseCase,
    LoadCompIndexUseCase,
    LoadCompSessionsUseCase,
)
from magatama_core.domain.entities.base import EntityType
from magatama_core.domain.entities.relationships import RelationshipType
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


# ---------------------------------------------------------------------------
# LoadCompSessionsUseCase
# ---------------------------------------------------------------------------


def make_session_workspace(tmp_path: Path) -> Path:
    """Workspace with a comP index (one file, one symbol) and session data."""
    workspace = tmp_path / "sessproj"
    comp_dir = workspace / ".comp"
    comp_dir.mkdir(parents=True)

    db_path = comp_dir / "index.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.execute(
        "INSERT INTO files (id, path, hash, language) VALUES (1, 'src/app.py', 'h', 'python')"
    )
    conn.execute(
        "INSERT INTO nodes (id, file_id, name, kind, line, col) VALUES (1, 1, 'main', 'function', 1, 0)"
    )
    conn.commit()
    conn.close()

    memory = {
        "sessions": [
            {
                "id": "s1",
                "timestamp": 1780341799978,
                "calls": [
                    {
                        "query": "refactor main",
                        "outcome": "done",
                        "files": ["src/app.py", "missing/file.py"],
                        "symbols": ["main", "no_such_symbol"],
                        "timestamp": 1780341799978,
                    }
                ],
            }
        ]
    }
    (comp_dir / "session-memory.json").write_text(json.dumps(memory), encoding="utf-8")
    return workspace


def test_sessions_load_and_link(tmp_path: Path) -> None:
    workspace = make_session_workspace(tmp_path)
    kg = NetworkXKnowledgeGraph()
    LoadCompIndexUseCase(kg).execute(workspace)

    result = LoadCompSessionsUseCase(kg).execute(workspace)

    assert result.success
    assert result.alias == "sessproj"
    assert result.sessions_loaded == 1
    # src/app.py (file) + main (symbol) matched; the other two unmatched
    assert result.discussed_links == 2
    assert result.unmatched_files == 1
    assert result.unmatched_symbols == 1

    sessions = [e for e in kg.entities.all() if e.type == EntityType.SESSION]
    assert len(sessions) == 1
    discussed = [r for r in kg.relationships.all() if r.type == RelationshipType.DISCUSSED]
    assert len(discussed) == 2
    assert all(r.source_id == sessions[0].id for r in discussed)


def test_sessions_replace_idempotent(tmp_path: Path) -> None:
    workspace = make_session_workspace(tmp_path)
    kg = NetworkXKnowledgeGraph()
    LoadCompIndexUseCase(kg).execute(workspace)

    usecase = LoadCompSessionsUseCase(kg)
    usecase.execute(workspace)
    result = usecase.execute(workspace)

    assert result.entities_removed == 1
    sessions = [e for e in kg.entities.all() if e.type == EntityType.SESSION]
    assert len(sessions) == 1
    discussed = [r for r in kg.relationships.all() if r.type == RelationshipType.DISCUSSED]
    assert len(discussed) == 2


def test_sessions_without_index_all_unmatched(tmp_path: Path) -> None:
    """Session data loads even when no code entities are in the graph."""
    workspace = make_session_workspace(tmp_path)
    kg = NetworkXKnowledgeGraph()

    result = LoadCompSessionsUseCase(kg).execute(workspace)

    assert result.success
    assert result.sessions_loaded == 1
    assert result.discussed_links == 0
    assert result.unmatched_files == 2
    assert result.unmatched_symbols == 2


def test_sessions_file_suffix_match(tmp_path: Path) -> None:
    """Relative session paths match code entities indexed by longer paths."""
    workspace = make_session_workspace(tmp_path)
    comp_dir = workspace / ".comp"
    memory = {
        "sessions": [
            {
                "id": "s2",
                "timestamp": 1,
                "calls": [{"query": "q", "outcome": "o", "files": ["app.py"], "symbols": []}],
            }
        ]
    }
    (comp_dir / "session-memory.json").write_text(json.dumps(memory), encoding="utf-8")

    kg = NetworkXKnowledgeGraph()
    LoadCompIndexUseCase(kg).execute(workspace)
    result = LoadCompSessionsUseCase(kg).execute(workspace)

    # "app.py" matches "src/app.py" via suffix
    assert result.discussed_links == 1
    assert result.unmatched_files == 0


def test_sessions_unc_absolute_path_links(tmp_path: Path) -> None:
    """Daemon auto-records use //?/E:/... paths; they must still link."""
    workspace = make_session_workspace(tmp_path)
    comp_dir = workspace / ".comp"
    memory = {
        "sessions": [
            {
                "id": "s3",
                "timestamp": 1,
                "calls": [
                    {
                        "query": "q",
                        "outcome": "o",
                        "files": ["//?/E:/dev/sessproj/src/app.py"],
                        "symbols": [],
                    }
                ],
            }
        ]
    }
    (comp_dir / "session-memory.json").write_text(json.dumps(memory), encoding="utf-8")

    kg = NetworkXKnowledgeGraph()
    LoadCompIndexUseCase(kg).execute(workspace)
    result = LoadCompSessionsUseCase(kg).execute(workspace)

    # "//?/e:/dev/sessproj/src/app.py" endswith "/src/app.py" (graph path)
    assert result.discussed_links == 1
    assert result.unmatched_files == 0


def test_sessions_not_found(tmp_path: Path) -> None:
    kg = NetworkXKnowledgeGraph()
    result = LoadCompSessionsUseCase(kg).execute(tmp_path / "nowhere")
    assert not result.success
    assert result.errors


def test_sessions_invalid_mode(tmp_path: Path) -> None:
    kg = NetworkXKnowledgeGraph()
    result = LoadCompSessionsUseCase(kg).execute(tmp_path, mode="bogus")
    assert not result.success
    assert "Invalid mode" in result.errors[0]


# ---------------------------------------------------------------------------
# EntityHistoryUseCase
# ---------------------------------------------------------------------------


def make_history_graph(tmp_path: Path) -> NetworkXKnowledgeGraph:
    workspace = make_session_workspace(tmp_path)
    kg = NetworkXKnowledgeGraph()
    LoadCompIndexUseCase(kg).execute(workspace)
    LoadCompSessionsUseCase(kg).execute(workspace)
    return kg


def test_entity_history_by_symbol(tmp_path: Path) -> None:
    kg = make_history_graph(tmp_path)
    result = EntityHistoryUseCase(kg).execute("main")

    assert result.success
    assert any(e["name"] == "main" for e in result.matched_entities)
    assert len(result.history) == 1
    assert result.history[0]["request"] == "refactor main"
    assert result.history[0]["outcome"] == "done"
    assert result.history[0]["when"]  # timestamp prefix parsed
    mentions = result.history[0]["mentions"]
    assert any(m["kind"] == "symbol" for m in mentions)


def test_entity_history_by_file_suffix(tmp_path: Path) -> None:
    """A bare file name finds the MODULE indexed under a longer path."""
    kg = make_history_graph(tmp_path)
    result = EntityHistoryUseCase(kg).execute("app.py", analyze=False)

    assert result.success
    assert any(e["type"] == "module" for e in result.matched_entities)
    assert len(result.history) == 1
    assert result.impact is None  # analyze=False


def test_entity_history_impact_excludes_sessions(tmp_path: Path) -> None:
    """DISCUSSED links must not count as dependents in impact analysis."""
    from magatama_core.application.usecases.framework_usecase import DependencyImpactUseCase

    workspace = make_session_workspace(tmp_path)
    kg = NetworkXKnowledgeGraph()
    LoadCompIndexUseCase(kg).execute(workspace)
    baseline = DependencyImpactUseCase(kg).analyze_impact("main").total_affected

    LoadCompSessionsUseCase(kg).execute(workspace)
    result = EntityHistoryUseCase(kg).execute("main")

    assert result.impact is not None
    # Loading sessions adds a DISCUSSED link to "main"; impact must not grow.
    assert result.impact["total_affected"] == baseline


def test_entity_history_not_found(tmp_path: Path) -> None:
    kg = make_history_graph(tmp_path)
    result = EntityHistoryUseCase(kg).execute("no_such_thing")
    assert not result.success
    assert result.errors


def test_entity_history_limit(tmp_path: Path) -> None:
    workspace = make_session_workspace(tmp_path)
    comp_dir = workspace / ".comp"
    history = comp_dir / "history"
    history.mkdir()
    # Well after the session-memory.json record, one minute apart so the
    # second-resolution "when" strings are strictly ordered.
    lines = [
        json.dumps(
            {
                "timestamp": 1780341899978 + i * 60_000,
                "query": f"req {i}",
                "outcome": "o",
                "files": ["src/app.py"],
            }
        )
        for i in range(5)
    ]
    (history / "log-2026-07.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")

    kg = NetworkXKnowledgeGraph()
    LoadCompIndexUseCase(kg).execute(workspace)
    LoadCompSessionsUseCase(kg).execute(workspace)
    result = EntityHistoryUseCase(kg).execute("src/app.py", limit=3, analyze=False)

    assert result.success
    assert len(result.history) == 3
    # Newest first
    assert result.history[0]["request"] == "req 4"
