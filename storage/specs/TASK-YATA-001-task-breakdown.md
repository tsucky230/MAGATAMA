# YATA タスク分解書

**Project**: YATA (八咫)
**Document ID**: TASK-YATA-001
**Version**: 1.0
**Created**: 2025-12-31
**Status**: Approved
**Author**: MUSUBI SDD

---

## 1. 概要

本文書は、YATA MCP Serverの実装タスクを分解し、スプリント計画を定義する。MUSUBI SDD Article V（トレーサビリティ）に準拠し、各タスクは要件ID・設計書と紐付けられている。

### 1.1 プロジェクト構成（Article VII準拠）

3プロジェクト以下の制約を遵守：

| プロジェクト | 説明 | 独立デプロイ |
|-------------|------|-------------|
| `yata-core` | 知識グラフエンジン（ライブラリ） | ✅ pip install |
| `yata-mcp` | MCP Server（アプリケーション） | ✅ CLI/Server |

**※ 2プロジェクト構成でArticle VII制約をクリア**

---

## 2. スプリント計画

### 2.1 スプリント概要

| Sprint | 期間 | Focus | 成果物 |
|--------|------|-------|--------|
| Sprint 1 | Week 1-2 | 基盤構築 | プロジェクト構造、コアドメインモデル |
| Sprint 2 | Week 3-4 | パーサー実装 | Tree-sitter統合、5言語対応 |
| Sprint 3 | Week 5-6 | グラフエンジン | NetworkX統合、ストレージ層 |
| Sprint 4 | Week 7-8 | MCP Server | 14 Tools、3 Resources、4 Prompts |
| Sprint 5 | Week 9-10 | CLI & 統合 | CLI実装、E2Eテスト |
| Sprint 6 | Week 11-12 | 品質・リリース | パフォーマンス最適化、ドキュメント |

---

## 3. Sprint 1: 基盤構築（Week 1-2）

### 3.1 タスク一覧

#### TASK-001: プロジェクト構造セットアップ

**説明**: Clean Architecture準拠のディレクトリ構造を作成

**Requirements Coverage**:
- Article I (Library-First)
- Article VI (Project Memory)

**Acceptance Criteria**:
- [ ] monorepo構造（`yata-core/`, `yata-mcp/`）
- [ ] pyproject.toml（両プロジェクト）
- [ ] 開発環境設定（uv, ruff, mypy, pytest）
- [ ] CI/CD設定（GitHub Actions）

**Dependencies**: なし
**Estimated**: 4h
**Priority**: P0

```
yata/
├── yata-core/                    # ライブラリ（Article I）
│   ├── src/yata_core/
│   │   ├── domain/              # Domain Layer
│   │   │   ├── entities/
│   │   │   ├── value_objects/
│   │   │   └── repositories/
│   │   ├── application/         # Application Layer
│   │   │   └── services/
│   │   ├── infrastructure/      # Infrastructure Layer
│   │   │   ├── parsers/
│   │   │   ├── storage/
│   │   │   └── github/
│   │   └── __init__.py
│   ├── tests/
│   └── pyproject.toml
├── yata-mcp/                     # アプリケーション
│   ├── src/yata_mcp/
│   │   ├── server/
│   │   ├── cli/
│   │   └── __init__.py
│   ├── tests/
│   └── pyproject.toml
└── pyproject.toml               # ワークスペース
```

---

#### TASK-002: ドメインエンティティ実装

**説明**: 知識グラフのコアエンティティを定義

**Requirements Coverage**:
- REQ-KGC-001 (エンティティ抽出)
- REQ-KGC-002 (関係性抽出)

**Design Reference**: [DES-YATA-003](DES-YATA-003-c4-component.md) Section 3

**Acceptance Criteria**:
- [ ] `Entity`基底クラス（id, name, type, location）
- [ ] `ClassEntity`, `FunctionEntity`, `ModuleEntity`
- [ ] `Relationship`型（継承、呼び出し、依存等）
- [ ] `Library`集約ルート
- [ ] pydantic Modelでバリデーション

**Dependencies**: TASK-001
**Estimated**: 6h
**Priority**: P0

**Test First (Article III)**:
```python
# tests/domain/test_entities.py - RED phase first
def test_entity_creation():
    entity = FunctionEntity(
        id="func_001",
        name="calculate",
        location=Location(file="main.py", line=10)
    )
    assert entity.type == EntityType.FUNCTION
```

---

