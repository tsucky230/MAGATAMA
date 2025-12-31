# YATA MCP - AI Coding Support MCP Server

[![PyPI version](https://badge.fury.io/py/yata-mcp.svg)](https://badge.fury.io/py/yata-mcp)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Model Context Protocol (MCP) サーバーとして、AI コーディングツールに知識グラフコンテキストを提供します。

## 特徴

- 🤖 **MCP 完全対応**: 8 Tools, 3 Prompts, 1 Resource
- 🔌 **AI ツール連携**: Claude Desktop, GitHub Copilot, Cursor
- 📡 **複数トランスポート**: stdio / SSE
- 🔒 **プライバシー**: 完全ローカル実行

## インストール

```bash
pip install yata-mcp
```

## 使用方法

### CLI コマンド

```bash
# ファイルを解析
yata parse path/to/file.py

# ディレクトリを解析
yata parse path/to/project --pattern "**/*.py"

# MCP サーバーを起動（stdio）
yata serve

# MCP サーバーを起動（SSE）
yata serve --transport sse --port 8080

# エンティティを検索
yata query "function_name" --type function

# 統計情報を表示
yata stats

# グラフの整合性を検証
yata validate --graph graph.json --repair
```

### AI ツール設定

#### Claude Desktop

```json
{
  "mcpServers": {
    "yata": {
      "command": "yata",
      "args": ["serve"]
    }
  }
}
```

#### GitHub Copilot (VS Code)

`.vscode/mcp.json`:

```json
{
  "mcpServers": {
    "yata": {
      "command": "yata",
      "args": ["serve"]
    }
  }
}
```

## MCP Tools

| Tool | 説明 |
|------|------|
| `parse_file` | ソースファイルを解析してエンティティを抽出 |
| `parse_directory` | ディレクトリ内のファイルを一括解析 |
| `search_entities` | 名前や型でエンティティを検索 |
| `get_entity` | 特定エンティティの詳細を取得 |
| `get_related_entities` | 関連エンティティを取得 |
| `get_graph_stats` | 知識グラフの統計情報を取得 |
| `save_graph` | 知識グラフを JSON ファイルに保存 |
| `load_graph` | JSON ファイルから知識グラフを読み込み |

## MCP Prompts

| Prompt | 説明 |
|--------|------|
| `analyze_codebase` | コードベース構造を分析 |
| `explain_entity` | コードエンティティを説明 |
| `find_dependencies` | 依存関係を分析 |

## ライセンス

MIT License - 詳細は [LICENSE](../../LICENSE) を参照してください。

## 関連プロジェクト

- [yata-core](https://github.com/your-org/yata/tree/main/packages/yata-core) - Knowledge Graph Engine
