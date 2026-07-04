"""Patrol use case: watch a comP index for changes and leave notes.

One patrol pass:

1. Read a lightweight snapshot (file hashes + symbol signatures) of the
   workspace's .comp/index.db.
2. Diff it against the snapshot saved by the previous pass
   (.magatama/patrol-state.json).
3. For changed/added symbols, load the index into a knowledge graph and run
   impact + quality analysis.
4. Append a summary record to .comp/history/log-YYYY-MM.jsonl so the next
   session's session_recall picks up "what changed while you were away".

The first pass has no previous snapshot; it saves a baseline and reports
without analyzing or logging.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from magatama_core.application.usecases.comp_usecase import LoadCompIndexUseCase
from magatama_core.application.usecases.framework_usecase import (
    CodeQualityUseCase,
    DependencyImpactUseCase,
)
from magatama_core.infrastructure.storage.comp_history_writer import append_history_record
from magatama_core.infrastructure.storage.comp_index_reader import (
    CompIndexNotFoundError,
    CompSnapshot,
    read_comp_snapshot,
    resolve_db_path,
)
from magatama_core.infrastructure.storage.networkx_graph import NetworkXKnowledgeGraph

STATE_DIR_NAME = ".magatama"
STATE_FILE_NAME = "patrol-state.json"


@dataclass
class SymbolAnalysis:
    """Impact/quality analysis for one changed symbol."""

    name: str
    change: str  # added, changed, removed
    impact_score: float = 0.0
    risk_level: str = "low"
    total_affected: int = 0
    quality_score: float = 0.0
    quality_status: str = "unknown"


@dataclass
class PatrolReport:
    """Result of one patrol pass."""

    success: bool
    baseline: bool = False
    changed: bool = False
    workspace: str = ""
    files_added: list[str] = field(default_factory=list)
    files_changed: list[str] = field(default_factory=list)
    files_removed: list[str] = field(default_factory=list)
    symbols_added: list[str] = field(default_factory=list)
    symbols_changed: list[str] = field(default_factory=list)
    symbols_removed: list[str] = field(default_factory=list)
    analyses: list[SymbolAnalysis] = field(default_factory=list)
    history_file: str = ""
    errors: list[str] = field(default_factory=list)


def _symbol_name(key: str) -> str:
    """Extract the symbol name from a 'path::name::kind' snapshot key."""
    parts = key.split("::")
    return parts[1] if len(parts) >= 2 else key


class PatrolUseCase:
    """Diff the comP index against the last patrol pass and leave notes."""

    def __init__(self, max_analyzed: int = 10, impact_depth: int = 3) -> None:
        self._max_analyzed = max_analyzed
        self._impact_depth = impact_depth

    def execute(self, workspace: str | Path, log_history: bool = True) -> PatrolReport:
        workspace = Path(workspace)
        try:
            db_path = resolve_db_path(workspace)
            snapshot = read_comp_snapshot(db_path)
        except CompIndexNotFoundError as e:
            return PatrolReport(success=False, errors=[str(e)])
        except Exception as e:
            return PatrolReport(success=False, errors=[f"Failed to read comP index: {e}"])

        report = PatrolReport(success=True, workspace=str(workspace))
        state_file = workspace / STATE_DIR_NAME / STATE_FILE_NAME
        previous = self._load_state(state_file)

        if previous is None:
            report.baseline = True
            self._save_state(state_file, snapshot, report)
            return report

        self._diff(previous, snapshot, report)
        report.changed = bool(
            report.files_added
            or report.files_changed
            or report.files_removed
            or report.symbols_added
            or report.symbols_changed
            or report.symbols_removed
        )

        if report.changed:
            self._analyze(db_path, report)
            if log_history:
                self._log_history(db_path, report)

        self._save_state(state_file, snapshot, report)
        return report

    # -- state ---------------------------------------------------------

    def _load_state(self, state_file: Path) -> CompSnapshot | None:
        if not state_file.is_file():
            return None
        try:
            payload = json.loads(state_file.read_text(encoding="utf-8"))
            return CompSnapshot(
                files=dict(payload["files"]),
                symbols=dict(payload["symbols"]),
            )
        except (OSError, json.JSONDecodeError, KeyError, TypeError):
            # Corrupt state: treat as first run rather than failing.
            return None

    def _save_state(self, state_file: Path, snapshot: CompSnapshot, report: PatrolReport) -> None:
        try:
            state_file.parent.mkdir(parents=True, exist_ok=True)
            state_file.write_text(
                json.dumps({"files": snapshot.files, "symbols": snapshot.symbols}),
                encoding="utf-8",
            )
        except OSError as e:
            report.errors.append(f"Failed to save patrol state: {e}")

    # -- diff ----------------------------------------------------------

    def _diff(self, prev: CompSnapshot, curr: CompSnapshot, report: PatrolReport) -> None:
        report.files_added = sorted(set(curr.files) - set(prev.files))
        report.files_removed = sorted(set(prev.files) - set(curr.files))
        report.files_changed = sorted(
            p for p in set(curr.files) & set(prev.files) if curr.files[p] != prev.files[p]
        )

        added_keys = sorted(set(curr.symbols) - set(prev.symbols))
        removed_keys = sorted(set(prev.symbols) - set(curr.symbols))
        # Changed = same key, different signature. Line-number drift is
        # invisible here by design (signatures don't contain line numbers).
        changed_keys = sorted(
            k for k in set(curr.symbols) & set(prev.symbols) if curr.symbols[k] != prev.symbols[k]
        )
        report.symbols_added = added_keys
        report.symbols_changed = changed_keys
        report.symbols_removed = removed_keys

    # -- analysis ------------------------------------------------------

    def _analyze(self, db_path: Path, report: PatrolReport) -> None:
        """Run impact/quality analysis for changed symbols (capped)."""
        # Priority: changed first (edits to existing code carry the most
        # risk), then added. Removed symbols are no longer in the graph, so
        # they are listed in the report without analysis.
        targets: list[tuple[str, str]] = [
            (_symbol_name(k), "changed") for k in report.symbols_changed
        ] + [(_symbol_name(k), "added") for k in report.symbols_added]

        seen: set[str] = set()
        unique_targets = []
        for name, change in targets:
            if name not in seen:
                seen.add(name)
                unique_targets.append((name, change))
        unique_targets = unique_targets[: self._max_analyzed]
        if not unique_targets:
            return

        try:
            graph = NetworkXKnowledgeGraph()
            LoadCompIndexUseCase(graph).execute(db_path)
            impact = DependencyImpactUseCase(graph)
            quality = CodeQualityUseCase(graph)
        except Exception as e:
            report.errors.append(f"Analysis setup failed: {e}")
            return

        for name, change in unique_targets:
            analysis = SymbolAnalysis(name=name, change=change)
            try:
                r = impact.analyze_impact(entity_name=name, depth=self._impact_depth)
                analysis.impact_score = r.impact_score
                analysis.risk_level = r.risk_level
                analysis.total_affected = r.total_affected
            except Exception as e:  # per-symbol failure must not stop the patrol
                report.errors.append(f"impact({name}): {e}")
            try:
                q = quality.analyze_quality(name)
                analysis.quality_score = q.overall_score
                analysis.quality_status = q.overall_status
            except Exception as e:
                report.errors.append(f"quality({name}): {e}")
            report.analyses.append(analysis)

    # -- history -------------------------------------------------------

    def _log_history(self, db_path: Path, report: PatrolReport) -> None:
        comp_dir = db_path.parent
        try:
            log_file = append_history_record(
                comp_dir,
                query="magatama patrol: 変更検知",
                outcome=self.format_summary(report),
                files=report.files_added + report.files_changed + report.files_removed,
                symbols=[a.name for a in report.analyses],
            )
            report.history_file = str(log_file)
        except OSError as e:
            report.errors.append(f"Failed to write history: {e}")

    @staticmethod
    def format_summary(report: PatrolReport) -> str:
        """Human/LLM-readable one-paragraph summary of a patrol pass."""
        parts = [
            f"ファイル: +{len(report.files_added)} ~{len(report.files_changed)}"
            f" -{len(report.files_removed)} / "
            f"シンボル: +{len(report.symbols_added)} ~{len(report.symbols_changed)}"
            f" -{len(report.symbols_removed)}"
        ]
        for a in report.analyses:
            parts.append(
                f"{a.name}({a.change}): impact={a.impact_score:.1f}"
                f" risk={a.risk_level} affected={a.total_affected}"
                f" quality={a.quality_score:.0f}({a.quality_status})"
            )
        if report.symbols_removed:
            removed_names = sorted({_symbol_name(k) for k in report.symbols_removed})
            parts.append("削除: " + ", ".join(removed_names[:10]))
        return " | ".join(parts)
