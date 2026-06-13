"""
Relationship Repository Interface

REQ-KGC-007: Data persistence abstraction for relationships.
Defines the contract for relationship storage operations.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from magatama_core.domain.entities.relationships import Relationship, RelationshipType
from magatama_core.domain.value_objects.ids import EntityId


class RelationshipRepository(ABC):
    """
    Abstract repository interface for Relationship persistence.

    Follows Repository pattern (DDD) to abstract data access.
    Handles edges/connections between entities in the knowledge graph.
    """

    @abstractmethod
    def add(self, relationship: Relationship) -> None:
        """
        Add a relationship to the repository.

        Args:
            relationship: The relationship to add
        """
        ...

    @abstractmethod
    def get_outgoing(self, source_id: EntityId) -> Sequence[Relationship]:
        """
        Get all relationships originating from an entity.

        Args:
            source_id: The source entity ID

        Returns:
            Sequence of relationships where source_id is the source
        """
        ...

    @abstractmethod
    def get_incoming(self, target_id: EntityId) -> Sequence[Relationship]:
        """
        Get all relationships pointing to an entity.

        Args:
            target_id: The target entity ID

        Returns:
            Sequence of relationships where target_id is the target
        """
        ...

    @abstractmethod
    def get_by_type(self, rel_type: RelationshipType) -> Sequence[Relationship]:
        """
        Get all relationships of a specific type.

        Args:
            rel_type: The relationship type to filter by

        Returns:
            Sequence of relationships matching the type
        """
        ...

    @abstractmethod
    def delete(
        self,
        source_id: EntityId | None = None,
        target_id: EntityId | None = None,
        rel_type: RelationshipType | None = None,
    ) -> int:
        """
        Delete relationships matching criteria.

        Args:
            source_id: Filter by source entity ID (optional)
            target_id: Filter by target entity ID (optional)
            rel_type: Filter by relationship type (optional)

        Returns:
            Number of relationships deleted
        """
        ...

    @abstractmethod
    def all(self) -> Sequence[Relationship]:
        """
        Get all relationships in the repository.

        Returns:
            Sequence of all relationships
        """
        ...
