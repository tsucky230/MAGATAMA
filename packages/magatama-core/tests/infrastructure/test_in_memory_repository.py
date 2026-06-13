"""
In-Memory Repository Tests - RED Phase First (Article III)

REQ-KGC-007: Data persistence abstraction
"""

import pytest

from magatama_core.domain.entities.base import EntityType
from magatama_core.domain.entities.code_entities import ClassEntity, FunctionEntity
from magatama_core.domain.entities.relationships import Relationship, RelationshipType
from magatama_core.domain.errors import EntityAlreadyExistsError, EntityNotFoundError
from magatama_core.domain.value_objects.ids import EntityId
from magatama_core.domain.value_objects.location import Location
from magatama_core.infrastructure.storage.in_memory_repository import (
    InMemoryEntityRepository,
    InMemoryRelationshipRepository,
)


class TestInMemoryEntityRepository:
    """Test in-memory entity repository implementation."""

    @pytest.fixture
    def repo(self) -> InMemoryEntityRepository:
        """Create a fresh repository."""
        return InMemoryEntityRepository()

    @pytest.fixture
    def sample_entity(self) -> FunctionEntity:
        """Create a sample function entity."""
        return FunctionEntity(
            id=EntityId(value="func_001"),
            name="my_function",
            location=Location(file="test.py", line=10),
            parameters=[("a", "int"), ("b", "str")],
            return_type="bool",
        )

    @pytest.mark.unit
    def test_add_entity(
        self, repo: InMemoryEntityRepository, sample_entity: FunctionEntity
    ) -> None:
        """Test adding an entity."""
        repo.add(sample_entity)
        assert repo.count() == 1

    @pytest.mark.unit
    def test_get_entity(
        self, repo: InMemoryEntityRepository, sample_entity: FunctionEntity
    ) -> None:
        """Test retrieving an entity by ID."""
        repo.add(sample_entity)
        retrieved = repo.get(sample_entity.id)
        assert retrieved is not None
        assert retrieved.name == "my_function"

    @pytest.mark.unit
    def test_get_nonexistent_entity(self, repo: InMemoryEntityRepository) -> None:
        """Test getting non-existent entity returns None."""
        result = repo.get(EntityId(value="nonexistent"))
        assert result is None

    @pytest.mark.unit
    def test_add_duplicate_raises_error(
        self, repo: InMemoryEntityRepository, sample_entity: FunctionEntity
    ) -> None:
        """Test adding duplicate entity raises error."""
        repo.add(sample_entity)
        with pytest.raises(EntityAlreadyExistsError):
            repo.add(sample_entity)

    @pytest.mark.unit
    def test_get_by_type(self, repo: InMemoryEntityRepository) -> None:
        """Test filtering entities by type."""
        func = FunctionEntity(
            id=EntityId(value="func_001"),
            name="my_func",
            location=Location(file="test.py", line=10),
        )
        cls = ClassEntity(
            id=EntityId(value="cls_001"),
            name="MyClass",
            location=Location(file="test.py", line=20),
        )
        repo.add(func)
        repo.add(cls)

        functions = repo.get_by_type(EntityType.FUNCTION)
        assert len(functions) == 1
        assert functions[0].name == "my_func"

    @pytest.mark.unit
    def test_get_by_name(self, repo: InMemoryEntityRepository) -> None:
        """Test filtering entities by name."""
        func1 = FunctionEntity(
            id=EntityId(value="func_001"),
            name="calculate",
            location=Location(file="a.py", line=10),
        )
        func2 = FunctionEntity(
            id=EntityId(value="func_002"),
            name="calculate",
            location=Location(file="b.py", line=20),
        )
        repo.add(func1)
        repo.add(func2)

        results = repo.get_by_name("calculate")
        assert len(results) == 2

    @pytest.mark.unit
    def test_update_entity(
        self, repo: InMemoryEntityRepository, sample_entity: FunctionEntity
    ) -> None:
        """Test updating an existing entity."""
        repo.add(sample_entity)

        updated = FunctionEntity(
            id=sample_entity.id,
            name="updated_function",
            location=sample_entity.location,
        )
        repo.update(updated)

        retrieved = repo.get(sample_entity.id)
        assert retrieved is not None
        assert retrieved.name == "updated_function"

    @pytest.mark.unit
    def test_update_nonexistent_raises_error(
        self, repo: InMemoryEntityRepository, sample_entity: FunctionEntity
    ) -> None:
        """Test updating non-existent entity raises error."""
        with pytest.raises(EntityNotFoundError):
            repo.update(sample_entity)

    @pytest.mark.unit
    def test_delete_entity(
        self, repo: InMemoryEntityRepository, sample_entity: FunctionEntity
    ) -> None:
        """Test deleting an entity."""
        repo.add(sample_entity)
        result = repo.delete(sample_entity.id)
        assert result is True
        assert repo.count() == 0

    @pytest.mark.unit
    def test_delete_nonexistent(self, repo: InMemoryEntityRepository) -> None:
        """Test deleting non-existent entity returns False."""
        result = repo.delete(EntityId(value="nonexistent"))
        assert result is False

    @pytest.mark.unit
    def test_all_entities(self, repo: InMemoryEntityRepository) -> None:
        """Test listing all entities."""
        func1 = FunctionEntity(
            id=EntityId(value="func_001"),
            name="func1",
            location=Location(file="test.py", line=10),
        )
        func2 = FunctionEntity(
            id=EntityId(value="func_002"),
            name="func2",
            location=Location(file="test.py", line=20),
        )
        repo.add(func1)
        repo.add(func2)

        all_entities = repo.all()
        assert len(all_entities) == 2

    @pytest.mark.unit
    def test_count(self, repo: InMemoryEntityRepository) -> None:
        """Test counting entities."""
        assert repo.count() == 0

        func = FunctionEntity(
            id=EntityId(value="func_001"),
            name="func",
            location=Location(file="test.py", line=10),
        )
        repo.add(func)
        assert repo.count() == 1


