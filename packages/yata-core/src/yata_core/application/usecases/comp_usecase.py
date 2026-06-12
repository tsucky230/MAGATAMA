"""Use case for loading a comP external index into the knowledge graph."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from yata_core.domain.errors import EntityAlreadyExistsError
from yata_core.domain.repositories.knowledge_graph_repository import (
    KnowledgeGraphRepository,
)
from yata_core.infrastructure.storage.comp_index_reader import (
    CompIndexReader,
    CompIndexNotFoundError,
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

    def execute(
        self, path: str | Path, mode: str = "replace"
    ) -> LoadCompIndexResult:
        if mode not in ("replace", "merge"):
            return LoadCompIndexResult(
                success=False, errors=[f"Invalid mode: {mode!r}"]
            )
        try:
            data = self._reader.read(path)
        except CompIndexNotFoundError as e:
            return LoadCompIndexResult(success=False, errors=[str(e)])
        except Exception as e:
            return LoadCompIndexResult(
                success=False, errors=[f"Failed to read comP index: {e}"]
            )

        removed = 0
        if mode == "replace":
            prefix = f"comp:{data.alias}:"
            stale = [
                e.id
                for e in self._graph.entities.all()
                if e.id.value.startswith(prefix)
            ]
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
