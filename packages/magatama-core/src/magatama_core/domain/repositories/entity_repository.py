"""
Entity Repository Interface

REQ-KGC-007: Data persistence abstraction for entities.
Defines the contract for entity storage operations.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from magatama_core.domain.entities.base import Entity, EntityType
from magatama_core.domain.value_objects.ids import EntityId


class EntityRepository(ABC):
    """
    Abstract repository interface for Entity persistence.

    Follows Repository pattern (DDD) to abstract data access.
    Implementations may use in-memory storage, SQLite, or other backends.
    """

    @abstractmethod
    def add(self, entity: Entity) -> None:
        """
        Add an entity to the repository.

        Args:
            entity: The entity to add

        Raises:
            EntityAlreadyExistsError: If entity with same ID exists
        """
        ...

    @abstractmethod
    def get(self, entity_id: EntityId) -> Entity | None:
        """
        Retrieve an entity by its ID.

        Args:
            entity_id: The entity ID to look up

        Returns:
            The entity if found, None otherwise
        """
        ...

    @abstractmethod
    def get_by_type(self, entity_type: EntityType) -> Sequence[Entity]:
        """
        Get all entities of a specific type.

        Args:
            entity_type: The type to filter by

        Returns:
            Sequence of entities matching the type
        """
        ...

    @abstractmethod
    def get_by_name(self, name: str) -> Sequence[Entity]:
        """
        Get all entities with a specific name.

        Args:
            name: The name to search for

        Returns:
            Sequence of entities with matching name
        """
        ...

    @abstractmethod
    def update(self, entity: Entity) -> None:
        """
        Update an existing entity.

        Args:
            entity: The entity with updated values

        Raises:
            EntityNotFoundError: If entity doesn't exist
        """
        ...

    @abstractmethod
    def delete(self, entity_id: EntityId) -> bool:
        """
        Delete an entity by its ID.

        Args:
            entity_id: The ID of entity to delete

        Returns:
            True if entity was deleted, False if not found
        """
        ...

    @abstractmethod
    def all(self) -> Sequence[Entity]:
        """
        Get all entities in the repository.

        Returns:
            Sequence of all entities
        """
        ...

    @abstractmethod
    def count(self) -> int:
        """
        Get the total number of entities.

        Returns:
            Count of entities in repository
        """
        ...