#### TASK-003: リポジトリインターフェース定義

**説明**: Ports & Adapters パターンでリポジトリ契約を定義

**Requirements Coverage**:
- REQ-KGC-003 (グラフストレージ)
- Article VIII (Anti-Abstraction: フレームワーク直接使用)

**Design Reference**: [ADR-001](ADR-001-clean-architecture.md)

**Acceptance Criteria**:
- [ ] `LibraryRepository` Protocol
- [ ] `EntityRepository` Protocol
- [ ] `GraphRepository` Protocol
- [ ] 型ヒント完備

**Dependencies**: TASK-002
**Estimated**: 3h
**Priority**: P0

```python
# domain/repositories/library_repository.py
from typing import Protocol

class LibraryRepository(Protocol):
    def save(self, library: Library) -> str: ...
    def find_by_id(self, library_id: str) -> Library | None: ...
    def find_by_name(self, name: str) -> list[Library]: ...
    def list_all(self) -> list[Library]: ...
    def delete(self, library_id: str) -> bool: ...
```

---

#### TASK-004: 値オブジェクト実装

**説明**: イミュータブルな値オブジェクトを定義

**Requirements Coverage**:
- REQ-KGC-001 (ファイルパス、行番号)
- REQ-KGC-005 (バージョン管理)

**Acceptance Criteria**:
- [ ] `Location`（file, line, column）
- [ ] `Version`（semver準拠）
- [ ] `EntityId`（型安全なID）
- [ ] `LibraryId`

**Dependencies**: TASK-001
**Estimated**: 2h
**Priority**: P1

---

#### TASK-005: エラー型定義

**説明**: YATA固有のエラーコード体系を実装

**Requirements Coverage**:
- REQ-MCP-008 (エラー応答形式)
- REQ-NFR-004 (エラーハンドリング)

**Design Reference**: [DES-YATA-005](DES-YATA-005-error-codes.md)

**Acceptance Criteria**:
- [ ] `YataError`基底クラス
- [ ] エラーカテゴリ別サブクラス（Library, Parser, Storage, GitHub, Query）
- [ ] エラーコード定数（1000-5999）
- [ ] MCP準拠フォーマット変換

**Dependencies**: TASK-001
**Estimated**: 3h
**Priority**: P0

---

#### TASK-006: 設定管理実装

**説明**: TOML設定ファイルと環境変数の統合

**Requirements Coverage**:
- REQ-NFR-007 (ローカル実行)
- REQ-KGC-007 (GitHub認証)

**Design Reference**: [DES-YATA-006](DES-YATA-006-configuration.md)

**Acceptance Criteria**:
- [ ] `~/.yata/config.toml`読み込み
- [ ] 環境変数オーバーライド
- [ ] pydantic-settings統合
- [ ] デフォルト値設定

**Dependencies**: TASK-001
**Estimated**: 3h
**Priority**: P1

---

### 3.2 Sprint 1 サマリー

| Task ID | Title | Est | Dep | Priority | REQ Coverage |
|---------|-------|-----|-----|----------|--------------|
| TASK-001 | プロジェクト構造 | 4h | - | P0 | Art.I, Art.VI |
| TASK-002 | ドメインエンティティ | 6h | 001 | P0 | KGC-001,002 |
| TASK-003 | リポジトリIF | 3h | 002 | P0 | KGC-003 |
| TASK-004 | 値オブジェクト | 2h | 001 | P1 | KGC-001,005 |
| TASK-005 | エラー型 | 3h | 001 | P0 | MCP-008, NFR-004 |
| TASK-006 | 設定管理 | 3h | 001 | P1 | NFR-007, KGC-007 |

**Sprint 1 合計**: 21h（約3日）

---

## 4. Sprint 2: パーサー実装（Week 3-4）

### 4.1 タスク一覧

#### TASK-007: Tree-sitter基盤セットアップ

**説明**: Tree-sitterのPythonバインディング統合

**Requirements Coverage**:
- REQ-KGC-001 (AST解析)
- REQ-NFR-008 (言語追加拡張性)

**Design Reference**: [ADR-003](ADR-003-tree-sitter-parser.md)

**Acceptance Criteria**:
- [ ] tree-sitter ^0.21.0 インストール
- [ ] 言語パーサー（python, typescript, javascript, rust, go）
- [ ] `LanguageParser` Protocol定義
- [ ] パーサーレジストリ実装

**Dependencies**: TASK-001
**Estimated**: 4h
**Priority**: P0

