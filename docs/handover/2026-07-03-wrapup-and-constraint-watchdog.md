# 引継書: /wrapup スキル + 制約番犬 hook の実装

作成日: 2026-07-03
対象リポジトリ: `e:\dev\MAGATAMA`
実装者向け: この文書だけで実装が完結するように書いてある。不明点は「既知の問題」節を先に読むこと。

---

## 0. 背景と目的

このプロジェクトでは **comP**（VSCode 拡張 + Rust デーモン。コードをインデックスし `.comp/index.db` に保存。v0.9 からトーク履歴インデックス機能あり）と **MAGATAMA**（comP のインデックスを知識グラフとして分析する MCP サーバー）を併用している。

作るものは 2 つ。どちらも「comP の会話履歴（記憶）と、コード/git の現実を突合する接着剤」である。

1. **案1: `/wrapup` スキル（言行不一致チェッカー）** — セッション中に「やる」と言ったことと、実際の git 変更を突合して漏れを報告する
2. **案2: 制約番犬（PreToolUse hook）** — 「修正禁止」と記録されたファイルを LLM が編集しようとした瞬間、警告をコンテキストに注入する

---

## 1. 利用可能な道具（実在確認済み）

### comP MCP ツール（サーバー名 `comp`、`.mcp.json` に設定済み）

| ツール | 用途 |
|---|---|
| `mcp__comp__session_recall` | 過去の会話履歴を取得。`{query: "キーワード"}` でフィルタ、`{limit: N}` で件数指定 |
| `mcp__comp__session_log` | 会話・作業内容を履歴に明示的に記録 |
| `mcp__comp__get_git_diff_context` | git diff のコンテキストを取得 |
| `mcp__comp__get_dependencies` | シンボルの依存を取得（`direction: "in"` で被依存＝dependents） |
| `mcp__comp__get_impact_graph` | シンボル変更の影響範囲（要 numeric symbol_id） |
| `mcp__comp__get_project_overview` | プロジェクト統計（**注意: 出力が 12 万文字超になる。直接呼ぶとコンテキストが溢れる**） |

### Claude Code の機構

- **スキル**: `.claude/skills/<name>/SKILL.md` を置くと `/name` で起動できる
- **hooks**: `.claude/settings.json` の `hooks` キー。今回使うイベント:
  - `PreToolUse`（matcher: `Edit|Write`）— ツール実行前に発火。stdin に JSON が来る
  - hook が stdout に返す JSON の `hookSpecificOutput.additionalContext` で **モデルのコンテキストにテキストを注入できる**

### 実行環境

- Windows 11。hooks の `command` は Git Bash (POSIX sh) で実行される
- `jq` の存在は**未確認**。hook スクリプト実装時に `command -v jq` で確認し、無ければ grep/sed ベースにフォールバックするか、導入を README に明記すること

---

## 2. 現在のリポジトリ状態

前セッションの試作物は以下の通り。実装時の参考になるが、動作保証はない。

| ファイル | 状態 | 扱い |
|---|---|---|
| `.claude/settings.json` | 存在しない（リセットで削除）| 案2実装時に新規作成 |
| `CLAUDE.md` | 存在しない | comP constraint tracking の説明は実装後に追加 |

### ⚠️ 既知の問題（必ず読むこと）

1. **リポジトリが reset された**。前セッションの試作ファイルは物理的に削除されている。この引継書が唯一の実装仕様。
2. **`.mcp.json` はローカル設定として .gitignore に登録済み**。各開発環境で個別に設定が必要。
3. **comP の `session_recall` はローカルマシンの履歴のみ参照**。チーム間では共有されない。

---

## 3. 案1: `/wrapup` スキル（言行不一致チェッカー）

### 3.1 仕様

**起動**: ユーザーが `/wrapup` と打つ。引数なし（あれば `--since <時刻>` 的な絞り込みは拡張でよい）。

**動作手順**（SKILL.md にこの手順を書く）:

1. `mcp__comp__session_recall` を `{limit: 30}` 程度で呼び、直近セッションの会話履歴を取得する
2. 履歴から「実行の約束」を抽出する。抽出基準:
   - 「〜する」「〜しておく」「後で〜」「TODO」「テスト書く」「直す」等の宣言
   - ユーザー発言・アシスタント発言の両方を対象にする（「やっておきます」も約束）
3. `mcp__comp__get_git_diff_context` を呼び、実際のコード変更を取得。取れない/空の場合は `git status --porcelain` と `git log --oneline -10 --stat` で代替する
4. 約束と変更を突合し、3 分類で報告する:
   - ✅ **完了**: 約束に対応する変更が確認できた（対応 commit/ファイルを添える）
   - ❌ **未着手**: 約束したが対応する変更が見当たらない
   - ⚠️ **判定不能**: 対応関係が曖昧（正直に「不明」と言う。無理にどちらかに寄せない）
5. 最後に `mcp__comp__session_log` で本日のまとめ（完了/未完了リスト）を記録し、次回セッションの `session_recall` で拾えるようにする

**出力フォーマット例**:

```
📋 今日の宣言 vs 実績
✅ Token validation にキャッシュ追加 → packages/magatama-core/... で確認
❌ 「エッジケースのテスト書く」→ tests/ に変更なし
⚠️ 「ドキュメント更新」→ README.md に変更はあるが該当箇所か不明
💾 このまとめを session_log に記録しました。
```

