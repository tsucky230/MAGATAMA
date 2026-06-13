"""
SQLite Storage Tests

TASK-015: SQLite storage implementation tests.
Tests for SQLiteKnowledgeGraph and related repositories.
"""

import json
import tempfile
from pathlib import Path

from magatama_core.domain.entities.base import EntityType
from magatama_core.domain.entities.code_entities import (
    ClassEntity,
    EnumEntity,
    FunctionEntity,
    InterfaceEntity,
    MethodEntity,
    ModuleEntity,
    TypeEntity,
)
from magatama_core.domain.entities.relationships import Relationship, RelationshipType
from magatama_core.domain.value_objects.ids import EntityId
from magatama_core.domain.value_objects.location import Location
from magatama_core.infrastructure.storage.sqlite_storage import (
    SQLiteKnowledgeGraph,
)


class TestSQLiteKnowledgeGraph:
    """Tests for SQLiteKnowledgeGraph."""

    def test_initialization_in_memory(self):
        """Test in-memory database initialization."""
        graph = SQLiteKnowledgeGraph(":memory:")
        assert graph._conn is not None
        stats = graph.get_stats()
        assert stats["total_entities"] == 0
        assert stats["total_relationships"] == 0
        graph.close()

    def test_initialization_with_file(self):
        """Test file-based database initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            graph = SQLiteKnowledgeGraph(db_path)
            assert db_path.exists()
            graph.close()

    def test_add_and_get_entity(self):
        """Test adding and retrieving entities."""
        with SQLiteKnowledgeGraph(":memory:") as graph:
            entity = FunctionEntity(
                id=EntityId(value="func_001"),
                name="test_function",
                location=Location(file="test.py", line=10),
                parameters=[("x", "int"), ("y", "str")],
                return_type="bool",
                is_async=False,
            )

            graph.entities.add(entity)

            retrieved = graph.entities.get(EntityId(value="func_001"))
            assert retrieved is not None
            assert retrieved.name == "test_function"
            assert retrieved.type == EntityType.FUNCTION

    def test_add_class_entity(self):
        """Test adding ClassEntity."""
        with SQLiteKnowledgeGraph(":memory:") as graph:
            entity = ClassEntity(
                id=EntityId(value="class_001"),
                name="TestClass",
                location=Location(file="test.py", line=1),
                bases=["BaseClass"],
                decorators=["@dataclass"],
            )

            graph.entities.add(entity)

            retrieved = graph.entities.get(EntityId(value="class_001"))
            assert retrieved is not None
            assert retrieved.name == "TestClass"
            assert isinstance(retrieved, ClassEntity)
            assert retrieved.bases == ["BaseClass"]

    def test_add_method_entity(self):
        """Test adding MethodEntity."""
        with SQLiteKnowledgeGraph(":memory:") as graph:
            entity = MethodEntity(
                id=EntityId(value="method_001"),
                name="test_method",
                location=Location(file="test.py", line=5),
                class_id=EntityId(value="class_001"),
                parameters=[("self", None)],
                is_async=True,
            )

            graph.entities.add(entity)

            retrieved = graph.entities.get(EntityId(value="method_001"))
            assert retrieved is not None
            assert isinstance(retrieved, MethodEntity)
            assert retrieved.class_id.value == "class_001"
            assert retrieved.is_async is True

    def test_add_module_entity(self):
        """Test adding ModuleEntity."""
        with SQLiteKnowledgeGraph(":memory:") as graph:
            entity = ModuleEntity(
                id=EntityId(value="module_001"),
                name="test_module",
                location=Location(file="test.py", line=1),
                exports=["func1", "Class1"],
            )

            graph.entities.add(entity)

            retrieved = graph.entities.get(EntityId(value="module_001"))
            assert retrieved is not None
            assert isinstance(retrieved, ModuleEntity)
            assert retrieved.exports == ["func1", "Class1"]

    def test_add_interface_entity(self):
        """Test adding InterfaceEntity."""
        with SQLiteKnowledgeGraph(":memory:") as graph:
            entity = InterfaceEntity(
                id=EntityId(value="interface_001"),
                name="ITestInterface",
                location=Location(file="test.ts", line=1),
                method_signatures=["method1(): void", "method2(x: number): string"],
                extends=["IBase"],
            )

            graph.entities.add(entity)

            retrieved = graph.entities.get(EntityId(value="interface_001"))
            assert retrieved is not None
            assert isinstance(retrieved, InterfaceEntity)
            assert len(retrieved.method_signatures) == 2

    def test_add_type_entity(self):
        """Test adding TypeEntity."""
        with SQLiteKnowledgeGraph(":memory:") as graph:
            entity = TypeEntity(
                id=EntityId(value="type_001"),
                name="MyType",
                location=Location(file="test.ts", line=1),
                definition="string | number",
            )

            graph.entities.add(entity)

            retrieved = graph.entities.get(EntityId(value="type_001"))
            assert retrieved is not None
            assert isinstance(retrieved, TypeEntity)
            assert retrieved.definition == "string | number"

    def test_add_enum_entity(self):
        """Test adding EnumEntity."""
        with SQLiteKnowledgeGraph(":memory:") as graph:
            entity = EnumEntity(
                id=EntityId(value="enum_001"),
                name="Status",
                location=Location(file="test.py", line=1),
                variants=["ACTIVE", "INACTIVE", "PENDING"],
            )

            graph.entities.add(entity)

            retrieved = graph.entities.get(EntityId(value="enum_001"))
            assert retrieved is not None
            assert isinstance(retrieved, EnumEntity)
            assert "ACTIVE" in retrieved.variants

    def test_add_relationship(self):
        """Test adding relationships."""
        with SQLiteKnowledgeGraph(":memory:") as graph:
            # Add entities first
            entity1 = FunctionEntity(
                id=EntityId(value="func_001"),
                name="caller",
                location=Location(file="test.py", line=1),
            )
            entity2 = FunctionEntity(
                id=EntityId(value="func_002"),
                name="callee",
                location=Location(file="test.py", line=10),
            )

            graph.entities.add(entity1)
            graph.entities.add(entity2)

            # Add relationship
            rel = Relationship(
                source_id=EntityId(value="func_001"),
                target_id=EntityId(value="func_002"),
                type=RelationshipType.CALLS,
            )

            graph.relationships.add(rel)

            # Verify
            outgoing = graph.relationships.get_outgoing(EntityId(value="func_001"))
            assert len(outgoing) == 1
            assert outgoing[0].target_id.value == "func_002"

    def test_get_neighbors(self):
        """Test getting neighboring entities."""
        with SQLiteKnowledgeGraph(":memory:") as graph:
            # Create connected entities
            for i in range(5):
                entity = FunctionEntity(
                    id=EntityId(value=f"func_{i}"),
                    name=f"func_{i}",
                    location=Location(file="test.py", line=i * 10 + 1),
                )
                graph.entities.add(entity)

            # Create chain: func_0 -> func_1 -> func_2 -> func_3 -> func_4
            for i in range(4):
                rel = Relationship(
                    source_id=EntityId(value=f"func_{i}"),
                    target_id=EntityId(value=f"func_{i + 1}"),
                    type=RelationshipType.CALLS,
                )
                graph.relationships.add(rel)

            # Get depth-1 neighbors of func_2
            neighbors = graph.get_neighbors(EntityId(value="func_2"), depth=1)
            neighbor_names = {e.name for e in neighbors}
            assert "func_1" in neighbor_names
            assert "func_3" in neighbor_names
            assert len(neighbors) == 2

    def test_find_path(self):
        """Test path finding between entities."""
        with SQLiteKnowledgeGraph(":memory:") as graph:
            # Create entities
            for i in range(3):
                entity = FunctionEntity(
                    id=EntityId(value=f"func_{i}"),
                    name=f"func_{i}",
                    location=Location(file="test.py", line=i * 10 + 1),
                )
                graph.entities.add(entity)

            # Create path: func_0 -> func_1 -> func_2
            for i in range(2):
                rel = Relationship(
                    source_id=EntityId(value=f"func_{i}"),
                    target_id=EntityId(value=f"func_{i + 1}"),
                    type=RelationshipType.CALLS,
                )
                graph.relationships.add(rel)

            # Find path
            path = graph.find_path(
                EntityId(value="func_0"),
                EntityId(value="func_2"),
            )

            assert path is not None
            assert len(path) == 3
            assert path[0].value == "func_0"
            assert path[2].value == "func_2"

    def test_file_hash_operations(self):
        """Test file hash storage and retrieval."""
        with SQLiteKnowledgeGraph(":memory:") as graph:
            # Set hash
            graph.set_file_hash("test.py", "abc123")

            # Get hash
            hash_value = graph.get_file_hash("test.py")
            assert hash_value == "abc123"

            # Update hash
            graph.set_file_hash("test.py", "def456")
            hash_value = graph.get_file_hash("test.py")
            assert hash_value == "def456"

            # Get tracked files
            files = graph.get_tracked_files()
            assert "test.py" in files

    def test_remove_file(self):
        """Test removing all entities from a file."""
        with SQLiteKnowledgeGraph(":memory:") as graph:
            # Add entities from different files
            entity1 = FunctionEntity(
                id=EntityId(value="func_001"),
                name="func1",
                location=Location(file="file1.py", line=1),
            )
            entity2 = FunctionEntity(
                id=EntityId(value="func_002"),
                name="func2",
                location=Location(file="file1.py", line=10),
            )
            entity3 = FunctionEntity(
                id=EntityId(value="func_003"),
                name="func3",
                location=Location(file="file2.py", line=1),
            )

            graph.entities.add(entity1)
            graph.entities.add(entity2)
            graph.entities.add(entity3)
            graph.set_file_hash("file1.py", "hash1")
            graph.set_file_hash("file2.py", "hash2")

            # Remove file1.py
            removed = graph.remove_file("file1.py")
            assert removed == 2

            # Verify
            assert graph.entities.get(EntityId(value="func_001")) is None
            assert graph.entities.get(EntityId(value="func_002")) is None
            assert graph.entities.get(EntityId(value="func_003")) is not None
            assert graph.get_file_hash("file1.py") is None
            assert graph.get_file_hash("file2.py") == "hash2"

    def test_save_and_load_json(self):
        """Test JSON export and import."""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "graph.json"

            # Create and populate graph
            with SQLiteKnowledgeGraph(":memory:") as graph:
                entity = FunctionEntity(
                    id=EntityId(value="func_001"),
                    name="test_func",
                    location=Location(file="test.py", line=1),
                    parameters=[("x", "int")],
                    return_type="str",
                )
                graph.entities.add(entity)
                graph.set_file_hash("test.py", "hash123")

                # Save
                graph.save(json_path)

            # Verify JSON file
            assert json_path.exists()
            data = json.loads(json_path.read_text())
            assert len(data["entities"]) == 1
            assert data["entities"][0]["name"] == "test_func"

            # Load into new graph
            with SQLiteKnowledgeGraph(":memory:") as graph2:
                graph2.load(json_path)

                # Verify loaded data
                loaded_entity = graph2.entities.get(EntityId(value="func_001"))
                assert loaded_entity is not None
                assert loaded_entity.name == "test_func"
                assert graph2.get_file_hash("test.py") == "hash123"

    def test_clear(self):
        """Test clearing all data."""
        with SQLiteKnowledgeGraph(":memory:") as graph:
            # Add data
            entity = FunctionEntity(
                id=EntityId(value="func_001"),
                name="test_func",
                location=Location(file="test.py", line=1),
            )
            graph.entities.add(entity)
            graph.set_file_hash("test.py", "hash123")

            # Clear
            graph.clear()

            # Verify
            assert graph.entities.count() == 0
            assert len(graph.get_tracked_files()) == 0

    def test_get_stats(self):
        """Test getting graph statistics."""
        with SQLiteKnowledgeGraph(":memory:") as graph:
            # Add various entities
            func = FunctionEntity(
                id=EntityId(value="func_001"),
                name="func1",
                location=Location(file="test.py", line=1),
            )
            cls = ClassEntity(
                id=EntityId(value="class_001"),
                name="Class1",
                location=Location(file="test.py", line=10),
            )

            graph.entities.add(func)
            graph.entities.add(cls)
            graph.set_file_hash("test.py", "hash")

            # Get stats
            stats = graph.get_stats()
            assert stats["total_entities"] == 2
            assert stats["tracked_files"] == 1
            assert "function" in stats["entity_types"]
            assert "class" in stats["entity_types"]

    def test_get_subgraph(self):
        """Test extracting subgraph."""
        with SQLiteKnowledgeGraph(":memory:") as graph:
            # Add entities
            for i in range(4):
                entity = FunctionEntity(
                    id=EntityId(value=f"func_{i}"),
                    name=f"func_{i}",
                    location=Location(file="test.py", line=i * 10 + 1),
                )
                graph.entities.add(entity)

            # Add relationships
            graph.relationships.add(
                Relationship(
                    source_id=EntityId(value="func_0"),
                    target_id=EntityId(value="func_1"),
                    type=RelationshipType.CALLS,
                )
            )
            graph.relationships.add(
                Relationship(
                    source_id=EntityId(value="func_2"),
                    target_id=EntityId(value="func_3"),
                    type=RelationshipType.CALLS,
                )
            )

            # Get subgraph with func_0 and func_1
            entities, relationships = graph.get_subgraph(
                [
                    EntityId(value="func_0"),
                    EntityId(value="func_1"),
                ]
            )

            assert len(entities) == 2
            assert len(relationships) == 1

    def test_persistence_across_sessions(self):
        """Test data persists across database sessions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            # Session 1: Add data
            with SQLiteKnowledgeGraph(db_path) as graph:
                entity = FunctionEntity(
                    id=EntityId(value="func_001"),
                    name="test_func",
                    location=Location(file="test.py", line=1),
                )
                graph.entities.add(entity)
                graph.set_file_hash("test.py", "hash123")

            # Session 2: Verify data persisted
            with SQLiteKnowledgeGraph(db_path) as graph:
                loaded = graph.entities.get(EntityId(value="func_001"))
                assert loaded is not None
                assert loaded.name == "test_func"
                assert graph.get_file_hash("test.py") == "hash123"

    def test_transaction_rollback(self):
        """Test transaction rollback on error."""
        with SQLiteKnowledgeGraph(":memory:") as graph:
            entity = FunctionEntity(
                id=EntityId(value="func_001"),
                name="test_func",
                location=Location(file="test.py", line=1),
            )
            graph.entities.add(entity)

            # Try to add duplicate (should fail)
            try:
                with graph.transaction():
                    # This should cause integrity error
                    graph._entity_repo.add(entity)
            except Exception:
                pass

            # Original entity should still exist
            assert graph.entities.get(EntityId(value="func_001")) is not None