---

#### TASK-008: Python パーサー実装

**説明**: Pythonソースコードのエンティティ抽出

**Requirements Coverage**:
- REQ-LANG-001 (Python対応)

**Acceptance Criteria**:
- [ ] クラス抽出（継承含む）
- [ ] 関数抽出（引数、戻り値型）
- [ ] 型ヒント解析
- [ ] デコレータ認識
- [ ] `__init__.py`エクスポート認識

**Dependencies**: TASK-007
**Estimated**: 8h
**Priority**: P0

**Test First**:
```python
def test_python_parser_extracts_class():
    code = '''
class Calculator:
    def add(self, a: int, b: int) -> int:
        return a + b
    '''
    entities = python_parser.parse(code)
    assert len(entities) == 2  # class + method
    assert entities[0].type == EntityType.CLASS
```

---

#### TASK-009: TypeScript パーサー実装

**説明**: TypeScriptソースコードのエンティティ抽出

**Requirements Coverage**:
- REQ-LANG-002 (TypeScript対応)

**Acceptance Criteria**:
- [ ] クラス定義抽出
- [ ] インターフェース定義抽出
- [ ] 型エイリアス（type）抽出
- [ ] ジェネリクス認識
- [ ] export/import認識

**Dependencies**: TASK-007
**Estimated**: 8h
**Priority**: P0

---

#### TASK-010: JavaScript パーサー実装

**説明**: JavaScriptソースコードのエンティティ抽出

**Requirements Coverage**:
- REQ-LANG-003 (JavaScript対応)

**Acceptance Criteria**:
- [ ] ES6+クラス抽出
- [ ] アロー関数認識
- [ ] JSDoc型情報抽出
- [ ] CommonJS/ESMモジュール認識

**Dependencies**: TASK-007
**Estimated**: 6h
**Priority**: P0

---

#### TASK-011: Rust パーサー実装 ✅ DONE

**説明**: Rustソースコードのエンティティ抽出

**Requirements Coverage**:
- REQ-LANG-004 (Rust対応)

**Acceptance Criteria**:
- [x] struct/enum定義抽出
- [x] trait定義抽出
- [x] impl block抽出
- [x] ジェネリクス/ライフタイム認識
- [x] pub/mod構造認識

**Dependencies**: TASK-007
**Estimated**: 8h
**Priority**: P1
**Completed**: Sprint 9

---

#### TASK-012: Go パーサー実装 ✅ DONE

**説明**: Goソースコードのエンティティ抽出

**Requirements Coverage**:
- REQ-LANG-005 (Go対応)

**Acceptance Criteria**:
- [x] struct定義抽出
- [x] interface定義抽出
- [x] メソッド（レシーバー付き）抽出
- [x] パッケージ構造認識

**Dependencies**: TASK-007
**Estimated**: 6h
**Priority**: P1
**Completed**: Sprint 9

---

#### TASK-013: 関係性抽出エンジン

**説明**: エンティティ間の関係性を検出

**Requirements Coverage**:
- REQ-KGC-002 (関係性抽出)

**Acceptance Criteria**:
- [ ] 継承関係（extends, inherits）
- [ ] インターフェース実装関係
- [ ] 関数/メソッド呼び出し関係
- [ ] インポート/依存関係
- [ ] 型参照関係

**Dependencies**: TASK-008, 009, 010, 011, 012
**Estimated**: 10h
**Priority**: P0

---

### 4.2 Sprint 2 サマリー

| Task ID | Title | Est | Dep | Priority | REQ Coverage |
|---------|-------|-----|-----|----------|--------------|
| TASK-007 | Tree-sitter基盤 | 4h | 001 | P0 | KGC-001, NFR-008 |
| TASK-008 | Pythonパーサー | 8h | 007 | P0 | LANG-001 |
| TASK-009 | TypeScriptパーサー | 8h | 007 | P0 | LANG-002 |
| TASK-010 | JavaScriptパーサー | 6h | 007 | P0 | LANG-003 |
| TASK-011 | Rustパーサー | 8h | 007 | P1 | LANG-004 |
| TASK-012 | Goパーサー | 6h | 007 | P1 | LANG-005 |
| TASK-013 | 関係性抽出 | 10h | 008-012 | P0 | KGC-002 |

**Sprint 2 合計**: 50h（約6日）

---

## 5. Sprint 3: グラフエンジン（Week 5-6）

### 5.1 タスク一覧

