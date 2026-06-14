# MAGATAMA (勾玉) — 巨大なコードベースの「地図」を AI に渡す

[![CI](https://github.com/tsucky230/MAGATAMA/workflows/CI/badge.svg)](https://github.com/tsucky230/MAGATAMA/actions)
[![Coverage](https://codecov.io/gh/tsucky230/MAGATAMA/branch/main/graph/badge.svg)](https://codecov.io/gh/tsucky230/MAGATAMA)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> 🇺🇸 [English README](README.md)

---

## 🗺️ 30 秒でわかる MAGATAMA

知らない街に着いたばかりの人を想像してください。目的地にたどり着くのに、
**すべての通りを端から端まで歩いて確かめる**人はいません。普通は **地図**を
見て、必要な道だけを把握します。

LLM（Claude / Copilot など）に大きなコードベースを理解させるとき、多くの人は
LLM に**全ソースを読ませて**います。これは「街の全通りを歩かせる」のと同じで、
時間（＝トークン＝コスト）を浪費します。

ここで効くのが、**兄弟ソフト [comP](https://github.com/tsucky230/comP)（VSCode
拡張機能）との組み合わせ**です。MAGATAMA は単体でも使えますが、comP と組み合わせる
と効果が倍増します。両者の役割はこう分かれています。

- **comP** は、あなたのコードを歩き回って**地図（インデックス）を作る測量士**です。
- **MAGATAMA** は、その地図を読み、LLM に**「いま必要な区画だけ」を手渡す案内人**です。

結果、LLM は全ソースを読まずに、関数・クラス・依存関係といった「街の構造」を
把握できます。実測で **概観把握なら約 1/500 のトークン**で済みました
（→ [OVERVIEW_jp.md](OVERVIEW_jp.md) に計測の全データ）。

> **一言で**: MAGATAMA は、コードを「知識グラフ（地図）」に変換し、AI に最小の
> トークンで文脈を渡す **MCP サーバ**です。
> [YATA (八咫)](https://github.com/nahisaho/YATA) のフォークに、コードインデクサー
> [comP](https://github.com/tsucky230/comP) との直接連携を加えたものです。

---

## 💡 これで何ができるのか（3 つの代表シーン）

### シーン 1: 初見の巨大リポジトリを 5 分で把握したい

> 「このリポジトリ、何ができて、どんな構造？ どこから読めばいい？」

LLM は全ファイルを開く代わりに、comP の地図から**統計・主要モジュール・
エクスポートされたシンボル**だけを読み、概観を返します。実際にこの MAGATAMA
自身でやった結果が [OVERVIEW_jp.md](OVERVIEW_jp.md) です。

### シーン 2: ある関数を変えたら何が壊れるか知りたい

> 「`save_graph` を直すと、どこに影響する？」

`analyze_impact` / `get_call_graph` が、地図をたどって**影響範囲**を返します。
grep で全文検索して目視する作業を、構造グラフが肩代わりします。

### シーン 3: フレームワークの作法に沿って書きたい

> 「FastAPI の依存性注入って、どう書くのが正解？」

MAGATAMA には **47 フレームワークの作り付け知識グラフ**が入っており、
`hybrid_search` であなたのコードと公式作法を**横断検索**できます（YATA 由来）。

---

## 🧩 comP と MAGATAMA の関係

```text
[comP（VSCode拡張 + Rust常駐）]
        │ ワークスペースを解析して地図を書き込む
        ▼
   .comp/index.db  (SQLite, WALモード)   ← 街の地図
        │
        ├─→ comP MCP …………… 地図を直接引く（1ファイル要約・1シンボル取得など軽量）
        │
        └─→ MAGATAMA Bridge … 地図を知識グラフに取り込み、横断分析（36ツール）
                  │
                  ▼
        Claude Desktop / Cursor / Copilot / Claude Code
```

- **comP** = 地図を作る＆軽く引く。`get_file_summary` / `get_symbol` など。
- **MAGATAMA** = 地図を俯瞰して分析。`search_entities` / `analyze_impact` /
  `hybrid_search` など。

---

## 🚀 セットアップ（実例つき）

ゴール: **① comP でコードをインデックス化 → ② MAGATAMA を入れる →
③ AI ツールに MCP として登録 → ④ 動作確認**。

### Step 1. comP を VSCode 拡張として入れて、インデックス化を始める

1. VSCode に comP 拡張（`tsucky230.comp-vscode`）をインストールします。
   （[comP リポジトリ](https://github.com/tsucky230/comP) の手順／VSIX を参照）
2. 対象プロジェクトのフォルダを VSCode で開きます。
3. comP が自動でワークスペースを解析し、
   **`<プロジェクト>/.comp/index.db`** に地図を書き出します（WAL モードの SQLite）。
   大きなリポジトリでも初回だけ時間がかかり、以降は変更分のみ増分更新されます。

> 確認: エクスプローラに `.comp/` フォルダと `index.db` ができていれば成功です。

comP 自身を MCP として AI に直接つなぐ場合は、`.mcp.json` にこう書きます
（このリポジトリの実例）:

```json
{
  "mcpServers": {
    "comp": {
      "command": "c:\\Users\\<you>\\.vscode\\extensions\\tsucky230.comp-vscode-0.8.1\\daemon\\target\\release\\comp-daemon-win.exe",
      "args": [],
      "env": {
        "COMP_WORKSPACE_ROOT": "e:\\dev\\MAGATAMA",
        "RUST_LOG": "info"
      }
    }
  }
}
```

> `COMP_WORKSPACE_ROOT` をインデックス対象のフォルダに合わせてください。
> パスのバージョン番号（`0.8.1`）は導入した拡張のバージョンに置き換えます。

### Step 2. MAGATAMA をインストール

```bash
# 開発版（このリポジトリ）を使う場合
git clone https://github.com/tsucky230/MAGATAMA.git
cd MAGATAMA
uv sync --all-packages       # uv が未導入なら https://astral.sh/uv

# もしくは PyPI から
pip install magatama
```

動作確認:

```bash
magatama info        # バージョン・ツール数（36）が表示されれば OK
```

### Step 3. AI ツールに MCP として登録

#### Claude Desktop（Windows の例）

`%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "magatama": {
      "command": "uv",
      "args": ["run", "--directory", "C:\\path\\to\\MAGATAMA", "magatama", "serve"]
    }
  }
}
```

#### GitHub Copilot / VS Code

プロジェクトルートの `.vscode/mcp.json`:

```json
{
  "mcpServers": {
    "magatama": {
      "command": "uv",
      "args": ["run", "--directory", "${workspaceFolder}", "magatama", "serve"]
    }
  }
}
```

PyPI 版を入れた場合は `"command": "magatama", "args": ["serve"]` でも可。
他ツール（Cursor / Continue）や SSE モードは
[AI ツール設定ガイド](docs/AI_TOOLS_SETUP.md) を参照してください。

### Step 4. つないで使う

AI ツールを再起動し、チャットからこう頼みます:

```text
get_external_graph_info(path="e:/dev/myproject") で comP の地図を確認して。
問題なければ read_external_graph で取り込んで、このプロジェクトを概観して。
```

これで LLM が comP の地図を MAGATAMA に取り込み、全ソースを読まずに概観します。

---

## 🎬 使ってみる: プロンプト → 出力サンプル

実際の操作イメージです（AI ツールのチャットに投げる想定）。

### 例 A: プロジェクト概観

**プロンプト**

```text
read_external_graph(path="e:/dev/MAGATAMA") で取り込んでから、
get_graph_stats でこのプロジェクトの規模と構成を要約して。
```

**出力サンプル（実データ）**

```text
✓ 取り込み完了（203 ファイル / 3,829 シンボル）
- 言語: Python 123 / Markdown 38 / JSON 36 / YAML 1
- 最大モジュール: framework_usecase.py（133 シンボル）
- 構成: packages/magatama-core（エンジン）＋ packages/magatama-mcp（MCP+CLI）
→ Clean Architecture（domain → application → infrastructure → interface）
```

### 例 B: 影響範囲の調査

**プロンプト**

```text
search_entities(query="save_graph") で対象を特定して、
analyze_impact でこの関数を変更したときの影響範囲を教えて。
```

**出力サンプル**

```text
対象: _handle_save_graph (mcp_server.py:442)
影響を受ける可能性: save コマンド（cli/main.py）, parse --output の保存処理
→ 変更時はこの 2 経路のテストを確認してください。
```

### 例 C: フレームワーク作法の確認（YATA 由来）

**プロンプト**

```text
hybrid_search(query="FastAPI dependency injection") で、
公式の作法と、うちのコードの該当箇所を横断検索して。
```

**出力サンプル**

```text
[Framework] FastAPI: Depends() を関数引数に宣言（Router/Dependency）
[Local]    （該当なし）→ まだ DI を使っていません。導入候補: routes 層
```

> CLI だけで試したい場合は、まず地図を JSON 化して再利用できます:
>
> ```bash
> magatama parse ./src -o graph.json
> magatama stats --graph graph.json
> magatama query "UseCase" --type class --graph graph.json
> ```

---

## 🔧 MCP Tools（36）

LLM はこれらから**必要なものだけ**を自律的に選んで呼びます。

<details>
<summary><b>🔌 comP Bridge（2）— 地図の取り込み</b></summary>

| Tool | 説明 |
|------|------|
| `read_external_graph` | comP インデックスを知識グラフに読み込む（`mode=replace`/`merge`） |
| `get_external_graph_info` | comP インデックスの統計を確認（ロードなし・鮮度チェック） |

</details>

<details>
<summary><b>📁 基本（10）— 解析と検索</b></summary>

| Tool | 説明 |
|------|------|
| `parse_file` / `parse_directory` | ソースを解析してエンティティ抽出 |
| `search_entities` / `get_entity` | 名前・型で検索 / 詳細取得 |
| `get_related_entities` | 隣接ノード（関係先）取得 |
| `get_graph_stats` | グラフ統計 |
| `save_graph` / `load_graph` | JSON への保存／読込 |
| `list_supported_languages` / `get_language_for_file` | 24 言語の一覧 / 判定 |

</details>

<details>
<summary><b>🧠 フレームワーク知識（7）— 47 FW の作り付け地図</b></summary>

`list_frameworks` / `search_framework_docs` / `search_all_frameworks` /
`find_code_patterns` / `get_framework_entity_context` /
`framework_semantic_search_tool` / `framework_find_by_pattern`

</details>

<details>
<summary><b>🔍 検索・コンテキスト（4）/ 📚 ドキュメント・推奨（4）</b></summary>

`semantic_search` / `find_by_pattern` / `get_code_context` /
`find_usage_examples` ・ `generate_documentation` / `recommend_code` /
`analyze_impact` / `find_critical_paths`

</details>

<details>
<summary><b>🔎 ハイブリッド検索・品質（4）/ 🤖 AI 支援（5）</b></summary>

`hybrid_search` / `analyze_quality` / `track_evolution` / `find_hotspots` ・
`get_coding_guidance` / `detect_patterns` / `check_api_compatibility` /
`navigate_code` / `get_call_graph`

</details>

**MCP Prompts**: `analyze_codebase` / `explain_entity` / `find_dependencies`
**MCP Resources**: `magatama://graph/stats`

---

## 💻 CLI コマンド（人が手で叩く用）

| コマンド | 何をするか | 例 |
|---------|-----------|----|
| `parse` | 解析して知識グラフを構築（`-o` で保存） | `magatama parse ./src -o graph.json` |
| `query` | エンティティ検索 | `magatama query "User" -t class -g graph.json` |
| `stats` | 統計表示 | `magatama stats -g graph.json` |
| `serve` | MCP サーバ起動 | `magatama serve` / `--transport sse --port 8080` |
| `watch` | 変更を監視して自動更新（`-o` で自動保存） | `magatama watch ./src -o graph.json` |
| `validate` | グラフ整合性チェック（`--repair` で修復） | `magatama validate -g graph.json --repair` |
| `info` | サーバ情報・ツール一覧 | `magatama info` |

> ヒント: `parse`/`query`/`stats` は**別プロセスで状態を持ちません**。
> `parse -o` で地図を JSON 化し、`query`/`stats` の `--graph` で読み込んで使います。
> AI 連携では代わりに `serve` の常駐サーバがグラフを保持し、LLM がツールを呼びます。

---

## 🏗️ 対応言語・フレームワーク

- **24 言語**: Python, TypeScript/JS, Rust, Go, Java, Kotlin, Scala, C/C++, C#,
  Swift, Objective-C, PHP, Ruby, Dart, Elixir, Haskell, Julia, Lua, Groovy,
  SQL, Zig, YAML
- **47 フレームワーク**（457K+ エンティティ）: Django/Flask/FastAPI, React/Vue/
  Angular/Next.js, Actix/Axum/Tauri, Gin/Echo, Phoenix, Spring Boot, Rails,
  Laravel, SwiftUI, Jetpack Compose ほか

---

## 🛠️ 開発

```bash
uv sync --all-packages
uv run pytest                         # テスト（794 件）
uv run pytest --cov=magatama_core --cov=magatama_mcp
uv run ruff check . && uv run mypy packages/
```

```text
MAGATAMA/
├── packages/
│   ├── magatama-core/   # 知識グラフエンジン（ライブラリ）
│   └── magatama-mcp/    # MCP サーバ＋CLI（magatama コマンド）
├── steering/            # プロジェクトメモリ・規約
└── storage/specs/       # 設計ドキュメント（要件・C4図・ADR）
```

設計は **Clean Architecture**。詳細・実測は [OVERVIEW_jp.md](OVERVIEW_jp.md)。

---

## 📜 ライセンス / 謝辞

MIT License。本プロジェクトは
[YATA](https://github.com/nahisaho/YATA)（Copyright (c) 2025 nahisaho）を
MIT のもとフォークし、comP Bridge を追加したものです。

- [YATA](https://github.com/nahisaho/YATA) by **nahisaho** — 基盤
- [comP](https://github.com/tsucky230/comP) by **tsucky230** — コードインデクサー
- [Model Context Protocol](https://modelcontextprotocol.io/) / Tree-sitter / NetworkX / FastMCP

---

## 📖 ドキュメント

- [プロジェクト概観＋トークン実測（OVERVIEW_jp.md）](OVERVIEW_jp.md)
- [AI ツール設定ガイド](docs/AI_TOOLS_SETUP.md)
- [知識データベース更新ガイド](docs/KNOWLEDGE_UPDATE_GUIDE.md)
- [トラブルシューティング](docs/TROUBLESHOOTING.md)
- [English README](README.md) / [CHANGELOG](CHANGELOG.md)

---

## 📛 名前の由来

**YATA（八咫）** は「非常に大きい」を意味する古語。広大なコードと膨大な
フレームワーク知識を丸ごと扱う思想を表します。**MAGATAMA（勾玉）** は
「小さな石に強い力を凝縮したもの」。広大な情報から本質だけを抽出し、高密度に
圧縮して LLM へ届ける——三種の神器のひとつ、勾玉のように。
