# YATA 設計ドキュメント

**Project**: YATA (八咫)
**Document ID**: DES-YATA-000
**Version**: 1.0
**Created**: 2025-12-31
**Status**: Draft
**Author**: MUSUBI SDD

---

## 1. 概要

本文書は、YATA (八咫) MCP Serverの設計ドキュメントの統合インデックスです。MUSUBI SDD設計フェーズの成果物として、C4モデルとADR（Architecture Decision Records）を提供します。

---

## 2. 設計ドキュメント一覧

### 2.1 C4 Model Diagrams

| Document ID | Title | Description | Status |
|-------------|-------|-------------|--------|
| [DES-YATA-001](DES-YATA-001-c4-context.md) | C4 Context Diagram | システムと外部アクター・システムとの関係 | ✅ Complete |
| [DES-YATA-002](DES-YATA-002-c4-container.md) | C4 Container Diagram | システム内部のコンテナ構成 | ✅ Complete |
| [DES-YATA-003](DES-YATA-003-c4-component.md) | C4 Component Diagram | 各コンテナ内のコンポーネント詳細 | ✅ Complete |

### 2.2 Supplementary Design Documents

| Document ID | Title | Description | Status |
|-------------|-------|-------------|--------|
| [DES-YATA-004](DES-YATA-004-test-strategy.md) | テスト戦略 | Article III/IX準拠のテスト設計 | ✅ Complete |
| [DES-YATA-005](DES-YATA-005-error-codes.md) | エラーコード設計 | MCP準拠エラー体系 | ✅ Complete |
| [DES-YATA-006](DES-YATA-006-configuration.md) | 設定ファイル設計 | 設定管理方式 | ✅ Complete |
| [DES-YATA-007](DES-YATA-007-sequence-diagrams.md) | シーケンス図 | 主要ユースケースの処理フロー | ✅ Complete |
| [DES-YATA-008](DES-YATA-008-deployment.md) | デプロイメント図 | AIツール連携・インストール方法 | ✅ Complete |

### 2.3 Architecture Decision Records (ADR)

| ADR ID | Title | Status | Decision |
|--------|-------|--------|----------|
| [ADR-001](ADR-001-clean-architecture.md) | Clean Architecture採用 | Accepted | 4層構造（Domain/Application/Infrastructure/Interface） |
| [ADR-002](ADR-002-mcp-protocol.md) | MCP Python SDK採用 | Accepted | mcp ^1.0.0 公式SDKを使用 |
| [ADR-003](ADR-003-tree-sitter-parser.md) | Tree-sitterによるAST解析 | Accepted | 多言語対応の統一パーサー |
| [ADR-004](ADR-004-graph-storage.md) | NetworkX + SQLiteストレージ | Accepted | インメモリグラフ + ファイルDB |

### 2.4 Task Breakdown

| Document ID | Title | Description | Status |
|-------------|-------|-------------|--------|
| [TASK-YATA-001](TASK-YATA-001-task-breakdown.md) | タスク分解書 | 42タスク/6スプリント計画 | ✅ Complete |

---

## 3. アーキテクチャ概要

### 3.1 System Context

```
┌─────────────────┐         ┌─────────────────┐
│   AI Developer  │         │  Library Author │
└────────┬────────┘         └────────┬────────┘
         │                           │
         │ MCP経由                   │ CLI
         ▼                           ▼
┌────────────────────────────────────────────────┐
│                    YATA                         │
│                                                 │
│  知識グラフを構築し、MCPでコンテキストを提供    │
│                                                 │
└────────────────────┬───────────────────────────┘
                     │
         ┌───────────┼───────────┐
         ▼           ▼           ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐
    │ GitHub  │ │Local FS │ │  OSS    │
    │         │ │         │ │Libraries│
    └─────────┘ └─────────┘ └─────────┘
```

### 3.2 Container Structure