#### TASK-014: NetworkXグラフ統合

**説明**: インメモリグラフ構造の実装

**Requirements Coverage**:
- REQ-KGC-003 (グラフストレージ)

**Design Reference**: [ADR-004](ADR-004-graph-storage.md)

**Acceptance Criteria**:
- [ ] NetworkX DiGraph使用
- [ ] ノード（Entity）追加/削除/更新
- [ ] エッジ（Relationship）追加/削除
- [ ] グラフクエリメソッド

**Dependencies**: TASK-002, 003
**Estimated**: 6h
**Priority**: P0

---

#### TASK-015: SQLiteストレージ実装 ✅ DONE

**説明**: グラフデータの永続化

**Requirements Coverage**:
- REQ-KGC-003 (永続化)

**Acceptance Criteria**:
- [x] SQLiteデータベーススキーマ
- [x] NetworkX ↔ SQLite変換
- [x] インクリメンタル更新
- [x] JSONエクスポート

**Dependencies**: TASK-014
**Estimated**: 8h
**Priority**: P0
**Completed**: Sprint 10

---

#### TASK-016: バージョン管理機能

**説明**: ライブラリバージョン別グラフ管理

**Requirements Coverage**:
- REQ-KGC-005 (バージョン管理)

**Acceptance Criteria**:
- [ ] semverバージョン区別
- [ ] 複数バージョン同時保持
- [ ] バージョン間差分取得
- [ ] 古いバージョン削除

**Dependencies**: TASK-015
**Estimated**: 6h
**Priority**: P1

---

#### TASK-017: コミュニティ検出実装

**説明**: GraphRAGのためのモジュールクラスタリング

**Requirements Coverage**:
- REQ-KGC-006 (コミュニティ検出)

**Acceptance Criteria**:
- [ ] Louvainアルゴリズム実装
- [ ] コミュニティサマリー生成
- [ ] 階層構造サポート
- [ ] コミュニティ単位クエリ

**Dependencies**: TASK-014
**Estimated**: 8h
**Priority**: P2

---

#### TASK-018: ドキュメント統合機能

**説明**: Markdown/RSTドキュメントの解析と統合

**Requirements Coverage**:
- REQ-KGC-004 (ドキュメント統合)

**Acceptance Criteria**:
- [ ] Markdownセクション/コードブロック抽出
- [ ] RSTセクション/コードブロック抽出
- [ ] コードエンティティ関連付け
- [ ] バージョン情報付与

**Dependencies**: TASK-014
**Estimated**: 6h
**Priority**: P2

---

#### TASK-019: GitHub連携機能

**説明**: GitHubリポジトリの取得とメタデータ抽出

**Requirements Coverage**:
- REQ-KGC-007 (GitHub取得)
- REQ-KGC-008 (メタデータ抽出)

**Acceptance Criteria**:
- [ ] `git clone --depth 1`サポート
- [ ] タグ/ブランチ/コミット指定
- [ ] GitHub API連携（オプション）
- [ ] レートリミット考慮
- [ ] PAT認証サポート
- [ ] メタデータ抽出（package.json, pyproject.toml等）

**Dependencies**: TASK-006
**Estimated**: 10h
**Priority**: P0

---

### 5.2 Sprint 3 サマリー

| Task ID | Title | Est | Dep | Priority | REQ Coverage |
|---------|-------|-----|-----|----------|--------------|
| TASK-014 | NetworkX統合 | 6h | 002,003 | P0 | KGC-003 |
| TASK-015 | SQLiteストレージ | 8h | 014 | P0 | KGC-003 |
| TASK-016 | バージョン管理 | 6h | 015 | P1 | KGC-005 |
| TASK-017 | コミュニティ検出 | 8h | 014 | P2 | KGC-006 |
| TASK-018 | ドキュメント統合 | 6h | 014 | P2 | KGC-004 |
| TASK-019 | GitHub連携 | 10h | 006 | P0 | KGC-007,008 |

**Sprint 3 合計**: 44h（約5.5日）

---

## 6. Sprint 4: MCP Server（Week 7-8）

### 6.1 タスク一覧

#### TASK-020: MCP Server基盤

**説明**: MCP Python SDKを使用したサーバー初期化

**Requirements Coverage**:
- REQ-MCP-001 (MCPプロトコル準拠)

**Design Reference**: [ADR-002](ADR-002-mcp-protocol.md), [DES-YATA-008](DES-YATA-008-deployment.md)

