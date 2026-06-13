"""
In-Memory Repository Implementations

REQ-KGC-007: Data persistence abstraction.
Simple in-memory implementations for testing and development.
"""

from __future__ import annotations

from collections.abc import Sequence

from magatama_core.domain.entities.base import Entity, EntityType
from magatama_core.domain.entities.relationships import Relationship, RelationshipType
from magatama_core.domain.errors import EntityAlreadyExistsError, EntityNotFoundError
from magatama_core.domain.repositories.entity_repository import EntityRepository
from magatama_core.domain.repositories.relationship_repository import RelationshipRepository
from magatama_core.domain.value_objects.ids import EntityId


class InMemoryEntityRepository(EntityRepository):
    """
    In-memory implementation of EntityRepository.

    Uses a simple dictionary for O(1) lookups by ID.
    Suitable for testing and small codebases.
    """

    def __init__(self) -> None:
        """Initialize empty repository."""
        self._entities: dict[str, Entity] = {}

    def add(self, entity: Entity) -> None:
        """Add an entity to the repository."""
        key = entity.id.value
        if key in self._entities:
            raise EntityAlreadyExistsError(entity.id)
        self._entities[key] = entity

    def get(self, entity_id: EntityId) -> Entity | None:
        """Retrieve an entity by its ID."""
        return self._entities.get(entity_id.value)

    def get_by_type(self, entity_type: EntityType) -> Sequence[Entity]:
        """Get all entities of a specific type."""
        return [e for e in self._entities.values() if e.type == entity_type]

    def get_by_name(self, name: str) -> Sequence[Entity]:
        """Get all entities with a specific name."""
        return [e for e in self._entities.values() if e.name == name]

    def update(self, entity: Entity) -> None:
        """Update an existing entity."""
        key = entity.id.value
        if key not in self._entities:
            raise EntityNotFoundError(entity.id)
        self._entities[key] = entity

    def delete(self, entity_id: EntityId) -> bool:
        """Delete an entity by its ID."""
        key = entity_id.value
        if key in self._entities:
            del self._entities[key]
            return True
        return False

    def all(self) -> Sequence[Entity]:
        """Get all entities in the repository."""
        return list(self._entities.values())

    def count(self) -> int:
        """Get the total number of entities."""
        return len(self._entities)


class InMemoryRelationshipRepository(RelationshipRepository):
    """
    In-memory implementation of RelationshipRepository.

    Uses a list for simple iteration-based queries.
    Suitable for testing and small graphs.
    """

    def __init__(self) -> None:
        """Initialize empty repository."""
        self._relationships: list[Relationship] = []

    def add(self, relationship: Relationship) -> None:
        """Add a relationship to the repository."""
        self._relationships.append(relationship)

    def get_outgoing(self, source_id: EntityId) -> Sequence[Relationship]:
        """Get all relationships originating from an entity."""
        return [r for r in self._relationships if r.source_id.value == source_id.value]

    def get_incoming(self, target_id: EntityId) -> Sequence[Relationship]:
        """Get all relationships pointing to an entity."""
        return [r for r in self._relationships if r.target_id.value == target_id.value]

    def get_by_type(self, rel_type: RelationshipType) -> Sequence[Relationship]:
        """Get all relationships of a specific type."""
        return [r for r in self._relationships if r.type == rel_type]

    def delete(
        self,
        source_id: EntityId | None = None,
        target_id: EntityId | None = None,
        rel_type: RelationshipType | None = None,
    ) -> int:
        """Delete relationships matching criteria."""
        to_delete: list[Relationship] = []

        for r in self._relationships:
            match = True
            if source_id is not None and r.source_id.value != source_id.value:
                match = False
            if target_id is not None and r.target_id.value != target_id.value:
                match = False
            if rel_type is not None and r.type != rel_type:
                match = False
            if match:
                to_delete.append(r)

        for r in to_delete:
            self._relationships.remove(r)

        return len(to_delete)

    def all(self) -> Sequence[Relationship]:
        """Get all relationships in the repository."""
        return list(self._relationships)
