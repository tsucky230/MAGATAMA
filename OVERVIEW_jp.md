# MAGATAMA 実演カタログ & プロジェクト概観

> 🇺🇸 English version: [OVERVIEW.md](OVERVIEW.md)
> ベースの考え方は [README_jp.md](README_jp.md) を参照。

---

## 🗺️ この文書の狙い —「地図を渡す」とはどういうことか

大量のソースコードを短期間に読まなければいけない人を想像してください。
新人のオンボーディング、引き継いだレガシー、OSS への初コントリビュート……
**全ファイルを開いて読む時間はありません**。欲しいのは「どこに何があるか」の
**地図**です。

- **comP** が地図を作り（コードを解析して `.comp/index.db` に蓄積）、
- **MAGATAMA**（または comP MCP）が、その地図から **LLM が今必要な区画だけ**を
  抜き出して渡します。

この文書では、その地図を使って **実際に何ができるのか** を
「プロンプト → 出力サンプル」の形で**ふんだんに**示します。最後に、
地図を使った場合と使わなかった場合の **トークン消費を実測比較**します。

> 📌 **表記の約束**
> - 🟢 **実測** … 実際に comP / MAGATAMA を動かして得た本物のデータ。
> - 🔵 **形式イメージ** … ツールの応答フォーマットを示す代表例（説明用）。
>   数値・件数は説明のための例で、環境により変わります。

---

# 第 1 部 ｜ comP の地図で、この MAGATAMA 自身を把握する 🟢

> 🟢 **実測**: comP インデックス（**203 ファイル / 3,829 シンボル**）を
> Claude Code から MCP 経由で読み、全ソースを読まずに以下を生成しました。

## 1. 一言で言うと

コードベースを「知識グラフ」に変換し、AI コーディング支援ツール（Claude
Desktop・Copilot 等）へ**最小トークンで文脈を渡す MCP サーバ**。YATA を
フォークし、別ツール comP のインデックスを再解析なしで取り込む機能を追加した。

## 2. 解決する課題と価値

LLM にコードを理解させると全文を読ませてトークンを浪費しがち。MAGATAMA は
**コードを構造（エンティティ＋関係）に圧縮**し、検索・影響分析・呼び出しグラフ
だけを渡す。完全ローカル実行で外部送信なし。

## 3. 全体像

```text
[comP Daemon] ─→ .comp/index.db (SQLite)
                       │ 読み取り専用で接続
ソース ─Tree-sitter→ [MAGATAMA] ─→ NetworkX知識グラフ ＋ 47FW事前知識
                       │
                       ▼
       MCP Server (FastMCP / 36 tools) ・ CLI (Click)
                       │
                       ▼
          Claude Desktop / Cursor / Copilot
```

設計は **Clean Architecture**（domain → application → infrastructure → interface）。

## 4. ディレクトリ構成

| パス | 役割 |
|---|---|
| `packages/magatama-core/` | 知識グラフエンジン（ライブラリ）。24言語パーサ・NetworkXグラフ・comP Bridge |
| `packages/magatama-mcp/` | MCPサーバ＋CLI（`magatama` コマンドの実体） |
| `knowledge_graphs/` | 47フレームワークの事前学習済みグラフ（JSON 36ファイル） |
| `storage/specs/` | 設計書（要件・C4図・ADR） |
| `steering/` | プロジェクト規約・メモリ |
| `docs/` | 利用ガイド（日英、Markdown 38ファイル） |

## 5. 主要技術スタック

- **言語比率（comP実測）**: Python 123 / Markdown 38 / JSON 36 / unknown 5 / YAML 1
- **解析**: `tree-sitter` ＋ 言語別パーサ23種（Python/TS/Rust/Go/Java/C#…）
- **グラフ**: `networkx` ／ **データ検証**: `pydantic` ／ **ログ**: `structlog`
- **MCP**: `mcp>=1.0` ／ **CLI**: `click`＋`rich` ／ **SSE**: `uvicorn`+`httpx` ／ **監視**: `watchdog`
- **構成**: uv モノレポ（`magatama-core` ライブラリ ＋ `magatama` アプリ）、Python 3.11+、MIT

## 6. 使い方

```bash
magatama parse ./src -o graph.json        # 解析→知識グラフ保存
magatama stats --graph graph.json         # 統計表示
magatama query "UseCase" --type class --graph graph.json
magatama serve                            # MCPサーバ起動（AIツールから利用）
```

## 7. 現在の状態

- **成熟度**: `Development Status :: 3 - Alpha`（pyproject classifiers）
- **テスト**: 794件・カバレッジ76%（README）。手元でCLIテストの成功を確認。
- **既知の制約 / 要確認**: comP インデックスの依存エッジ数が `0`（要確認）。
  インデックスがやや古く削除済みファイルが残存 → 再インデックスで解消見込み。

