"""Tests for PatrolUseCase."""

import json
import sqlite3
from pathlib import Path

from magatama_core.application.usecases.patrol_usecase import (
    PatrolUseCase,
    _symbol_name,
)
from magatama_core.infrastructure.storage.comp_history_writer import append_history_record
from magatama_core.infrastructure.storage.comp_index_reader import read_comp_snapshot

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


def make_workspace(tmp_path: Path) -> Path:
    """Workspace with a comP index: two files, three symbols, one edge."""
    workspace = tmp_path / "proj"
    comp_dir = workspace / ".comp"
    comp_dir.mkdir(parents=True)
    conn = sqlite3.connect(comp_dir / "index.db")
    conn.executescript(SCHEMA)
    conn.execute("INSERT INTO files (id, path, hash, language) VALUES (1, 'a.py', 'h1', 'python')")
    conn.execute("INSERT INTO files (id, path, hash, language) VALUES (2, 'b.py', 'h2', 'python')")
    conn.execute(
        "INSERT INTO nodes (id, file_id, name, kind, line, col, signature)"
        " VALUES (1, 1, 'main', 'function', 1, 0, 'def main()')"
    )
    conn.execute(
        "INSERT INTO nodes (id, file_id, name, kind, line, col, signature)"
        " VALUES (2, 1, 'helper', 'function', 5, 0, 'def helper(x)')"
    )
    conn.execute(
        "INSERT INTO nodes (id, file_id, name, kind, line, col, signature)"
        " VALUES (3, 2, 'Service', 'class', 1, 0, 'class Service')"
    )
    conn.execute("INSERT INTO edges (from_id, to_id, kind) VALUES (1, 2, 'calls')")
    conn.commit()
    conn.close()
    return workspace


def mutate_index(workspace: Path) -> None:
    """Change helper's signature, remove Service, add fresh symbol."""
    conn = sqlite3.connect(workspace / ".comp" / "index.db")
    conn.execute("UPDATE files SET hash = 'h1-new' WHERE id = 1")
    conn.execute("UPDATE nodes SET signature = 'def helper(x, y)' WHERE id = 2")
    conn.execute("DELETE FROM nodes WHERE id = 3")
    conn.execute("DELETE FROM files WHERE id = 2")
    conn.execute(
        "INSERT INTO nodes (id, file_id, name, kind, line, col, signature)"
        " VALUES (4, 1, 'newcomer', 'function', 9, 0, 'def newcomer()')"
    )
    conn.commit()
    conn.close()


def test_symbol_name_helper() -> None:
    assert _symbol_name("a.py::main::function") == "main"
    assert _symbol_name("weird-key") == "weird-key"


