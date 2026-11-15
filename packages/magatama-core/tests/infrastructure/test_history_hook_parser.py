"""Regression tests for the Claude Stop hook's transcript parser."""

import json
import os
import subprocess
from pathlib import Path

PARSER = Path(__file__).resolve().parents[4] / ".claude" / "hooks" / "history-record.js"


def run_parser(tmp_path: Path, lines: list[dict]) -> str:
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("\n".join(json.dumps(line) for line in lines), encoding="utf-8")
    env = {**os.environ, "COMP_HOOK_INPUT": json.dumps({"transcript_path": str(transcript)})}
    completed = subprocess.run(
        ["node", str(PARSER)], capture_output=True, text=True, env=env, check=True
    )
    return completed.stdout


def test_nested_claude_message_content_is_recorded(tmp_path: Path) -> None:
    output = run_parser(
        tmp_path,
        [
            {"type": "user", "message": {"content": "old question"}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "old answer"}]}},
            {"type": "user", "message": {"content": [{"type": "text", "text": "new question"}]}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "new answer"}]}},
        ],
    )
    assert json.loads(output) == {"request": "new question", "outcome": "new answer"}


def test_latest_unanswered_turn_does_not_reuse_previous_answer(tmp_path: Path) -> None:
    output = run_parser(
        tmp_path,
        [
            {"type": "user", "message": {"content": "first"}},
            {"type": "assistant", "message": {"content": "answer to first"}},
            {"type": "user", "message": {"content": "second"}},
        ],
    )
    assert json.loads(output) == {"request": "second", "outcome": None}


def test_secret_prefix_is_redacted_before_fallback_write(tmp_path: Path) -> None:
    output = run_parser(
        tmp_path,
        [{"type": "user", "message": {"content": "token ghp_abcdefghijklmnopqrstuvwxyz123456"}}],
    )
    assert json.loads(output) == {"request": "token [REDACTED]", "outcome": None}


def test_secret_crossing_length_limit_is_redacted(tmp_path: Path) -> None:
    output = run_parser(
        tmp_path,
        [{"type": "user", "message": {"content": "x" * 593 + " ghp_abcdefghijklmnopqrstuvwxyz"}}],
    )
    assert "ghp_" not in json.loads(output)["request"]
