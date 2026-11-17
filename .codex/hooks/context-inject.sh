#!/bin/bash
# context-inject.sh: UserPromptSubmit hook で .comp/history/*.jsonl の直近5件を注入。
# WHY: harness 側で強制注入することで、LLM の自発的な session_recall 呼び出しに
# 依存せず前回までの作業文脈を復元する（comP の同名 hook から履歴注入部分を移植。
# comP デーモン/MAGATAMA が書く "query" キーのレコードも読めるよう修正済み）。

# Git Bash の pwd は POSIX 形式 (/e/dev/...) を返し node が誤解釈するため pwd -W
export COMP_WORKSPACE="${COMP_WORKSPACE_ROOT:-${CLAUDE_PROJECT_DIR:-$(pwd -W 2>/dev/null || pwd)}}"

node -e '
const fs = require("fs");
const path = require("path");

let historySection = "";
try {
  const workspace = process.env.COMP_WORKSPACE || process.cwd();
  const historyDir = path.join(workspace, ".comp", "history");
  if (fs.existsSync(historyDir)) {
    const files = fs.readdirSync(historyDir)
      .filter(f => f.startsWith("log-") && f.endsWith(".jsonl"))
      .map(f => path.join(historyDir, f))
      .sort();

    if (files.length > 0) {
      const entries = [];
      for (const f of files.slice(-2)) {
        try {
          const lines = fs.readFileSync(f, "utf8").split("\n").filter(l => l.trim());
          for (const l of lines) {
            try { entries.push(JSON.parse(l)); } catch(e) {}
          }
        } catch(e) {}
      }
      entries.sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0));
      const recent = entries.slice(0, 5);

      if (recent.length > 0) {
        const summaries = recent.map(e => {
          const d = new Date(e.timestamp || 0);
          const dt = d.toISOString().slice(0, 16).replace("T", " ");
          const req = (e.request || e.query || "").slice(0, 80).replace(/\n/g, " ");
          const out = e.outcome ? (" → " + (e.outcome || "").slice(0, 80).replace(/\n/g, " ")) : "";
          return "- " + dt + " " + req + out;
        });
        historySection = "【直近の対話履歴（.comp/history から自動注入）】\n" + summaries.join("\n")
          + "\n詳細は session_recall / get_entity_history で参照可能。";
      }
    }
  }
} catch(e) {}

if (historySection) {
  console.log(JSON.stringify({hookSpecificOutput:{hookEventName:"UserPromptSubmit",additionalContext:historySection}}));
}
' 2>/dev/null

exit 0
