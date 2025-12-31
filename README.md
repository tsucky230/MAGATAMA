# YATA (八咫) - AI Coding Support MCP Server

[![CI](https://github.com/nahisaho/YATA/workflows/CI/badge.svg)](https://github.com/nahisaho/YATA/actions)
[![Coverage](https://codecov.io/gh/nahisaho/YATA/branch/main/graph/badge.svg)](https://codecov.io/gh/nahisaho/YATA)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**YATA** (八咫 - やた) は、AI コーディング支援のための知識グラフ MCP Server です。

ライブラリのソースコードを解析し、知識グラフを構築することで、Claude Desktop、GitHub Copilot、Cursor などの AI ツールに正確なコンテキストを提供します。

## ✨ 特徴

- 🔍 **コード解析**: Tree-sitter による高速な AST 解析（24言語対応）
- 🕸️ **知識グラフ**: NetworkX によるエンティティ・関係性グラフ
- 🔗 **関係性検出**: CALLS/IMPORTS/INHERITS/CONTAINS 関係の自動検出
- 🤖 **MCP 準拠**: Model Context Protocol 完全対応（32 Tools, 3 Prompts, 1 Resource）
- 📚 **フレームワーク知識**: 47フレームワークの組み込み知識グラフ
- 🔎 **ハイブリッド検索**: キーワード＋セマンティック統合検索
- 📝 **ドキュメント生成**: JSDoc/docstring 自動生成
- 🎯 **パターン検出**: 10種類のデザインパターン自動検出
- 🔄 **互換性チェック**: API バージョン互換性分析
- 📈 **品質分析**: 循環的複雑度・結合度・凝集度メトリクス
- 📊 **進化追跡**: Git 履歴からコードホットスポット分析
- 💾 **永続化**: JSON/SQLite への保存/読み込み
- 🔒 **プライバシー**: 完全ローカル実行（データ外部送信なし）

## 🚀 クイックスタート

### インストール

```bash
# リポジトリをクローン
git clone https://github.com/nahisaho/YATA.git
cd yata

# uv で依存関係をインストール（推奨）
uv sync --all-packages
```

### 基本的な使い方

```bash
# ファイルを解析
yata parse path/to/file.py

# ディレクトリを解析
yata parse path/to/project --pattern "**/*.py" --pattern "**/*.ts"

# MCP サーバーを起動（stdio モード）
yata serve

# MCP サーバーを起動（SSE モード）
yata serve --transport sse --port 8080

# サーバー情報を表示
yata info

# エンティティを検索
yata query "parse" --type function

# 統計情報を表示
yata stats --graph graph.json

# グラフの整合性を検証
yata validate --graph graph.json --repair

# ディレクトリを監視
yata watch ./src --output graph.json

# パフォーマンス計測
yata benchmark ./src

# 知識データベースを一括更新（47フレームワーク）
python scripts/update_knowledge_db.py

# 特定のフレームワークのみ更新
python scripts/update_knowledge_db.py --frameworks react django fastapi
```

### AI ツールとの連携

#### GitHub Copilot (VS Code)

`.vscode/mcp.json`:

```json
{
  "mcpServers": {
    "yata": {
      "command": "uv",
      "args": ["run", "yata", "serve"]
    }
  }
}
```

#### Claude Desktop

`~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "yata": {
      "command": "uv",
      "args": ["run", "yata", "serve"]
    }
  }
}
```

## 🔧 MCP Tools (32 Tools)

### 📁 基本ツール

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

### 🧠 フレームワーク知識グラフツール

| Tool | 説明 |
|------|------|
| `register_framework` | フレームワーク知識グラフを登録 |
| `search_framework` | フレームワーク内でエンティティを検索 |
| `get_framework_entity` | フレームワークエンティティの詳細を取得 |
| `list_frameworks` | 登録済みフレームワーク一覧を取得 |
| `get_framework_stats` | フレームワーク統計情報を取得 |
| `get_usage_examples` | フレームワークの使用例を取得 |
| `get_framework_structure` | フレームワーク構造を取得 |

### 📚 ドキュメント生成ツール（Phase 1）

| Tool | 説明 |
|------|------|
| `generate_documentation` | エンティティのドキュメントを自動生成（JSDoc/docstring形式） |
| `recommend_code` | 知識グラフからコード推奨を取得（類似コード、パターン提案） |
| `analyze_impact` | 依存関係の影響分析（変更影響範囲の特定） |

### 🔍 ハイブリッド検索・品質分析ツール（Phase 2）

| Tool | 説明 |
|------|------|
| `hybrid_search` | キーワード検索＋セマンティック検索の統合検索 |
| `analyze_quality` | コード品質メトリクス分析（循環的複雑度、結合度、凝集度） |
| `track_evolution` | Git履歴からコードの変更頻度・ホットスポットを分析 |
| `find_hotspots` | 変更頻度の高いファイル・関数を特定 |

### 🤖 AI コーディング支援ツール（Phase 3）

| Tool | 説明 |
|------|------|
| `get_coding_guidance` | AIコーディングガイダンス生成（フレームワーク推奨コード） |
| `detect_patterns` | デザインパターン自動検出（Singleton, Factory等10パターン） |
| `check_api_compatibility` | APIバージョン互換性チェック（Django, FastAPI, React対応） |
| `navigate_code` | インタラクティブコードナビゲーション（関係性探索） |
| `get_call_graph` | 関数の呼び出しグラフを取得 |

## 💬 MCP Prompts

| Prompt | 説明 |
|--------|------|
| `analyze_codebase` | コードベース構造を分析してインサイトを提供 |
| `explain_entity` | 特定のコードエンティティを説明 |
| `find_dependencies` | エンティティの依存関係を分析 |

## 📚 MCP Resources

| URI | 説明 |
|-----|------|
| `yata://graph/stats` | 知識グラフの統計情報 |

## 💻 CLI コマンド詳細

### parse - ソースコード解析

```bash
yata parse <PATH> [OPTIONS]
```

| オプション | 説明 |
|-----------|------|
| `-p, --pattern` | 対象ファイルのパターン（デフォルト: `**/*.py`） |
| `-e, --exclude` | 除外パターン |
| `-o, --output` | 知識グラフの保存先 |

### query - エンティティ検索

```bash
yata query <QUERY> [OPTIONS]
```

| オプション | 説明 |
|-----------|------|
| `-t, --type` | エンティティ型でフィルタ（function, class, method 等） |
| `-n, --max-results` | 最大結果数（デフォルト: 20） |
| `-g, --graph` | 読み込むグラフファイルのパス |
| `--json` | JSON 形式で出力 |

### stats - 統計情報表示

```bash
yata stats [OPTIONS]
```

| オプション | 説明 |
|-----------|------|
| `-g, --graph` | 読み込むグラフファイルのパス |
| `--json` | JSON 形式で出力 |

### validate - 整合性検証

```bash
yata validate [OPTIONS]
```

| オプション | 説明 |
|-----------|------|
| `-g, --graph` | 検証するグラフファイル |
| `-r, --repair` | 問題を自動修復 |
| `--json` | JSON 形式で出力 |

### watch - ファイル監視

```bash
yata watch <DIRECTORY> [OPTIONS]
```

| オプション | 説明 |
|-----------|------|
| `-p, --pattern` | 監視パターン |
| `-e, --exclude` | 除外パターン |
| `-d, --debounce` | デバウンス遅延（秒、デフォルト: 1.0） |
| `-o, --output` | グラフの自動保存先 |

### benchmark - パフォーマンス測定

```bash
yata benchmark <DIRECTORY> [OPTIONS]
```

| オプション | 説明 |
|-----------|------|
| `-p, --pattern` | 対象ファイルパターン |
| `--json` | JSON 形式で出力 |

### serve - MCP サーバー起動

```bash
yata serve [OPTIONS]
```

| オプション | 説明 |
|-----------|------|
| `-t, --transport` | トランスポート: `stdio` or `sse`（デフォルト: stdio） |
| `-p, --port` | SSE 用ポート（デフォルト: 8080） |

## 🏗️ 対応言語 (24言語)

| 言語 | 拡張子 | 状態 |
|------|--------|------|
| Python | `.py` | ✅ 対応 |
| TypeScript | `.ts`, `.tsx` | ✅ 対応 |
| JavaScript | `.js`, `.jsx` | ✅ 対応 |
| Rust | `.rs` | ✅ 対応 |
| Go | `.go` | ✅ 対応 |
| Java | `.java` | ✅ 対応 |
| Kotlin | `.kt` | ✅ 対応 |
| Scala | `.scala` | ✅ 対応 |
| C | `.c`, `.h` | ✅ 対応 |
| C++ | `.cpp`, `.hpp` | ✅ 対応 |
| C# | `.cs` | ✅ 対応 |
| Swift | `.swift` | ✅ 対応 |
| Objective-C | `.m` | ✅ 対応 |
| PHP | `.php` | ✅ 対応 |
| Ruby | `.rb` | ✅ 対応 |
| Dart | `.dart` | ✅ 対応 |
| Elixir | `.ex`, `.exs` | ✅ 対応 |
| Haskell | `.hs` | ✅ 対応 |
| Julia | `.jl` | ✅ 対応 |
| Lua | `.lua` | ✅ 対応 |
| Groovy | `.groovy` | ✅ 対応 |
| SQL | `.sql` | ✅ 対応 |
| Zig | `.zig` | ✅ 対応 |
| YAML | `.yaml`, `.yml` | ✅ 対応 |

## 📚 対応フレームワーク (47フレームワーク)

YATAは主要フレームワークの構造を事前学習済みの知識グラフとして提供します。

### Python

| フレームワーク | カテゴリ | 主要エンティティ |
|---------------|---------|----------------|
| Django | Web Framework | Model, View, Template, Form, Middleware |
| Flask | Web Framework | Blueprint, Route, Extension |
| FastAPI | Web Framework | Router, Dependency, Pydantic Model |
| Pytest | Testing | Fixture, Marker, Plugin |
| NumPy | Data Science | ndarray, ufunc, dtype |
| Pandas | Data Science | DataFrame, Series, Index |
| SQLAlchemy | ORM | Model, Session, Query, Engine |
| LangChain | AI/LLM | Chain, Agent, Memory, Tool |
| Haystack | AI/NLP | Pipeline, Document Store, Retriever |
| Streamlit | Dashboard | App, Widget, Cache, Session |
| LangGraph | AI/Agent | Graph, Node, Edge, State |

### JavaScript / TypeScript

| フレームワーク | カテゴリ | 主要エンティティ |
|---------------|---------|----------------|
| React | UI Framework | Component, Hook, Context, Props |
| Vue.js | UI Framework | Component, Composition API, Directive |
| Angular | UI Framework | Component, Service, Module, Pipe |
| Next.js | Full-stack | Page, API Route, Middleware, Server Component |
| Express | Web Framework | Router, Middleware, Request, Response |
| NestJS | Web Framework | Controller, Service, Module, Guard |
| Jest | Testing | Test, Describe, Mock, Expect |
| Astro | Meta Framework | Component, Island, Integration |
| SolidJS | UI Framework | Signal, Effect, Component |
| Remix | Full-stack | Loader, Action, Route, Form |
| htmx | Hypermedia | Attribute, Swap, Trigger |
| Hono | Edge Runtime | Router, Middleware, Context |
| tRPC | Type-safe API | Router, Procedure, Query, Mutation |
| Qwik | Resumable | Component, Signal, QRL |
| Bun | Runtime | Server, File, Plugin |
| Expo | Mobile | App, Navigation, Component |

### Rust

| フレームワーク | カテゴリ | 主要エンティティ |
|---------------|---------|----------------|
| Actix-web | Web Framework | App, Route, Handler, Middleware |
| Tokio | Async Runtime | Runtime, Task, Channel, Stream |
| Serde | Serialization | Serialize, Deserialize, Attribute |
| Rocket | Web Framework | Route, Guard, Fairing, Responder |
| Axum | Web Framework | Router, Handler, Extension, State |
| Tauri | Desktop App | Command, Window, Plugin, State |

### Go

| フレームワーク | カテゴリ | 主要エンティティ |
|---------------|---------|----------------|
| Gin | Web Framework | Router, Handler, Middleware, Context |
| Echo | Web Framework | Router, Handler, Middleware, Context |
| Fiber | Web Framework | App, Route, Handler, Middleware |
| GORM | ORM | Model, DB, Query, Association |

### Elixir

| フレームワーク | カテゴリ | 主要エンティティ |
|---------------|---------|----------------|
| Phoenix | Web Framework | Controller, LiveView, Channel, Router |

### Database/ORM

| フレームワーク | 言語 | 主要エンティティ |
|---------------|------|----------------|
| Prisma | TypeScript | Schema, Client, Query, Migration |
| Drizzle | TypeScript | Schema, Query, Migration, Relation |

### Mobile

| フレームワーク | 言語 | 主要エンティティ |
|---------------|------|----------------|
| SwiftUI | Swift | View, State, Binding, Environment |
| Jetpack Compose | Kotlin | Composable, State, Modifier, Theme |

### その他

| フレームワーク | 言語 | カテゴリ |
|---------------|------|--------|
| Spring Boot | Java | Web Framework |
| .NET Core | C# | Web Framework |
| Ruby on Rails | Ruby | Web Framework |
| Laravel | PHP | Web Framework |

## 🎯 検出可能なデザインパターン (10パターン)

| パターン | カテゴリ | 検出条件 |
|---------|---------|----------|
| Singleton | 生成 | `getInstance`, `__new__`, 静的インスタンス |
| Factory Method | 生成 | `create*`, `build*`, `make*` メソッド |
| Builder | 生成 | `set*`, `with*`, `build` チェーン |
| Adapter | 構造 | `adapt`, `wrap`, インターフェース変換 |
| Decorator | 構造 | `@decorator`, ラッパー関数 |
| Facade | 構造 | 複数サービスの統合インターフェース |
| Observer | 振る舞い | `subscribe`, `notify`, `on*` イベント |
| Strategy | 振る舞い | `execute`, `handle`, 戦略インターフェース |
| Command | 振る舞い | `execute`, `undo`, コマンドオブジェクト |
| Template Method | 振る舞い | 抽象メソッド + 具象実装 |

## �🔗 関係性の自動検出

YATA は以下の関係性を自動的に検出します：

| 関係性タイプ | 説明 |
|-------------|------|
| `CALLS` | 関数/メソッドの呼び出し関係 |
| `IMPORTS` | モジュールのインポート関係 |
| `CONTAINS` | モジュール→クラス→メソッドの包含関係 |
| `INHERITS` | クラスの継承関係 |
| `DEPENDS_ON` | 依存関係（パッケージ、モジュール間） |
| `IMPLEMENTS` | インターフェース実装関係 |

## 🛠️ 開発

### セットアップ

```bash
# リポジトリをクローン
git clone https://github.com/nahisaho/YATA.git
cd yata

# uv で依存関係をインストール
uv sync --all-packages

# テストを実行
uv run pytest

# カバレッジ付きテスト
uv run pytest --cov=yata_core --cov=yata_mcp

# リンターを実行
uv run ruff check .
uv run mypy packages/
```

### プロジェクト構成

```
yata/
├── packages/
│   ├── yata-core/          # 知識グラフエンジン（ライブラリ）
│   │   ├── src/yata_core/
│   │   │   ├── domain/     # ドメイン層（エンティティ、値オブジェクト）
│   │   │   ├── application/ # アプリケーション層（ユースケース）
│   │   │   └── infrastructure/ # インフラ層（パーサー、ストレージ）
│   │   └── tests/
│   └── yata-mcp/           # MCP Server（アプリケーション）
│       ├── src/yata_mcp/
│       │   ├── server/     # MCP 実装（FastMCP）
│       │   └── cli/        # CLI 実装（Click）
│       └── tests/
├── steering/               # MUSUBI SDD プロジェクトメモリ
└── storage/specs/          # 設計ドキュメント
```

### アーキテクチャ

YATA は Clean Architecture に基づいて設計されています：

- **Domain Layer**: コアエンティティ（FunctionEntity, ClassEntity 等）、値オブジェクト（EntityId, Location）、リポジトリインターフェース
- **Application Layer**: ユースケース（ParseFileUseCase, ParseDirectoryUseCase）
- **Infrastructure Layer**: 実装（PythonParser, TypeScriptParser, NetworkXKnowledgeGraph）
- **Interface Layer**: MCP サーバーと CLI

## 📊 テスト状況

- **テスト数**: 592+
- **カバレッジ**: 82%+
- **カバレッジ基準**: 80% 以上
- **対応言語パーサー**: 24
- **フレームワーク知識グラフ**: 47

## 📜 ライセンス

MIT License - 詳細は [LICENSE](LICENSE) を参照してください。

## 🙏 謝辞

- [Model Context Protocol](https://modelcontextprotocol.io/) - Anthropic
- [Tree-sitter](https://tree-sitter.github.io/tree-sitter/) - AST パーサー
- [NetworkX](https://networkx.org/) - グラフライブラリ
- [FastMCP](https://github.com/jlowin/fastmcp) - MCP SDK

## 📖 ドキュメント

- [AI ツール設定ガイド](docs/AI_TOOLS_SETUP.md) - Claude, Copilot, Cursor の設定
- [知識データベース更新ガイド](docs/KNOWLEDGE_UPDATE_GUIDE.md) - フレームワーク知識の更新方法
- [トラブルシューティング](docs/TROUBLESHOOTING.md) - よくある問題と解決方法
- [YATA vs Context7](docs/YATA_vs_Context7.md) - Context7との詳細比較
- [CHANGELOG](CHANGELOG.md) - 変更履歴

---

**YATA** - 八咫鏡のように、コードの真実を映し出す 🪞
