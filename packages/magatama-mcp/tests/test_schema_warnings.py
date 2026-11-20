"""comP の索引の形式の版がずれているとき、ツールの応答に warnings が出ることを確かめる。

エージェントが読むのはツールの応答だけなので、LoadCompIndexResult.warnings を応答に載せないと
ユーザーは更新が必要なことに気づけない。
"""

import sqlite3
from pathlib import Path

import pytest

from magatama_mcp.server import MagatamaMcpServer
from magatama_mcp.server.protocol import create_mcp_server


def _write_workspace(root: Path, schema_version: str | None) -> Path:
    comp_dir = root / ".comp"
    comp_dir.mkdir(parents=True)
    conn = sqlite3.connect(comp_dir / "index.db")
    conn.executescript(
        "CREATE TABLE files (id INTEGER PRIMARY KEY, path TEXT, hash TEXT,"
        " language TEXT, last_indexed INTEGER DEFAULT 0);"
        "CREATE TABLE nodes (id INTEGER PRIMARY KEY, file_id INTEGER, name TEXT,"
        " kind TEXT, line INTEGER, col INTEGER, scope TEXT,"
        " is_exported INTEGER DEFAULT 0, signature TEXT);"
        "CREATE TABLE edges (from_id INTEGER, to_id INTEGER, kind TEXT);"
        "CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT);"
    )
    if schema_version is not None:
        conn.execute("INSERT INTO metadata VALUES ('schema_version', ?)", (schema_version,))
    conn.execute(
        "INSERT INTO files (id, path, hash, language) VALUES (1, 'src/a.py', 'h', 'python')"
    )
    conn.execute(
        "INSERT INTO nodes (id, file_id, name, kind, line, col) VALUES (1, 1, 'f', 'function', 1, 0)"
    )
    conn.commit()
    conn.close()
    return root


async def _call(name: str, arguments: dict) -> dict:
    result = await create_mcp_server().call_tool(name, arguments)
    return result.structured_content


@pytest.mark.asyncio
async def test_read_external_graph_reports_missing_schema_version(tmp_path: Path) -> None:
    ws = _write_workspace(tmp_path / "old", None)
    payload = await _call("read_external_graph", {"path": str(ws)})
    assert payload["success"] is True
    assert len(payload["warnings"]) == 1
    assert "comP" in payload["warnings"][0]


@pytest.mark.asyncio
async def test_read_external_graph_current_version_has_no_warnings(tmp_path: Path) -> None:
    ws = _write_workspace(tmp_path / "cur", "1")
    payload = await _call("read_external_graph", {"path": str(ws)})
    assert payload["success"] is True
    assert payload["warnings"] == []


@pytest.mark.asyncio
async def test_analyze_change_scope_reports_unsupported_version(tmp_path: Path) -> None:
    ws = _write_workspace(tmp_path / "new", "2")
    payload = await _call("analyze_change_scope", {"path": str(ws), "files": ["src/a.py"]})
    assert payload["success"] is True
    assert len(payload["warnings"]) == 1
    assert "MAGATAMA" in payload["warnings"][0]


@pytest.mark.asyncio
async def test_analyze_change_scope_current_version_has_no_warnings(tmp_path: Path) -> None:
    ws = _write_workspace(tmp_path / "cur", "1")
    payload = await _call("analyze_change_scope", {"path": str(ws), "files": ["src/a.py"]})
    assert payload["warnings"] == []


@pytest.mark.asyncio
async def test_cli_server_read_external_graph_reports_warning(tmp_path: Path) -> None:
    ws = _write_workspace(tmp_path / "old", None)
    result = await MagatamaMcpServer().call_tool("read_external_graph", {"path": str(ws)})
    assert len(result["warnings"]) == 1


@pytest.mark.asyncio
async def test_get_entity_history_with_path_reports_warning(tmp_path: Path) -> None:
    ws = _write_workspace(tmp_path / "old", None)
    payload = await _call("get_entity_history", {"name": "f", "path": str(ws)})
    assert len(payload["warnings"]) == 1


@pytest.mark.asyncio
async def test_get_entity_history_without_path_has_no_warnings() -> None:
    payload = await _call("get_entity_history", {"name": "nothing"})
    assert payload["warnings"] == []
