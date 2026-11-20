"""配布物が宣言する依存の範囲が、コードが実際に必要とする版と合っているかを確かめる。

0.7.1 は `mcp>=1.0.0,<3` と宣言したが、コードは mcp 2 の `MCPServer` を使う。そのため mcp 1.x が
入った環境に入れると、インストールは成功するのに起動時に ImportError になった。
"""

import tomllib
from pathlib import Path

from packaging.requirements import Requirement

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def _declared_mcp() -> Requirement:
    deps = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]["dependencies"]
    reqs = [Requirement(d) for d in deps]
    return next(r for r in reqs if r.name == "mcp")


def test_declared_mcp_range_rejects_mcp_1() -> None:
    assert not _declared_mcp().specifier.contains("1.27.2")


def test_declared_mcp_range_accepts_tested_mcp_2() -> None:
    assert _declared_mcp().specifier.contains("2.3.0")


def test_code_needs_mcp_2() -> None:
    # 宣言の下限を上げる根拠: protocol.py は mcp 2 で導入された MCPServer を import する
    from mcp.server import MCPServer

    assert MCPServer.__module__.startswith("mcp.server.mcpserver")
