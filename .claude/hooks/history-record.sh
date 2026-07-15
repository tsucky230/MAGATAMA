#!/bin/bash
# history-record.sh: Stop hook で対話履歴を .comp/history/log-YYYY-MM.jsonl へ自動記録。
# stdin(transcript_path) → 最後の user 依頼 + assistant 応答 → JSONL 追記
# WHY: LLM の自発的な session_log 呼び出しに頼らず、harness 側で確実に記録して
# セッション切れ耐性を得る（comP の同名 hook の移植）。

INPUT=$(cat)
export COMP_HOOK_INPUT="$INPUT"
# Git Bash の pwd は POSIX 形式 (/e/dev/...) を返し node が誤解釈するため pwd -W
export COMP_WORKSPACE="${COMP_WORKSPACE_ROOT:-${CLAUDE_PROJECT_DIR:-$(pwd -W 2>/dev/null || pwd)}}"

node -e '
const fs = require("fs");
const path = require("path");
try {
  const event = JSON.parse(process.env.COMP_HOOK_INPUT || "{}");
  const transcriptPath = event.transcript_path;
  if (!transcriptPath || !fs.existsSync(transcriptPath)) process.exit(0);

  const workspace = process.env.COMP_WORKSPACE || process.cwd();
  const historyDir = path.join(workspace, ".comp", "history");
  fs.mkdirSync(historyDir, { recursive: true });

  const month = new Date().toISOString().slice(0, 7);
  const logFile = path.join(historyDir, "log-" + month + ".jsonl");

  const raw = fs.readFileSync(transcriptPath, "utf8");
  const messages = raw.split("\n").flatMap(l => {
    try { return [JSON.parse(l.trim())]; } catch(e) { return []; }
  });

  function extractText(content) {
    if (typeof content === "string") return content.trim();
    if (Array.isArray(content)) {
      for (const c of content) {
        if (c && c.type === "text" && c.text) return c.text.trim();
      }
    }
    return "";
  }

  let lastUser = "";
  let lastAssistant = "";
  for (const msg of messages) {
    const role = msg.role || msg.type || "";
    const text = extractText(msg.content);
    if (role === "user" && text) lastUser = text;
    if (role === "assistant" && text) lastAssistant = text;
  }

  if (!lastUser) process.exit(0);

  const entry = {
    timestamp: Date.now(),
    request: lastUser.slice(0, 600),
    outcome: lastAssistant ? lastAssistant.slice(0, 400) : null
  };
  fs.appendFileSync(logFile, JSON.stringify(entry) + "\n", "utf8");
} catch(e) {}
process.exit(0);
' 2>/dev/null

exit 0
