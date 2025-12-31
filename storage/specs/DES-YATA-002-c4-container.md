# YATA C4 Container Diagram

**Project**: YATA (八咫)
**Document ID**: DES-YATA-002
**Version**: 1.0
**Created**: 2025-12-31
**Status**: Draft
**Author**: MUSUBI SDD

---

## 1. 概要

本文書は、YATAシステムのC4 Container図を定義する。システム内部の主要コンテナ（デプロイ可能な単位）とその相互作用を示す。

---

## 2. C4 Container Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    YATA System                                           │
│                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐    │
│  │                           Interface Layer                                        │    │
│  │                                                                                  │    │
│  │  ┌──────────────────────────────┐    ┌──────────────────────────────┐          │    │
│  │  │        MCP Server            │    │         CLI Application      │          │    │
│  │  │                              │    │                              │          │    │
│  │  │  [Container: Python]         │    │  [Container: Python]         │          │    │
│  │  │                              │    │                              │          │    │
│  │  │  - Tools (14種)              │    │  - index コマンド            │          │    │
│  │  │  - Resources (3種)           │    │  - serve コマンド            │          │    │
│  │  │  - Prompts (4種)             │    │  - query コマンド            │          │    │
│  │  │  - stdio/SSE Transport       │    │  - stats コマンド            │          │    │
│  │  │                              │    │  - watch コマンド            │          │    │
│  │  │  Framework: mcp ^1.0.0       │    │  Framework: click ^8.1.0     │          │    │
│  │  │                              │    │                              │          │    │
│  │  └───────────────┬──────────────┘    └───────────────┬──────────────┘          │    │
│  │                  │                                   │                          │    │
│  └──────────────────┼───────────────────────────────────┼──────────────────────────┘    │
│                     │                                   │                               │
│                     │ Uses                              │ Uses                          │
│                     ▼                                   ▼                               │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐    │
│  │                          Application Layer                                       │    │
│  │                                                                                  │    │
│  │  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐        │    │
│  │  │  Library Service   │  │   Query Service    │  │   Index Service    │        │    │
│  │  │                    │  │                    │  │                    │        │    │
│  │  │  [Component]       │  │  [Component]       │  │  [Component]       │        │    │
│  │  │                    │  │                    │  │                    │        │    │
│  │  │  - resolve_library │  │  - query_docs      │  │  - index_library   │        │    │
│  │  │  - list_libraries  │  │  - query_structure │  │  - update_library  │        │    │
│  │  │  - remove_library  │  │  - find_*          │  │  - watch_path      │        │    │
│  │  │                    │  │  - search          │  │                    │        │    │
│  │  └─────────┬──────────┘  └─────────┬──────────┘  └─────────┬──────────┘        │    │
│  │            │                       │                       │                    │    │
│  └────────────┼───────────────────────┼───────────────────────┼────────────────────┘    │
│               │                       │                       │                         │
│               │ Uses                  │ Uses                  │ Uses                    │
│               ▼                       ▼                       ▼                         │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐    │
│  │                            Domain Layer                                          │    │
│  │                                                                                  │    │
│  │  ┌────────────────────────────────────────────────────────────────────────┐    │    │
│  │  │                     Knowledge Graph Engine                              │    │    │
│  │  │                                                                         │    │    │
│  │  │  [Container: Python + NetworkX]                                         │    │    │
│  │  │                                                                         │    │    │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │    │    │
│  │  │  │  Entities   │  │  Relations  │  │    Graph    │  │   Indexer   │   │    │    │
│  │  │  │             │  │             │  │             │  │             │   │    │    │
│  │  │  │ - Class     │  │ - Inherits  │  │ - add_node  │  │ - extract   │   │    │    │
│  │  │  │ - Function  │  │ - Calls     │  │ - add_edge  │  │ - analyze   │   │    │    │
│  │  │  │ - Method    │  │ - Depends   │  │ - query     │  │ - build     │   │    │    │
│  │  │  │ - Type      │  │ - Implements│  │ - traverse  │  │             │   │    │    │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │    │    │
│  │  │                                                                         │    │    │
│  │  └─────────────────────────────────────────────────────────────────────────┘    │    │
│  │                                                                                  │    │
│  └──────────────────────────────────────────────────────────────────────────────────┘    │
│                                          │                                              │
│                                          │ Uses                                         │
│                                          ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐    │
│  │                         Infrastructure Layer                                     │    │
│  │                                                                                  │    │
│  │  ┌──────────────────────────┐         ┌──────────────────────────┐             │    │
│  │  │     Storage Adapter      │         │     Parser Adapter       │             │    │
│  │  │                          │         │                          │             │    │
│  │  │  [Container: SQLite]     │         │  [Container: Tree-sitter]│             │    │
│  │  │                          │         │                          │             │    │
│  │  │  - グラフ永続化          │         │  - Python Parser         │             │    │
│  │  │  - キャッシュ            │         │  - TypeScript Parser     │             │    │
│  │  │  - バージョン管理        │         │  - JavaScript Parser     │             │    │
│  │  │                          │         │  - Rust Parser           │             │    │
│  │  │  File: ~/.yata/db.sqlite │         │  - Go Parser             │             │    │
│  │  │                          │         │                          │             │    │
│  │  └──────────────────────────┘         └──────────────────────────┘             │    │
│  │                                                                                  │    │
│  │  ┌──────────────────────────┐         ┌──────────────────────────┐             │    │
│  │  │     GitHub Adapter       │         │    FileSystem Adapter    │             │    │
│  │  │                          │         │                          │             │    │
│  │  │  [Container: httpx]      │         │  [Container: Python]     │             │    │
│  │  │                          │         │                          │             │    │
│  │  │  - git clone             │         │  - ファイル読み取り      │             │    │
│  │  │  - GitHub API            │         │  - ディレクトリ走査      │             │    │
│  │  │  - Rate limit handling   │         │  - ファイル監視          │             │    │
│  │  │                          │         │                          │             │    │
│  │  └──────────────────────────┘         └──────────────────────────┘             │    │
│  │                                                                                  │    │
│  └──────────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘

                │                                              │
                │ MCP Protocol                                 │ Git/HTTPS
                ▼                                              ▼