## 8. 次に読むべきファイル

1. `README_jp.md` — 全機能と設計思想の入口
2. `packages/magatama-core/src/magatama_core/application/usecases/comp_usecase.py` — comP Bridge の中核
3. `packages/magatama-core/src/magatama_core/infrastructure/storage/comp_index_reader.py` — SQLite→グラフ変換
4. `packages/magatama-mcp/src/magatama_mcp/server/mcp_server.py` — 36ツールの登録口
5. `packages/magatama-core/src/magatama_core/application/usecases/framework_usecase.py` — 最大モジュール（133シンボル）

---

# 第 2 部 ｜ 実演カタログ: プロンプト → 出力サンプル

AI ツール（Claude Desktop / Copilot / Claude Code）のチャットに**そのまま投げる**
プロンプトと、返ってくる出力のイメージを機能別にまとめました。

## 🅰️ comP の地図でプロジェクトを概観する

### A-1. 「このリポジトリ、5 分で教えて」

**プロンプト**

```text
get_external_graph_info(path="e:/dev/myproject") で comP の地図の鮮度を確認して。
問題なければ read_external_graph(path="e:/dev/myproject") で取り込み、
get_graph_stats と search_entities を使って、
「目的・構造・主要モジュール・どこから読むべきか」を 10 行以内で要約して。
```

🟢 **実測**（この MAGATAMA 自身に対して実行した結果の要約）

```text
✓ 地図を取り込み: 203 ファイル / 3,829 シンボル
- 目的    : コードを知識グラフ化し AI に最小トークンで文脈を渡す MCP サーバ
- 構造    : magatama-core（エンジン）＋ magatama-mcp（MCP+CLI）の 2 パッケージ
- 言語    : Python 123 / Markdown 38 / JSON 36
- 最大モジュール: framework_usecase.py（133 シンボル）
- 設計    : Clean Architecture（domain→application→infrastructure→interface）
- 入口    : comp_usecase.py（comP Bridge の中核）から読むのがおすすめ
```

### A-2. 「どのファイルが“重い”のか教えて（ホットスポット候補）」

**プロンプト**

```text
list_indexed_files の結果から、シンボル数が多い上位 5 ファイルを挙げて、
それぞれ何の役割か一言で説明して。
```

🟢 **実測**（comP の Top Files by Symbol Count より）

```text
1. framework_usecase.py            133  フレームワーク知識のユースケース群
2. docs/KNOWLEDGE_UPDATE_GUIDE.md   92  知識DB更新ガイド
3. sqlite_storage.py                68  SQLite 永続化
4. test_framework_usecase.py        81  上記のテスト
5. steering/product.ja.md           68  プロダクト方針メモ
```

---

## 🅱️ 旧 YATA でできること（フレームワーク知識・横断検索・分析）

MAGATAMA は YATA の 36 ツールをそのまま継承しています。代表的なものを、
プロンプトと出力イメージで紹介します。

### B-1. フレームワークの作法を引く — `search_framework_docs`

**プロンプト**

```text
list_frameworks で対応フレームワーク一覧を見せて。
そのうえで search_framework_docs(framework="fastapi", query="dependency")
で FastAPI の依存性注入まわりの主要エンティティを教えて。
```

🔵 **形式イメージ**

```text
[frameworks] 47 件: fastapi, django, flask, react, vue, axum, gin, phoenix, ...
[fastapi / "dependency"]
  - Depends            (function)  ルート関数の引数に宣言して依存を注入
  - Dependency         (concept)   再利用可能な依存プロバイダ
  - Security           (function)  認可付き依存（OAuth2 等）
```

### B-2. 自分のコード × 公式作法を一気に — `hybrid_search`

**プロンプト**

```text
hybrid_search(query="retry with backoff") で、
公式フレームワークの定石と、うちのコードの該当箇所をまとめて出して。
```

🔵 **形式イメージ**

```text
[Local]     util/http.py:42  request_with_retry()  ← 既に指数バックオフ実装あり
[Framework] tenacity: @retry(wait=wait_exponential())  公式定石
→ 自前実装を tenacity に寄せると保守が楽になります。
```

### B-3. 変更の影響範囲 — `analyze_impact` / `get_call_graph`

**プロンプト**

```text
search_entities(query="save_graph") で対象を特定し、
analyze_impact でこの関数を変えたときの影響範囲、
get_call_graph で呼び出し関係を見せて。
```

🔵 **形式イメージ**（対象は 🟢 実在: `_handle_save_graph`）

```text
[impact] _handle_save_graph (mcp_server.py:442)
  ← 呼ばれる: save コマンド (cli/main.py), parse --output の保存処理
  → 依存:    NetworkXKnowledgeGraph.save(), entities.count()
[call graph]
  save (CLI) ──► call_tool("save_graph") ──► _handle_save_graph ──► graph.save()
→ 変更時は CLI save と parse --output の 2 経路をテストしてください。
```