**Acceptance Criteria**:
- [ ] MCP SDK ^1.0.0 統合
- [ ] stdioトランスポート
- [ ] SSEトランスポート
- [ ] 正しいJSONスキーマ

**Dependencies**: TASK-001
**Estimated**: 6h
**Priority**: P0

---

#### TASK-021: Library Discovery Tools実装

**説明**: `resolve_library`, `list_libraries`ツール

**Requirements Coverage**:
- REQ-MCP-002 (ライブラリ検索)

**Design Reference**: [DES-YATA-003](DES-YATA-003-c4-component.md) Section 2.1

**Acceptance Criteria**:
- [ ] `resolve_library` - 部分一致検索
- [ ] `list_libraries` - 全ライブラリ一覧
- [ ] 類似度スコアランキング
- [ ] max_resultsパラメータ

**Dependencies**: TASK-020, 015
**Estimated**: 4h
**Priority**: P0

---

#### TASK-022: Documentation Tools実装

**説明**: `query_docs`, `get_api_reference`ツール

**Requirements Coverage**:
- REQ-MCP-003 (ドキュメントクエリ)
- REQ-MCP-004 (コード構造クエリ)

**Acceptance Criteria**:
- [ ] `query_docs` - キーワードベース検索
- [ ] `get_api_reference` - エンティティ詳細
- [ ] バージョン指定
- [ ] max_tokensパラメータ

**Dependencies**: TASK-020, 015
**Estimated**: 6h
**Priority**: P0

---

#### TASK-023: Code Structure Tools実装

**説明**: `query_code_structure`, `find_*`ツール群

**Requirements Coverage**:
- REQ-MCP-004 (コード構造)
- REQ-MCP-005 (グラフ探索)

**Acceptance Criteria**:
- [ ] `query_code_structure`
- [ ] `find_dependencies`
- [ ] `find_callers`
- [ ] `find_implementations`
- [ ] 探索深度指定

**Dependencies**: TASK-020, 014
**Estimated**: 8h
**Priority**: P0

---

#### TASK-024: GraphRAG Tools実装

**説明**: `global_search`, `local_search`ツール

**Requirements Coverage**:
- REQ-KGC-006 (コミュニティベース検索)

**Acceptance Criteria**:
- [ ] `global_search` - コミュニティ横断検索
- [ ] `local_search` - エンティティ起点検索
- [ ] max_resultsパラメータ

**Dependencies**: TASK-020, 017
**Estimated**: 6h
**Priority**: P1

---

#### TASK-025: Management Tools実装

**説明**: `index_library`, `update_library`, `remove_library`, `get_stats`

**Requirements Coverage**:
- REQ-CLI-001 (インデックス作成)

**Acceptance Criteria**:
- [ ] `index_library` - 新規インデックス
- [ ] `update_library` - インクリメンタル更新
- [ ] `remove_library` - 削除
- [ ] `get_stats` - 統計情報

**Dependencies**: TASK-020, 015
**Estimated**: 6h
**Priority**: P0

---

#### TASK-026: MCP Resources実装

**説明**: 3つのMCPリソースを実装

**Requirements Coverage**:
- REQ-MCP-006 (MCPリソース)

**Acceptance Criteria**:
- [ ] `yata://libraries` - ライブラリ一覧
- [ ] `yata://entities/{id}` - エンティティ詳細
- [ ] `yata://stats` - グラフ統計

**Dependencies**: TASK-020, 015
**Estimated**: 4h
**Priority**: P1

---

#### TASK-027: MCP Prompts実装

**説明**: 4つのプロンプトテンプレート

**Requirements Coverage**:
- REQ-MCP-007 (MCPプロンプト)

**Acceptance Criteria**:
- [ ] `implement_with_library`
- [ ] `explain_api`
- [ ] `migrate_version`
- [ ] `best_practices`

**Dependencies**: TASK-020
**Estimated**: 4h
**Priority**: P2

---

#### TASK-028: MCPエラーハンドリング

**説明**: MCP仕様準拠のエラー応答

**Requirements Coverage**:
- REQ-MCP-008 (エラー応答形式)

**Design Reference**: [DES-YATA-005](DES-YATA-005-error-codes.md)

**Acceptance Criteria**:
- [ ] MCP標準エラーコード（-32600〜-32603）
- [ ] YATA固有エラーコード（1000-5999）
- [ ] 人間可読メッセージ
- [ ] dataフィールド詳細情報

