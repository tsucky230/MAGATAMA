# Technology Stack

**Project**: MAGATAMA (勾玉)
**Last Updated**: 2026-01-01
**Status**: 決定済み

> MAGATAMA は [YATA (八咫)](https://github.com/nahisaho/YATA) のフォークに、
> コードインデクサー [comP](https://github.com/tsucky230/comP) との連携
> （comP Bridge）を追加したものです。フレームワーク知識機能は YATA 由来です。

---

## Overview

MAGATAMAは、AI Codingを支援するMCP Serverです。プログラミング言語・フレームワークの知識グラフを構築し、MCPプロトコルで提供します。加えて、兄弟ツール comP（VSCode 拡張）が生成する `.comp/index.db` を再パースなしで知識グラフに取り込む **comP Bridge** を備えます。

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
| AST Parser | tree-sitter | ^0.24.0 | ソースコード解析 |
| Graph | networkx | ^3.2.0 | グラフ構造管理 |
| Storage | sqlite3 | (stdlib) | データ永続化（comP の index.db 読取含む） |
| CLI | click | ^8.1.0 | CLIフレームワーク |
| CLI 表示 | rich | ^13.7.0 | CLI のリッチ出力 |
| HTTP/SSE | uvicorn / httpx | ^0.27.0 | SSE トランスポート・HTTP通信 |
| File Watch | watchdog | ^4.0.0 | `watch` コマンドのファイル監視 |
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
MAGATAMA/                            # uv モノレポ
├── packages/
│   ├── magatama-core/               # 知識グラフエンジン（ライブラリ）
│   │   └── src/magatama_core/
│   │       ├── domain/              # Domain 層（entities, value_objects, repositories）
│   │       ├── application/         # Application 層（usecases: parse / comp / framework …）
│   │       └── infrastructure/      # Infrastructure 層
│   │           ├── parsers/         # Tree-sitter 言語別パーサ（24言語）
│   │           └── storage/         # networkx_graph / sqlite_storage / comp_index_reader
│   └── magatama-mcp/                # MCP サーバ＋CLI（配布名 `magatama`）
│       └── src/magatama_mcp/
│           ├── server/              # MCP 実装（FastMCP, mcp_server.py / protocol.py）
│           └── cli/                 # CLI 実装（Click, main.py）
├── knowledge_graphs/                # 47 フレームワークの事前学習済みグラフ（JSON）
├── docs/                            # 利用ガイド（日英）
├── steering/                        # プロジェクトメモリ（このファイル等）
├── storage/specs/                   # SDD 設計ドキュメント
├── pyproject.toml                   # ワークスペース設定
├── README.md                        # English（メイン）
└── README_jp.md                     # 日本語
```

> comP Bridge の中核: `infrastructure/storage/comp_index_reader.py`（SQLite 読取）と
> `application/usecases/comp_usecase.py`（`LoadCompIndexUseCase`）。

---

## Environment Setup

### Requirements

- Python 3.11+
- uv (推奨パッケージマネージャ) / pip
- Git

### Installation

```bash
# Clone repository
git clone https://github.com/tsucky230/MAGATAMA.git
cd MAGATAMA

# Install dependencies (uv, モノレポ全パッケージ)
uv sync --all-packages

# もしくは PyPI から
pip install magatama
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