class TestSQLiteEntityRepository:
    """Tests for SQLiteEntityRepository."""

    def test_get_by_type(self):
        """Test filtering entities by type."""
        with SQLiteKnowledgeGraph(":memory:") as graph:
            # Add different types
            func = FunctionEntity(
                id=EntityId(value="func_001"),
                name="func1",
                location=Location(file="test.py", line=1),
            )
            cls = ClassEntity(
                id=EntityId(value="class_001"),
                name="Class1",
                location=Location(file="test.py", line=10),
            )

            graph.entities.add(func)
            graph.entities.add(cls)

            # Get by type
            functions = graph.entities.get_by_type(EntityType.FUNCTION)
            assert len(functions) == 1
            assert functions[0].name == "func1"

            classes = graph.entities.get_by_type(EntityType.CLASS)
            assert len(classes) == 1
            assert classes[0].name == "Class1"

    def test_get_by_name(self):
        """Test filtering entities by name."""
        with SQLiteKnowledgeGraph(":memory:") as graph:
            entity1 = FunctionEntity(
                id=EntityId(value="func_001"),
                name="common_name",
                location=Location(file="test1.py", line=1),
            )
            entity2 = FunctionEntity(
                id=EntityId(value="func_002"),
                name="common_name",
                location=Location(file="test2.py", line=1),
            )

            graph.entities.add(entity1)
            graph.entities.add(entity2)

            # Get by name
            results = graph.entities.get_by_name("common_name")
            assert len(results) == 2

    def test_update_entity(self):
        """Test updating an entity."""
        with SQLiteKnowledgeGraph(":memory:") as graph:
            entity = FunctionEntity(
                id=EntityId(value="func_001"),
                name="original_name",
                location=Location(file="test.py", line=1),
            )
            graph.entities.add(entity)

            # Update
            updated = FunctionEntity(
                id=EntityId(value="func_001"),
                name="updated_name",
                location=Location(file="test.py", line=1),
                docstring="Updated docstring",
            )
            graph.entities.update(updated)

            # Verify
            result = graph.entities.get(EntityId(value="func_001"))
            assert result.name == "updated_name"
            assert result.docstring == "Updated docstring"

    def test_delete_entity(self):
        """Test deleting an entity."""
        with SQLiteKnowledgeGraph(":memory:") as graph:
            entity = FunctionEntity(
                id=EntityId(value="func_001"),
                name="test_func",
                location=Location(file="test.py", line=1),
            )
            graph.entities.add(entity)

            # Delete
            result = graph.entities.delete(EntityId(value="func_001"))
            assert result is True

            # Verify
            assert graph.entities.get(EntityId(value="func_001")) is None

    def test_count_and_all(self):
        """Test count and all methods."""
        with SQLiteKnowledgeGraph(":memory:") as graph:
            for i in range(5):
                entity = FunctionEntity(
                    id=EntityId(value=f"func_{i}"),
                    name=f"func_{i}",
                    location=Location(file="test.py", line=i * 10 + 1),
                )
                graph.entities.add(entity)

            assert graph.entities.count() == 5
            assert len(graph.entities.all()) == 5


