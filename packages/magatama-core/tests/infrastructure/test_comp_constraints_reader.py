"""Tests for the .comp/constraints.json reader."""

import json
from pathlib import Path

from magatama_core.infrastructure.storage.comp_constraints_reader import read_constraints


def write(tmp_path: Path, payload: object) -> Path:
    comp_dir = tmp_path / ".comp"
    comp_dir.mkdir(exist_ok=True)
    (comp_dir / "constraints.json").write_text(
        payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )
    return comp_dir


def test_reads_constraints(tmp_path: Path) -> None:
    comp_dir = write(
        tmp_path,
        {
            "constraints": [
                {
                    "id": "no-touch",
                    "file": "src/legacy.py",
                    "line_range": [10, 20],
                    "entity": "Legacy.run",
                    "issue": "fragile",
                    "rule": "修正禁止",
                    "reason": "顧客納品済み",
                    "severity": "CRITICAL",
                    "created_at": "2026-07-04",
                }
            ]
        },
    )
    constraints = read_constraints(comp_dir)
    assert len(constraints) == 1
    c = constraints[0]
    assert c.id == "no-touch"
    assert c.file == "src/legacy.py"
    assert c.entity == "Legacy.run"
    assert c.severity == "CRITICAL"


def test_severity_defaults_to_warning(tmp_path: Path) -> None:
    comp_dir = write(tmp_path, {"constraints": [{"file": "a.py"}]})
    assert read_constraints(comp_dir)[0].severity == "WARNING"


def test_missing_file_is_empty(tmp_path: Path) -> None:
    (tmp_path / ".comp").mkdir()
    assert read_constraints(tmp_path / ".comp") == []


def test_malformed_json_is_empty(tmp_path: Path) -> None:
    comp_dir = write(tmp_path, "{broken")
    assert read_constraints(comp_dir) == []


def test_entries_without_file_skipped(tmp_path: Path) -> None:
    comp_dir = write(
        tmp_path,
        {"constraints": [{"id": "x"}, "not-a-dict", {"file": "ok.py"}]},
    )
    constraints = read_constraints(comp_dir)
    assert [c.file for c in constraints] == ["ok.py"]
