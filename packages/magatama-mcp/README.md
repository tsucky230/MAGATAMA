# magatama - AI Coding Support MCP Server

[![PyPI version](https://badge.fury.io/py/magatama.svg)](https://badge.fury.io/py/magatama)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> [MAGATAMA](https://github.com/tsucky230/MAGATAMA)（[YATA](https://github.com/nahisaho/YATA) のフォーク）の
> MCP サーバーパッケージです（PyPI 配布名 `magatama` / import 名 `magatama_mcp` / CLI コマンド `magatama`）。

Model Context Protocol (MCP) サーバーとして、AI コーディングツールに知識グラフコンテキストを提供します。

## 特徴

- 🤖 **MCP 完全対応**: 36 Tools, 3 Prompts, 1 Resource
- 🔌 **comP Bridge**: comP の `.comp/index.db` を再パースなしで知識グラフに取り込み
- 🔌 **AI ツール連携**: Claude Desktop, GitHub Copilot, Cursor
- 📡 **複数トランスポート**: stdio / SSE
- 🔒 **プライバシー**: 完全ローカル実行

## インストール

```bash
pip install magatama
```

## 使用方法

### CLI コマンド

```bash
# ファイルを解析
magatama parse path/to/file.py

# ディレクトリを解析
magatama parse path/to/project --pattern "**/*.py"

# MCP サーバーを起動（stdio）
magatama serve

# MCP サーバーを起動（SSE）
magatama serve --transport sse --port 8080

# エンティティを検索
magatama query "function_name" --type function

# 統計情報を表示
magatama stats

# グラフの整合性を検証
magatama validate --graph graph.json --repair
```

### AI ツール設定

#### Claude Desktop

```json
{
  "mcpServers": {
    "magatama": {
      "command": "magatama",
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
    "magatama": {
      "command": "magatama",
      "args": ["serve"]
    }
  }
}
```

## MCP Tools

全 **36 ツール**を提供します（基本・フレームワーク知識・検索・品質分析・
AI 支援・comP Bridge）。下表は基本ツールの抜粋で、全 36 ツールの一覧は
[ルート README](https://github.com/tsucky230/MAGATAMA#-mcp-tools-36) を参照してください。

| Tool | 説明 |
|------|------|
| `parse_file` | ソースファイルを解析してエンティティを抽出 |
| `parse_directory` | ディレクトリ内のファイルを一括解析 |
| `search_entities` | 名前や型でエンティティを検索 |
| `get_entity` / `get_related_entities` | 詳細取得 / 関連エンティティ取得 |
| `get_graph_stats` | 知識グラフの統計情報を取得 |
| `save_graph` / `load_graph` | JSON への保存 / 読み込み |
| `read_external_graph` | **comP Bridge**: comP インデックスを取り込み |
| `get_external_graph_info` | **comP Bridge**: comP インデックスの統計を確認 |

## MCP Prompts

| Prompt | 説明 |
|--------|------|
| `analyze_codebase` | コードベース構造を分析 |
| `explain_entity` | コードエンティティを説明 |
| `find_dependencies` | 依存関係を分析 |

## ライセンス

MIT License - 詳細は [LICENSE](../../LICENSE) を参照してください。

## 関連プロジェクト

- [magatama-core](https://github.com/tsucky230/MAGATAMA/tree/main/packages/magatama-core) - Knowledge Graph Engine
