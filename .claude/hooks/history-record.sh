#!/bin/bash
# history-record.sh: Stop hook で対話履歴を .comp/history/log-YYYY-MM.jsonl へ自動記録。
# stdin(transcript_path) → 最後の user 依頼 + assistant 応答 → JSONL 追記
# WHY: LLM の自発的な session_log 呼び出しに頼らず、harness 側で確実に記録して
# セッション切れ耐性を得る（comP の同名 hook の移植）。

INPUT=$(cat)
export COMP_HOOK_INPUT="$INPUT"
# Git Bash の pwd は POSIX 形式 (/e/dev/...) を返し node が誤解釈するため pwd -W
export COMP_WORKSPACE="${COMP_WORKSPACE_ROOT:-${CLAUDE_PROJECT_DIR:-$(pwd -W 2>/dev/null || pwd)}}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ENTRY_JSON=$(node "$SCRIPT_DIR/history-record.js" 2>/dev/null)
[ -z "$ENTRY_JSON" ] && exit 0

COMP_ENTRY="$ENTRY_JSON" node -e '
const fs = require("fs");
const path = require("path");
try {
  const workspace = process.env.COMP_WORKSPACE || process.cwd();
  const historyDir = path.join(workspace, ".comp", "history");
  fs.mkdirSync(historyDir, { recursive: true });

  const month = new Date().toISOString().slice(0, 7);
  const logFile = path.join(historyDir, "log-" + month + ".jsonl");

  const entry = JSON.parse(process.env.COMP_ENTRY);
  entry.timestamp = Date.now();
  fs.appendFileSync(logFile, JSON.stringify(entry) + "\n", "utf8");
} catch(e) {}
process.exit(0);
' 2>/dev/null

exit 0
