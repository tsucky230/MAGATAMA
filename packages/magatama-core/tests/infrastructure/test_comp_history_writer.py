"""Tests for comp_history_writer: agent attribution, JSONL shape, and the
exclusive-lock contract that must interoperate with comP's Rust writer.

Test groups:
- Unit: record shape / agent field (always run).
- Concurrency (pure Python): multiple processes appending through
  append_history_record itself must never interleave a line (always run).
- Integration (Rust): a real `comp-daemon append-history` child process must
  actually contend for the same lock. Skipped when no comp-daemon binary is
  resolvable (e.g. in CI, which doesn't build comP) -- see
  _resolve_comp_daemon_bin below.
"""

from __future__ import annotations

import json
import multiprocessing
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from magatama_core.infrastructure.storage.comp_history_writer import (
    _exclusive_lock,
    append_history_record,
)

# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


def test_default_agent_is_magatama(tmp_path: Path) -> None:
    comp_dir = tmp_path / ".comp"
    comp_dir.mkdir()
    log_file = append_history_record(comp_dir, query="q", outcome="o")
    record = json.loads(log_file.read_text(encoding="utf-8").splitlines()[0])
    assert record["agent"] == "magatama"


def test_explicit_agent_is_recorded(tmp_path: Path) -> None:
    comp_dir = tmp_path / ".comp"
    comp_dir.mkdir()
    log_file = append_history_record(comp_dir, query="q", outcome="o", agent="magatama-patrol")
    record = json.loads(log_file.read_text(encoding="utf-8").splitlines()[0])
    assert record["agent"] == "magatama-patrol"


def test_record_has_all_comp_session_call_keys(tmp_path: Path) -> None:
    """comP's SessionCall struct requires these keys (or defaults them) --
    all of them must be present in what we write so session_recall renders
    MAGATAMA-written lines identically to daemon-written ones."""
    comp_dir = tmp_path / ".comp"
    comp_dir.mkdir()
    log_file = append_history_record(
        comp_dir, query="q", outcome="o", files=["a.py"], symbols=["Foo"]
    )
    record = json.loads(log_file.read_text(encoding="utf-8").splitlines()[0])
    assert record.keys() == {
        "timestamp",
        "query",
        "outcome",
        "files",
        "symbols",
        "tokens",
        "stale",
        "agent",
    }


def test_two_appends_produce_two_parseable_lines(tmp_path: Path) -> None:
    comp_dir = tmp_path / ".comp"
    comp_dir.mkdir()
    f1 = append_history_record(comp_dir, query="q1", outcome="o1")
    f2 = append_history_record(comp_dir, query="q2", outcome="o2", files=["x.py"])
    assert f1 == f2
    lines = f1.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["query"] == "q1"
    assert json.loads(lines[1])["files"] == ["x.py"]


def test_exclusive_lock_releases_when_body_raises(tmp_path: Path) -> None:
    """AC-18, exercised directly against _exclusive_lock rather than through
    append_history_record: io.TextIOWrapper is a C-implemented type whose
    flush() can't be monkeypatched to simulate a mid-write failure (CPython
    rejects assignment to it, at both the class and instance level), so the
    write path itself can't be fault-injected. Testing the lock's own
    exception safety directly is the level this contract actually lives at.

    If the exception from the `with` body propagated but the lock leaked,
    the second acquisition below would hang (POSIX flock) or raise
    immediately (Windows LK_NBLCK) instead of succeeding.
    """
    target = tmp_path / "lockfile.jsonl"
    target.touch()

    f1 = target.open("a+", encoding="utf-8")
    try:
        with pytest.raises(ValueError, match="boom"), _exclusive_lock(f1):
            raise ValueError("boom")
    finally:
        f1.close()

    f2 = target.open("a+", encoding="utf-8")
    try:
        with _exclusive_lock(f2):
            f2.write("still works\n")
    finally:
        f2.close()

    assert target.read_text(encoding="utf-8") == "still works\n"


