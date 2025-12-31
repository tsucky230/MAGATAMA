# YATA (八咫) - AI Coding Support MCP Server

[![CI](https://github.com/your-org/yata/workflows/CI/badge.svg)](https://github.com/your-org/yata/actions)
[![Coverage](https://codecov.io/gh/your-org/yata/branch/main/graph/badge.svg)](https://codecov.io/gh/your-org/yata)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**YATA** (八咫 - やた) は、AI コーディング支援のための知識グラフ MCP Server です。

ライブラリのソースコードを解析し、知識グラフを構築することで、Claude Desktop、GitHub Copilot、Cursor などの AI ツールに正確なコンテキストを提供します。

## ✨ 特徴

- 🔍 **コード解析**: Tree-sitter による高速な AST 解析（Python, TypeScript/TSX, JavaScript/JSX）
- 🕸️ **知識グラフ**: NetworkX によるエンティティ・関係性グラフ
- 🔗 **関係性検出**: CALLS/IMPORTS 関係の自動検出
- 🤖 **MCP 準拠**: Model Context Protocol 完全対応（8 Tools, 3 Prompts, 1 Resource）
- 💾 **永続化**: JSON ファイルへの保存/読み込み
- 🔒 **プライバシー**: 完全ローカル実行（データ外部送信なし）

## 🚀 クイックスタート

### インストール

```bash
# リポジトリをクローン
git clone https://github.com/your-org/yata.git
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

## 🔧 MCP Tools

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

## 🏗️ 対応言語

| 言語 | 拡張子 | 状態 |
|------|--------|------|
| Python | `.py` | ✅ 対応 |
| TypeScript | `.ts`, `.tsx` | ✅ 対応 |
| JavaScript | `.js`, `.jsx` | ✅ 対応 |

## 🔗 関係性の自動検出

YATA は以下の関係性を自動的に検出します：

| 関係性タイプ | 説明 |
|-------------|------|
| `CALLS` | 関数/メソッドの呼び出し関係 |
| `IMPORTS` | モジュールのインポート関係 |
| `CONTAINS` | モジュール→クラス→メソッドの包含関係 |
| `INHERITS` | クラスの継承関係 |

## 🛠️ 開発

### セットアップ

```bash
# リポジトリをクローン
git clone https://github.com/your-org/yata.git
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

- **テスト数**: 274+
- **カバレッジ**: 82%+
- **カバレッジ基準**: 80% 以上

## 📜 ライセンス

MIT License - 詳細は [LICENSE](LICENSE) を参照してください。

## 🙏 謝辞

- [Model Context Protocol](https://modelcontextprotocol.io/) - Anthropic
- [Tree-sitter](https://tree-sitter.github.io/tree-sitter/) - AST パーサー
- [NetworkX](https://networkx.org/) - グラフライブラリ
- [FastMCP](https://github.com/jlowin/fastmcp) - MCP SDK

---

**YATA** - 八咫鏡のように、コードの真実を映し出す 🪞
