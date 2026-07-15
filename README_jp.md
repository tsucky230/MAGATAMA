# MAGATAMA (勾玉) — 巨大コードベースの「地図」をAIに渡す

[![CI](https://github.com/tsucky230/MAGATAMA/workflows/CI/badge.svg)](https://github.com/tsucky230/MAGATAMA/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> 🇬🇧 [English README](README.md)

---

## 🗺️ 30秒でわかるMAGATAMA

知らない街に着いた人は、全部の道を歩いて覚えたりしません。**地図**を見て、必要な道だけを覚えます。

ところがLLM（Claude・Copilot等）に大きなコードベースを渡すとき、人は**全ソースを読ませます**。全部の道を歩かせているのと同じで、時間＝トークン＝コストが燃えます。

そこで兄弟ツール **[comP](https://github.com/tsucky230/comP)**（VSCode拡張）との分業です：

- **comP** ＝ コードを歩いて**地図（索引）を作る測量士**
- **MAGATAMA** ＝ 地図を読み、**今必要な区画だけをLLMに渡す案内人**

本リポジトリ自身で計測した結果、プロジェクト概要の把握に必要なトークンは**約1/500**になりました（実測データ: [OVERVIEW.md](OVERVIEW.md)）。

> **一言で**：コードを「知識グラフ（地図）」に変換し、**最小トークンで最大コンテキスト**をAIに供給するMCPサーバー。[YATA (八咫)](https://github.com/nahisaho/YATA) のフォークに [comP](https://github.com/tsucky230/comP) 直結ブリッジを加えたもの。

---

## 📊 効果の見積もり：どの用途で、どれだけ効くのか

効果は用途に依存します。正直な目安を示します。

| 用途 | 削減の目安 | なぜそうなるか |
| --- | --- | --- |
| **巨大リポジトリの概要把握** | **〜1/500**（実測） | 全読みが「統計＋主要モジュール＋公開シンボル」の読み取りに置き換わる |
| **変更の影響分析** | **大** | `analyze_impact` が波及先を **risk=high/medium/low 判定済み**で返す。LLMが行う「集計と解釈」のトークンごと消える |
| **フレームワークの正しい書き方** | **大（間接効果）** | 47フレームワークの知識グラフを `hybrid_search` で横断。**存在しないAPIを幻覚→実装→失敗→やり直し**のループを根絶 |
| **セッション引き継ぎ** | **大** | `generate_handoff` がトークン予算内で引き継ぎ文書を自動生成。前提の再説明が不要に |
| **小規模リポジトリの単発質問** | 小 | comP直結で足りる（後述の使い分け表を参照） |
| **コードと無関係な作業** | ゼロ | 対象外 |

### 数字に表れない2つの効果

**① 失敗リトライの消滅**
安価なモデルの隠れコストは「間違った前提で実装→失敗→やり直し」のループです。MAGATAMAはこれを2方向から潰します：

```
方向1（構造の誤解を防ぐ）：
  analyze_impact が波及先をリスク判定済みで提示
  → 「気づかなかった呼び出し元」起因の手戻りが消える

方向2（知識の幻覚を防ぐ）：
  hybrid_search が公式イディオムと自コードを同時提示
  → 「それっぽいが存在しないAPI」起因の手戻りが消える
```

**② 判断のオフロード（安価なモデルほど効く）**
comP直結では「関連ノードのリスト」が返り、**解釈はLLM任せ**です。高性能モデルなら解釈できますが、安価なモデルはここで間違えます。MAGATAMAは解釈（リスク判定・集計・品質分析）を**決定的なコードで済ませてから**渡すため、**モデルの判断力に依存する部分が減り、安いモデルの守備範囲が広がります**。

---

## 💡 実際にできること（5つの代表シーン）

### シーン1：見知らぬ巨大リポジトリを5分で把握
>
> 「このリポジトリは何をしていて、どこから読めばいい？」

全ファイルを開く代わりに、地図の**統計・主要モジュール・公開シンボル**だけを読んで概要を返します。本リポジトリ自身での実践例が [OVERVIEW.md](OVERVIEW.md)。

### シーン2：関数を変えたら何が壊れるか知る
>
> 「`save_graph` を触ったらどこに影響する？」

`analyze_impact` / `get_call_graph` が地図を辿り、**影響範囲（blast radius）をリスク判定つきで**返します。grepと目視のループが不要に。

### シーン3：フレームワークの流儀に沿ったコードを書く
>
> 「FastAPIの依存性注入の正しいやり方は？」

**47フレームワークの知識グラフを内蔵**（YATA由来）。`hybrid_search` が公式イディオムと自分のコードを横断検索します。

### シーン4：「このファイル、過去にどんな依頼で触ったっけ？」
>
> 「認証を作り直したい。過去セッションで何を議論した？」

comPは会話を `.comp/` に記録します。MAGATAMAの `read_external_sessions` はその**会話記録をコードと同じグラフに載せ**、言及したファイル・シンボルと接続（DISCUSSEDエッジ）します。以降、ファイルへの `get_related_entities` が**そのファイルに触れた過去の依頼**も返します。**会話の記憶とコードの地図が、ひとつの地図になります。**

### シーン5：「留守中に何が変わったか」を自動で引き継ぐ
>
> 「昨晩チームの誰かが何か変えた。影響は？」

`magatama patrol` を回しておくと、comPの地図を定期的に読み直して**前回からの差分を検出**し、各変更に影響・品質分析を添えて**comPの会話履歴に書き込みます**。次のチャットでAIが `session_recall` を呼んだ時点で、もう「何がどこで変わって、どこが痛いか」を知っています。

```bash
magatama patrol . --interval 600   # 10分ごとに巡回
magatama patrol . --once           # 単発実行（cron / CI 向け）
```

---

## 🧩 comPとMAGATAMAの関係・使い分け

```
[comP（VSCode拡張 + Rustデーモン）]
        │ ワークスペースを解析して地図を書き出す
        ▼
   .comp/index.db（SQLite, WALモード）  ← 街の地図
        │
        ├─→ comP MCP ……………… 地図を直接引く（ファイル要約・単一シンボル — 軽量）
        │
        └─→ MAGATAMA Bridge … 地図を知識グラフに取り込んで分析（39ツール）
                  │
                  ▼
      Claude Desktop / Claude Code / Cursor / Copilot
```

### 「comP直結だけで十分では？」

**単発の照会なら十分です。** MAGATAMAの価値は照会の**その先**にあります。

| | comP直結 | MAGATAMA併用 |
| --- | --- | --- |
| **影響分析** | 接続ノードのリストを返す（解釈はLLM任せ） | しきい値判定して `risk=high/medium/low` で返す。LLMの集計トークンを節約 |
| **会話記憶** | `session_recall` ＝ 部分一致のフラットなリスト | 会話がコードの隣のグラフノードになる。「このファイルに触れた過去の依頼」が1クエリ |
| **動作環境** | VSCode拡張のデーモンが必要 | index.dbを直接読むため**エディタなしのCI/cronで動く**（`patrol`） |
| **プロジェクト横断** | 1デーモン＝1ワークスペース | 複数プロジェクトの地図を1グラフに載せて横断検索 |
| **知識** | 自分のコードのみ | 47フレームワークの知識グラフを横断検索 |

一言で：**comPが地図を描き、MAGATAMAはその上で働く分析官・記録係。**

---

## 🤖 Claudeでのうまい使い方

### 使い方①：新セッションは handoff から始める

セッション終了時と開始時をこの2行で繋ぎます：

```markdown
# 終了時：
generate_handoff を実行して、今日の決定事項と未解決課題を引き継ぎ文書にして

# 翌日の開始時：
session_recall で前回の handoff を復元してから作業を始めて
```

`generate_handoff` は**トークン予算内に収まるよう自動要約**し、comP履歴に書き込むため、次セッションの `session_recall` で確実に拾えます。手書きの引き継ぎメモは不要になります。

### 使い方②：安価なモデルへの「判断済みデータ」供給

設計＝上位モデル、実装＝安価なモデル、の階層運用で真価が出ます：

```markdown
# 上位モデル（設計セッション）：
analyze_impact の結果と handoff を添えて、実装手順リストを作って

# 安価なモデル（実装セッション）：
handoff と risk=low の判定済み影響リストの範囲内でのみ実装して。
リスト外のファイルに触れる必要が出たら実装せず報告して
```

安価なモデルに渡るのは**判断済み・範囲確定済みの材料だけ**。迷子になる余地を構造的に奪います。

### 使い方③：Reviewer役に客観データを持たせる

レビューセッション（実装とは別会話）でこう指示します：

```markdown
この差分を analyze_impact / analyze_quality / find_hotspots の結果と
突き合わせてレビューして。risk=high の波及先で未修正のものを最優先で指摘
```

LLMの「感想レビュー」が、グラフ由来の**機械的検出＋LLMの解釈**という2段構えになります。

### 使い方④：patrol でレビューを非同期化

`magatama patrol` をRaspberry PiやCIで常駐させれば、**誰もチャットしていない間に差分検出と影響分析が済んでいます**。朝一番のセッションが「調査」からでなく「判断」から始められます。

### 使い方⑤：未知のOSSを読むときの型

```markdown
get_external_graph_info(path="...") で地図の鮮度を確認して。
問題なければ read_external_graph → get_graph_stats で全体像、
次に find_critical_paths で読むべき順路を出して
```

---

## 📝 CLAUDE.md への反映方法（プロンプト集）

MAGATAMAを入れても、**AI側の行動ルールを更新しなければ宝の持ち腐れ**です。以下のプロンプトをClaudeに投げると、CLAUDE.mdをMAGATAMA前提に書き換えられます。

### プロンプト例①：初期導入（MUST/NEVERの追記）

```markdown
CLAUDE.md に以下のルールを MUST/NEVER として追記してください：

MUST:
- セッション開始時に session_recall で handoff と patrol 記録を復元する
- コード全体の把握は read_external_graph + get_graph_stats を最初に使う
- 既存コードの変更前に analyze_impact を実行し、risk=high の波及先を列挙する
- フレームワークのAPIを使う実装の前に hybrid_search で公式イディオムを確認する
- セッション終了前に generate_handoff を実行する

NEVER:
- グラフ化されたプロジェクトのソース全読み
- analyze_impact を経ない既存関数のシグネチャ変更
- hybrid_search で確認していないフレームワークAPIの使用

各ルールに理由を1行添え、既存ルールとの矛盾があれば指摘してください。
```

### プロンプト例②：幻覚API事故の再発防止（違反の学習）

```markdown
先ほどあなたは存在しない FastAPI の API を使って実装し、失敗しました。
hybrid_search で事前確認していれば防げたはずです。
原因を1行で述べ、同種の事故を防ぐルールを CLAUDE.md の NEVER 節に
1行追加する形で提案してください。
```

### プロンプト例③：3段階ワークフローへの組み込み

```markdown
私の開発フローは 設計→実装→レビュー の3段階です。各段階で MAGATAMA の
どのツール（read_external_graph / analyze_impact / hybrid_search /
generate_handoff / analyze_quality / find_hotspots / session_recall）を
どの順で使うべきか、「段階別 MAGATAMA 利用手順」として CLAUDE.md に
追記する原稿を書いてください。トークン最小化を最優先とします。
```

### プロンプト例④：責任分界の固定（comP・Claude メモリーとの棲み分け）

```markdown
CLAUDE.md に以下の1行を追記してください：
「記憶の正は3層で管理する。コード構造と影響分析の正は MAGATAMA（グラフ）、
セッション記録の正は comP（.comp/）、人物・好みの正は Claude メモリーとし、
層をまたいで同じ情報を重複記録しない」
```

> 💡 CLAUDE.mdは「失敗のたびに1行育てる」もの。違反→原因→ルール追加のループを回すのが最短です。

---

## 🚀 セットアップ（実例つき）

ゴール：**① comPでコードを索引化 → ② MAGATAMAをインストール → ③ AIツールにMCPサーバー登録 → ④ 動作確認**

### Step 1. comPをVSCode拡張として導入し、索引を作る

1. VSCodeにcomP拡張（`tsucky230.comp-vscode`）をインストール（手順は [comPリポジトリ](https://github.com/tsucky230/comP) 参照）
2. プロジェクトフォルダをVSCodeで開く
3. comPが自動で解析し、**`<project>/.comp/index.db`**（SQLite, WALモード）に地図を書き出す。初回のみ時間がかかり、以降は差分更新

> 確認：`.comp/` フォルダに `index.db` があればOK。

comP自体をMCPサーバーとしてAIに繋ぐ場合の `.mcp.json`（本リポジトリでの実例）：

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

> `COMP_WORKSPACE_ROOT` は索引化したいフォルダに、パス中のバージョン（`0.8.1`）はインストール済みの拡張バージョンに合わせてください。

### Step 2. MAGATAMAをインストール

```bash
# ソースから（本リポジトリ）
git clone https://github.com/tsucky230/MAGATAMA.git
cd MAGATAMA
uv sync --all-packages       # uv未導入なら https://astral.sh/uv

# または PyPI から
pip install magatama
```

確認：

```bash
magatama info        # バージョンとツール数（39）が表示されればOK
```

### Step 3. MCPサーバーとして登録

#### Claude Desktop（Windows）

`%APPDATA%\Claude\claude_desktop_config.json`：

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

プロジェクトルートの `.vscode/mcp.json`：

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

PyPI導入なら `"command": "magatama", "args": ["serve"]` でOK。Cursor / Continue・SSEモードは [AIツール設定ガイド](docs/AI_TOOLS_SETUP.md) 参照。

### Step 4. 接続して使う

AIツールを再起動し、チャットで：

```
get_external_graph_info(path="e:/dev/myproject") で comP の地図を確認して。
問題なければ read_external_graph して、プロジェクトの概要を教えて
```

LLMがcomPの地図をMAGATAMAに取り込み、**全ソースを読まずに**プロジェクトを概観します。

---

## 🎬 試してみる：プロンプト→出力例

### 例A：プロジェクト概要

**プロンプト**

```
read_external_graph(path="e:/dev/MAGATAMA") してから get_graph_stats で
このプロジェクトの規模と構造を要約して
```

**出力例（実データ）**

```
✓ 取り込み完了（203ファイル / 3,829シンボル）
- 言語: Python 123 / Markdown 38 / JSON 36 / YAML 1
- 最大モジュール: framework_usecase.py（133シンボル）
- 構成: packages/magatama-core（エンジン）+ packages/magatama-mcp（MCP+CLI）
→ Clean Architecture（domain → application → infrastructure → interface）
```

### 例B：影響分析

**プロンプト**

```
search_entities(query="save_graph") で対象を特定し、analyze_impact で
この関数を変更した場合の影響範囲を教えて
```

**出力例**

```
対象: _handle_save_graph (mcp_server.py:442)
影響の可能性: `save` コマンド (cli/main.py)、parse --output の保存経路
→ 変更時はこの2経路のテストを確認
```

### 例C：フレームワークのイディオム（YATA由来）

**プロンプト**

```
hybrid_search(query="FastAPI dependency injection") で公式の流儀と、
自分のコードでの該当箇所を横断検索して
```

**出力例**

```
[Framework] FastAPI: Depends() を関数引数で宣言（Router/Dependency）
[Local]    （該当なし）→ DI未使用。導入候補: routes 層
```

> CLIだけで試したい場合は、地図をJSONに永続化して使い回せます：
>
> ```bash
> magatama parse ./src -o graph.json
> magatama stats --graph graph.json
> magatama query "UseCase" --type class --graph graph.json
> ```

---

## 🔧 MCPツール（39）

LLMはこの中から**必要なツールだけを自律的に選んで**使います。

**🔌 comP Bridge（5）— 地図と記憶の取り込み**

| ツール | 説明 |
| --- | --- |
| `read_external_graph` | comP索引を知識グラフに読み込む（`mode=replace`/`merge`） |
| `read_external_sessions` | comP会話履歴をSESSIONノードとして取り込み、言及ファイル・シンボルと接続（DISCUSSEDエッジ） |
| `get_entity_history` | ファイル/シンボルを「過去にどの依頼が触ったか」（新しい順）＋現在の影響分析を1コールで返す |
| `generate_handoff` | 引き継ぎMarkdownを生成（直近セッション＋git状態、トークン予算制御）。全文は`.magatama/handoffs/`、履歴には要約1行を記録 |
| `get_external_graph_info` | 読み込まずにcomP索引の統計を確認（鮮度チェック） |

**📁 コア（10）— 解析と検索**

`parse_file` / `parse_directory` / `search_entities` / `get_entity` / `get_related_entities` / `get_graph_stats` / `save_graph` / `load_graph` / `list_supported_languages` / `get_language_for_file`

**🧠 フレームワーク知識（7）— 47フレームワークの内蔵地図**

`list_frameworks` / `search_framework_docs` / `search_all_frameworks` / `find_code_patterns` / `get_framework_entity_context` / `framework_semantic_search_tool` / `framework_find_by_pattern`

**🔍 検索・コンテキスト（4）／📚 ドキュメント・推薦（4）**

`semantic_search` / `find_by_pattern` / `get_code_context` / `find_usage_examples` ・ `generate_documentation` / `recommend_code` / `analyze_impact` / `find_critical_paths`

**🔎 ハイブリッド検索・品質（4）／🤖 AI支援（5）**

`hybrid_search` / `analyze_quality` / `track_evolution` / `find_hotspots` ・ `get_coding_guidance` / `detect_patterns` / `check_api_compatibility` / `navigate_code` / `get_call_graph`

**MCP Prompts**: `analyze_codebase` / `explain_entity` / `find_dependencies`　**MCP Resources**: `magatama://graph/stats`

---

## 💻 CLIコマンド（ターミナルの人間向け）

| コマンド | 何をするか | 例 |
| --- | --- | --- |
| `parse` | 知識グラフを構築（`-o` で保存） | `magatama parse ./src -o graph.json` |
| `query` | エンティティ検索 | `magatama query "User" -t class -g graph.json` |
| `stats` | 統計表示 | `magatama stats -g graph.json` |
| `serve` | MCPサーバー起動 | `magatama serve` / `--transport sse --port 8080` |
| `watch` | 監視と自動更新（`-o` で自動保存） | `magatama watch ./src -o graph.json` |
| `patrol` | comPの地図を定期巡回し、差分＋影響分析をcomP履歴に記録 | `magatama patrol . --interval 600` |
| `validate` | グラフ整合性チェック（`--repair`） | `magatama validate -g graph.json --repair` |
| `info` | サーバー情報・ツール一覧 | `magatama info` |

> 注：`parse`/`query`/`stats` は**プロセス間で状態を持ちません**。`parse -o` でJSONに書き出し、`query`/`stats` の `--graph` で読み込んでください。AI連携では常駐の `serve` プロセスがグラフを保持します。

---

## 🏗️ 対応言語・フレームワーク

- **24言語**: Python, TypeScript/JS, Rust, Go, Java, Kotlin, Scala, C/C++, C#, Swift, Objective-C, PHP, Ruby, Dart, Elixir, Haskell, Julia, Lua, Groovy, SQL, Zig, YAML
- **47フレームワーク**（457K+エンティティ）: Django/Flask/FastAPI, React/Vue/Angular/Next.js, Actix/Axum/Tauri, Gin/Echo, Phoenix, Spring Boot, Rails, Laravel, SwiftUI, Jetpack Compose 等

---

## 🛠️ 開発

```bash
uv sync --all-packages
uv run pytest                         # テスト（918）
uv run pytest --cov=magatama_core --cov=magatama_mcp
uv run ruff check . && uv run mypy packages/
```

```
MAGATAMA/
├── packages/
│   ├── magatama-core/   # 知識グラフエンジン（ライブラリ）
│   └── magatama-mcp/    # MCPサーバー + CLI（magatama コマンド）
├── steering/            # プロジェクトメモリ・ルール
└── storage/specs/       # 設計ドキュメント（要件、C4、ADR）
```

**Clean Architecture** で構築。詳細と計測は [OVERVIEW.md](OVERVIEW.md)。

---

## 📜 ライセンス／クレジット

MITライセンス。本プロジェクトは [YATA](https://github.com/nahisaho/YATA)（Copyright (c) 2025 nahisaho, MIT License）のフォークにcomP Bridgeを追加したものです。

- [YATA](https://github.com/nahisaho/YATA) by **nahisaho** — 土台
- [comP](https://github.com/tsucky230/comP) by **tsucky230** — コードインデクサー
- [Model Context Protocol](https://modelcontextprotocol.io/) / Tree-sitter / NetworkX / FastMCP

---

## 📖 ドキュメント

- [プロジェクト概要＋トークン計測（OVERVIEW.md）](OVERVIEW.md)
- [AIツール設定ガイド](docs/AI_TOOLS_SETUP.md)
- [知識データベース更新ガイド](docs/KNOWLEDGE_UPDATE_GUIDE.md)
- [トラブルシューティング](docs/TROUBLESHOOTING.md)
- [English README](README.md) / [CHANGELOG](CHANGELOG.md)

---

## 💖 支援する

MAGATAMAは完全無料・オープンソースです。役に立ったら開発を支援していただけませんか？

- ☕ **[GitHub スポンサー](https://github.com/sponsors/tsucky230)** — 開発を応援
- 💖 **このリポジトリに Star をつける** — 他の人に知らせてください

---

## 📛 名前について

**YATA（八咫）** は「非常に大きい」を表す古語で、巨大なコードベースとフレームワーク知識を丸ごと扱う志を表します。**MAGATAMA（勾玉）** は「大きな力を凝縮した小さな石」——その広大さから本質を抽出し、高密度でLLMに届ける役割を表します。三種の神器のひとつ、勾玉のように。
