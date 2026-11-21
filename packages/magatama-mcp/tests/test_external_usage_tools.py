"""外部パッケージの利用の地図の入口(CLI `usage` と MCP ツール `analyze_external_usage`)のテスト。

契約:
- CLI: ``magatama usage PATH [--exclude GLOB]... [--package NAME]... [--json]``
  - ``--json``: ExternalUsageResult.to_dict() を UTF-8 の JSON で標準出力に出し、終了コード 0(gaps があっても 0)
  - ``--json`` なし: 件数の要約を人向けに出し、終了コード 0
  - PATH が存在しない・ディレクトリでない: 終了コード 2、標準出力は空
  - 想定外の内部エラー: 終了コード 1、標準出力は空、標準エラーに理由
- MCP(MagatamaMcpServer と FastMCP の両方): ``analyze_external_usage(path, exclude=None, packages=None)``
  - 成功: to_dict() に ``"success": True`` を足した dict
  - PATH が存在しない・ディレクトリでない: ``{"success": False, "errors": [理由]}``(例外を出さない)
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
def project(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    (root / "app").mkdir(parents=True)
    (root / "app" / "a.py").write_text(
        'import yaml\n\nAPPS = ["yaml"]\n\n\ndef f(p):\n    return yaml.load(p)\n', encoding="utf-8"
    )
    (root / "web").mkdir()
    (root / "web" / "b.js").write_text('const t = require("lodash/template");\n', encoding="utf-8")
    return root


# ---------------------------------------------------------------- CLI


def test_cli_usage_json(project: Path) -> None:
    result = CliRunner().invoke(cli, ["usage", str(project), "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["schema_version"] == "1"
    assert {(i["top"], i["file"]) for i in data["imports"]} == {
        ("yaml", "app/a.py"),
        ("lodash", "web/b.js"),
    }
    assert data["gaps"] == []


def test_cli_usage_json_with_packages_and_exclude(project: Path) -> None:
    result = CliRunner().invoke(
        cli, ["usage", str(project), "--package", "yaml", "--exclude", "web", "--json"]
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert {i["top"] for i in data["imports"]} == {"yaml"}
    assert data["excluded_dirs"] == ["web"]
    assert [(g["kind"], g["candidates"]) for g in data["gaps"]] == [("string_reference", ["yaml"])]


def test_cli_usage_gaps_do_not_change_exit_code(tmp_path: Path) -> None:
    (tmp_path / "broken.py").write_text("def f(:\n", encoding="utf-8")
    result = CliRunner().invoke(cli, ["usage", str(tmp_path), "--json"])
    assert result.exit_code == 0
    assert [g["kind"] for g in json.loads(result.stdout)["gaps"]] == ["parse_error"]


def test_cli_usage_human_summary(project: Path) -> None:
    result = CliRunner().invoke(cli, ["usage", str(project)])
    assert result.exit_code == 0
    assert "yaml" in result.stdout


@pytest.mark.parametrize("kind", ["missing", "file"])
def test_cli_usage_bad_path_exits_2_with_empty_stdout(tmp_path: Path, kind: str) -> None:
    target = tmp_path / "nope"
    if kind == "file":
        target = tmp_path / "f.py"
        target.write_text("import yaml\n", encoding="utf-8")
    result = CliRunner().invoke(cli, ["usage", str(target), "--json"])
    assert result.exit_code == 2
    assert result.stdout == ""
    assert target.name in result.stderr  # 「未知のコマンド」の終了コード 2 と区別する


def test_cli_usage_internal_error_exits_1_with_empty_stdout(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from magatama_core.application.usecases import external_usage_usecase

    def boom(self, *args, **kwargs):
        raise RuntimeError("unexpected")

    monkeypatch.setattr(external_usage_usecase.ExternalUsageUseCase, "execute", boom)
    result = CliRunner().invoke(cli, ["usage", str(project), "--json"])
    assert result.exit_code == 1
    assert result.stdout == ""
    assert "unexpected" in result.stderr


# ---------------------------------------------------------------- MCP(CLI 向けのサーバー)


def test_legacy_server_registers_tool() -> None:
    names = [t.name for t in MagatamaMcpServer(name="t").list_tools()]
    assert "analyze_external_usage" in names
    assert len(names) == 15  # 変更前(main)の 14 に1つ足しただけ


@pytest.mark.asyncio
async def test_legacy_server_analyze(project: Path) -> None:
    server = MagatamaMcpServer(name="t")
    result = await server.call_tool(
        "analyze_external_usage", {"path": str(project), "packages": ["yaml"]}
    )
    assert result["success"] is True
    assert result["schema_version"] == "1"
    assert {i["top"] for i in result["imports"]} == {"yaml", "lodash"}
    assert [g["kind"] for g in result["gaps"]] == ["string_reference"]


@pytest.mark.asyncio
async def test_legacy_server_bad_path(tmp_path: Path) -> None:
    server = MagatamaMcpServer(name="t")
    result = await server.call_tool("analyze_external_usage", {"path": str(tmp_path / "nope")})
    assert result["success"] is False
    assert result["errors"]


# ---------------------------------------------------------------- MCP(FastMCP)


def test_fastmcp_registers_tool() -> None:
    mcp = create_mcp_server()
    assert "analyze_external_usage" in mcp._tool_manager._tools
    assert len(mcp._tool_manager._tools) == 41  # 変更前(main)の 40 に1つ足しただけ


@pytest.mark.asyncio
async def test_fastmcp_analyze(project: Path) -> None:
    mcp = create_mcp_server()
    result = (
        await mcp.call_tool("analyze_external_usage", {"path": str(project), "exclude": ["web"]})
    ).structured_content
    assert result["success"] is True
    assert {i["top"] for i in result["imports"]} == {"yaml"}
    assert result["excluded_dirs"] == ["web"]


@pytest.mark.asyncio
async def test_fastmcp_bad_path(tmp_path: Path) -> None:
    mcp = create_mcp_server()
    result = (
        await mcp.call_tool("analyze_external_usage", {"path": str(tmp_path / "nope")})
    ).structured_content
    assert result["success"] is False
    assert result["errors"]