### B-4. デザインパターン検出 — `detect_patterns`

**プロンプト**

```text
detect_patterns でこのコードベースに使われているデザインパターンを挙げて、
代表的な実装箇所を 1 つずつ示して。
```

🔵 **形式イメージ**

```text
- Repository    : domain/repositories/*  （永続化の抽象）
- Use Case      : application/usecases/*  （ビジネスロジック）
- Strategy      : infrastructure/parsers/* （言語別パーサの切替）
- Adapter       : comp_index_reader.py     （SQLite → グラフ）
```

### B-5. コード品質メトリクス — `analyze_quality` / `find_hotspots`

**プロンプト**

```text
analyze_quality で複雑度や結合度の気になる箇所を、
find_hotspots で Git 履歴上「変更が集中している」ファイルを教えて。
```

🔵 **形式イメージ**

```text
[quality] 高複雑度: framework_usecase.py（多機能ゆえ分割候補）
[hotspots] 直近で変更頻度が高い: cli/main.py, mcp_server.py
→ 仕様変更の波及点。レビュー時の重点対象に。
```

### B-6. ドキュメント自動生成 — `generate_documentation`

**プロンプト**

```text
generate_documentation(entity="LoadCompIndexUseCase") で、
この中核クラスの docstring 草案を作って。
```

🔵 **形式イメージ**

```text
LoadCompIndexUseCase — comP の index.db を知識グラフに取り込むユースケース。
  load(path, mode="replace"|"merge") -> 取り込み結果（件数・除去数・メタdata）
  関連: CompIndexReader（読取）, NetworkXKnowledgeGraph（格納）
```

> これらの出力は、地図（インデックス）があるからこそ **LLM が全文を読まずに**
> 生成できます。地図が無ければ、同じ答えを得るのに毎回ソースを読み直すことに
> なります — それが次のトークン比較です。

---

# 第 3 部 ｜ トークン消費の実測比較: 地図あり vs 地図なし 🟢

「上の概観（第 1 部）を LLM が作るのに必要なトークン量」を、**comP の地図を
使った場合**と**使わずに全ソースを読んだ場合**で実測しました。

## 計測方法

- 対象: `packages/magatama-core/src` と `packages/magatama-mcp/src` 配下の
  Python ソース（テスト・`__pycache__` を除く **64 ファイル**）。
- トークン算定: `tiktoken` の `cl100k_base` を代理トークナイザとして使用
  （Claude の正確なトークナイザは非公開のため**近似値**。傾向比較が目的）。
- 計測スクリプト: `scripts/measure_overview_tokens.py`（再現可能）。
  再現コマンド: `uv run --with tiktoken python scripts/measure_overview_tokens.py`
  （`tiktoken` が無い環境では自動で chars/4 近似にフォールバック）。

## A. 地図あり（comP の構造化サマリを読む）

| 参照したデータ | トークン数 |
|---|---:|
| 概観の生成に実際に使ったサマリ（統計＋言語比率＋主要ファイル） | **289** |
| comP インデックス全エクスポート（全 203 ファイルのシンボル列挙） | 50,515 |

## B. 地図なし（全ソースを直読み）

| 読み込んだデータ | 文字数 | トークン数 |
|---|---:|---:|
| ソース 64 ファイルの全文 | 730,411 | **145,978** |

## 結果

| 方式 | トークン数 | B 比 削減率 | 倍率 |
|---|---:|---:|---:|
| **B. 全ソース直読み** | 145,978 | — | 基準 |
| A. comP インデックス全エクスポート | 50,515 | **−65.4%** | 2.9× 少 |
| **A. comP サマリ（概観に実使用）** | **289** | **−99.8%** | **約 505× 少** |

---

## 🎁 まとめ — なぜ「お得」なのか

- **速い**: 全ファイルを読ませる待ち時間が消える。地図の該当区画だけを見る。
- **安い**: 概観なら **約 1/500 のトークン**。API 課金でもコンテキスト枠でも効く。
- **広い**: 24 言語＋47 フレームワークの作法を横断検索（YATA 由来の 36 ツール）。
- **安全**: 完全ローカル。コードは外に出ない。
- **楽**: VSCode に comP を入れて開くだけで地図は自動更新。あとは AI に聞くだけ。

> 大量のコードを前に「どこから読めば…」と固まる時間を、地図が消してくれます。
> まずは [README_jp.md](README_jp.md) の **Step 1〜4** を 10 分で試してみてください。

> 注: トークン数は `cl100k_base` による近似で、絶対値はモデルにより前後します。
> 重要なのは桁オーダーの差（数百 vs 約15万トークン）で、これは安定した傾向です。