def test_read_comp_snapshot(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    snapshot = read_comp_snapshot(workspace)
    assert snapshot.files == {"a.py": "h1", "b.py": "h2"}
    assert snapshot.symbols["a.py::main::function"] == "def main()"
    assert len(snapshot.symbols) == 3


def test_first_pass_is_baseline(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    report = PatrolUseCase().execute(workspace)
    assert report.success
    assert report.baseline
    assert not report.changed
    assert (workspace / ".magatama" / "patrol-state.json").is_file()
    # Baseline writes no history
    assert not (workspace / ".comp" / "history").exists()


def test_no_changes_second_pass(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    usecase = PatrolUseCase()
    usecase.execute(workspace)
    report = usecase.execute(workspace)
    assert report.success
    assert not report.baseline
    assert not report.changed
    assert not (workspace / ".comp" / "history").exists()


def test_detects_changes_and_analyzes(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    usecase = PatrolUseCase()
    usecase.execute(workspace)
    mutate_index(workspace)

    report = usecase.execute(workspace)

    assert report.success and report.changed
    assert report.files_changed == ["a.py"]
    assert report.files_removed == ["b.py"]
    assert report.symbols_changed == ["a.py::helper::function"]
    assert report.symbols_added == ["a.py::newcomer::function"]
    assert report.symbols_removed == ["b.py::Service::class"]

    analyzed = {a.name: a for a in report.analyses}
    assert set(analyzed) == {"helper", "newcomer"}
    # helper is called by main -> at least one dependent
    assert analyzed["helper"].total_affected >= 1
    assert analyzed["helper"].change == "changed"
    assert analyzed["newcomer"].change == "added"


def test_history_written_on_change(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    usecase = PatrolUseCase()
    usecase.execute(workspace)
    mutate_index(workspace)

    report = usecase.execute(workspace)

    assert report.history_file
    log_file = Path(report.history_file)
    assert log_file.is_file()
    record = json.loads(log_file.read_text(encoding="utf-8").splitlines()[-1])
    assert record["query"].startswith("magatama patrol")
    assert "helper" in record["outcome"]
    assert "a.py" in record["files"]
    # Same shape the comP daemon writes
    assert set(record) == {"timestamp", "query", "outcome", "files", "symbols", "tokens", "stale"}


def test_no_log_flag(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    usecase = PatrolUseCase()
    usecase.execute(workspace)
    mutate_index(workspace)

    report = usecase.execute(workspace, log_history=False)

    assert report.changed
    assert report.history_file == ""
    assert not (workspace / ".comp" / "history").exists()


def test_state_updated_after_change(tmp_path: Path) -> None:
    """After a change is reported once, the next pass sees no changes."""
    workspace = make_workspace(tmp_path)
    usecase = PatrolUseCase()
    usecase.execute(workspace)
    mutate_index(workspace)
    usecase.execute(workspace)

    report = usecase.execute(workspace)
    assert not report.changed


def test_corrupt_state_treated_as_baseline(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    state_file = workspace / ".magatama" / "patrol-state.json"
    state_file.parent.mkdir(parents=True)
    state_file.write_text("{broken", encoding="utf-8")

    report = PatrolUseCase().execute(workspace)
    assert report.success
    assert report.baseline


def test_missing_index(tmp_path: Path) -> None:
    report = PatrolUseCase().execute(tmp_path / "nowhere")
    assert not report.success
    assert report.errors


def test_max_analyzed_cap(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    usecase = PatrolUseCase(max_analyzed=1)
    usecase.execute(workspace)
    mutate_index(workspace)

    report = usecase.execute(workspace)
    assert len(report.analyses) == 1
    # changed symbols take priority over added ones
    assert report.analyses[0].name == "helper"


def register_constraint(workspace: Path, **overrides: object) -> None:
    constraint = {
        "id": "no-touch-a",
        "file": "a.py",
        "entity": "",
        "rule": "修正禁止",
        "reason": "顧客納品済み",
        "severity": "CRITICAL",
    }
    constraint.update(overrides)
    (workspace / ".comp" / "constraints.json").write_text(
        json.dumps({"constraints": [constraint]}, ensure_ascii=False), encoding="utf-8"
    )


def test_constraint_hit_on_changed_file(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    register_constraint(workspace)
    usecase = PatrolUseCase()
    usecase.execute(workspace)
    mutate_index(workspace)

    report = usecase.execute(workspace)

    assert len(report.constraint_hits) == 1
    hit = report.constraint_hits[0]
    assert hit.constraint_id == "no-touch-a"
    assert hit.severity == "CRITICAL"
    assert "a.py" in hit.matched
    # Hits lead the summary and switch the history query
    summary = PatrolUseCase.format_summary(report)
    assert summary.startswith("[CRITICAL]")
    record = json.loads(Path(report.history_file).read_text(encoding="utf-8").splitlines()[-1])
    assert record["query"] == "magatama patrol: 制約対象の変更を検知"
    assert "[CRITICAL]" in record["outcome"]


def test_constraint_hit_on_entity(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    register_constraint(workspace, id="no-touch-helper", file="zzz.py", entity="Api.helper")
    usecase = PatrolUseCase()
    usecase.execute(workspace)
    mutate_index(workspace)

    report = usecase.execute(workspace)

    # File "zzz.py" never changed, but the "helper" symbol did; the last
    # dotted segment of the entity matches it.
    assert len(report.constraint_hits) == 1
    assert "helper" in report.constraint_hits[0].matched


def test_constraint_directory_match(tmp_path: Path) -> None:
    """A trailing-slash constraint covers every file under the directory."""
    workspace = make_workspace(tmp_path)
    conn = sqlite3.connect(workspace / ".comp" / "index.db")
    conn.execute(
        "INSERT INTO files (id, path, hash, language) VALUES (3, 'src/c.py', 'h3', 'python')"
    )
    conn.commit()
    conn.close()
    register_constraint(workspace, id="no-touch-src", file="src/")

    usecase = PatrolUseCase()
    usecase.execute(workspace)
    conn = sqlite3.connect(workspace / ".comp" / "index.db")
    conn.execute("UPDATE files SET hash = 'h3-new' WHERE id = 3")
    conn.commit()
    conn.close()

    report = usecase.execute(workspace)
    assert len(report.constraint_hits) == 1
    assert "src/c.py" in report.constraint_hits[0].matched


def test_no_constraint_no_hits(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    usecase = PatrolUseCase()
    usecase.execute(workspace)
    mutate_index(workspace)

    report = usecase.execute(workspace)
    assert report.constraint_hits == []
    assert not PatrolUseCase.format_summary(report).startswith("[")


def test_unrelated_constraint_no_hit(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    register_constraint(workspace, file="other/unrelated.py", entity="")
    usecase = PatrolUseCase()
    usecase.execute(workspace)
    mutate_index(workspace)

    report = usecase.execute(workspace)
    assert report.constraint_hits == []
    assert (
        json.loads(Path(report.history_file).read_text(encoding="utf-8").splitlines()[-1])["query"]
        == "magatama patrol: 変更検知"
    )


def test_comp_internal_files_ignored(tmp_path: Path) -> None:
    """Indexed .comp/history/*.jsonl entries must not trigger the patrol.

    If comP starts indexing its own history JSONL (BM25 carve-out), each
    patrol pass would otherwise detect its own previous log write.
    """
    workspace = make_workspace(tmp_path)
    usecase = PatrolUseCase()
    usecase.execute(workspace)

    conn = sqlite3.connect(workspace / ".comp" / "index.db")
    conn.execute(
        "INSERT INTO files (id, path, hash, language)"
        " VALUES (9, '.comp/history/log-2026-07.jsonl', 'hx', 'jsonl')"
    )
    conn.execute(
        "INSERT INTO nodes (id, file_id, name, kind, line, col, signature)"
        " VALUES (9, 9, 'entry', 'variable', 1, 0, NULL)"
    )
    conn.commit()
    conn.close()

    report = usecase.execute(workspace)
    assert not report.changed


def test_append_history_record_appends(tmp_path: Path) -> None:
    comp_dir = tmp_path / ".comp"
    comp_dir.mkdir()
    f1 = append_history_record(comp_dir, query="q1", outcome="o1")
    f2 = append_history_record(comp_dir, query="q2", outcome="o2", files=["x.py"])
    assert f1 == f2
    lines = f1.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["query"] == "q1"
    assert json.loads(lines[1])["files"] == ["x.py"]