```
┌─────────────────────────────────────────────────────────────┐
│                         YATA System                          │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                  Interface Layer                     │    │
│  │                                                      │    │
│  │  ┌──────────────────┐    ┌──────────────────┐       │    │
│  │  │   MCP Server     │    │  CLI Application │       │    │
│  │  │   (14 Tools)     │    │  (5 Commands)    │       │    │
│  │  └──────────────────┘    └──────────────────┘       │    │
│  └─────────────────────────────────────────────────────┘    │
│                              │                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                 Application Layer                    │    │
│  │                                                      │    │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐      │    │
│  │  │ Library    │ │  Query     │ │  Index     │      │    │
│  │  │ Service    │ │  Service   │ │  Service   │      │    │
│  │  └────────────┘ └────────────┘ └────────────┘      │    │
│  └─────────────────────────────────────────────────────┘    │
│                              │                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                   Domain Layer                       │    │
│  │                                                      │    │
│  │  ┌─────────────────────────────────────────────┐    │    │
│  │  │          Knowledge Graph Engine              │    │    │
│  │  │  (Entity, Relation, Graph, Indexer)         │    │    │
│  │  └─────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────┘    │
│                              │                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │               Infrastructure Layer                   │    │
│  │                                                      │    │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐      │    │
│  │  │  Storage   │ │  Parser    │ │  GitHub    │      │    │
│  │  │  (SQLite)  │ │(Tree-sitter)│ │  Client    │      │    │
│  │  └────────────┘ └────────────┘ └────────────┘      │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 3.3 Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| **Language** | Python | 3.11+ |
| **MCP** | mcp | ^1.0.0 |
| **CLI** | click | ^8.1.0 |
| **Graph** | networkx | ^3.2.0 |
| **Parser** | tree-sitter | ^0.21.0 |
| **Storage** | sqlite3 | (stdlib) |
| **HTTP** | httpx | ^0.25.0 |
| **Validation** | pydantic | ^2.5.0 |
| **Logging** | structlog | ^24.0.0 |

---

## 4. 要件トレーサビリティ

### 4.1 設計 → 要件マッピング

| Design ID | 要件ID | 説明 |
|-----------|--------|------|
| DES-001 | REQ-KGC-001, REQ-KGC-002 | ソースコード解析・関係性抽出 |
| DES-002 | REQ-KGC-003, REQ-KGC-005 | グラフストレージ・バージョン管理 |
| DES-003 | REQ-KGC-004 | ドキュメント統合 |
| DES-004 | REQ-MCP-001 | MCPプロトコル準拠 |
| DES-005 | REQ-MCP-002〜005 | MCPツール実装 |
| DES-006 | REQ-MCP-006 | MCPリソース |
| DES-007 | REQ-MCP-007 | MCPプロンプト |
| DES-008 | REQ-CLI-001〜005 | CLIコマンド |
| DES-009 | REQ-LANG-001〜005, REQ-NFR-008 | 言語サポート・拡張性 |
| DES-010 | REQ-NFR-001〜003, REQ-NFR-006 | パフォーマンス |
| DES-011 | REQ-NFR-004〜005 | 信頼性 |
| DES-012 | REQ-NFR-007 | セキュリティ（ローカル実行） |
| DES-013 | REQ-KGC-006 | コミュニティ検出（GraphRAG） |
| DES-014 | REQ-MCP-008 | エラー応答形式 |
| DES-015 | REQ-CLI-006 | ウォッチモード |
| DES-016 | REQ-NFR-009 | ログ出力 |
| DES-017 | REQ-KGC-007, REQ-KGC-008 | GitHub連携 |

### 4.2 ADR → 要件マッピング

| ADR | 関連要件 | 影響範囲 |
|-----|----------|----------|
| ADR-001 | REQ-NFR-008 | 全コンポーネント |
| ADR-002 | REQ-MCP-001〜008 | MCP Server |
| ADR-003 | REQ-KGC-001, REQ-LANG-001〜005 | Parser Adapter |
| ADR-004 | REQ-KGC-003, REQ-NFR-003〜005 | Storage Adapter |

---

## 5. ディレクトリ構造

```
src/yata/
├── __init__.py
├── __main__.py              # CLI entry point
├── server.py                # MCP server main
├── config.py                # Configuration
│
├── core/                    # Domain Layer
│   ├── __init__.py
│   ├── entities.py          # Entity models
│   ├── relations.py         # Relation models
│   ├── graph.py             # KnowledgeGraph
│   └── indexer.py           # Indexing logic
│
├── application/             # Application Layer
│   ├── __init__.py
│   ├── library_service.py   # Library management
│   ├── query_service.py     # Query execution
│   ├── index_service.py     # Index creation
│   └── ports.py             # Infrastructure interfaces
│
├── infrastructure/          # Infrastructure Layer
│   ├── __init__.py
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── sqlite.py        # SQLite storage
│   │   └── cache.py         # Graph cache
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── base.py          # Parser interface
│   │   ├── registry.py      # Parser registry
│   │   ├── python.py        # Python parser
│   │   ├── typescript.py    # TypeScript parser
│   │   ├── javascript.py    # JavaScript parser
│   │   ├── rust.py          # Rust parser
│   │   └── go.py            # Go parser
│   ├── github/
│   │   ├── __init__.py
│   │   ├── client.py        # GitHub client
│   │   └── metadata.py      # Metadata extractor
│   └── filesystem/
│       ├── __init__.py
│       └── watcher.py       # File watcher
│
├── mcp/                     # Interface Layer (MCP)
│   ├── __init__.py
│   ├── tools.py             # MCP Tools (14)
│   ├── resources.py         # MCP Resources (3)
│   └── prompts.py           # MCP Prompts (4)
│
└── cli/                     # Interface Layer (CLI)
    ├── __init__.py
    └── commands.py          # CLI commands