**Dependencies**: TASK-005, 020
**Estimated**: 4h
**Priority**: P0

---

### 6.2 Sprint 4 サマリー

| Task ID | Title | Est | Dep | Priority | REQ Coverage |
|---------|-------|-----|-----|----------|--------------|
| TASK-020 | MCP Server基盤 | 6h | 001 | P0 | MCP-001 |
| TASK-021 | Library Tools | 4h | 020,015 | P0 | MCP-002 |
| TASK-022 | Doc Tools | 6h | 020,015 | P0 | MCP-003,004 |
| TASK-023 | Structure Tools | 8h | 020,014 | P0 | MCP-004,005 |
| TASK-024 | GraphRAG Tools | 6h | 020,017 | P1 | KGC-006 |
| TASK-025 | Management Tools | 6h | 020,015 | P0 | CLI-001 |
| TASK-026 | MCP Resources | 4h | 020,015 | P1 | MCP-006 |
| TASK-027 | MCP Prompts | 4h | 020 | P2 | MCP-007 |
| TASK-028 | Error Handling | 4h | 005,020 | P0 | MCP-008 |

**Sprint 4 合計**: 48h（約6日）

---

## 7. Sprint 5: CLI & 統合（Week 9-10）

### 7.1 タスク一覧

#### TASK-029: CLI基盤（click）

**説明**: clickを使用したCLIフレームワーク構築

**Requirements Coverage**:
- Article II (CLI Interface Mandate)
- REQ-CLI-005 (ヘルプ表示)

**Acceptance Criteria**:
- [ ] click ^8.1.0 統合
- [ ] `--help`フラグ全コマンド
- [ ] 一貫した引数パターン
- [ ] 終了コード規約（0=成功）

**Dependencies**: TASK-001
**Estimated**: 4h
**Priority**: P0

---

#### TASK-030: `yata index`コマンド

**説明**: ライブラリインデックス作成CLI

**Requirements Coverage**:
- REQ-CLI-001 (インデックス作成)

**Design Reference**: [DES-YATA-007](DES-YATA-007-sequence-diagrams.md) Section 2.1

**Acceptance Criteria**:
- [ ] ローカルパス指定
- [ ] GitHubリポジトリURL指定
- [ ] `--version`, `--tag`, `--branch`オプション
- [ ] `--token`オプション（GitHub PAT）
- [ ] プログレスバー表示
- [ ] 完了時統計情報

**Dependencies**: TASK-029, 019, 015
**Estimated**: 6h
**Priority**: P0

---

#### TASK-031: `yata serve`コマンド

**説明**: MCPサーバー起動CLI

**Requirements Coverage**:
- REQ-CLI-002 (サーバー起動)

**Acceptance Criteria**:
- [ ] stdioモード起動
- [ ] SSEモード起動（`--port`）
- [ ] 知識グラフ指定
- [ ] 起動メッセージ表示

**Dependencies**: TASK-029, 020
**Estimated**: 4h
**Priority**: P0

---

#### TASK-032: `yata query`コマンド

**説明**: CLIからのクエリ実行

**Requirements Coverage**:
- REQ-CLI-003 (クエリ実行)

**Acceptance Criteria**:
- [ ] 自然言語クエリ入力
- [ ] JSON形式出力
- [ ] 人間可読形式出力
- [ ] `--max-results`オプション

**Dependencies**: TASK-029, 022, 023
**Estimated**: 4h
**Priority**: P1

---

#### TASK-033: `yata stats`コマンド

**説明**: 統計情報表示CLI

**Requirements Coverage**:
- REQ-CLI-004 (統計情報)

**Acceptance Criteria**:
- [ ] 登録ライブラリ数
- [ ] エンティティ数（種類別）
- [ ] 関係性数
- [ ] ストレージサイズ

**Dependencies**: TASK-029, 025
**Estimated**: 2h
**Priority**: P2

---

#### TASK-034: `yata watch`コマンド

**説明**: ファイル監視・自動インデックス

**Requirements Coverage**:
- REQ-CLI-006 (ウォッチモード)

**Acceptance Criteria**:
- [ ] ファイル変更検出（作成/更新/削除）
- [ ] デバウンス設定（デフォルト1秒）
- [ ] インクリメンタル再インデックス
- [ ] ログ出力
- [ ] Ctrl+C正常終了

**Dependencies**: TASK-029, 025
**Estimated**: 6h
**Priority**: P1

---

#### TASK-035: 構造化ログ実装

