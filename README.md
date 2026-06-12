# MAGATAMA (勾玉) - YATA fork with comP Bridge

[![CI](https://github.com/tsucky230/MAGATAMA/workflows/CI/badge.svg)](https://github.com/tsucky230/MAGATAMA/actions)
[![Coverage](https://codecov.io/gh/tsucky230/MAGATAMA/branch/main/graph/badge.svg)](https://codecov.io/gh/tsucky230/MAGATAMA)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> 🇺🇸 [English README](README.en.md)

**MAGATAMA** は [YATA (八咫)](https://github.com/nahisaho/YATA)（nahisaho 氏作、MIT License）を
フォークし、**[comP](https://github.com/tsucky230/comP) コードインデクサーとの直接連携**を追加した
AI コーディング支援 MCP Server です。

YATA が持つ 34 の MCP ツール群をそのまま継承しつつ、comP が `.comp/index.db` に蓄積した
コードインデックスを再パース不要で YATA の知識グラフに取り込める **comP Bridge（2 ツール）** を追加しています。

## comP Bridge とは

[comP](https://github.com/tsucky230/comP) は VSCode 拡張 + Rust デーモンで構成されるコードインデクサーです。
ワークスペースを解析した結果を `<workspace>/.comp/index.db`（SQLite, WAL モード）に保存します。

MAGATAMA の comP Bridge はこの SQLite を直接読み取り、YATA の NetworkX 知識グラフに変換します。
これにより **comP が構築済みのインデックスを `search_entities` / `hybrid_search` / `analyze_impact`
などの全 YATA ツールからそのまま利用**できます。

```text
[comP Rust Daemon] ──書込──> .comp/index.db (SQLite, WALモード)
                                   │ 読み取り専用で接続
                                   ▼
                     [MAGATAMA CompIndexReader] ──変換──> NetworkXKnowledgeGraph
                                   │
                                   ▼
                [MAGATAMA MCP Server (FastMCP)] ──MCP──> Claude Desktop / Cursor / Copilot
```

## ✨ 特徴

- 🔌 **comP Bridge**: comP の `.comp/index.db` を再パースなしで知識グラフに取り込み
- 🔍 **コード解析**: Tree-sitter による高速 AST 解析（24 言語対応）
- 🕸️ **知識グラフ**: NetworkX によるエンティティ・関係性グラフ
- 🔗 **関係性検出**: CALLS/IMPORTS/INHERITS/CONTAINS 関係の自動検出
- 🤖 **MCP 準拠**: Model Context Protocol 完全対応（36 Tools, 3 Prompts, 1 Resource）
- 📚 **フレームワーク知識**: 47 フレームワークの組み込み知識グラフ（457K+ エンティティ）
- 🔎 **ハイブリッド検索**: ローカルコード＋フレームワーク横断検索
- 🎯 **パターン検出**: デザインパターン自動検出
- 📝 **ドキュメント生成**: 自動ドキュメント生成
- 📊 **品質分析**: コード品質メトリクス
- 💾 **永続化**: JSON/SQLite への保存/読み込み
- 🔒 **プライバシー**: 完全ローカル実行（データ外部送信なし）
- 🔄 **増分解析**: 変更ファイルのみを効率的に再解析

## 🚀 クイックスタート

### インストール

```bash
# リポジトリをクローン
git clone https://github.com/tsucky230/MAGATAMA.git
cd MAGATAMA

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
```

### comP と連携する

```bash
# 1. comP でプロジェクトをインデックス（VSCode + comP 拡張で自動実行されます）

# 2. MAGATAMA MCP サーバーを起動
yata serve
```

MCP 経由（Claude Desktop 等）で:

```python
# インデックスの確認（ロードなし）
get_external_graph_info(path="e:/dev/myproject")

# 知識グラフへ取り込み
read_external_graph(path="e:/dev/myproject")

# 取り込んだコードを通常の YATA ツールで検索
search_entities(query="MyClass")
get_related_entities(entity_id="comp:myproject:n42")
analyze_impact(entity_id="comp:myproject:n42")
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

## 🔧 MCP Tools (36 Tools)

### 🔌 comP Bridge (2 Tools)

| Tool | 説明 |
|------|------|
| `read_external_graph` | comP インデックスを YATA 知識グラフに読み込む |
| `get_external_graph_info` | comP インデックスの統計情報を確認（ロードなし） |

`read_external_graph` のオプション:

| パラメータ | 説明 |
| ----------- | ------ |
| `path` | ワークスペースルート / `.comp` ディレクトリ / `.db` ファイルのいずれか |
| `mode` | `replace`（デフォルト）: 既存を削除して再ロード / `merge`: 追加ロード |

### 📁 基本ツール (10 Tools)

| Tool | 説明 |
|------|------|
| `parse_file` | ソースファイルを解析してエンティティを抽出 |
| `parse_directory` | ディレクトリ内のファイルを一括解析 |
| `search_entities` | 名前や型でエンティティを検索 |
| `get_entity` | 特定エンティティの詳細を取得 |
| `get_related_entities` | 関連エンティティを取得（グラフの隣接ノード） |
| `get_graph_stats` | 知識グラフの統計情報を取得 |
| `save_graph` | 知識グラフを JSON ファイルに保存 |
| `load_graph` | JSON ファイルから知識グラフを読み込み |
| `list_supported_languages` | サポートする 24 言語の一覧を取得 |
| `get_language_for_file` | ファイル拡張子から言語を判定 |

### 🧠 フレームワーク知識グラフツール (7 Tools)

| Tool | 説明 |
|------|------|
| `list_frameworks` | 利用可能なフレームワーク一覧を取得 |
| `search_framework_docs` | フレームワーク内でエンティティを検索 |
| `search_all_frameworks` | 全フレームワークを横断検索 |
| `find_code_patterns` | 複数フレームワークで共通パターンを検索 |
| `get_framework_entity_context` | フレームワークエンティティの詳細を取得 |
| `framework_semantic_search_tool` | フレームワークでセマンティック検索 |
| `framework_find_by_pattern` | フレームワーク全体でパターンマッチング |

### 🔍 検索・コンテキストツール (4 Tools)

| Tool | 説明 |
|------|------|
| `semantic_search` | ローカルコードでセマンティック検索 |
| `find_by_pattern` | 命名パターンでエンティティ検索 |
| `get_code_context` | エンティティの包括的コンテキスト取得 |
| `find_usage_examples` | エンティティの使用例を検索 |

### 📚 ドキュメント・推奨ツール (4 Tools)

| Tool | 説明 |
|------|------|
| `generate_documentation` | エンティティのドキュメントを自動生成 |
| `recommend_code` | コードスニペットを推奨 |
| `analyze_impact` | 変更の影響を分析 |
| `find_critical_paths` | 重要な依存パスを特定 |

### 🔎 ハイブリッド検索・品質分析ツール (4 Tools)

| Tool | 説明 |
| ------ | ------ |
| `hybrid_search` | ローカル＋フレームワーク横断検索 |
| `analyze_quality` | コード品質メトリクス分析 |
| `track_evolution` | Git 履歴からコード進化を追跡 |
| `find_hotspots` | 変更頻度の高いコードを特定 |

### 🤖 AI コーディング支援ツール (5 Tools)

| Tool | 説明 |
| ------ | ------ |
| `get_coding_guidance` | AI コーディングガイダンス生成 |
| `detect_patterns` | デザインパターン自動検出 |
| `check_api_compatibility` | API バージョン互換性チェック |
| `navigate_code` | コード関係性のナビゲーション |
| `get_call_graph` | 関数の呼び出しグラフを取得 |

## 💬 MCP Prompts (3 Prompts)

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

### serve - MCP サーバー起動

```bash
yata serve [OPTIONS]
```

| オプション | 説明 |
|-----------|------|
| `-t, --transport` | トランスポート: `stdio` or `sse`（デフォルト: stdio） |
| `-p, --port` | SSE 用ポート（デフォルト: 8080） |

## 🏗️ 対応言語 (24 言語)

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

## 📚 対応フレームワーク (26 フレームワーク)

YATA は主要フレームワークの構造を事前学習済みの知識グラフとして提供します。

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

## 🛠️ 開発

### セットアップ

```bash
git clone https://github.com/tsucky230/MAGATAMA.git
cd MAGATAMA
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

```text
MAGATAMA/
├── packages/
│   ├── yata-core/          # 知識グラフエンジン（ライブラリ）
│   │   ├── src/yata_core/
│   │   │   ├── domain/         # ドメイン層（エンティティ、値オブジェクト）
│   │   │   ├── application/    # アプリケーション層（ユースケース）
│   │   │   └── infrastructure/ # インフラ層（パーサー、ストレージ、comP Bridge）
│   │   └── tests/
│   └── yata-mcp/           # MCP Server（アプリケーション）
│       ├── src/yata_mcp/
│       │   ├── server/     # MCP 実装（FastMCP）
│       │   └── cli/        # CLI 実装（Click）
│       └── tests/
├── steering/               # プロジェクトメモリ
└── storage/specs/          # 設計ドキュメント
```

### アーキテクチャ

Clean Architecture に基づいて設計されています：

- **Domain Layer**: コアエンティティ、値オブジェクト、リポジトリインターフェース
- **Application Layer**: ユースケース（ParseFileUseCase, LoadCompIndexUseCase 等）
- **Infrastructure Layer**: パーサー、NetworkXKnowledgeGraph、**CompIndexReader（comP Bridge）**
- **Interface Layer**: MCP サーバー（FastMCP）と CLI（Click）

## 📊 テスト状況

- **テスト数**: 794 (694 yata-core + 100 yata-mcp)
- **E2E テスト**: 42 (18 統合 + 24 セキュリティ)
- **カバレッジ**: 76%
- **対応言語パーサー**: 24
- **フレームワーク知識グラフ**: 47 (457K+ エンティティ)

## 📜 ライセンス

MIT License

本プロジェクトは [YATA](https://github.com/nahisaho/YATA)（Copyright (c) 2025 nahisaho）を
MIT License のもとでフォークし、comP Bridge 機能を追加したものです。
詳細は [LICENSE](LICENSE) を参照してください。

## 🙏 謝辞

- [YATA](https://github.com/nahisaho/YATA) by nahisaho — 本プロジェクトのベース
- [comP](https://github.com/tsucky230/comP) by tsucky230 — VSCode コードインデクサー
- [Model Context Protocol](https://modelcontextprotocol.io/) — Anthropic
- [Tree-sitter](https://tree-sitter.github.io/tree-sitter/) — AST パーサー
- [NetworkX](https://networkx.org/) — グラフライブラリ
- [FastMCP](https://github.com/jlowin/fastmcp) — MCP SDK

## 📖 ドキュメント

- [English README](README.en.md)
- [AI ツール設定ガイド](docs/AI_TOOLS_SETUP.md)
- [知識データベース更新ガイド](docs/KNOWLEDGE_UPDATE_GUIDE.md)
- [トラブルシューティング](docs/TROUBLESHOOTING.md)
- [CHANGELOG](CHANGELOG.md)

## 📛 プロジェクト名の由来

**YATA（八咫）** とは、古代日本の長さの単位「咫（あた）」の 8 倍の大きさのこと。転じて「非常に大きい」「非常に長い」という意味を持つ言葉です。広大なコードベースや膨大なフレームワーク知識を丸ごと扱う、という思想を体現しています。

**MAGATAMA（勾玉）** は、本来「小さな石の中に強大な力や魂を凝縮して閉じ込めたもの」です。広大な情報（YATA）から本質だけを抽出し、高密度に圧縮して連携させる（comP）という設計思想そのものを体現しています。

MAGATAMA は YATA の姉妹プロジェクトとして、八咫の知識を勾玉のように小さく凝縮し、comP が構築したインデックスと結びつけることで、LLM に最小限のトークンで最大限のコンテキストを届けることを目指しています。

---

**MAGATAMA** (勾玉) — 三種の神器のひとつ、勾玉のように。YATA (八咫鏡) の兄弟プロジェクト。
