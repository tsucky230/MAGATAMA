#!/bin/bash
# history-record.sh: Stop hook で対話履歴を .comp/history/log-YYYY-MM.jsonl へ自動記録。
# stdin(transcript_path) → 最後の user 依頼 + assistant 応答 →
# comp-daemon append-history 経由でロック付き追記（可能な場合）。
# WHY: LLM の自発的な session_log 呼び出しに頼らず、harness 側で確実に記録して
# セッション切れ耐性を得る（comP の同名 hook の移植）。
#
# WHY comp-daemon 経由を優先する: 直書き(fs.appendFileSync)は comP の
# append_history_line / MAGATAMA の append_history_record が取る排他ロックを
# 経由しない「第3の書き手」になり、同時書き込み時のJSONL行インターリーブ破損を
# 理論上防げない。
#
# WHY comP 本家と違いバイナリ未解決時のみフォールバックする（非ゼロ終了時はしない）:
# comp-daemon の append_history_line はブロッキングロックのため競合では失敗しない。
# 起動できて非ゼロ終了する場合はIOエラー等の実障害であり、そこで無ロック書き込みに
# 落ちると本修正が防ごうとしている破損を自ら起こすため、記録を諦める方を選ぶ。
# バイナリが最初から無い環境（＝ロック機構自体が使えない）は元々ロックの恩恵が無いため
# 「記録が残ること」を優先し直書きにフォールバックする。

INPUT=$(cat)
export COMP_HOOK_INPUT="$INPUT"
# Git Bash の pwd は POSIX 形式 (/e/dev/...) を返し node/exe が誤解釈するため pwd -W
export COMP_WORKSPACE="${COMP_WORKSPACE_ROOT:-${CLAUDE_PROJECT_DIR:-$(pwd -W 2>/dev/null || pwd)}}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ENTRY_JSON=$(node "$SCRIPT_DIR/history-record.js" 2>/dev/null)

[ -z "$ENTRY_JSON" ] && exit 0

# WHY $COMP_DAEMON_BIN が最優先: comp-daemon は MAGATAMA リポジトリには同梱されず、
# 開発機ごとに comP のビルド有無・パスが異なる。絶対パスをこのスクリプトに埋め込むと
# 他マシン・CIで壊れるため、環境変数か PATH 解決のみに頼る。
resolve_daemon_bin() {
  if [ -n "$COMP_DAEMON_BIN" ] && [ -f "$COMP_DAEMON_BIN" ]; then
    printf '%s' "$COMP_DAEMON_BIN"
    return 0
  fi
  local found
  found=$(command -v comp-daemon 2>/dev/null)
  if [ -n "$found" ]; then
    printf '%s' "$found"
    return 0
  fi
  return 1
}

write_fallback() {
  COMP_WORKSPACE="$COMP_WORKSPACE" COMP_ENTRY="$ENTRY_JSON" node -e '
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
  entry.agent = "magatama-hook";
  fs.appendFileSync(logFile, JSON.stringify(entry) + "\n", "utf8");
} catch(e) {}
' 2>/dev/null
}

DAEMON_BIN=$(resolve_daemon_bin)
if [ -z "$DAEMON_BIN" ]; then
  # ケースA: バイナリ自体が解決できない -- ロック機構がそもそも使えない環境なので、
  # 「記録が残ること」を優先して直書きにフォールバックする。
  write_fallback
  exit 0
fi

# ケースB: バイナリはある。起動できて非ゼロ終了する場合は実障害とみなし、
# 1回だけリトライしてなお失敗なら記録を諦める（直書きにはフォールバックしない）。
if printf '%s' "$ENTRY_JSON" | "$DAEMON_BIN" append-history "$COMP_WORKSPACE" magatama-hook 2>/dev/null; then
  exit 0
fi

if printf '%s' "$ENTRY_JSON" | "$DAEMON_BIN" append-history "$COMP_WORKSPACE" magatama-hook 2>/dev/null; then
  exit 0
fi

echo "[MAGATAMA] comp-daemon append-history failed twice; history entry dropped (not falling back to unlocked write)" >&2
exit 0
