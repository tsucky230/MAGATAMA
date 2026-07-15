"""Reader for .comp/constraints.json (constraint-watchdog data).

The constraint watchdog hook (.claude/hooks/constraint-watchdog.sh) warns
when an agent edits a registered "do not touch" file. This reader gives
Python-side consumers (patrol) access to the same registry:

    {"constraints": [{"id", "file", "line_range", "entity", "issue",
                      "rule", "reason", "severity", "created_at"}]}

Only ``file`` is required; a trailing "/" marks a directory constraint.
A missing or malformed file yields an empty list — constraints are an
overlay, never a reason to fail the caller.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Constraint:
    """One "do not modify" entry from constraints.json."""

    id: str = ""
    file: str = ""
    entity: str = ""
    rule: str = ""
    reason: str = ""
    severity: str = ""


def read_constraints(comp_dir: str | Path) -> list[Constraint]:
    """Read constraints from <comp_dir>/constraints.json.

    Accepts the .comp directory. Returns [] when the file is missing,
    unparseable, or holds no valid entries.
    """
    path = Path(comp_dir) / "constraints.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    raw = payload.get("constraints") if isinstance(payload, dict) else None
    if not isinstance(raw, list):
        return []

    constraints = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        file = item.get("file")
        if not isinstance(file, str) or not file:
            continue
        constraints.append(
            Constraint(
                id=str(item.get("id") or ""),
                file=file,
                entity=str(item.get("entity") or ""),
                rule=str(item.get("rule") or ""),
                reason=str(item.get("reason") or ""),
                severity=str(item.get("severity") or "WARNING"),
            )
        )
    return constraints