┌──────────────────────────┐                    ┌──────────────────────────┐
│     AI Coding Tool       │                    │         GitHub           │
│                          │                    │                          │
│  [External System]       │                    │  [External System]       │
└──────────────────────────┘                    └──────────────────────────┘
```

---

## 3. コンテナ定義

### 3.1 Interface Layer

#### MCP Server

| 項目 | 値 |
|------|-----|
| **名前** | MCP Server |
| **技術** | Python + mcp ^1.0.0 |
| **責務** | MCPプロトコルを介してAI Coding Toolにコンテキストを提供 |
| **エントリポイント** | `src/yata/server.py` |

**提供機能**:

| カテゴリ | 機能 | 数 |
|----------|------|-----|
| **Tools** | ライブラリ検索、ドキュメントクエリ、コード構造クエリ、グラフ探索、管理 | 14 |
| **Resources** | ライブラリ一覧、エンティティ詳細、統計情報 | 3 |
| **Prompts** | 実装ガイド、API説明、バージョン移行、ベストプラクティス | 4 |

#### CLI Application

| 項目 | 値 |
|------|-----|
| **名前** | CLI Application |
| **技術** | Python + click ^8.1.0 |
| **責務** | コマンドラインからのYATA操作 |
| **エントリポイント** | `src/yata/__main__.py` |

**提供コマンド**:

| コマンド | 説明 | 関連要件 |
|----------|------|----------|
| `yata index <path>` | ライブラリインデックス作成 | REQ-CLI-001 |
| `yata serve` | MCPサーバー起動 | REQ-CLI-002 |
| `yata query <query>` | クエリ実行 | REQ-CLI-003 |
| `yata stats` | 統計情報表示 | REQ-CLI-004 |
| `yata watch <path>` | ファイル監視 | REQ-CLI-006 |

---

### 3.2 Application Layer

#### Library Service

| 項目 | 値 |
|------|-----|
| **名前** | Library Service |
| **責務** | ライブラリ管理（登録、検索、削除） |
| **場所** | `src/yata/application/library_service.py` |

**メソッド**:
- `resolve_library(query: str) -> list[Library]`
- `list_libraries() -> list[Library]`
- `get_library(library_id: str) -> Library`
- `remove_library(library_id: str) -> bool`

#### Query Service

| 項目 | 値 |
|------|-----|
| **名前** | Query Service |
| **責務** | 知識グラフに対するクエリ実行 |
| **場所** | `src/yata/application/query_service.py` |

**メソッド**:
- `query_docs(library_id: str, query: str, version: str) -> list[Doc]`
- `query_code_structure(library_id: str, entity_name: str) -> CodeStructure`
- `find_dependencies(entity_id: str, depth: int) -> list[Entity]`
- `find_callers(entity_id: str) -> list[Entity]`
- `find_implementations(interface_id: str) -> list[Entity]`
- `global_search(query: str) -> list[SearchResult]`
- `local_search(query: str, entity_id: str) -> list[SearchResult]`

#### Index Service

| 項目 | 値 |
|------|-----|
| **名前** | Index Service |
| **責務** | ライブラリのインデックス作成・更新 |
| **場所** | `src/yata/application/index_service.py` |

**メソッド**:
- `index_library(path: str, name: str, version: str) -> IndexResult`
- `update_library(library_id: str, incremental: bool) -> IndexResult`
- `watch_path(path: str, callback: Callable) -> WatchHandle`

---

### 3.3 Domain Layer

#### Knowledge Graph Engine

| 項目 | 値 |
|------|-----|
| **名前** | Knowledge Graph Engine |
| **技術** | Python + NetworkX ^3.2.0 |
| **責務** | 知識グラフのコアロジック |
| **場所** | `src/yata/core/` |

**モジュール構成**:

| モジュール | 責務 | 主要クラス/関数 |
|------------|------|-----------------|
| `entities.py` | エンティティモデル定義 | `Entity`, `Class`, `Function`, `Method`, `TypeDef` |
| `relations.py` | 関係性モデル定義 | `Relation`, `Inherits`, `Calls`, `Depends`, `Implements` |
| `graph.py` | グラフ操作 | `KnowledgeGraph`, `add_entity()`, `add_relation()`, `query()` |
| `indexer.py` | インデックス構築ロジック | `Indexer`, `extract_entities()`, `extract_relations()` |

---

### 3.4 Infrastructure Layer

#### Storage Adapter

| 項目 | 値 |
|------|-----|
| **名前** | Storage Adapter |
| **技術** | SQLite (stdlib) |
| **責務** | 知識グラフの永続化 |
| **場所** | `src/yata/infrastructure/storage/` |
| **データファイル** | `~/.yata/db.sqlite` |

**機能**:
- グラフデータの保存・読み込み
- バージョン別グラフ管理
- キャッシュ機構

#### Parser Adapter

| 項目 | 値 |
|------|-----|
| **名前** | Parser Adapter |
| **技術** | Tree-sitter ^0.21.0 |
| **責務** | ソースコードのAST解析 |
| **場所** | `src/yata/infrastructure/parsers/` |

**サポート言語**:

| 言語 | パーサー | 優先度 |
|------|----------|--------|
| Python | tree-sitter-python | High |
| TypeScript | tree-sitter-typescript | High |
| JavaScript | tree-sitter-javascript | High |
| Rust | tree-sitter-rust | Medium |
| Go | tree-sitter-go | Medium |

#### GitHub Adapter

| 項目 | 値 |
|------|-----|
| **名前** | GitHub Adapter |
| **技術** | httpx ^0.25.0, subprocess (git) |
| **責務** | GitHubリポジトリの取得 |
| **場所** | `src/yata/infrastructure/github/` |

**機能**:
- `git clone --depth 1` による浅いクローン
- GitHub REST API によるファイル取得
- Personal Access Token (PAT) 認証
- レートリミット対応

#### FileSystem Adapter

| 項目 | 値 |
|------|-----|
| **名前** | FileSystem Adapter |
| **技術** | Python stdlib (os, pathlib, watchdog) |
| **責務** | ローカルファイルシステム操作 |
| **場所** | `src/yata/infrastructure/filesystem/` |

**機能**:
- ファイル/ディレクトリ走査
- ファイル読み取り
- ファイル変更監視（watchモード用）

---

## 4. コンテナ間通信

### 4.1 内部通信

| 発信元 | 宛先 | 通信方式 | 説明 |
|--------|------|----------|------|
| MCP Server | Application Services | 関数呼び出し | MCPツールからサービス呼び出し |
| CLI Application | Application Services | 関数呼び出し | CLIコマンドからサービス呼び出し |
| Application Services | Knowledge Graph Engine | 関数呼び出し | グラフ操作 |
| Application Services | Infrastructure Adapters | インターフェース経由 | ストレージ、パーサー利用 |

### 4.2 外部通信

| 発信元 | 宛先 | プロトコル | 説明 |
|--------|------|-----------|------|
| AI Coding Tool | MCP Server | MCP (stdio/SSE) | コンテキストクエリ |
| GitHub Adapter | GitHub | HTTPS (Git/API) | リポジトリ取得 |

---

## 5. 技術スタック詳細

### 5.1 依存関係

```
┌─────────────────────────────────────────────────────────────────┐
│                       YATA Dependencies                          │
├─────────────────────────────────────────────────────────────────┤
│ Core                                                             │
│   ├── mcp ^1.0.0               # MCP Protocol                    │
│   ├── networkx ^3.2.0          # Graph Engine                    │
│   ├── click ^8.1.0             # CLI Framework                   │
│   ├── pydantic ^2.5.0          # Data Validation                 │
│   ├── httpx ^0.25.0            # HTTP Client                     │
│   └── structlog ^24.0.0        # Structured Logging              │
├─────────────────────────────────────────────────────────────────┤
│ Parsers                                                          │
│   ├── tree-sitter ^0.21.0      # AST Parser Core                 │
│   ├── tree-sitter-python       # Python Grammar                  │
│   ├── tree-sitter-typescript   # TypeScript Grammar              │
│   ├── tree-sitter-javascript   # JavaScript Grammar              │
│   ├── tree-sitter-rust         # Rust Grammar                    │
│   └── tree-sitter-go           # Go Grammar                      │
├─────────────────────────────────────────────────────────────────┤
│ Development                                                      │
│   ├── pytest ^8.0.0            # Testing                         │
│   ├── pytest-cov               # Coverage                        │
│   ├── pytest-asyncio           # Async Testing                   │
│   ├── ruff                     # Linter/Formatter                │
│   ├── mypy                     # Type Checking                   │
│   └── pre-commit               # Git Hooks                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. 要件トレーサビリティ

| 要件ID | コンテナ | 説明 |
|--------|----------|------|
| REQ-MCP-001〜008 | MCP Server | MCPプロトコル機能 |
| REQ-CLI-001〜006 | CLI Application | CLIコマンド |
| REQ-KGC-001〜006 | Knowledge Graph Engine | 知識グラフ構築 |
| REQ-KGC-007〜008 | GitHub Adapter | GitHub連携 |
| REQ-LANG-001〜005 | Parser Adapter | 言語サポート |
| REQ-NFR-001〜003 | 全コンテナ | パフォーマンス要件 |
| REQ-NFR-004〜005 | Storage Adapter | 信頼性要件 |

---

## 7. 変更履歴

| バージョン | 日付 | 著者 | 変更内容 |
|------------|------|------|----------|
| 1.0 | 2025-12-31 | MUSUBI SDD | 初版作成 |

---

*Generated by MUSUBI SDD - Design Phase (C4 Container)*
