#!/usr/bin/env bash
# 制約番犬 (constraint watchdog) — PreToolUse hook for Edit|Write.
#
# .comp/constraints.json に登録された「修正禁止」ファイルへの編集を検出し、
# additionalContext で警告をモデルのコンテキストに注入する。物理ブロックは
# しない（制約に触れない範囲の編集は正当なので、判断は警告を受けた LLM に
# 委ねる）。constraints.json が無い・壊れている場合は素通しする（hook の
# 失敗で開発を止めない）。
#
# 単体テスト:
#   echo '{"tool_name":"Edit","tool_input":{"file_path":"E:\\dev\\MAGATAMA\\README.md"}}' \
#     | bash .claude/hooks/constraint-watchdog.sh

set -u

# Git Bash の pwd は POSIX 形式 (/e/dev/...) を返すので、Windows 形式が
# 必要なら pwd -W を使う。CLAUDE_PROJECT_DIR があればそれを優先。
ROOT="${CLAUDE_PROJECT_DIR:-$(pwd -W 2>/dev/null || pwd)}"

# jq が無い環境（本リポジトリの開発機を含む）でも動くよう、JSON の解析は
# Python で行う。Python も無ければ何もしない。
PY="$(command -v python || command -v python3 || true)"
if [ -z "$PY" ]; then
  echo '{}'
  exit 0
fi

# 注意: python にスクリプトを heredoc (stdin) で渡すため、hook の JSON 入力は
# 先に読み取って環境変数で引き継ぐ（stdin は一度しか使えない）。
HOOK_INPUT="$(cat)"
export HOOK_INPUT

"$PY" - "$ROOT" <<'PYEOF'
import json
import os
import sys
from pathlib import Path

# Windows のコンソールは cp932 が既定で、⚠️ や日本語が UnicodeEncodeError に
# なるため UTF-8 に固定する（cli/main.py と同じ対処）。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def out(obj):
    print(json.dumps(obj, ensure_ascii=False))
    sys.exit(0)

root = Path(sys.argv[1])

try:
    payload = json.loads(os.environ.get("HOOK_INPUT", ""))
    file_path = payload.get("tool_input", {}).get("file_path") or ""
except Exception:
    out({})
if not file_path:
    out({})

# パス正規化: バックスラッシュ→スラッシュ、リポジトリルートを除去して
# 相対パス化、Windows なので大文字小文字は無視して比較する。
norm = file_path.replace("\\", "/")
root_norm = str(root).replace("\\", "/").rstrip("/") + "/"
if norm.lower().startswith(root_norm.lower()):
    norm = norm[len(root_norm):]
norm_l = norm.lower()

constraints_file = root / ".comp" / "constraints.json"
try:
    data = json.loads(constraints_file.read_text(encoding="utf-8"))
    constraints = data.get("constraints", [])
    assert isinstance(constraints, list)
except Exception:
    out({})

hits = []
for c in constraints:
    if not isinstance(c, dict):
        continue
    target = str(c.get("file", "")).replace("\\", "/").lower()
    if not target:
        continue
    # 末尾 / はディレクトリ制約（プレフィックス一致）、それ以外は完全一致
    if target.endswith("/"):
        if norm_l.startswith(target):
            hits.append(c)
    elif norm_l == target:
        hits.append(c)

if not hits:
    out({})

lines = []
for c in hits:
    loc = ""
    lr = c.get("line_range")
    if isinstance(lr, list) and len(lr) == 2:
        loc = f" L{lr[0]}-{lr[1]}"
    entity = f" ({c['entity']})" if c.get("entity") else ""
    sev = c.get("severity", "WARN")
    issue = c.get("issue", "")
    rule = c.get("rule", "")
    reason = f"（理由: {c['reason']}）" if c.get("reason") else ""
    lines.append(f"[{sev}]{loc}{entity}: {issue} — {rule}{reason}")

context = (
    f"⚠️ 制約警告: {norm} には記録された制約があります。"
    + " / ".join(lines)
    + " この編集が制約に抵触しないか確認し、抵触するなら編集を中止して"
    + "ユーザーに報告すること。"
)
out({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext": context,
    }
})
PYEOF