**説明**: structlogによるログ出力

**Requirements Coverage**:
- REQ-NFR-009 (ログ出力)

**Acceptance Criteria**:
- [ ] JSON形式構造化ログ
- [ ] ログレベル設定
- [ ] ファイル/コンソール出力選択
- [ ] リクエストID/コリレーションID
- [ ] パフォーマンス < 1ms

**Dependencies**: TASK-001
**Estimated**: 4h
**Priority**: P1

---

#### TASK-036: E2E統合テスト

**説明**: 実サービスを使用した統合テスト

**Requirements Coverage**:
- Article IX (Integration-First Testing)
- REQ-MCP-001 (AI Tool接続テスト)

**Design Reference**: [DES-YATA-004](DES-YATA-004-test-strategy.md)

**Acceptance Criteria**:
- [ ] Claude Desktop接続テスト
- [ ] GitHub Copilot接続テスト（可能な範囲）
- [ ] 実OSSライブラリ（requests等）インデックステスト
- [ ] E2Eシナリオ（index → query → result）

**Dependencies**: 全MCP/CLI実装タスク
**Estimated**: 12h
**Priority**: P0

---

### 7.2 Sprint 5 サマリー

| Task ID | Title | Est | Dep | Priority | REQ Coverage |
|---------|-------|-----|-----|----------|--------------|
| TASK-029 | CLI基盤 | 4h | 001 | P0 | Art.II, CLI-005 |
| TASK-030 | index cmd | 6h | 029,019,015 | P0 | CLI-001 |
| TASK-031 | serve cmd | 4h | 029,020 | P0 | CLI-002 |
| TASK-032 | query cmd | 4h | 029,022,023 | P1 | CLI-003 |
| TASK-033 | stats cmd | 2h | 029,025 | P2 | CLI-004 |
| TASK-034 | watch cmd | 6h | 029,025 | P1 | CLI-006 |
| TASK-035 | 構造化ログ | 4h | 001 | P1 | NFR-009 |
| TASK-036 | E2Eテスト | 12h | all | P0 | Art.IX, MCP-001 |

**Sprint 5 合計**: 42h（約5日）

---

## 8. Sprint 6: 品質・リリース（Week 11-12）

### 8.1 タスク一覧

#### TASK-037: パフォーマンス最適化

**説明**: NFR要件のパフォーマンス達成

**Requirements Coverage**:
- REQ-NFR-001 (インデックス速度)
- REQ-NFR-002 (クエリ応答時間)
- REQ-NFR-003 (メモリ使用量)
- REQ-NFR-006 (起動時間)

**Acceptance Criteria**:
- [ ] インデックス: 100K行/30秒以下
- [ ] クエリ応答: 平均200ms、95%ile 500ms
- [ ] メモリ: 起動100MB、運用500MB以下
- [ ] 起動時間: 2秒以下
- [ ] ベンチマークスイート作成

**Dependencies**: Sprint 1-5完了
**Estimated**: 12h
**Priority**: P0

---

#### TASK-038: データ整合性検証

**説明**: グラフデータの整合性保証

**Requirements Coverage**:
- REQ-NFR-005 (データ整合性)

**Acceptance Criteria**:
- [ ] トランザクション的更新
- [ ] 孤立ノード/エッジ検出
- [ ] グラフ検証コマンド
- [ ] 自動修復機能（オプション）

**Dependencies**: TASK-015
**Estimated**: 6h
**Priority**: P1

---

#### TASK-039: セキュリティ検証

**説明**: ローカル実行・データ保護の検証

**Requirements Coverage**:
- REQ-NFR-007 (ローカル実行)

**Acceptance Criteria**:
- [ ] ネットワークアクセス監査
- [ ] 外部送信なしの確認
- [ ] オフライン動作テスト
- [ ] テレメトリ無効化確認

**Dependencies**: 全実装タスク
**Estimated**: 4h
**Priority**: P0

---

#### TASK-040: ユーザードキュメント作成

**説明**: READMEおよびユーザーガイド

**Requirements Coverage**:
- 運用ドキュメント

**Acceptance Criteria**:
- [ ] README.md（インストール、クイックスタート）
- [ ] CLI Reference
- [ ] MCP Tools Reference
- [ ] AI Tool設定ガイド（Claude, Copilot, Cursor）
- [ ] トラブルシューティング

**Dependencies**: Sprint 1-5完了
**Estimated**: 8h
**Priority**: P0