### 3.2 成果物

- `.claude/skills/wrapup/SKILL.md` 1 ファイル
- frontmatter に `name: wrapup` と `description`（日本語でよい。「セッション中に宣言したタスクと git の実変更を突合し、やり残しを報告する。/wrapup で起動」）

### 3.3 受け入れ基準

- [ ] `/wrapup` でスキルが起動する
- [ ] session_recall が空（初回セッション等）でもエラーにならず「履歴がありません」と報告する
- [ ] git 変更ゼロの場合「変更なし」と報告し、約束だけがあれば全部 ❌ になる
- [ ] 判定不能を捏造せず ⚠️ で出す

---

## 4. 案2: 制約番犬（PreToolUse hook）

### 4.1 仕様

**構成要素は 3 つ**: 制約ファイル、hook スクリプト、settings.json のエントリ。

#### (a) 制約ファイル `.comp/constraints.json`

スキーマ:

```json
{
  "constraints": [
    {
      "id": "example-id",
      "file": "auth/session.py",
      "line_range": [145, 156],
      "entity": "Session.timeout_handler",
      "issue": "race condition: 同時タイムアウトで session 二重削除",
      "rule": "修正禁止。新規依存も追加しない",
      "reason": "顧客納品済み",
      "severity": "CRITICAL",
      "created_at": "2026-07-03"
    }
  ]
}
```

- `file` は**リポジトリルートからの相対パス**。マッチングはこのフィールドで行う（`line_range` と `entity` は警告文の表示用であり、マッチング条件にしない — Edit の対象行を hook から確実に特定できないため）
- ディレクトリ単位の制約を許す: `"file": "auth/"` のように末尾 `/` ならプレフィックス一致

#### (b) hook スクリプト `.claude/hooks/constraint-watchdog.sh`

**入力**（stdin、PreToolUse の JSON）:

```json
{
  "session_id": "...",
  "tool_name": "Edit",
  "tool_input": { "file_path": "E:\\dev\\MAGATAMA\\auth\\session.py", "old_string": "...", "new_string": "..." }
}
```

**ロジック**:

1. stdin から `tool_input.file_path` を抽出（jq 推奨。`jq -r '.tool_input.file_path // empty'`）
2. パスを正規化: バックスラッシュ→スラッシュ、リポジトリルート prefix を除去して相対パス化、大文字小文字は Windows なので無視して比較
3. `.comp/constraints.json` の各 `constraints[].file` と照合（完全一致 or ディレクトリプレフィックス一致）
4. **ヒット時**: 以下の JSON を stdout に出す（exit 0）:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": "⚠️ 制約警告: auth/session.py には記録された制約があります。[CRITICAL] L145-156 (Session.timeout_handler): race condition — 修正禁止。新規依存も追加しない（理由: 顧客納品済み）。この編集が制約に抵触しないか確認し、抵触するなら編集を中止してユーザーに報告すること。"
  }
}
```

5. **非ヒット時**: `{}` を出して exit 0（何も注入しない）
6. constraints.json が無い・壊れている場合も exit 0 で素通しする（**hook の失敗で開発を止めない**）

**設計判断**: `permissionDecision: "deny"` で物理ブロックはしない。制約があっても「制約に触れない範囲の編集」（別の行の修正）は正当なので、判断は警告を受けた LLM に委ねる。

#### (c) `.claude/settings.json` の hooks エントリ

新規作成:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/constraint-watchdog.sh",
            "timeout": 10,
            "statusMessage": "Checking constraints..."
          }
        ]
      }
    ]
  }
}
```

#### (d) 制約の登録方法

CLI は作らない。登録は人間が `.comp/constraints.json` を直接編集するか、LLM が会話で受けた「修正禁止」の指示を json に書く。

### 4.2 テスト手順

1. **パイプテスト**（hook 登録前にスクリプト単体で）:

```bash
echo '{"tool_name":"Edit","tool_input":{"file_path":"E:\\dev\\MAGATAMA\\README.md"}}' | bash .claude/hooks/constraint-watchdog.sh
```

2. **JSON 検証**: `jq -e '.hooks.PreToolUse[]' .claude/settings.json` が exit 0 になること
3. **実発火テスト**: constraints.json にこのリポジトリの実在ファイルを登録し、Edit → 警告が出ることを確認

### 4.3 受け入れ基準

- [ ] 制約ファイルに載ったファイルの Edit/Write で additionalContext が注入される
- [ ] 載っていないファイルでは何も起きない
- [ ] constraints.json 不在でも編集がブロックされない
- [ ] Windows の絶対パスと相対パスの両方で照合が成立する

---

## 5. 実装順序の推奨

1. 案2 の hook スクリプト（パイプテストで単体完結）
2. 案2 の settings.json 統合 + 実発火テスト
3. 案1 の SKILL.md
4. 全体を 1 commit（例: `feat(claude): add /wrapup skill and constraint watchdog hook`）

---

## 6. スコープ外

- comP/MAGATAMA 本体のコード変更は不要
- 制約登録用 CLI の新規開発
- 編集の物理ブロック（deny）
