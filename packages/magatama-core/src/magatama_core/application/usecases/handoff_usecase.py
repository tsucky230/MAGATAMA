"""Handoff use case: generate a context-handoff document for the next session.

Combines the most recent comP session records (which include patrol notes)
with the current git state into one Markdown document sized to a token
budget, and appends it to .comp/history so the next session's session_recall
starts with it.

Token counting here is an estimate: budget is converted to characters at
2 chars/token, which is conservative for Japanese text (English averages
~4 chars/token, Japanese ~1-2).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from magatama_core.infrastructure.storage.comp_history_writer import append_history_record
from magatama_core.infrastructure.storage.comp_session_reader import (
    CompSessionReader,
    CompSessionsNotFoundError,
)

_CHARS_PER_TOKEN = 2
_OUTCOME_SNIPPET_LEN = 200


@dataclass
class HandoffResult:
    success: bool
    markdown: str = ""
    estimated_tokens: int = 0
    sessions_included: int = 0
    history_file: str = ""
    errors: list[str] = field(default_factory=list)


def _git(workspace: Path, *args: str) -> str:
    """Run a git command in the workspace; return stdout or '' on failure."""
    try:
        result = subprocess.run(
            ["git", "-C", str(workspace), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


class GenerateHandoffUseCase:
    """Generate a handoff Markdown for the next chat session."""

    def execute(
        self,
        workspace: str | Path,
        token_budget: int = 2000,
        recent: int = 10,
        log_history: bool = True,
    ) -> HandoffResult:
        workspace = Path(workspace)
        result = HandoffResult(success=True)
        char_budget = max(token_budget, 100) * _CHARS_PER_TOKEN

        # -- recent session records (includes patrol notes) -------------
        records = []
        try:
            data = CompSessionReader().read(workspace)
            records = sorted(
                data.records,
                key=lambda r: r.timestamp_ms or 0,
                reverse=True,
            )[:recent]
        except CompSessionsNotFoundError:
            result.errors.append(
                "セッション履歴なし（.comp/session-memory.json / history/ が未作成）"
            )
        except Exception as e:
            result.errors.append(f"セッション履歴の読み取りに失敗: {e}")

        # -- git state ---------------------------------------------------
        branch = _git(workspace, "rev-parse", "--abbrev-ref", "HEAD")
        status = _git(workspace, "status", "--porcelain")
        log = _git(workspace, "log", "--oneline", "-10")

        # -- assemble within budget --------------------------------------
        now = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M UTC")
        parts: list[str] = [f"# 引継ぎ ({now})", ""]

        parts.append("## git の現状")
        if branch:
            parts.append(f"- ブランチ: `{branch}`")
            uncommitted = [ln for ln in status.splitlines() if ln.strip()]
            if uncommitted:
                parts.append(f"- 未コミット: {len(uncommitted)} 件")
                parts.extend(f"  - `{ln.strip()}`" for ln in uncommitted[:10])
            else:
                parts.append("- 未コミット: なし")
            if log:
                parts.append("- 直近コミット:")
                parts.extend(f"  - {ln}" for ln in log.splitlines()[:5])
        else:
            parts.append("- (git リポジトリではないか、git が使えません)")
        parts.append("")

        parts.append("## 直近のセッション記録（新しい順）")
        if not records:
            parts.append("- (記録なし)")
        included = 0
        for record in records:
            when = ""
            if record.timestamp_ms:
                try:
                    when = datetime.fromtimestamp(record.timestamp_ms / 1000, tz=UTC).strftime(
                        "%m-%d %H:%M "
                    )
                except (OverflowError, OSError, ValueError):
                    when = ""
            outcome = (record.entity.docstring or "").split("] ", 1)[-1]
            if len(outcome) > _OUTCOME_SNIPPET_LEN:
                outcome = outcome[: _OUTCOME_SNIPPET_LEN - 1] + "…"
            entry = f"- {when}**{record.entity.name}**"
            if outcome:
                entry += f"\n  - {outcome}"
            # Stop adding entries once the budget would be exceeded.
            if sum(len(p) + 1 for p in parts) + len(entry) > char_budget:
                parts.append(f"- …ほか {len(records) - included} 件（予算により省略）")
                break
            parts.append(entry)
            included += 1

        markdown = "\n".join(parts)
        if len(markdown) > char_budget:
            markdown = markdown[: char_budget - 1] + "…"

        result.markdown = markdown
        result.estimated_tokens = len(markdown) // _CHARS_PER_TOKEN
        result.sessions_included = included

        # -- record to history so the next session can recall it ---------
        if log_history:
            comp_dir = workspace if workspace.name == ".comp" else workspace / ".comp"
            try:
                log_file = append_history_record(
                    comp_dir,
                    query="handoff: 次セッションへの引継ぎ",
                    outcome=markdown,
                )
                result.history_file = str(log_file)
            except OSError as e:
                result.errors.append(f"履歴への記録に失敗: {e}")

        return result
