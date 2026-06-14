# Project Structure

**Project**: MAGATAMA (勾玉)
**Last Updated**: 2026-01-01
**Version**: 1.2

> MAGATAMA は [YATA (八咫)](https://github.com/nahisaho/YATA) のフォークに、
> コードインデクサー [comP](https://github.com/tsucky230/comP) との連携
> （comP Bridge）を追加した MCP Server です。

---

## Architecture Pattern

**Primary Pattern**: Clean Architecture + MCP Server（uv モノレポ）

> MAGATAMA は Clean Architecture を採用し、MCP プロトコルを通じて AI コーディング
> ツールにコンテキストを提供します。コア機能は `magatama-core` ライブラリとして
> 独立実装され、`magatama-mcp`（MCP サーバ＋CLI）から公開されます（Article I）。

---

## Architecture Layers

### Layer 1: Domain / Core

**Purpose**: 知識グラフのコアロジックとエンティティ定義
**Location**: `packages/magatama-core/src/magatama_core/domain/`
**Rules**: フレームワーク非依存の純粋 Python / MCP 非依存 / 外部 I/O なし

| パス | 説明 |
|------|------|
| `entities/code_entities.py` | エンティティモデル（Class, Function, Method 等） |
| `entities/relationships.py` | 関係性モデル（CALLS, IMPORTS, INHERITS, CONTAINS） |
| `value_objects/` | 値オブジェクト（EntityId, Location, Version） |
| `repositories/` | リポジトリインターフェース（Ports） |

### Layer 2: Application / Use Cases

**Purpose**: ユースケースの実装とオーケストレーション
**Location**: `packages/magatama-core/src/magatama_core/application/`
**Rules**: Domain 層のみに依存 / 直接 I/O なし

| パス | 説明 |
|------|------|
| `usecases/parse_usecase.py` | ファイル／ディレクトリ解析 |
| `usecases/comp_usecase.py` | **comP Bridge**: `LoadCompIndexUseCase`（index.db 取り込み） |
| `usecases/framework_usecase.py` | フレームワーク知識・検索・コンテキスト生成 |
| `services/` | benchmark, graph_validator 等 |

### Layer 3: Infrastructure / Adapters

**Purpose**: 外部システム統合（ストレージ、パーサー、comP）
**Location**: `packages/magatama-core/src/magatama_core/infrastructure/`
**Rules**: Application 層の Ports を実装 / I/O をここに集約

| サブディレクトリ | 説明 |
|------------------|------|
| `parsers/` | Tree-sitter パーサー実装（24 言語） |
| `storage/networkx_graph.py` | NetworkX 知識グラフ |
| `storage/sqlite_storage.py` | SQLite 永続化 |
| `storage/comp_index_reader.py` | **comP Bridge**: `.comp/index.db` 読取（WAL, 読み取り専用） |

### Layer 4: Interface / Presentation

**Purpose**: MCP プロトコルインターフェース、CLI
**Location**: `packages/magatama-mcp/src/magatama_mcp/`
**Rules**: Application 層を呼び出し / 入力検証・整形 / MCP 準拠

| パス | 説明 |
|------|------|
| `server/mcp_server.py` | MCP ツール登録（36 ツール） |
| `server/protocol.py` | FastMCP サーバ生成・プロンプト・リソース |
| `cli/main.py` | CLI コマンド（parse / query / stats / serve / watch …） |

### Layer Dependency Rules

```
┌─────────────────────────────────────────┐
│   Interface Layer (MCP/CLI)             │ ← Entry points
├─────────────────────────────────────────┤
│   Application Layer (Use Cases)         │
├─────────────────────────────────────────┤
│   Infrastructure Layer (Storage/Parser) │ ← I/O & External (comP)
├─────────────────────────────────────────┤
│   Domain Layer (Core)                   │ ← Pure logic
└─────────────────────────────────────────┘

Dependency Direction: ↓ (outer → inner)
Domain layer has NO dependencies
```

---

## Directory Organization

```
MAGATAMA/                            # uv モノレポ
├── packages/
│   ├── magatama-core/               # 知識グラフエンジン（ライブラリ）
│   │   ├── src/magatama_core/
│   │   │   ├── domain/              # entities, value_objects, repositories
│   │   │   ├── application/         # usecases, services
│   │   │   └── infrastructure/      # parsers/, storage/（comp_index_reader 含む）
│   │   └── tests/
│   └── magatama-mcp/                # MCP サーバ＋CLI（配布名 `magatama`）
│       ├── src/magatama_mcp/
│       │   ├── server/              # FastMCP 実装（36 ツール）
│       │   └── cli/                 # Click 実装
│       └── tests/                   # cli / server / e2e
├── knowledge_graphs/                # 47 フレームワーク事前学習済みグラフ（JSON）
├── docs/                            # 利用ガイド（日英）
├── storage/specs/                   # SDD 設計ドキュメント（要件・C4・ADR）
├── steering/                        # Project memory（structure / tech / product / rules）
├── scripts/                         # 補助スクリプト
├── pyproject.toml                   # ワークスペース設定
├── README.md                        # English（メイン）
├── README_jp.md                     # 日本語
└── AGENTS.md                        # AI Agent 設定
```

---

## MCP Tools Architecture (Article II: CLI Interface)

MAGATAMA は **36 種類**の MCP ツールを提供します（YATA 由来 34 + comP Bridge 2）。

### Tool Categories

#### comP Bridge (2)
| ツール | 説明 | パラメータ |
|--------|------|-----------|
| `read_external_graph` | comP インデックスを知識グラフに取り込む | path, mode |
| `get_external_graph_info` | comP インデックスの統計を確認（ロードなし） | path |

#### 基本ツール (10)
| ツール | 説明 | パラメータ |
|--------|------|-----------|
| `parse_file` | ソースファイル解析 | file_path |
| `parse_directory` | ディレクトリ一括解析 | directory, patterns |
| `search_entities` | エンティティ検索 | query, entity_type |
| `get_entity` | エンティティ詳細取得 | entity_id |
| `get_related_entities` | 関連エンティティ取得 | entity_id |
| `get_graph_stats` | 統計情報取得 | - |
| `save_graph` / `load_graph` | グラフ保存／読込 | file_path |
| `list_supported_languages` | 24 言語一覧 | - |
| `get_language_for_file` | 拡張子から言語判定 | file_path |

#### フレームワーク知識グラフツール (7)
`list_frameworks` / `search_framework_docs` / `search_all_frameworks` /
`find_code_patterns` / `get_framework_entity_context` /
`framework_semantic_search_tool` / `framework_find_by_pattern`

#### 検索・コンテキスト (4)
`semantic_search` / `find_by_pattern` / `get_code_context` / `find_usage_examples`

#### ドキュメント・推奨 (4)
`generate_documentation` / `recommend_code` / `analyze_impact` / `find_critical_paths`

#### ハイブリッド検索・品質 (4)
`hybrid_search` / `analyze_quality` / `track_evolution` / `find_hotspots`

#### AI コーディング支援 (5)
`get_coding_guidance` / `detect_patterns` / `check_api_compatibility` /
`navigate_code` / `get_call_graph`

**MCP Prompts (3)**: `analyze_codebase` / `explain_entity` / `find_dependencies`
**MCP Resources (1)**: `magatama://graph/stats`

---

## Test Organization

```
packages/<pkg>/tests/
├── domain/              # ドメイン層ユニットテスト
├── application/         # ユースケース・サービステスト
├── infrastructure/      # パーサー・ストレージ・comP Bridge テスト
├── server/ , cli/       # MCP サーバ・CLI テスト（magatama-mcp）
└── e2e/                 # 統合・セキュリティ E2E（magatama-mcp）
```

### Test Guidelines

- **Test-First**: 実装前にテストを記述（Article III）
- **Coverage**: 76%（目標 80%）
- **Naming**: `test_*.py`（pytest）

---

## Naming Conventions

### File Naming (Python)

- **モジュール / パッケージ**: `snake_case.py`（例: `comp_index_reader.py`）
- **テスト**: `test_*.py`
- **クラス**: `PascalCase`（例: `LoadCompIndexUseCase`）

### Variable Naming

- **変数・関数**: `snake_case`
- **定数**: `SCREAMING_SNAKE_CASE`
- **クラス / 型**: `PascalCase`

---

## Deployment Structure

### Deployment Units（独立配布可能）

1. `magatama-core` — 知識グラフエンジン（ライブラリ, PyPI: `magatama-core`）
2. `magatama` — MCP サーバ＋CLI（PyPI: `magatama`、`magatama-core` に依存）

> ⚠️ **Simplicity Gate (Article VII)**: 当面はこの 2 パッケージ構成を維持する。

---

## Version Control

### Commit Message Convention

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `ci`, `build`

---

## Constitutional Compliance

This structure enforces:

- **Article I**: Library-first（`magatama-core` を独立ライブラリとして実装）
- **Article II**: CLI interfaces（`magatama` コマンド）
- **Article III**: Test-First を支えるテスト構成
- **Article VI**: Steering files によるプロジェクトメモリ維持

---

## Changelog

### Version 1.2

- YATA → MAGATAMA、モノレポ構成（`packages/`）に全面更新
- comP Bridge（2 ツール / `comp_index_reader` / `comp_usecase`）を追記
- MCP ツール数を 36 に修正、別プロジェクトのテンプレート残骸を除去

---

**Last Updated**: 2026-01-01
**Maintained By**: MAGATAMA Development Team
