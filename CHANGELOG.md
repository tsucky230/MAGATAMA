# Changelog

All notable changes to MAGATAMA (勾玉) will be documented in this file.

MAGATAMA は [YATA (八咫)](https://github.com/nahisaho/YATA) のフォークです。
**0.5.0 までのリリースは上流 YATA で行われた履歴**であり、当時の記録として原文のまま残しています。
`[Unreleased]` 以降が MAGATAMA としての変更です。

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

#### 外部インデックス連携 (comP Bridge) — 新規MCPツール（34 → 36 Tools）

- **`read_external_graph`** — comP (`e:/dev/comP`) の `.comp/index.db` を MAGATAMA 知識グラフに取り込む
  - `mode="replace"`（デフォルト）: 同一ワークスペースの旧エンティティを削除してから投入
  - `mode="merge"`: 既存グラフに追加投入（同一 ID は上書き）
  - 戻り値: `entities_loaded`, `relationships_loaded`, `entities_removed`, `skipped_edges`, `comp_metadata`

- **`get_external_graph_info`** — comP インデックスの統計情報を確認（ロードなし）
  - ファイル数・ノード数・エッジ数・`last_indexed`・メタデータを返す
  - インデックスの鮮度確認に使用

#### 新規モジュール

- `packages/magatama-core/src/magatama_core/infrastructure/storage/comp_index_reader.py`
  - `CompIndexReader` — SQLite 読み取り専用接続 (WAL + `busy_timeout=5000`)
  - `CompIndexData` — 読み取り結果の集約データクラス
  - `CompIndexNotFoundError`, `resolve_db_path`, `derive_alias`
  - comP `nodes.kind` → `EntityType` / `edges.kind` → `RelationshipType` マッピング
  - 未知の kind はフォールバック（エラーなし）

- `packages/magatama-core/src/magatama_core/application/usecases/comp_usecase.py`
  - `LoadCompIndexUseCase` — グラフへの投入・replace/merge モード制御
  - `LoadCompIndexResult` — 結果サマリー

#### テスト追加

- `packages/magatama-core/tests/infrastructure/test_comp_index_reader.py` — 18 テストケース
- `packages/magatama-core/tests/application/test_comp_usecase.py` — 8 テストケース
- `packages/magatama-mcp/tests/test_protocol.py` — comP Bridge ツールのテストクラス追加

---

## [0.5.0] - 2026-01-01

### 🚀 Full Language Integration Release

24言語パーサーのMCPサーバー完全統合、言語情報ツール追加、ドキュメント整備。

### Added

#### 新規MCPツール（32 → 34 Tools）

- **`list_supported_languages`** - サポートする24言語の一覧を取得
  - 言語ID、名前、対応拡張子、パーサー名を返却
  - 合計言語数・拡張子数のサマリー付き

- **`get_language_for_file`** - ファイル拡張子から言語を判定
  - ファイルパスから対応言語を自動検出
  - 未対応拡張子の場合はサポート拡張子一覧を返却

#### 24言語パーサーMCP統合

すべてのパーサーをMCPサーバーに登録:
- Python, TypeScript, JavaScript, Rust, Go
- Ruby, Java, C#, C++, C
- Objective-C, PHP, Swift, Kotlin, Scala
- Lua, Haskell, Elixir, Julia, SQL
- Groovy, Dart, Zig, YAML

### Changed

- **`magatama info` コマンド修正**
  - `MagatamaMcpServer` から `create_mcp_server()` に変更
  - 実際のMCPツール数を正確に表示（34 Tools）

### Updated

- **README.md / README.en.md**
  - MCP Tools: 32 → 34
  - フレームワーク数: 47 → 26（実際の知識グラフ数）
  - テスト数: 683 (592 magatama-core + 91 magatama-mcp)
  - E2Eテスト: 42 (18 統合 + 24 セキュリティ)
  - カバレッジ: 75.65%

- **AGENTS.md** - Review Gate Prompts (v6.2.0) 追加

- **steering/project.yml** - Review Gate / Traceability 設定追加

### Test Results

- **Total Tests**: 683 passed
- **E2E Tests**: 42 passed (integration: 18, security: 24)
- **Coverage**: 75.65%

---

## [0.4.0] - 2026-01-01

### 🎯 Language & Framework Expansion Release

言語パーサー3種追加、フレームワーク22種追加、知識データベース一括更新スクリプト実装。

### Added

#### 新規言語パーサー（21 → 24言語）

- **C Parser** (`c_parser.py`)
  - tree-sitter-c による C 言語解析
  - struct, enum, function, typedef, include の抽出
  - パラメータ型情報の抽出

- **Zig Parser** (`zig_parser.py`)
  - tree-sitter-zig による Zig 言語解析
  - function, struct, test, import の抽出

- **YAML Parser** (`yaml_parser.py`)
  - tree-sitter-yaml による YAML ファイル解析
  - 階層的 key/value 構造の抽出

#### 新規フレームワーク知識グラフ（27 → 47フレームワーク）

**Phase 1: モダン Web フレームワーク**
- Astro - Meta Framework (Component, Island, Integration)
- Hono - Edge Runtime (Router, Middleware, Context)
- Prisma - TypeScript ORM (Schema, Client, Query)
- tRPC - Type-safe API (Router, Procedure, Query)
- htmx - Hypermedia (Attribute, Swap, Trigger)

**Phase 2: フルスタックフレームワーク**
- SolidJS - UI Framework (Signal, Effect, Component)
- Remix - Full-stack (Loader, Action, Route)
- Drizzle - TypeScript ORM (Schema, Query, Migration)
- Tauri - Desktop App (Command, Window, Plugin)

**Phase 3: 高性能フレームワーク**
- Phoenix - Elixir Web (Controller, LiveView, Channel)
- Fiber - Go Web (App, Route, Handler)
- Axum - Rust Web (Router, Handler, Extension)
- Qwik - Resumable (Component, Signal, QRL)
- Bun - JS Runtime (Server, File, Plugin)

**Phase 4: AI/ML フレームワーク**
- LangChain - AI/LLM (Chain, Agent, Memory, Tool)
- Haystack - AI/NLP (Pipeline, Document Store, Retriever)
- Streamlit - Dashboard (App, Widget, Cache)
- LangGraph - AI/Agent (Graph, Node, Edge, State)

**Phase 5: モバイルフレームワーク**
- SwiftUI - iOS (View, State, Binding, Environment)
- Jetpack Compose - Android (Composable, State, Modifier)
- Expo - React Native (App, Navigation, Component)

**Phase 6: Web フレームワーク追加**
- Actix-web - Rust (既存だが知識グラフ更新)

#### 知識データベース管理スクリプト

- **`scripts/update_knowledge_db.py`** - 一括更新スクリプト
  - 47フレームワークの git pull 一括実行
  - 知識グラフの自動再構築
  - 並列処理対応（`--parallel`オプション）
  - ドライラン対応（`--dry-run`）
  - 選択的更新（`--frameworks`）
  - 欠落リポジトリのクローン（`--clone-missing`）

### Changed

- **プロジェクトバージョン**: 0.3.0 → 0.4.0
- **言語パーサー**: 21 → 24（+3）
- **フレームワーク知識グラフ**: 27 → 47（+20）
- **テスト数**: 658 → 592（一部テスト整理）

### Documentation

- [README.md](README.md) - 言語24、フレームワーク47に更新
- [MAGATAMA_vs_Context7.md](docs/MAGATAMA_vs_Context7.md) - 最新メトリクスに更新
- [KNOWLEDGE_UPDATE_GUIDE.md](docs/KNOWLEDGE_UPDATE_GUIDE.md) - クイックスタートセクション追加
- [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) - プロジェクト背景（MUSUBI, CodeGraph）追加
- [steering/project.yml](steering/project.yml) - メトリクス更新
- [steering/tech.ja.md](steering/tech.ja.md) - 言語リスト更新

### Fixed

- GitHub リポジトリ URL を `https://github.com/nahisaho/YATA` に統一

### Dependencies

- **tree-sitter-c** >= 0.24.0: C 言語パーサー
- **tree-sitter-zig** >= 1.0.0: Zig 言語パーサー
- **tree-sitter-yaml** >= 0.7.0: YAML パーサー

---

## [0.3.0] - 2025-12-31

### 🚀 Context7 Superior Feature Release

Context7を超える高度なAIコーディング支援機能を実装。3フェーズで10の新機能を追加。

### Added

#### Phase 1: ドキュメント生成・コード推奨（Sprint 13）

- **REQ-001: DocumentationGenerationUseCase**
  - JSDoc/docstring形式のドキュメント自動生成
  - パラメータ、戻り値、例外の自動抽出
  - 使用例の自動生成
  - MCP Tool: `generate_documentation`

- **REQ-002: CodeRecommendationUseCase**
  - 知識グラフベースのコード推奨
  - 類似コードパターン検索
  - フレームワークベストプラクティス提案
  - MCP Tool: `recommend_code`

- **REQ-003: DependencyImpactUseCase**
  - 変更影響分析
  - 依存関係グラフの可視化
  - 影響範囲の自動特定
  - MCP Tool: `analyze_impact`

#### Phase 2: ハイブリッド検索・品質分析（Sprint 14）

- **REQ-004: HybridSearchUseCase**
  - キーワード検索＋セマンティック検索の統合
  - TF-IDFベクトル検索
  - 重み付けハイブリッドスコアリング
  - MCP Tool: `hybrid_search`

- **REQ-005: CodeQualityUseCase**
  - 循環的複雑度分析
  - 結合度・凝集度メトリクス
  - コード品質スコアリング
  - 改善提案の自動生成
  - MCP Tool: `analyze_quality`

- **REQ-006: CodeEvolutionUseCase**
  - Git履歴からの変更頻度分析
  - コードホットスポット検出
  - 著者別貢献度分析
  - 変更トレンド可視化
  - MCP Tools: `track_evolution`, `find_hotspots`

#### Phase 3: AIガイダンス・パターン検出（Sprint 15）

- **REQ-007: CodingGuidanceUseCase**
  - AIコーディングガイダンス生成
  - フレームワーク推奨コードスニペット
  - ベストプラクティス提案
  - MCP Tool: `get_coding_guidance`

- **REQ-008: PatternDetectionUseCase**
  - 10種類のデザインパターン自動検出
    - Singleton, Factory Method, Builder
    - Adapter, Decorator, Facade
    - Observer, Strategy, Command, Template Method
  - パターン品質スコアリング
  - MCP Tool: `detect_patterns`

- **REQ-009: APICompatibilityUseCase**
  - APIバージョン互換性チェック
  - 非推奨API検出
  - マイグレーションガイド提供
  - 対応フレームワーク: Django (4.0, 4.2), FastAPI (0.100), React (18.0), Flask (2.0)
  - MCP Tool: `check_api_compatibility`

- **REQ-010: CodeNavigationUseCase**
  - インタラクティブコードナビゲーション
  - 関係性グラフ探索
  - 呼び出しグラフ生成
  - MCP Tools: `navigate_code`, `get_call_graph`

### Changed

- MCP Tools: 19 → 32（13ツール追加）
- テスト数: 568 → 658（90テスト追加）
- フレームワーク知識グラフ: 27種類
- 言語パーサー: 21種類

### Technical Details

- `framework_usecase.py`: 約3500行の新コード追加
- `protocol.py`: Phase 1-3のMCPツール統合
- 新規テストファイル:
  - `test_phase1_usecases.py` (27 tests)
  - `test_phase2_usecases.py` (26 tests)
  - `test_phase3_usecases.py` (37 tests)

### Dependencies

- **GitPython** (optional): REQ-006 CodeEvolutionUseCase用

---

## [0.2.0] - 2025-12-30

### Added

- フレームワーク知識グラフ機能
- 27フレームワークの組み込み知識
- 7つのMCPツール追加

### Frameworks

Python: Django, Flask, FastAPI, Pytest, NumPy, Pandas, SQLAlchemy
JavaScript/TypeScript: React, Vue.js, Angular, Next.js, Express, NestJS, Jest
Rust: Actix-web, Tokio, Serde, Rocket
Go: Gin, Echo, Fiber, GORM
その他: Spring Boot, .NET Core, Rails, Laravel

---

## [0.1.0] - 2025-12-20

### Added

- 初期リリース
- 21言語対応パーサー
- 基本MCPツール（8ツール）
- 知識グラフエンジン
- CLI インターフェース

---

**MAGATAMA** (勾玉) - AI Coding Support MCP Server（[YATA (八咫)](https://github.com/nahisaho/YATA) のフォーク）