def test_append_after_failed_append_still_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end version of the same contract: if append_history_record
    itself fails (here: mkdir raising, before any lock is even taken), a
    subsequent call must succeed normally rather than being left in a bad
    state."""
    comp_dir = tmp_path / ".comp"

    from pathlib import Path as PathCls

    real_mkdir = PathCls.mkdir
    call_count = 0

    def flaky_mkdir(self: PathCls, *args: object, **kwargs: object) -> None:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise OSError("simulated failure")
        real_mkdir(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(PathCls, "mkdir", flaky_mkdir)

    with pytest.raises(OSError, match="simulated failure"):
        append_history_record(comp_dir, query="q1", outcome="o1")

    log_file = append_history_record(comp_dir, query="q2", outcome="o2")
    lines = log_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["query"] == "q2"


# ---------------------------------------------------------------------------
# Concurrency (pure Python, no comP binary required)
# ---------------------------------------------------------------------------

_WRITERS = 4
_APPENDS_PER_WRITER = 25


def _writer_worker(comp_dir: str, writer_id: int, count: int = _APPENDS_PER_WRITER) -> None:
    for i in range(count):
        append_history_record(comp_dir, query=f"w{writer_id}-{i}", outcome="o")


def test_concurrent_python_writers_never_interleave(tmp_path: Path) -> None:
    comp_dir = tmp_path / ".comp"
    comp_dir.mkdir()

    ctx = multiprocessing.get_context("spawn")
    procs = [ctx.Process(target=_writer_worker, args=(str(comp_dir), i)) for i in range(_WRITERS)]
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=60)
        assert p.exitcode == 0

    month = time.strftime("%Y-%m", time.gmtime())
    log_file = comp_dir / "history" / f"log-{month}.jsonl"
    lines = log_file.read_text(encoding="utf-8").splitlines()

    assert len(lines) == _WRITERS * _APPENDS_PER_WRITER
    seen = set()
    for line in lines:
        record = json.loads(line)  # raises if a line got interleaved/corrupted
        seen.add(record["query"])
    assert len(seen) == _WRITERS * _APPENDS_PER_WRITER


# ---------------------------------------------------------------------------
# Integration: real contention against comP's Rust writer
# ---------------------------------------------------------------------------


def _resolve_comp_daemon_bin() -> str | None:
    """Find a comp-daemon binary to run the integration test against.

    Never hardcodes an absolute dev-machine path (would break for every
    other contributor/CI). Checks, in order: $COMP_DAEMON_BIN, then PATH.
    Returns None if neither resolves, which the caller treats as "skip" --
    this is the expected outcome in CI (ubuntu-latest, no Rust build step
    for comP) and on any machine without a comP checkout.
    """
    env_path = os.environ.get("COMP_DAEMON_BIN")
    if env_path and Path(env_path).is_file():
        return env_path
    found = shutil.which("comp-daemon")
    if found:
        return found
    return None


_COMP_DAEMON_BIN = _resolve_comp_daemon_bin()
_SKIP_REASON = (
    "no comp-daemon binary resolvable via $COMP_DAEMON_BIN or PATH "
    "(expected in CI; set $COMP_DAEMON_BIN locally to run this test)"
)


@pytest.mark.integration
@pytest.mark.skipif(_COMP_DAEMON_BIN is None, reason=_SKIP_REASON)
def test_python_lock_blocks_concurrent_rust_writer(tmp_path: Path) -> None:
    """While MAGATAMA holds the exclusive lock, a concurrently-launched
    `comp-daemon append-history` must block until MAGATAMA releases it --
    proving the two implementations contend for the *same* OS lock, not
    just "a" lock. This is the core untested assumption Prompt A called out.
    """
    assert _COMP_DAEMON_BIN is not None
    comp_dir = tmp_path / ".comp"
    comp_dir.mkdir()
    history_dir = comp_dir / "history"
    history_dir.mkdir()
    month = time.strftime("%Y-%m", time.gmtime())
    log_file = history_dir / f"log-{month}.jsonl"
    log_file.touch()

    # Hold the lock from a subprocess (not this process) so we can observe,
    # from here, whether the Rust child blocks -- if we held the lock
    # in-process instead, we couldn't concurrently poll another process.
    holder_script = (
        "import sys, time\n"
        "sys.path.insert(0, sys.argv[3])\n"
        "from magatama_core.infrastructure.storage.comp_history_writer import _exclusive_lock\n"
        "f = open(sys.argv[1], 'a+', encoding='utf-8')\n"
        "with _exclusive_lock(f):\n"
        "    open(sys.argv[2], 'w').close()\n"  # signal: lock acquired
        "    time.sleep(3)\n"
        "f.close()\n"
    )
    src_root = str(Path(__file__).resolve().parents[2] / "src")  # packages/magatama-core/src
    ready_flag = tmp_path / "lock_acquired"
    holder = subprocess.Popen(
        [sys.executable, "-c", holder_script, str(log_file), str(ready_flag), src_root]
    )
    try:
        deadline = time.monotonic() + 5.0
        while not ready_flag.exists():
            assert time.monotonic() < deadline, "holder never signaled lock acquisition"
            time.sleep(0.05)

        t0 = time.monotonic()
        rust_proc = subprocess.Popen(
            [_COMP_DAEMON_BIN, "append-history", str(comp_dir.parent), "spike-agent"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert rust_proc.stdin is not None
        rust_proc.stdin.write(json.dumps({"request": "integration test", "outcome": "ok"}))
        rust_proc.stdin.close()

        # Poll: it must still be running while the Python side holds the
        # lock (holder sleeps 3s total).
        time.sleep(1.5)
        elapsed = time.monotonic() - t0
        assert rust_proc.poll() is None, (
            f"comp-daemon exited after {elapsed:.2f}s while the lock was still held -- "
            "the two implementations are NOT contending for the same OS lock"
        )

        _out, err = rust_proc.communicate(timeout=10)
        assert rust_proc.returncode == 0, f"comp-daemon failed: {err}"
    finally:
        holder.wait(timeout=10)

    lines = log_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["query"] == "integration test"
    assert parsed["agent"] == "spike-agent"


@pytest.mark.integration
@pytest.mark.skipif(_COMP_DAEMON_BIN is None, reason=_SKIP_REASON)
def test_python_and_rust_writers_interleave_without_corruption(tmp_path: Path) -> None:
    """Python and Rust each append repeatedly, concurrently, to the same
    file. Every line must still parse and the count must match exactly --
    the end-to-end version of the contract, as opposed to the previous
    test's single blocking check."""
    assert _COMP_DAEMON_BIN is not None
    comp_dir = tmp_path / ".comp"
    comp_dir.mkdir()

    n_python = 15
    n_rust = 15

    ctx = multiprocessing.get_context("spawn")
    py_proc = ctx.Process(target=_writer_worker, args=(str(comp_dir), 0, n_python))

    def rust_writer() -> None:
        for i in range(n_rust):
            p = subprocess.run(
                [_COMP_DAEMON_BIN, "append-history", str(comp_dir.parent), "rust-writer"],
                input=json.dumps({"request": f"rust-{i}", "outcome": "ok"}),
                capture_output=True,
                text=True,
            )
            assert p.returncode == 0, p.stderr

    import threading

    rust_thread = threading.Thread(target=rust_writer)

    py_proc.start()
    rust_thread.start()
    py_proc.join(timeout=60)
    rust_thread.join(timeout=60)
    assert py_proc.exitcode == 0

    month = time.strftime("%Y-%m", time.gmtime())
    log_file = comp_dir / "history" / f"log-{month}.jsonl"
    lines = log_file.read_text(encoding="utf-8").splitlines()

    assert len(lines) == n_python + n_rust
    for line in lines:
        json.loads(line)
