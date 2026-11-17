"""comP session history writer.

Appends records to .comp/history/log-YYYY-MM.jsonl in the same shape the
comP daemon writes for its session_log tool:

    {"timestamp", "query", "outcome", "files", "symbols", "tokens", "stale", "agent"}

so comP's session_recall surfaces them alongside daemon-written records in
later sessions. (Older daemons wrote "request" instead of "query"; readers
in this codebase accept both.)

Locking contract (must match comP's append_history_line in
daemon/src/mcp/mod.rs so both processes contend for the *same* OS lock):

- Always take an EXCLUSIVE lock, never shared. Windows' LockFileEx rejects
  writes from a handle holding only a shared lock (even its own writes),
  so comP standardized every writer on exclusive-only; this file must match
  or the two processes silently stop excluding each other.
- Lock -> write -> flush -> unlock -> close, with flush happening *before*
  unlock. If the OS write were still sitting in a Python-level buffer when
  the lock is released, another process could interleave its own write
  before ours actually reaches disk, defeating the whole point of locking.
- The lock must be released even if writing fails partway through, and the
  file handle must be closed even if releasing the lock itself fails
  (Windows drops all locks a handle holds when that handle is closed, so
  close() is the last-resort backstop).
"""

from __future__ import annotations

import json
import sys
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

# msvcrt.locking() takes a signed 32-bit length, so the largest range we can
# lock in one call is [0, 0x7FFFFFFF) -- about 2GB. comP's Rust side locks
# the *whole file* via File::lock() (no byte-range limit). A monthly JSONL
# history file realistically never approaches 2GB, so this is a documented
# limitation rather than a bug: if it ever did, appends past the 2GB mark
# would fall outside our locked range and stop being mutually exclusive
# with comP's writer.
_WINDOWS_LOCK_BYTES = 0x7FFFFFFF

# How long to keep retrying a non-blocking lock attempt before giving up.
# comP's own lock is held only for the duration of one write_all() call
# (a single JSONL line), so any real contention should clear in well under
# this window; it exists to fail loudly instead of hanging forever if
# something holds the lock indefinitely (e.g. a crashed process on a
# filesystem that doesn't release locks on its own).
_LOCK_RETRY_TIMEOUT_S = 10.0
_LOCK_RETRY_INTERVAL_S = 0.05


@contextmanager
def _exclusive_lock(f: IO[str]) -> Iterator[None]:
    """Hold an exclusive OS advisory lock on ``f`` for the duration of the block.

    Platform split:
    - Windows: msvcrt.locking() over a fixed byte range starting at 0, via a
      poll loop (LK_NBLCK) so a stuck lock raises instead of blocking forever.
    - POSIX: fcntl.flock(LOCK_EX), the same flock(2) call std::fs::File::lock()
      wraps on Unix -- so this is provably the identical OS primitive comP
      contends on there, not just "a lock".

    Unlocking always seeks back to the position the lock started at first:
    msvcrt.locking()'s range is relative to the file's *current* position,
    and a write in between the lock and unlock calls moves that position.
    Unlocking from the wrong offset raises PermissionError instead of
    releasing anything.
    """
    if sys.platform == "win32":
        import msvcrt

        fd = f.fileno()
        start = f.tell()
        deadline = time.monotonic() + _LOCK_RETRY_TIMEOUT_S
        while True:
            try:
                msvcrt.locking(fd, msvcrt.LK_NBLCK, _WINDOWS_LOCK_BYTES)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(_LOCK_RETRY_INTERVAL_S)
        try:
            yield
        finally:
            # Best-effort unlock: if this fails (e.g. a prior write already
            # left the handle in a bad state), don't let it mask whatever
            # exception is already propagating -- close() below is what
            # actually guarantees the lock doesn't outlive this function.
            try:
                f.seek(start)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, _WINDOWS_LOCK_BYTES)
            except OSError:
                pass
    else:
        import fcntl

        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass


def append_history_record(
    comp_dir: str | Path,
    query: str,
    outcome: str,
    files: list[str] | None = None,
    symbols: list[str] | None = None,
    agent: str = "magatama",
) -> Path:
    """Append one record to the current month's history JSONL.

    Creates .comp/history/ if needed. Takes the same exclusive lock comP's
    append_history_line takes on this file, so a concurrent comP daemon
    write and a concurrent MAGATAMA write cannot interleave into a broken
    JSONL line. Returns the path written to.

    ``agent`` identifies which MAGATAMA code path produced the record (e.g.
    "magatama-patrol", "magatama-handoff") -- without it, comP's
    session_recall falls back to "unknown" and the record can't be
    attributed to MAGATAMA at all.
    """
    history_dir = Path(comp_dir) / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    now_ms = int(time.time() * 1000)
    month = datetime.fromtimestamp(now_ms / 1000, tz=UTC).strftime("%Y-%m")
    log_file = history_dir / f"log-{month}.jsonl"

    record: dict[str, object] = {
        "timestamp": now_ms,
        "query": query,
        "outcome": outcome,
        "files": files or [],
        "symbols": symbols or [],
        "tokens": 0,
        "stale": False,
        "agent": agent,
    }
    line = json.dumps(record, ensure_ascii=False) + "\n"

    # "a+" (not "a"): Windows' locking APIs require a handle opened with
    # read access, matching comP's own .read(true).append(true) choice for
    # the same reason on the Rust side.
    f = log_file.open("a+", encoding="utf-8")
    try:
        with _exclusive_lock(f):
            f.write(line)
            f.flush()
    finally:
        f.close()
    return log_file
