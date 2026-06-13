"""
Knowledge Graph Repository Interface

REQ-KGC-007: Aggregate repository for the complete knowledge graph.
Combines entity and relationship repositories with graph operations.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path

from magatama_core.domain.entities.base import Entity
from magatama_core.domain.entities.relationships import Relationship
from magatama_core.domain.repositories.entity_repository import EntityRepository
from magatama_core.domain.repositories.relationship_repository import RelationshipRepository
from magatama_core.domain.value_objects.ids import EntityId


class KnowledgeGraphRepository(ABC):
    """
    Aggregate repository for the complete knowledge graph.

    Provides unified access to entities and relationships,
    plus graph traversal operations for AI context generation.

    REQ-CTX-001: Contextual code snippets
    REQ-CTX-002: Related entity retrieval
    """

    @property
    @abstractmethod
    def entities(self) -> EntityRepository:
        """Access the entity repository."""
        ...

    @property
    @abstractmethod
    def relationships(self) -> RelationshipRepository:
        """Access the relationship repository."""
        ...

    @abstractmethod
    def find_path(
        self,
        source_id: EntityId,
        target_id: EntityId,
        max_depth: int = 10,
    ) -> Sequence[EntityId] | None:
        """
        Find a path between two entities in the graph.

        Args:
            source_id: Starting entity ID
            target_id: Target entity ID
            max_depth: Maximum path length to search

        Returns:
            Sequence of entity IDs representing the path, or None if no path exists
        """
        ...

    @abstractmethod
    def get_neighbors(
        self,
        entity_id: EntityId,
        depth: int = 1,
    ) -> Sequence[Entity]:
        """
        Get all entities within N hops of a given entity.

        Args:
            entity_id: Center entity ID
            depth: Number of hops to traverse

        Returns:
            Sequence of neighboring entities
        """
        ...

    @abstractmethod
    def get_subgraph(
        self,
        entity_ids: Sequence[EntityId],
    ) -> tuple[Sequence[Entity], Sequence[Relationship]]:
        """
        Extract a subgraph containing specified entities and their connections.

        Args:
            entity_ids: Entity IDs to include in subgraph

        Returns:
            Tuple of (entities, relationships) forming the subgraph
        """
        ...

    @abstractmethod
    def save(self, path: Path) -> None:
        """
        Persist the knowledge graph to storage.

        Args:
            path: Path to save the graph data
        """
        ...

    @abstractmethod
    def load(self, path: Path) -> None:
        """
        Load the knowledge graph from storage.

        Args:
            path: Path to load the graph data from
        """
        ...

    @abstractmethod
    def clear(self) -> None:
        """
        Remove all entities and relationships from the graph.
        """
        ...

    @abstractmethod
    def remove_file(self, file_path: str) -> int:
        """
        Remove all entities and relationships from a specific file.

        Used for incremental updates when a file is modified or deleted.

        Args:
            file_path: Path of the file whose entities should be removed

        Returns:
            Number of entities removed
        """
        ...

    @abstractmethod
    def get_file_hash(self, file_path: str) -> str | None:
        """
        Get the stored hash for a file.

        Args:
            file_path: Path of the file

        Returns:
            Stored hash or None if not tracked
        """
        ...

    @abstractmethod
    def set_file_hash(self, file_path: str, hash_value: str) -> None:
        """
        Store the hash for a file.

        Args:
            file_path: Path of the file
            hash_value: Hash of the file contents
        """
        ...

    @abstractmethod
    def get_tracked_files(self) -> Sequence[str]:
        """
        Get all tracked file paths.

        Returns:
            Sequence of file paths that have been parsed
        """
        ...
