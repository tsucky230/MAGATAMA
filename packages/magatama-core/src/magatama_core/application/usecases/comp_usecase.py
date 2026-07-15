"""Use cases for loading comP external data into the knowledge graph."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from magatama_core.domain.entities.base import Entity, EntityType
from magatama_core.domain.entities.relationships import Relationship, RelationshipType
from magatama_core.domain.errors import EntityAlreadyExistsError
from magatama_core.domain.repositories.knowledge_graph_repository import (
    KnowledgeGraphRepository,
)
from magatama_core.domain.value_objects.ids import EntityId
from magatama_core.infrastructure.storage.comp_index_reader import (
    CompIndexNotFoundError,
    CompIndexReader,
)
from magatama_core.infrastructure.storage.comp_session_reader import (
    CompSessionReader,
    CompSessionsNotFoundError,
)


@dataclass
class LoadCompIndexResult:
    success: bool
    alias: str = ""
    db_path: str = ""
    entities_loaded: int = 0
    relationships_loaded: int = 0
    entities_removed: int = 0
    skipped_edges: int = 0
    comp_metadata: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


class LoadCompIndexUseCase:
    """Load (or reload) a comP index.db into the knowledge graph.

    mode="replace": remove all existing comp entities for the same alias,
                    then load fresh (default).
    mode="merge":   add on top of existing data; entities are upserted by ID.
    """

    def __init__(self, knowledge_graph: KnowledgeGraphRepository) -> None:
        self._graph = knowledge_graph
        self._reader = CompIndexReader()

    def execute(self, path: str | Path, mode: str = "replace") -> LoadCompIndexResult:
        if mode not in ("replace", "merge"):
            return LoadCompIndexResult(success=False, errors=[f"Invalid mode: {mode!r}"])
        try:
            data = self._reader.read(path)
        except CompIndexNotFoundError as e:
            return LoadCompIndexResult(success=False, errors=[str(e)])
        except Exception as e:
            return LoadCompIndexResult(success=False, errors=[f"Failed to read comP index: {e}"])

        removed = 0
        if mode == "replace":
            prefix = f"comp:{data.alias}:"
            stale = [e.id for e in self._graph.entities.all() if e.id.value.startswith(prefix)]
            for eid in stale:
                self._graph.relationships.delete(source_id=eid)
                self._graph.relationships.delete(target_id=eid)
                if self._graph.entities.delete(eid):
                    removed += 1

        for entity in data.entities:
            try:
                self._graph.entities.add(entity)
            except EntityAlreadyExistsError:
                self._graph.entities.update(entity)

        for rel in data.relationships:
            self._graph.relationships.add(rel)

        return LoadCompIndexResult(
            success=True,
            alias=data.alias,
            db_path=data.db_path,
            entities_loaded=len(data.entities),
            relationships_loaded=len(data.relationships),
            entities_removed=removed,
            skipped_edges=data.skipped_edges,
            comp_metadata=data.metadata,
        )


@dataclass
class LoadCompSessionsResult:
    success: bool
    alias: str = ""
    comp_dir: str = ""
    sessions_loaded: int = 0
    entities_removed: int = 0
    discussed_links: int = 0
    unmatched_files: int = 0
    unmatched_symbols: int = 0
    sources: list[str] = field(default_factory=list)
    skipped_records: int = 0
    errors: list[str] = field(default_factory=list)


def _norm_path(path: str) -> str:
    p = path.replace("\\", "/").lower()
    # comP daemon auto-records sometimes use extended-length Windows paths
    # (//?/E:/dev/...); strip the prefix so they compare like normal paths.
    if p.startswith("//?/"):
        p = p[4:]
    return p


def _match_file_targets(
    key: str,
    file_targets: dict[str, set[EntityId]],
    file_suffix_targets: list[tuple[str, EntityId]],
) -> set[EntityId]:
    """Match a normalized record path against graph MODULE paths.

    Tries exact match first, then suffix match in both directions: the
    record path may be relative while the graph path is absolute, or
    (daemon auto-records) absolute while the graph path is relative.
    """
    targets = set(file_targets.get(key, set()))
    if not targets:
        suffix = "/" + key
        targets = {eid for k, eid in file_suffix_targets if k.endswith(suffix)}
    if not targets:
        targets = {eid for k, eid in file_suffix_targets if k and key.endswith("/" + k)}
    return targets


class LoadCompSessionsUseCase:
    """Load comP session history into the knowledge graph.

    Each session record (from .comp/session-memory.json and
    .comp/history/*.jsonl) becomes a SESSION entity. Files and symbols
    mentioned by a record are linked to matching code entities already in
    the graph via DISCUSSED relationships, so questions like "what past
    requests touched this file?" can be answered with get_related_entities.

    mode="replace": remove existing session entities for the same alias
                    first (default).
    mode="merge":   upsert on top of existing data.
    """

    def __init__(self, knowledge_graph: KnowledgeGraphRepository) -> None:
        self._graph = knowledge_graph
        self._reader = CompSessionReader()

    def execute(self, path: str | Path, mode: str = "replace") -> LoadCompSessionsResult:
        if mode not in ("replace", "merge"):
            return LoadCompSessionsResult(success=False, errors=[f"Invalid mode: {mode!r}"])
        try:
            data = self._reader.read(path)
        except CompSessionsNotFoundError as e:
            return LoadCompSessionsResult(success=False, errors=[str(e)])
        except Exception as e:
            return LoadCompSessionsResult(
                success=False, errors=[f"Failed to read comP sessions: {e}"]
            )

        removed = 0
        if mode == "replace":
            prefix = f"comp-session:{data.alias}:"
            stale = [e.id for e in self._graph.entities.all() if e.id.value.startswith(prefix)]
            for eid in stale:
                self._graph.relationships.delete(source_id=eid)
                self._graph.relationships.delete(target_id=eid)
                if self._graph.entities.delete(eid):
                    removed += 1

        # Build lookups over the code entities currently in the graph.
        # Files match MODULE entities by normalized name/location; symbols
        # match any non-module, non-session entity by exact name.
        file_targets: dict[str, set[EntityId]] = {}
        file_suffix_targets: list[tuple[str, EntityId]] = []
        symbol_targets: dict[str, set[EntityId]] = {}
        for entity in self._graph.entities.all():
            if entity.type == EntityType.SESSION:
                continue
            if entity.type == EntityType.MODULE:
                for key in {_norm_path(entity.name), _norm_path(entity.location.file)}:
                    file_targets.setdefault(key, set()).add(entity.id)
                    file_suffix_targets.append((key, entity.id))
            else:
                symbol_targets.setdefault(entity.name, set()).add(entity.id)

        result = LoadCompSessionsResult(
            success=True,
            alias=data.alias,
            comp_dir=data.comp_dir,
            entities_removed=removed,
            sources=data.sources,
            skipped_records=data.skipped_lines,
        )

        for record in data.records:
            try:
                self._graph.entities.add(record.entity)
            except EntityAlreadyExistsError:
                self._graph.entities.update(record.entity)
            result.sessions_loaded += 1

            linked: set[EntityId] = set()
            for f in set(record.files):
                targets = _match_file_targets(_norm_path(f), file_targets, file_suffix_targets)
                if not targets:
                    result.unmatched_files += 1
                    continue
                for target_id in targets - linked:
                    self._graph.relationships.add(
                        Relationship(
                            source_id=record.entity.id,
                            target_id=target_id,
                            type=RelationshipType.DISCUSSED,
                            metadata={"origin": "comp-session", "kind": "file", "mention": f},
                        )
                    )
                    linked.add(target_id)
                    result.discussed_links += 1

            for s in set(record.symbols):
                targets = symbol_targets.get(s, set())
                if not targets:
                    result.unmatched_symbols += 1
                    continue
                for target_id in targets - linked:
                    self._graph.relationships.add(
                        Relationship(
                            source_id=record.entity.id,
                            target_id=target_id,
                            type=RelationshipType.DISCUSSED,
                            metadata={"origin": "comp-session", "kind": "symbol", "mention": s},
                        )
                    )
                    linked.add(target_id)
                    result.discussed_links += 1

        return result


_WHEN_PREFIX_RE = re.compile(r"^\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\] ")


@dataclass
class EntityHistoryResult:
    success: bool
    query: str = ""
    matched_entities: list[dict[str, str]] = field(default_factory=list)
    history: list[dict[str, object]] = field(default_factory=list)
    impact: dict[str, object] | None = None
    errors: list[str] = field(default_factory=list)


class EntityHistoryUseCase:
    """Answer "what past sessions touched this file/symbol, and what depends on it now?".

    Looks up a file path or symbol name in the knowledge graph, follows
    inbound DISCUSSED relationships back to SESSION entities (loaded by
    LoadCompSessionsUseCase), and optionally runs impact analysis on the
    entity so the caller sees past context and present blast radius in one
    query.
    """

    def __init__(self, knowledge_graph: KnowledgeGraphRepository) -> None:
        self._graph = knowledge_graph

    def execute(self, name: str, limit: int = 10, analyze: bool = True) -> EntityHistoryResult:
        result = EntityHistoryResult(success=True, query=name)
        targets = self._find_targets(name)
        if not targets:
            return EntityHistoryResult(
                success=False,
                query=name,
                errors=[
                    f"No entity matching {name!r} in the knowledge graph. "
                    "Load data first with read_external_graph / read_external_sessions."
                ],
            )

        result.matched_entities = [
            {
                "id": e.id.value,
                "name": e.name,
                "type": e.type.value,
                "file": e.location.file,
            }
            for e in targets
        ]

        # SESSION entity id -> aggregated history entry.
        entries: dict[str, dict[str, object]] = {}
        for target in targets:
            for rel in self._graph.relationships.get_incoming(target.id):
                if rel.type != RelationshipType.DISCUSSED:
                    continue
                session = self._graph.entities.get(rel.source_id)
                if session is None or session.type != EntityType.SESSION:
                    continue
                entry = entries.get(session.id.value)
                if entry is None:
                    docstring = session.docstring or ""
                    m = _WHEN_PREFIX_RE.match(docstring)
                    entry = {
                        "request": session.name,
                        "outcome": docstring[m.end() :] if m else docstring,
                        "when": m.group(1) if m else "",
                        "mentions": [],
                    }
                    entries[session.id.value] = entry
                mentions = entry["mentions"]
                assert isinstance(mentions, list)
                mentions.append(
                    {
                        "kind": (rel.metadata or {}).get("kind", ""),
                        "mention": (rel.metadata or {}).get("mention", ""),
                        "entity": target.name,
                    }
                )

        # Newest first; records without a timestamp go last.
        result.history = sorted(
            entries.values(),
            key=lambda e: str(e["when"]),
            reverse=True,
        )[: max(limit, 1)]

        if analyze:
            try:
                from magatama_core.application.usecases.framework_usecase import (
                    DependencyImpactUseCase,
                )

                r = DependencyImpactUseCase(self._graph).analyze_impact(entity_name=name)
                result.impact = {
                    "impact_score": r.impact_score,
                    "risk_level": r.risk_level,
                    "total_affected": r.total_affected,
                }
            except Exception as e:
                result.errors.append(f"impact analysis failed: {e}")

        return result

    def _find_targets(self, name: str) -> list[Entity]:
        """Match a symbol by exact name, or a file by (suffix-tolerant) path."""
        targets: dict[str, Entity] = {}
        for entity in self._graph.entities.get_by_name(name):
            if entity.type != EntityType.SESSION:
                targets[entity.id.value] = entity

        key = _norm_path(name)
        for entity in self._graph.entities.all():
            if entity.type != EntityType.MODULE or entity.id.value in targets:
                continue
            # File MODULE entities are named with their path. Deliberately
            # not matched on location.file: markdown headings etc. are also
            # MODULE-typed and share the file location, and matching them
            # would balloon the result with every section of the file.
            candidate = _norm_path(entity.name)
            if (
                candidate == key
                or candidate.endswith("/" + key)
                or (candidate and key.endswith("/" + candidate))
            ):
                targets[entity.id.value] = entity
        return list(targets.values())