class TestInMemoryRelationshipRepository:
    """Test in-memory relationship repository implementation."""

    @pytest.fixture
    def repo(self) -> InMemoryRelationshipRepository:
        """Create a fresh repository."""
        return InMemoryRelationshipRepository()

    @pytest.fixture
    def sample_relationship(self) -> Relationship:
        """Create a sample relationship."""
        return Relationship(
            source_id=EntityId(value="cls_001"),
            target_id=EntityId(value="cls_002"),
            type=RelationshipType.INHERITS,
        )

    @pytest.mark.unit
    def test_add_relationship(
        self, repo: InMemoryRelationshipRepository, sample_relationship: Relationship
    ) -> None:
        """Test adding a relationship."""
        repo.add(sample_relationship)
        all_rels = repo.all()
        assert len(all_rels) == 1

    @pytest.mark.unit
    def test_get_outgoing(self, repo: InMemoryRelationshipRepository) -> None:
        """Test getting outgoing relationships."""
        rel1 = Relationship(
            source_id=EntityId(value="a"),
            target_id=EntityId(value="b"),
            type=RelationshipType.CALLS,
        )
        rel2 = Relationship(
            source_id=EntityId(value="a"),
            target_id=EntityId(value="c"),
            type=RelationshipType.CALLS,
        )
        rel3 = Relationship(
            source_id=EntityId(value="b"),
            target_id=EntityId(value="c"),
            type=RelationshipType.CALLS,
        )
        repo.add(rel1)
        repo.add(rel2)
        repo.add(rel3)

        outgoing = repo.get_outgoing(EntityId(value="a"))
        assert len(outgoing) == 2

    @pytest.mark.unit
    def test_get_incoming(self, repo: InMemoryRelationshipRepository) -> None:
        """Test getting incoming relationships."""
        rel1 = Relationship(
            source_id=EntityId(value="a"),
            target_id=EntityId(value="c"),
            type=RelationshipType.CALLS,
        )
        rel2 = Relationship(
            source_id=EntityId(value="b"),
            target_id=EntityId(value="c"),
            type=RelationshipType.CALLS,
        )
        repo.add(rel1)
        repo.add(rel2)

        incoming = repo.get_incoming(EntityId(value="c"))
        assert len(incoming) == 2

    @pytest.mark.unit
    def test_get_by_type(self, repo: InMemoryRelationshipRepository) -> None:
        """Test filtering relationships by type."""
        rel1 = Relationship(
            source_id=EntityId(value="a"),
            target_id=EntityId(value="b"),
            type=RelationshipType.CALLS,
        )
        rel2 = Relationship(
            source_id=EntityId(value="c"),
            target_id=EntityId(value="d"),
            type=RelationshipType.INHERITS,
        )
        repo.add(rel1)
        repo.add(rel2)

        calls = repo.get_by_type(RelationshipType.CALLS)
        assert len(calls) == 1

    @pytest.mark.unit
    def test_delete_by_source(self, repo: InMemoryRelationshipRepository) -> None:
        """Test deleting relationships by source."""
        rel1 = Relationship(
            source_id=EntityId(value="a"),
            target_id=EntityId(value="b"),
            type=RelationshipType.CALLS,
        )
        rel2 = Relationship(
            source_id=EntityId(value="a"),
            target_id=EntityId(value="c"),
            type=RelationshipType.CALLS,
        )
        repo.add(rel1)
        repo.add(rel2)

        deleted = repo.delete(source_id=EntityId(value="a"))
        assert deleted == 2
        assert len(repo.all()) == 0

    @pytest.mark.unit
    def test_delete_by_type(self, repo: InMemoryRelationshipRepository) -> None:
        """Test deleting relationships by type."""
        rel1 = Relationship(
            source_id=EntityId(value="a"),
            target_id=EntityId(value="b"),
            type=RelationshipType.CALLS,
        )
        rel2 = Relationship(
            source_id=EntityId(value="c"),
            target_id=EntityId(value="d"),
            type=RelationshipType.INHERITS,
        )
        repo.add(rel1)
        repo.add(rel2)

        deleted = repo.delete(rel_type=RelationshipType.CALLS)
        assert deleted == 1
        assert len(repo.all()) == 1
