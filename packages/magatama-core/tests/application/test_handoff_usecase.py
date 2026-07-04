"""Tests for GenerateHandoffUseCase."""

import json
import subprocess
from pathlib import Path

from magatama_core.application.usecases.handoff_usecase import GenerateHandoffUseCase


def make_workspace(tmp_path: Path, with_git: bool = False) -> Path:
    """Workspace with .comp session data (2 records) and optionally git."""
    workspace = tmp_path / "proj"
    comp_dir = workspace / ".comp"
    history = comp_dir / "history"
    history.mkdir(parents=True)
    lines = [
        json.dumps(
            {
                "timestamp": 1783130000000,
                "query": "古い依頼",
                "outcome": "古い結果",
                "files": [],
                "symbols": [],
                "tokens": 0,
                "stale": False,
            },
            ensure_ascii=False,
        ),
        json.dumps(
            {
                "timestamp": 1783140000000,
                "query": "新しい依頼",
                "outcome": "新しい結果",
                "files": [],
                "symbols": [],
                "tokens": 0,
                "stale": False,
            },
            ensure_ascii=False,
        ),
    ]
    (history / "log-2026-07.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")

    if with_git:
        subprocess.run(["git", "init", "-q"], cwd=workspace, check=True)
        (workspace / ".gitignore").write_text(".comp/\n", encoding="utf-8")
        (workspace / "a.txt").write_text("hello", encoding="utf-8")
        subprocess.run(["git", "add", "a.txt", ".gitignore"], cwd=workspace, check=True)
        subprocess.run(
            ["git", "-c", "user.email=t@e.st", "-c", "user.name=t", "commit", "-qm", "init"],
            cwd=workspace,
            check=True,
        )
        (workspace / "b.txt").write_text("dirty", encoding="utf-8")
    return workspace


def test_handoff_includes_sessions_newest_first(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    result = GenerateHandoffUseCase().execute(workspace, log_history=False)

    assert result.success
    assert result.sessions_included == 2
    assert "新しい依頼" in result.markdown
    assert "古い依頼" in result.markdown
    assert result.markdown.index("新しい依頼") < result.markdown.index("古い依頼")


def test_handoff_includes_git_state(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path, with_git=True)
    result = GenerateHandoffUseCase().execute(workspace, log_history=False)

    assert "ブランチ" in result.markdown
    assert "未コミット: 1 件" in result.markdown
    assert "init" in result.markdown  # recent commit line


def test_handoff_without_git(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    result = GenerateHandoffUseCase().execute(workspace, log_history=False)
    assert result.success
    assert "git リポジトリではない" in result.markdown


def test_handoff_respects_budget(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    result = GenerateHandoffUseCase().execute(workspace, token_budget=150, log_history=False)
    # budget 150 tokens -> 300 chars
    assert len(result.markdown) <= 300
    assert result.estimated_tokens <= 150


def test_handoff_writes_history(tmp_path: Path) -> None:
    workspace = make_workspace(tmp_path)
    result = GenerateHandoffUseCase().execute(workspace)

    assert result.history_file
    lines = Path(result.history_file).read_text(encoding="utf-8").splitlines()
    record = json.loads(lines[-1])
    assert record["query"].startswith("handoff")
    assert "引継ぎ" in record["outcome"]


def test_handoff_no_sessions(tmp_path: Path) -> None:
    """Works (with note) when .comp has no session data at all."""
    workspace = tmp_path / "empty"
    (workspace / ".comp").mkdir(parents=True)
    result = GenerateHandoffUseCase().execute(workspace, log_history=False)
    assert result.success
    assert result.sessions_included == 0
    assert result.errors  # セッション履歴なし note