```

---

## 6. 主要コンポーネント仕様

### 6.1 MCP Tools (14種)

| Category | Tool | Parameters | Response |
|----------|------|------------|----------|
| **Discovery** | `resolve_library` | query, library_name? | library_id, candidates[] |
| | `list_libraries` | - | libraries[] |
| **Docs** | `query_docs` | library_id, query, version?, max_tokens? | docs[], code_examples[] |
| | `get_api_reference` | library_id, entity_name | signature, docstring, examples |
| **Structure** | `query_code_structure` | library_id, query | structure, signature, dependencies |
| | `find_dependencies` | entity_id, depth? | dependencies[] |
| | `find_callers` | entity_id | callers[] |
| | `find_implementations` | interface_id | implementations[] |
| **GraphRAG** | `global_search` | query, max_results? | results[] |
| | `local_search` | query, entity_id, max_results? | results[] |
| **Management** | `index_library` | path, name, version?, token? | library_id, stats |
| | `update_library` | library_id, incremental? | updated_count |
| | `remove_library` | library_id | success |
| | `get_stats` | library_id? | stats |

### 6.2 MCP Resources (3種)

| URI | Description |
|-----|-------------|
| `yata://libraries` | 登録済みライブラリ一覧 |
| `yata://entities/{id}` | エンティティ詳細 |
| `yata://stats` | グラフ統計情報 |

### 6.3 MCP Prompts (4種)

| Prompt | Parameters | Description |
|--------|------------|-------------|
| `implement_with_library` | library_id, task | ライブラリを使った実装ガイド |
| `explain_api` | library_id, entity_name | API説明プロンプト |
| `migrate_version` | library_id, from_version, to_version | バージョン移行ガイド |
| `best_practices` | library_id, topic | ベストプラクティスガイド |

### 6.4 CLI Commands (5種)

| Command | Options | Description |
|---------|---------|-------------|
| `yata index <path>` | --version, --tag, --branch, --token | ライブラリインデックス作成 |
| `yata serve` | --port, --transport | MCPサーバー起動 |
| `yata query <query>` | --format, --max-results | クエリ実行 |
| `yata stats` | --library | 統計情報表示 |
| `yata watch <path>` | --debounce | ファイル監視 |

---

## 7. データモデル

### 7.1 Entity Model

```python
@dataclass
class Entity:
    id: str                    # UUID
    kind: EntityKind           # class, function, method, type, module
    name: str                  # Short name
    qualified_name: str        # Full qualified name
    file_path: str             # Source file path
    line_start: int            # Start line number
    line_end: int              # End line number
    signature: str | None      # Function/method signature
    docstring: str | None      # Documentation string
    metadata: dict             # Additional attributes
```

### 7.2 Relation Model

```python
@dataclass
class Relation:
    id: str                    # UUID
    source_id: str             # Source entity ID
    target_id: str             # Target entity ID
    kind: RelationKind         # inherits, calls, depends, implements, type_ref
    metadata: dict             # Additional attributes
```

### 7.3 Library Model

```python
@dataclass
class Library:
    id: str                    # UUID
    name: str                  # Library name
    version: str               # Version string (semver)
    path: str                  # Source path or GitHub URL
    language: str              # Primary language
    description: str | None    # Library description
    metadata: dict             # package.json, pyproject.toml etc.
```

---

## 8. 次のステップ

設計フェーズ完了後、以下のフェーズに進みます：

1. **タスク分解** (`#sdd-tasks yata`)
   - 設計をタスクに分解
   - 優先度と依存関係の定義
   - スプリント計画

2. **実装** (`#sdd-implement yata`)
   - Test-First開発（Article III）
   - 段階的な機能実装
   - コードレビュー

3. **検証** (`#sdd-validate yata`)
   - 憲法準拠チェック
   - 統合テスト
   - パフォーマンステスト

---

## 9. 変更履歴

| バージョン | 日付 | 著者 | 変更内容 |
|------------|------|------|----------|
| 1.0 | 2025-12-31 | MUSUBI SDD | 初版作成 |

---

*Generated by MUSUBI SDD - Design Phase*
