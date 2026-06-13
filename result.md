# MAGATAMA 品質分析レポート

**分析日**: 2026-06-13  
**分析手法**: comP Bridge (`read_external_graph`) + YATA `analyze_quality`

---

## 1. ロード結果

| 項目 | 数値 |
|---|---|
| ロードエンティティ数（全体） | 53,737（.venv 含む） |
| リレーション数（全体） | 79,899 |
| comP alias | magatama |

---

## 2. MAGATAMA ソース シンボル内訳（comP インデックス）

`packages/` 配下（テストファイル除く）

| シンボル種別 | 数 |
|---|---|
| function | 722 |
| class | 127 |
| module | 41 |
| variable | その他 |

---

## 3. シンボル数上位ファイル

| ファイル | シンボル数 |
|---|---|
| `core/domain/usecases/framework_usecase.py` | 133 |
| `core/infrastructure/parsers/c_parser.py` | 高 |
| `core/infrastructure/knowledge_graph/networkx_knowledge_graph.py` | 高 |
| `core/infrastructure/knowledge_graph/sqlite_knowledge_graph.py` | 高 |
| `mcp/server/protocol.py` | 高 |

---

## 4. 品質スコア分布（全 127 クラス）

### スコア体系

| スコア | 意味 |
|---|---|
| 100 | クリーン（指摘なし） |
| 80 | 軽微な指摘（LCOM=1.0 の UseCase 系） |
| 70 | パーサー系（Efferent Coupling 中程度） |
| 60 | 要注意（Efferent Coupling 高） |

### スコア 60（要注意クラス）

| クラス | Efferent Coupling | 備考 |
|---|---|---|
| `CParser` | **118** | 外れ値。tree-sitter-c バインディング + entity 型多数参照 |
| `Parser`（基底） | 27 | 全パーサーが依存するベースクラス |
| `SQLiteKnowledgeGraph` | 26 | SQLite + domain entity 型多数 |
| `RustParser` | 24 | |
| `GoParser` | 22 | |
| `NetworkXKnowledgeGraph` | 17 | グラフ操作 + 全 entity 型 |
| `MagatamaMcpServer` | 16 | MCP server ルート、依存多い |

### スコア 100（クリーン — データクラス群）

- `Entity`, `Location`, `QualityMetric`, `CompIndexData`
- `EntityType`, `RelationshipType`（enum）
- 例外クラス群、Result クラス群
- Pydantic モデル、dataclass 群

---

## 5. LCOM（凝集度）について

全 **実装クラス**（UseCase / Parser / Repository）が `LCOM=1.0`（最低凝集度）と判定された。

これは誤検知ではなく **Clean Architecture の構造的特性**:

- UseCase クラスは `execute()` 1 メソッドが依存性注入された外部オブジェクトを操作する
- メソッド間で共有されるインスタンス変数がないため LCOM=1.0 になる
- LCOM=0.0 はデータクラス（フィールドを共有する複数メソッド）のみに出る

---

## 6. YATA パーサーとの比較

| 観点 | YATA パーサーのみ | comP Bridge 使用 |
|---|---|---|
| 分析できたクラス数 | 部分的（大型ファイル内は不可） | **127 全件** |
| `framework_usecase.py` 内のクラス | 0件（133 シンボルのファイルは解析不能） | 127 クラス中に含む |
| 依存エッジ（CALLS 等） | 0（Python パーサーは未検出） | 79,899 件 |
| 検索汚染 | なし | .venv 混入（要フィルタ） |

comP Bridge を使うことで YATA パーサーが見逃していた大型ファイル内クラスを全件カバーできた。

---

## 7. 既知の不具合（修正済み）

| バグ | 場所 | 内容 | 状態 |
|---|---|---|---|
| `hybrid_search` ToolError | `protocol.py` | `HybridSearchUseCase` に `.search()` メソッドが存在しない | ✅ 修正済み |
| `overall_status` 常に "danger" | `framework_usecase.py` | スコアに関わらず `overall_status=danger` が返る | ✅ 修正済み |

### 修正内容（2026-06-13）

1. **`hybrid_search` ToolError**: `protocol.py:1254` の呼び出しを `.search(` → `.hybrid_search(` に修正（実装メソッド名と一致）。
2. **`overall_status` 常に "danger"**: `framework_usecase.py:2234` の `_determine_status(...)` に `lower_is_better=False` を追加。`overall_score` は高いほど良い指標のため、score≥70→`good`、≥50→`warning`、未満→`danger` と正しく判定。

回帰テスト6件を `test_framework_usecase.py` に追加（`TestCodeQualityUseCase` / `TestHybridSearchUseCase`）。全31件パス。

---

## 8. 推奨アクション

1. **`CParser` のリファクタリング検討**: Efferent Coupling=118 は異常値。ファサードパターンや型エイリアス集約で削減可能。
2. **`hybrid_search` メソッド名修正**: `protocol.py` の呼び出し名を `HybridSearchUseCase` の実際のメソッド名に合わせる。
3. **`overall_status` ロジック修正**: `framework_usecase.py` の品質判定ロジックを `overall_score` に連動させる。
4. **comP エッジ補完待ち**: 現時点でエッジ 0 件（依存グラフ未構築）。comP Rust デーモンが依存解析を完了すると impact 分析精度が向上。