class TestSQLiteRelationshipRepository:
    """Tests for SQLiteRelationshipRepository."""

    def test_get_outgoing_relationships(self):
        """Test getting outgoing relationships."""
        with SQLiteKnowledgeGraph(":memory:") as graph:
            # Add entities
            for i in range(3):
                entity = FunctionEntity(
                    id=EntityId(value=f"func_{i}"),
                    name=f"func_{i}",
                    location=Location(file="test.py", line=i * 10 + 1),
                )
                graph.entities.add(entity)

            # Add relationships: func_0 -> func_1, func_0 -> func_2
            graph.relationships.add(
                Relationship(
                    source_id=EntityId(value="func_0"),
                    target_id=EntityId(value="func_1"),
                    type=RelationshipType.CALLS,
                )
            )
            graph.relationships.add(
                Relationship(
                    source_id=EntityId(value="func_0"),
                    target_id=EntityId(value="func_2"),
                    type=RelationshipType.CALLS,
                )
            )

            # Get outgoing
            outgoing = graph.relationships.get_outgoing(EntityId(value="func_0"))
            assert len(outgoing) == 2

    def test_get_incoming_relationships(self):
        """Test getting incoming relationships."""
        with SQLiteKnowledgeGraph(":memory:") as graph:
            # Add entities
            for i in range(3):
                entity = FunctionEntity(
                    id=EntityId(value=f"func_{i}"),
                    name=f"func_{i}",
                    location=Location(file="test.py", line=i * 10 + 1),
                )
                graph.entities.add(entity)

            # Add relationships: func_0 -> func_2, func_1 -> func_2
            graph.relationships.add(
                Relationship(
                    source_id=EntityId(value="func_0"),
                    target_id=EntityId(value="func_2"),
                    type=RelationshipType.CALLS,
                )
            )
            graph.relationships.add(
                Relationship(
                    source_id=EntityId(value="func_1"),
                    target_id=EntityId(value="func_2"),
                    type=RelationshipType.CALLS,
                )
            )

            # Get incoming
            incoming = graph.relationships.get_incoming(EntityId(value="func_2"))
            assert len(incoming) == 2

    def test_get_by_relationship_type(self):
        """Test filtering relationships by type."""
        with SQLiteKnowledgeGraph(":memory:") as graph:
            # Add entities
            for i in range(3):
                entity = FunctionEntity(
                    id=EntityId(value=f"func_{i}"),
                    name=f"func_{i}",
                    location=Location(file="test.py", line=i * 10 + 1),
                )
                graph.entities.add(entity)

            # Add different relationship types
            graph.relationships.add(
                Relationship(
                    source_id=EntityId(value="func_0"),
                    target_id=EntityId(value="func_1"),
                    type=RelationshipType.CALLS,
                )
            )
            graph.relationships.add(
                Relationship(
                    source_id=EntityId(value="func_0"),
                    target_id=EntityId(value="func_2"),
                    type=RelationshipType.IMPORTS,
                )
            )

            # Get by type
            calls = graph.relationships.get_by_type(RelationshipType.CALLS)
            assert len(calls) == 1

            imports = graph.relationships.get_by_type(RelationshipType.IMPORTS)
            assert len(imports) == 1

    def test_delete_relationships(self):
        """Test deleting relationships."""
        with SQLiteKnowledgeGraph(":memory:") as graph:
            # Add entities
            for i in range(3):
                entity = FunctionEntity(
                    id=EntityId(value=f"func_{i}"),
                    name=f"func_{i}",
                    location=Location(file="test.py", line=i * 10 + 1),
                )
                graph.entities.add(entity)

            # Add relationships
            graph.relationships.add(
                Relationship(
                    source_id=EntityId(value="func_0"),
                    target_id=EntityId(value="func_1"),
                    type=RelationshipType.CALLS,
                )
            )
            graph.relationships.add(
                Relationship(
                    source_id=EntityId(value="func_0"),
                    target_id=EntityId(value="func_2"),
                    type=RelationshipType.CALLS,
                )
            )

            # Delete by source
            deleted = graph.relationships.delete(source_id=EntityId(value="func_0"))
            assert deleted == 2
            assert len(graph.relationships.all()) == 0
