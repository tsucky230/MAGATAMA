# ADR-005: マルチLLM Director/ルーター化を却下し、MCPサーバーの立場を維持する

**Project**: MAGATAMA (勾玉)
**ADR ID**: ADR-005
**Status**: Accepted
**Date**: 2026-09-07
**Deciders**: MAGATAMA Team
**Related Requirements**: なし（新規機能追加ではなく、提案の却下を記録するADR）

---

## Context

外部から「MAGATAMAをマルチLLMのDirector（配車係）にし、Claude/Geminiへタスクを
動的ルーティングする」という進化提案を受けた。提案の中核は以下の3点：

1. MAGATAMAが呼び出し元（ホストクライアント）に代わってタスクを分析し、
   Claude/Geminiのどちらに投げるかを動的に決定する「Director」化
2. モデル間のルーティングロジックをMAGATAMA内部に実装する
3. ホストごとに異なるプロンプト形式へ動的に翻訳する機能

提案の一部（人間の修正差分から暗黙のルールを検知し、自動でルールファイルへ
書き込む「Autonomic Memory」相当の機能）も含まれていたが、これは本ADRの
Decision 2で別途扱う。

MAGATAMAは現在、以下のアーキテクチャで動作している：

- **MCPサーバー**として、ホストクライアント（Claude Code、Claude Desktop、
  Cursor等）から呼ばれる**受動側**（39 MCPツールを提供するのみで、自ら他の
  LLMやツールを呼び出すことはない）
- Clean Architecture（domain / application / infrastructure）に基づく既存資産
- 姉妹プロジェクトcomPとの連携（comP Bridge: `read_external_graph` /
  `get_external_graph_info` 等）

## Decision

**MAGATAMAはMCPサーバーの立場を維持し、マルチLLMのDirector/ルーターにはならない。**

提案の中核コンセプト（Director化・モデル間ルーティング・プロンプト動的翻訳）を
却下する。

### 理由

| 観点 | Director化した場合 | 現行（MCPサーバー） |
|------|---------------------|----------------------|
| **役割** | ホストクライアントに代わって能動的に他LLMを呼ぶ側 | ホストから呼ばれる受動側 |
| **アーキテクチャ影響** | 呼び出し方向の反転が必要。既存39ツール・Clean Architecture資産（domain/application/infrastructure の依存方向）と根本的に整合しない作り替えになる | 既存資産をそのまま活用できる |
| **責務の所在** | モデル使い分けのポリシーをMAGATAMAが持つ | ホスト側（Claude Code等の harness）がモデル使い分けを既に担っている（例: このリポジトリのYASAKANI方針） |
| **重複** | ホストのオーケストレーション機能と機能が重複する | 重複しない。MAGATAMAは「コンテキストを提供する」ことに専念 |

1. **アーキテクチャ不整合**: MAGATAMAはMCPサーバー（ホストクライアントから
   呼ばれる受動側）であり、逆に呼ぶ側（Director）になるには現行アーキテクチャの
   作り替えに等しく、既存の39ツール・Clean Architecture資産と整合しない。
2. **責務の逸脱**: 呼び出し元（Claude Code等）でのモデル使い分けは、MAGATAMAでは
   なくホスト側の役割分担ポリシーの領分であり、MAGATAMAの責務ではない。

一方、提案の一部（Scene 2/4相当のシナリオ）は `analyze_impact` /
`read_external_sessions` として既に実装済みであり、新機能としてではなく
「磨き込み・普及」の対象として扱う（[steering/product.ja.md](../../steering/product.ja.md) Phase 1 参照）。

### Decision 2: 「暗黙ルールの自動書き込み」機能も却下（人間承認を必須とする）

提案に含まれていた、人間の修正差分から暗黙のルールを検知し、検知結果を
**自動で**ルールファイル（CLAUDE.md / steering等）に書き込む機能
（Autonomic Memory相当）についても、**自動書き込みは却下する**。

**理由**: ルールファイルはプロジェクトの意思決定・制約を人間が読んで運用する
ドキュメントであり、検知ロジックの誤判定（過学習・一時的な例外パターンの
恒久ルール化等）がそのまま人間の判断を経ずに反映されると、レビュー不能な
劣化が蓄積するリスクがある。

将来この方向性を検討する場合は、「検知結果を提示し、人間が承認したものだけを
書き込む」設計（提案 → レビュー → 承認 → 書き込み、の各段階を分離する）を
必須の前提とする（[steering/product.ja.md](../../steering/product.ja.md) Phase 2 参照）。

## Consequences

### Positive

1. **既存資産の保全**: Clean Architecture・39ツール構成を作り替えずに済む
2. **責務の明確化**: 「コンテキスト提供」に専念することで、ホスト側の
   オーケストレーション機能との重複・競合を避けられる
3. **リスク回避**: ルールファイルへの誤った自動書き込みによる劣化を防げる

### Negative

1. 提案者が期待していた「MAGATAMA単体でのマルチLLM活用」は実現しない
2. モデル使い分けの恩恵を受けるには、ホスト側（Claude Code等）の設定・
   ポリシーに依存する

### Mitigations

| リスク | 対策 |
|--------|------|
| 提案の価値が失われる | 提案の一部（Scene 2/4相当）は既存ツールとして実装済みであることを明記し、普及（README/ドキュメント改善）で価値を活かす |
| 将来の再提案 | Phase 2として「人間承認必須」の設計条件を明記し、条件を満たせば再検討の余地を残す |

## References

- [steering/product.ja.md](../../steering/product.ja.md) — Product Roadmap（Phase 0/1/2）
- [ADR-001: Clean Architecture](ADR-001-clean-architecture.md)
- [ADR-002: MCP Python SDK採用](ADR-002-mcp-protocol.md)

---

## Change History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-09-07 | MAGATAMA Team | Initial version |
