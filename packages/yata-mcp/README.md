# YATA MCP - AI Coding Support MCP Server

Model Context Protocol (MCP) サーバーとして、AI コーディングツールに知識グラフコンテキストを提供します。

## インストール

```bash
pip install yata-mcp
```

## 使用方法

```bash
# ライブラリをインデックス
yata index https://github.com/psf/requests

# MCP サーバーを起動（stdio）
yata serve

# MCP サーバーを起動（SSE）
yata serve --port 8080
```

## MCP Tools

| Tool | 説明 |
|------|------|
| `resolve_library` | ライブラリを検索 |
| `query_docs` | ドキュメントをクエリ |
| `query_code_structure` | コード構造を取得 |
| `find_dependencies` | 依存関係を探索 |
| `find_callers` | 呼び出し元を探索 |
| ... | 他 9 ツール |

## ライセンス

MIT License
