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
from magatama_core.infrastructure.storage.comp_constraints_reader import (
    Constraint,
    read_constraints,
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
class ConstraintHit:
    """A changed file/symbol that falls under a registered constraint."""

    constraint_id: str
    file: str
    severity: str
    rule: str
    matched: list[str] = field(default_factory=list)


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
    constraint_hits: list[ConstraintHit] = field(default_factory=list)
    history_file: str = ""
    errors: list[str] = field(default_factory=list)


def _symbol_name(key: str) -> str:
    """Extract the symbol name from a 'path::name::kind' snapshot key."""
    parts = key.split("::")
    return parts[1] if len(parts) >= 2 else key


def _norm_path(path: str) -> str:
    p = path.replace("\\", "/").lower()
    if p.startswith("//?/"):
        p = p[4:]
    return p


def _is_comp_internal(path: str) -> bool:
    """True for paths inside a .comp directory (e.g. .comp/history/*.jsonl)."""
    p = _norm_path(path)
    return p.startswith(".comp/") or "/.comp/" in p


def _filter_snapshot(snapshot: CompSnapshot) -> CompSnapshot:
    """Drop .comp-internal entries from a snapshot.

    comP may index its own .comp/history/*.jsonl for BM25 recall; patrol
    itself appends to those files, so diffing them would make every pass
    detect its own previous log write (a self-trigger loop).
    """
    return CompSnapshot(
        files={p: h for p, h in snapshot.files.items() if not _is_comp_internal(p)},
        symbols={
            k: s for k, s in snapshot.symbols.items() if not _is_comp_internal(k.split("::")[0])
        },
    )


class PatrolUseCase:
    """Diff the comP index against the last patrol pass and leave notes."""

    def __init__(self, max_analyzed: int = 10, impact_depth: int = 3) -> None:
        self._max_analyzed = max_analyzed
        self._impact_depth = impact_depth

    def execute(self, workspace: str | Path, log_history: bool = True) -> PatrolReport:
        workspace = Path(workspace)
        try:
            db_path = resolve_db_path(workspace)
            snapshot = _filter_snapshot(read_comp_snapshot(db_path))
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

        self._diff(_filter_snapshot(previous), snapshot, report)
        report.changed = bool(
            report.files_added
            or report.files_changed
            or report.files_removed
            or report.symbols_added
            or report.symbols_changed
            or report.symbols_removed
        )

        if report.changed:
            self._check_constraints(db_path.parent, report)
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

    # -- constraints ---------------------------------------------------

    def _check_constraints(self, comp_dir: Path, report: PatrolReport) -> None:
        """Cross changed files/symbols against .comp/constraints.json.

        A change touching a registered "do not modify" file is the single
        most important thing a patrol pass can find, so hits are surfaced
        first in the summary and marked with their severity.
        """
        constraints = read_constraints(comp_dir)
        if not constraints:
            return

        changed_files = report.files_added + report.files_changed + report.files_removed
        changed_symbols = {
            _symbol_name(k)
            for k in report.symbols_added + report.symbols_changed + report.symbols_removed
        }

        for constraint in constraints:
            matched = self._match_constraint(constraint, changed_files, changed_symbols)
            if matched:
                report.constraint_hits.append(
                    ConstraintHit(
                        constraint_id=constraint.id or constraint.file,
                        file=constraint.file,
                        severity=constraint.severity,
                        rule=constraint.rule,
                        matched=matched,
                    )
                )

    @staticmethod
    def _match_constraint(
        constraint: Constraint, changed_files: list[str], changed_symbols: set[str]
    ) -> list[str]:
        matched: list[str] = []
        cfile = _norm_path(constraint.file)
        for f in changed_files:
            nf = _norm_path(f)
            if cfile.endswith("/"):
                # Directory constraint: any file under it counts.
                if nf.startswith(cfile) or f"/{cfile}" in f"/{nf}":
                    matched.append(f)
            elif nf == cfile or nf.endswith("/" + cfile) or cfile.endswith("/" + nf):
                matched.append(f)
        if constraint.entity:
            # comP symbol names are bare (no class prefix); accept the full
            # entity string or its last dotted segment.
            last = constraint.entity.rsplit(".", 1)[-1]
            for s in changed_symbols:
                if s == constraint.entity or s == last:
                    matched.append(s)
        return matched

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
        query = (
            "magatama patrol: 制約対象の変更を検知"
            if report.constraint_hits
            else "magatama patrol: 変更検知"
        )
        try:
            log_file = append_history_record(
                comp_dir,
                query=query,
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
        parts = []
        for hit in report.constraint_hits:
            rule = f"（{hit.rule}）" if hit.rule else ""
            parts.append(
                f"[{hit.severity}] 制約 {hit.constraint_id} に抵触の疑い: "
                f"{', '.join(hit.matched)} が変更されました{rule}"
            )
        parts.append(
            f"ファイル: +{len(report.files_added)} ~{len(report.files_changed)}"
            f" -{len(report.files_removed)} / "
            f"シンボル: +{len(report.symbols_added)} ~{len(report.symbols_changed)}"
            f" -{len(report.symbols_removed)}"
        )
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
