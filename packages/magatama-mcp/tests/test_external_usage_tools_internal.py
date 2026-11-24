"""外部パッケージの利用の地図の入口: 契約 第3版(`--internal` / `include_internal`)のテスト。

契約: KAGAMI の docs/contracts/magatama-external-usage.md の「第3版」。
- CLI: ``magatama usage PATH ... --json [--internal]``。指定したときだけ JSON に "internal_imports" がある
- MCP(MagatamaMcpServer と FastMCP): ``analyze_external_usage(path, exclude=None, packages=None, include_internal=False)``
- ツールの数は変えない(MagatamaMcpServer 15、FastMCP 41)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from magatama_mcp.cli.main import cli
from magatama_mcp.server import MagatamaMcpServer
from magatama_mcp.server.protocol import create_mcp_server


@pytest.fixture
def package_root(tmp_path: Path) -> Path:
    root = tmp_path / "pkg"
    root.mkdir()
    (root / "template.js").write_text('var a = require("./_a");\n', encoding="utf-8")
    (root / "_a.js").write_text("module.exports = 1;\n", encoding="utf-8")
    (root / "m.py").write_text("from . import sibling\n", encoding="utf-8")
    return root


EXPECTED = [("m.py", ".", "from_import"), ("template.js", "./_a", "require")]


def rows(data: dict) -> list[tuple[str, str, str]]:
    return [(r["file"], r["specifier"], r["kind"]) for r in data["internal_imports"]]


def test_cli_internal_flag_adds_internal_imports(package_root: Path) -> None:
    result = CliRunner().invoke(cli, ["usage", str(package_root), "--json", "--internal"])
    assert result.exit_code == 0, result.output
    assert rows(json.loads(result.stdout)) == EXPECTED


def test_cli_without_internal_flag_has_no_key(package_root: Path) -> None:
    result = CliRunner().invoke(cli, ["usage", str(package_root), "--json"])
    assert result.exit_code == 0, result.output
    assert "internal_imports" not in json.loads(result.stdout)


def test_cli_help_lists_internal_flag() -> None:
    result = CliRunner().invoke(cli, ["usage", "--help"])
    assert result.exit_code == 0
    assert "--internal" in result.stdout


@pytest.mark.asyncio
async def test_legacy_server_include_internal(package_root: Path) -> None:
    server = MagatamaMcpServer(name="t")
    assert len(server.list_tools()) == 15
    result = await server.call_tool("analyze_external_usage", {"path": str(package_root), "include_internal": True})
    assert result["success"] is True
    assert rows(result) == EXPECTED
    plain = await server.call_tool("analyze_external_usage", {"path": str(package_root)})
    assert "internal_imports" not in plain


@pytest.mark.asyncio
async def test_fastmcp_include_internal(package_root: Path) -> None:
    mcp = create_mcp_server()
    assert len(mcp._tool_manager._tools) == 41
    result = (
        await mcp.call_tool("analyze_external_usage", {"path": str(package_root), "include_internal": True})
    ).structured_content
    assert result["success"] is True
    assert rows(result) == EXPECTED
    plain = (await mcp.call_tool("analyze_external_usage", {"path": str(package_root)})).structured_content
    assert "internal_imports" not in plain
