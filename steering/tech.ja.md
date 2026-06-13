# Technology Stack

**Project**: YATA (八咫)
**Last Updated**: 2026-01-01
**Status**: 決定済み

---

## Overview

YATAは、AI Codingを支援するMCP Serverです。CodeGraphMCPServerの技術をベースに、プログラミング言語・フレームワークの知識グラフを構築し、MCPプロトコルで提供します。

## Technology Decisions

### Primary Language: Python 3.11+

**理由**:
- CodeGraphMCPServerとの技術的一貫性
- MCP Python SDKの成熟度
- Tree-sitterバインディングの充実
- 豊富なNLP/グラフ処理ライブラリ

### Core Dependencies

| カテゴリ | ライブラリ | バージョン | 用途 |
|----------|-----------|-----------|------|
| MCP | mcp | ^1.0.0 | MCPプロトコル実装 |
| AST Parser | tree-sitter | ^0.21.0 | ソースコード解析 |
| Graph | networkx | ^3.2.0 | グラフ構造管理 |
| Storage | sqlite3 | (stdlib) | データ永続化 |
| CLI | click | ^8.1.0 | CLIフレームワーク |
| HTTP | httpx | ^0.25.0 | HTTP通信 |
| Config | pydantic | ^2.5.0 | 設定管理・バリデーション |
| Logging | structlog | ^24.0.0 | 構造化ログ |

### Language Support (Tree-sitter Parsers) - 24言語

| 言語 | パーサー | 状態 |
|------|----------|------|
| Python | tree-sitter-python | ✅ 対応 |
| TypeScript | tree-sitter-typescript | ✅ 対応 |
| JavaScript | tree-sitter-javascript | ✅ 対応 |
| Rust | tree-sitter-rust | ✅ 対応 |
| Go | tree-sitter-go | ✅ 対応 |
| Java | tree-sitter-java | ✅ 対応 |
| Kotlin | tree-sitter-kotlin | ✅ 対応 |
| Scala | tree-sitter-scala | ✅ 対応 |
| C | tree-sitter-c | ✅ 対応 |
| C++ | tree-sitter-cpp | ✅ 対応 |
| C# | tree-sitter-c-sharp | ✅ 対応 |
| Swift | tree-sitter-swift | ✅ 対応 |
| Objective-C | tree-sitter-objc | ✅ 対応 |
| PHP | tree-sitter-php | ✅ 対応 |
| Ruby | tree-sitter-ruby | ✅ 対応 |
| Dart | tree-sitter-dart | ✅ 対応 |
| Elixir | tree-sitter-elixir | ✅ 対応 |
| Haskell | tree-sitter-haskell | ✅ 対応 |
| Julia | tree-sitter-julia | ✅ 対応 |
| Lua | tree-sitter-lua | ✅ 対応 |
| Groovy | tree-sitter-groovy | ✅ 対応 |
| SQL | tree-sitter-sql | ✅ 対応 |
| Zig | tree-sitter-zig | ✅ 対応 |
| YAML | tree-sitter-yaml | ✅ 対応 |

### Development Dependencies

| カテゴリ | ライブラリ | 用途 |
|----------|-----------|------|
| Testing | pytest | テストフレームワーク |
| Testing | pytest-cov | カバレッジ計測 |
| Testing | pytest-asyncio | 非同期テスト |
| Linting | ruff | リンター・フォーマッター |
| Type Check | mypy | 型チェック |
| Pre-commit | pre-commit | Git hooks |

---

## Architecture Pattern

### Clean Architecture + MCP

```
┌─────────────────────────────────────────────┐
│              MCP Interface                   │
│    (Tools, Resources, Prompts)              │
├─────────────────────────────────────────────┤
│            Application Layer                 │
│    (Use Cases, Services)                    │
├─────────────────────────────────────────────┤
│              Domain Layer                    │
│    (Entities, Graph Models)                 │
├─────────────────────────────────────────────┤
│           Infrastructure Layer               │
│    (Storage, Parsers, External APIs)        │
└─────────────────────────────────────────────┘
```

---

## Project Structure

```
magatama/
├── src/magatama/
│   ├── __init__.py
│   ├── __main__.py          # CLI entry point
│   ├── server.py            # MCP server
│   ├── config.py            # Configuration
│   ├── core/                # Domain layer
│   │   ├── entities.py      # Entity models
│   │   ├── graph.py         # Graph operations
│   │   └── indexer.py       # Indexing logic
│   ├── parsers/             # Language parsers
│   │   ├── base.py          # Parser interface
│   │   ├── python.py
│   │   ├── typescript.py
│   │   ├── javascript.py
│   │   ├── rust.py
│   │   └── go.py
│   ├── storage/             # Persistence
│   │   ├── sqlite.py
│   │   └── cache.py
│   └── mcp/                 # MCP interface
│       ├── tools.py
│       ├── resources.py
│       └── prompts.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── docs/
├── steering/
├── storage/
├── pyproject.toml
└── README.md
```

---

## Environment Setup

### Requirements

- Python 3.11+
- pip or uv (package manager)
- Git

### Installation

```bash
# Clone repository
git clone https://github.com/nahisaho/YATA.git
cd YATA

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or: .venv\Scripts\activate  # Windows

# Install dependencies
pip install -e ".[dev]"
```

---

## Configuration

### Environment Variables

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| MAGATAMA_DATA_DIR | ~/.magatama | データディレクトリ |
| MAGATAMA_LOG_LEVEL | INFO | ログレベル |
| MAGATAMA_MAX_FILE_SIZE | 10485760 | 最大ファイルサイズ(bytes) |

### Configuration File

`~/.magatama/config.toml`:

```toml
[server]
transport = "stdio"  # or "sse"
port = 8080

[indexing]
max_file_size = 10485760
exclude_patterns = ["node_modules", ".git", "__pycache__"]

[graph]
max_depth = 5
community_detection = true
```

---

## Build & Deploy

### Package Building

```bash
# Build wheel
python -m build

# Build for distribution
pip install build twine
python -m build
twine upload dist/*
```

### Docker (Future)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -e .
ENTRYPOINT ["magatama", "serve"]
```

---

## Quality Gates

| ゲート | 基準 | ツール |
|--------|------|--------|
| Unit Test | Coverage ≥ 80% | pytest-cov |
| Type Check | No errors | mypy |
| Lint | No errors | ruff |
| Format | Consistent | ruff format |

---

*Updated by MUSUBI SDD Workflow - 2025-12-31*
