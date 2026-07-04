## Session Continuity (デーモン再起動・セッション切れ対応)

セッションはデーモン再起動をまたいで永続化されます。
作業を再開したり、エージェントを再起動した場合は、まず `session_recall` を呼んで過去の文脈を復帰させてください。

**When resuming work**:

1. Call `session_recall()` to view past interactions
   - `session_recall({ "query": "keyword" })` — filter by task keywords
   - `session_recall({ "limit": 5 })` — show last N interactions
2. Review what was done previously and continue in that context

**Note**: The hook system also auto-injects recent history into each prompt (`<system-reminder>`),
but explicit `session_recall` is useful to manually review past work or search specific tasks.

## Constraint Tracking (制約番犬)

`.comp/constraints.json` に「修正禁止・要注意」ファイルを登録すると、
PreToolUse hook（`.claude/hooks/constraint-watchdog.sh`）が Edit/Write 時に
警告をコンテキストへ注入します。物理ブロックはしません — 警告を受けたら
編集が制約に抵触しないか確認し、抵触するなら中止してユーザーに報告してください。

**制約の登録方法**（ユーザーから「このファイルは触るな」等の指示を受けたら、
以下の形式で `.comp/constraints.json` に追記する）:

```json
{
  "constraints": [
    {
      "id": "short-id",
      "file": "path/from/repo/root.py",
      "line_range": [10, 20],
      "entity": "ClassName.method",
      "issue": "何が問題か",
      "rule": "修正禁止。新規依存も追加しない",
      "reason": "なぜか（例: 顧客納品済み）",
      "severity": "CRITICAL",
      "created_at": "YYYY-MM-DD"
    }
  ]
}
```

- `file` はリポジトリルートからの相対パス。末尾 `/` でディレクトリ単位の制約
- 必須は `file` のみ。`line_range` / `entity` は警告表示用

## /wrapup（言行不一致チェッカー）

作業の締めに `/wrapup` を実行すると、セッション中の「やる」宣言と git の
実変更を突合し、✅完了 / ❌未着手 / ⚠️判定不能で報告して session_log に記録します。
