"""File-scoped change impact over a loaded comP code graph."""

from __future__ import annotations

import os
import re
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import cast

from magatama_core.domain.entities.base import Entity, EntityType
from magatama_core.domain.entities.relationships import Relationship, RelationshipType
from magatama_core.domain.repositories.knowledge_graph_repository import KnowledgeGraphRepository


@dataclass
class ChangeScopeResult:
    success: bool
    changed_files: list[str] = field(default_factory=list)
    changed_symbols: list[dict[str, str]] = field(default_factory=list)
    affected_symbols: list[dict[str, object]] = field(default_factory=list)
    affected_files: list[str] = field(default_factory=list)
    impact_score: float = 0.0
    risk_level: str = "unknown"
    depth_analyzed: int = 3
    errors: list[str] = field(default_factory=list)


class ChangeScopeUseCase:
    """Analyze the dependents of all symbols in the specified indexed files.

    ``files`` uses comP's stored path format: relative for the main root,
    absolute for extra roots. Exact paths win; a suffix is accepted only when
    it names one file. Any missing or ambiguous file fails the whole request
    with ``risk_level='unknown'`` rather than returning a deceptively low risk.
    ``depth`` is clamped to 1..10. No filesystem or network writes occur.
    Dependency edges are traversed from callee to callers; DISCUSSED and
    CONTAINS are never treated as code dependencies. The result contains each
    affected symbol once, with the first edge that explains its inclusion.
    """

    def __init__(self, knowledge_graph: KnowledgeGraphRepository) -> None:
        self._graph = knowledge_graph

    def execute(
        self, files: list[str], depth: int = 3, workspace_root: str = "", alias: str = ""
    ) -> ChangeScopeResult:
        """``alias`` limits the analysis to one loaded comP index.

        The graph outlives a single request, so it can hold several workspaces;
        without the limit, same-named files elsewhere (``README.md``) read as
        ambiguous paths or duplicate path representations of this workspace.
        """
        depth = max(1, min(depth, 10))
        if not files or any(not isinstance(item, str) or not item.strip() for item in files):
            return ChangeScopeResult(
                success=False, depth_analyzed=depth, errors=["files must contain file paths"]
            )

        alias_pattern = re.escape(alias) if alias else "[^:]+"
        modules = [
            entity
            for entity in self._graph.entities.all()
            if entity.type == EntityType.MODULE
            and re.match(rf"^comp:{alias_pattern}:f\d+$", entity.id.value)
        ]
        canonical_counts: dict[str, int] = defaultdict(int)
        if workspace_root:
            root = normalize_comp_path(workspace_root).rstrip("/")
            for module in modules:
                stored = normalize_comp_path(module.name)
                canonical = stored if _is_absolute(stored) else f"{root}/{stored}"
                canonical_counts[canonical] += 1
        duplicate_paths = sorted(path for path, count in canonical_counts.items() if count > 1)
        selected: dict[str, Entity] = {}
        errors: list[str] = []
        for requested in files:
            matches = self._resolve_file(requested, modules)
            if len(matches) != 1:
                reason = "not found" if not matches else "ambiguous"
                errors.append(f"{reason} file {requested!r}; use a full indexed path")
            else:
                selected[matches[0].id.value] = matches[0]
        if errors:
            return ChangeScopeResult(success=False, depth_analyzed=depth, errors=errors)

        relationships = list(self._graph.relationships.all())
        code_entities = {
            entity.id.value: entity
            for entity in self._graph.entities.all()
            if entity.type != EntityType.SESSION
            and (not alias or entity.id.value.startswith(f"comp:{alias}:"))
        }
        changed_ids = {
            rel.target_id.value
            for rel in relationships
            if rel.type == RelationshipType.CONTAINS
            and rel.source_id.value in selected
            and rel.target_id.value in code_entities
        }
        changed = sorted(
            (code_entities[eid] for eid in changed_ids),
            key=lambda entity: (entity.location.file, entity.name, entity.id.value),
        )
        result = ChangeScopeResult(
            success=True,
            changed_files=sorted(entity.name for entity in selected.values()),
            changed_symbols=[
                {"id": entity.id.value, "name": entity.name, "file": entity.location.file}
                for entity in changed
            ],
            depth_analyzed=depth,
        )
        if duplicate_paths:
            result.errors.append(
                "Index contains duplicate path representations; force re-index comP: "
                + ", ".join(duplicate_paths[:3])
            )

        incoming: dict[str, list[Relationship]] = defaultdict(list)
        for rel in relationships:
            if rel.type in {RelationshipType.CONTAINS, RelationshipType.DISCUSSED}:
                continue
            if rel.source_id.value in code_entities and rel.target_id.value in code_entities:
                incoming[rel.target_id.value].append(rel)
        if not changed or not incoming:
            result.errors.append("No indexed symbols or dependency edges; impact is unknown")
            return result

        queue = deque((entity.id.value, 0) for entity in changed)
        visited = set(changed_ids)
        while queue:
            current_id, current_depth = queue.popleft()
            if current_depth >= depth:
                continue
            for rel in sorted(
                incoming[current_id], key=lambda edge: (edge.source_id.value, edge.type.value)
            ):
                dependent_id = rel.source_id.value
                if dependent_id in visited:
                    continue
                visited.add(dependent_id)
                entity = code_entities[dependent_id]
                next_depth = current_depth + 1
                result.affected_symbols.append(
                    {
                        "id": dependent_id,
                        "name": entity.name,
                        "file": entity.location.file,
                        "depth": next_depth,
                        "relationship": rel.type.value,
                        "via": current_id,
                    }
                )
                queue.append((dependent_id, next_depth))

        result.affected_symbols.sort(
            key=lambda item: (item["depth"], str(item["file"]), str(item["name"]))
        )
        result.affected_files = sorted({str(item["file"]) for item in result.affected_symbols})
        result.impact_score = round(
            sum(0.5 ** (cast("int", item["depth"]) - 1) for item in result.affected_symbols), 2
        )
        affected = len(result.affected_symbols)
        if result.impact_score >= 10 or affected >= 20:
            result.risk_level = "high"
        elif result.impact_score >= 5 or affected >= 10:
            result.risk_level = "medium"
        else:
            result.risk_level = "low"
        if duplicate_paths:
            result.risk_level = "unknown"
        return result

    @staticmethod
    def _resolve_file(requested: str, modules: list[Entity]) -> list[Entity]:
        key = normalize_comp_path(requested)
        exact = [entity for entity in modules if normalize_comp_path(entity.name) == key]
        if exact:
            return exact
        return [
            entity
            for entity in modules
            if normalize_comp_path(entity.name).endswith("/" + key)
            or key.endswith("/" + normalize_comp_path(entity.name))
        ]


def normalize_comp_path(value: str) -> str:
    """Normalize comP paths without folding case on Unix/UNC absolute paths."""
    path = value.replace("\\", "/")
    if path.lower().startswith("//?/unc/"):
        path = "//" + path[8:]
    elif path.startswith("//?/"):
        path = path[4:]
    if re.match(r"^[a-zA-Z]:/", path):
        return path.lower()
    if path.startswith("/"):
        return path
    return path.lower() if os.name == "nt" else path


def _is_absolute(path: str) -> bool:
    return path.startswith("/") or bool(re.match(r"^[a-zA-Z]:/", path))