---

#### TASK-041: PyPIパッケージング

**説明**: pip installable パッケージ作成

**Requirements Coverage**:
- Article I (独立デプロイ可能)

**Acceptance Criteria**:
- [ ] yata-core パッケージ
- [ ] yata-mcp パッケージ（依存: yata-core）
- [ ] PyPI公開設定
- [ ] GitHub Releases設定

**Dependencies**: 全タスク完了
**Estimated**: 4h
**Priority**: P0

---

#### TASK-042: CI/CDパイプライン

**説明**: 自動テスト・リリースパイプライン

**Requirements Coverage**:
- Article III (テスト自動化)
- Article IX (統合テスト)

**Acceptance Criteria**:
- [ ] GitHub Actions: lint, test, coverage
- [ ] カバレッジ80%ゲート
- [ ] 自動リリース（タグベース）
- [ ] Docker イメージビルド（オプション）

**Dependencies**: TASK-036
**Estimated**: 6h
**Priority**: P0

---

### 8.2 Sprint 6 サマリー

| Task ID | Title | Est | Dep | Priority | REQ Coverage |
|---------|-------|-----|-----|----------|--------------|
| TASK-037 | パフォーマンス最適化 | 12h | S1-5 | P0 | NFR-001,002,003,006 |
| TASK-038 | データ整合性 | 6h | 015 | P1 | NFR-005 |
| TASK-039 | セキュリティ検証 | 4h | all | P0 | NFR-007 |
| TASK-040 | ドキュメント | 8h | S1-5 | P0 | - |
| TASK-041 | PyPIパッケージ | 4h | all | P0 | Art.I |
| TASK-042 | CI/CD | 6h | 036 | P0 | Art.III, IX |

**Sprint 6 合計**: 40h（約5日）

---

## 9. 全体サマリー

### 9.1 タスク統計

| Sprint | Tasks | 合計時間 | P0 Tasks | P1 Tasks | P2 Tasks |
|--------|-------|----------|----------|----------|----------|
| Sprint 1 | 6 | 21h | 4 | 2 | 0 |
| Sprint 2 | 7 | 50h | 5 | 2 | 0 |
| Sprint 3 | 6 | 44h | 3 | 1 | 2 |
| Sprint 4 | 9 | 48h | 6 | 2 | 1 |
| Sprint 5 | 8 | 42h | 4 | 3 | 1 |
| Sprint 6 | 6 | 40h | 5 | 1 | 0 |
| **Total** | **42** | **245h** | **27** | **11** | **4** |

### 9.2 要件カバレッジ

| カテゴリ | 要件数 | カバー済みタスク |
|----------|--------|------------------|
| KGC (知識グラフ) | 8 | TASK-002,007-013,014-019 |
| MCP | 8 | TASK-020-028 |
| CLI | 6 | TASK-029-034 |
| LANG | 5 | TASK-008-012 |
| NFR | 9 | TASK-035-042 |
| **Total** | **36** | **100%** |

### 9.3 Constitution準拠

| Article | 説明 | 実装タスク |
|---------|------|------------|
| I | Library-First | TASK-001 (yata-core分離) |
| II | CLI Interface | TASK-029-034 |
| III | Test-First | 全タスク（TDDサイクル） |
| IV | EARS Format | REQ-YATA-001（完了済み） |
| V | Traceability | 本文書（タスク-要件マッピング） |
| VI | Project Memory | steering/ 参照 |
| VII | Simplicity Gate | 2プロジェクト構成 |
| VIII | Anti-Abstraction | フレームワーク直接使用 |
| IX | Integration Testing | TASK-036 |

---

## 10. リスクと対策

| リスク | 影響度 | 発生確率 | 対策 |
|--------|--------|----------|------|
| Tree-sitter言語サポート不足 | 高 | 低 | 言語追加はプラグイン形式で後から対応 |
| MCP SDK破壊的変更 | 高 | 低 | バージョン固定、変更監視 |
| パフォーマンス未達 | 中 | 中 | Sprint 6で最適化、必要に応じ追加スプリント |
| GitHub API レートリミット | 低 | 中 | キャッシュ、認証トークン必須化 |

---

## 11. 変更履歴

| バージョン | 日付 | 著者 | 変更内容 |
|------------|------|------|----------|
| 1.0 | 2025-12-31 | MUSUBI SDD | 初版作成 |

---

*Generated by MUSUBI SDD - Task Breakdown Phase*
