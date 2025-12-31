"""
Entity Tests - RED Phase First (Article III)

REQ-KGC-001: Entity extraction
REQ-KGC-002: Relationship extraction
"""

import pytest

from yata_core.domain.entities.base import Entity, EntityType
from yata_core.domain.entities.code_entities import (
    ClassEntity,
    FunctionEntity,
    ModuleEntity,
    MethodEntity,
    TypeEntity,
)
from yata_core.domain.entities.relationships import Relationship, RelationshipType
from yata_core.domain.value_objects.location import Location
from yata_core.domain.value_objects.ids import EntityId


class TestEntityType:
    """Test EntityType enumeration."""

    @pytest.mark.unit
    def test_entity_types_exist(self) -> None:
        """Test all required entity types exist."""
        assert EntityType.MODULE
        assert EntityType.CLASS
        assert EntityType.FUNCTION
        assert EntityType.METHOD
        assert EntityType.TYPE
        assert EntityType.VARIABLE


class TestEntity:
    """Test base Entity class."""

    @pytest.mark.unit
    def test_entity_creation(self) -> None:
        """Test creating a basic entity."""
        loc = Location(file="main.py", line=10)
        entity = Entity(
            id=EntityId(value="ent_001"),
            name="MyClass",
            type=EntityType.CLASS,
            location=loc,
        )
        assert entity.name == "MyClass"
        assert entity.type == EntityType.CLASS
        assert entity.location == loc

    @pytest.mark.unit
    def test_entity_with_docstring(self) -> None:
        """Test entity with docstring."""
        entity = Entity(
            id=EntityId(value="ent_001"),
            name="my_func",
            type=EntityType.FUNCTION,
            location=Location(file="main.py", line=10),
            docstring="This is a function.",
        )
        assert entity.docstring == "This is a function."

    @pytest.mark.unit
    def test_entity_equality(self) -> None:
        """Test entity equality based on ID."""
        e1 = Entity(
            id=EntityId(value="ent_001"),
            name="MyClass",
            type=EntityType.CLASS,
            location=Location(file="main.py", line=10),
        )
        e2 = Entity(
            id=EntityId(value="ent_001"),
            name="MyClass",
            type=EntityType.CLASS,
            location=Location(file="main.py", line=10),
        )
        assert e1 == e2


class TestFunctionEntity:
    """Test FunctionEntity."""

    @pytest.mark.unit
    def test_function_entity_creation(self) -> None:
        """Test creating a function entity."""
        func = FunctionEntity(
            id=EntityId(value="func_001"),
            name="calculate",
            location=Location(file="main.py", line=10),
            parameters=[("a", "int"), ("b", "int")],
            return_type="int",
        )
        assert func.name == "calculate"
        assert func.type == EntityType.FUNCTION
        assert func.parameters == [("a", "int"), ("b", "int")]
        assert func.return_type == "int"

    @pytest.mark.unit
    def test_function_signature(self) -> None:
        """Test function signature generation."""
        func = FunctionEntity(
            id=EntityId(value="func_001"),
            name="calculate",
            location=Location(file="main.py", line=10),
            parameters=[("a", "int"), ("b", "int")],
            return_type="int",
        )
        assert func.signature == "calculate(a: int, b: int) -> int"

    @pytest.mark.unit
    def test_function_with_decorators(self) -> None:
        """Test function with decorators."""
        func = FunctionEntity(
            id=EntityId(value="func_001"),
            name="my_func",
            location=Location(file="main.py", line=10),
            decorators=["staticmethod", "cache"],
        )
        assert func.decorators == ["staticmethod", "cache"]


class TestClassEntity:
    """Test ClassEntity."""

    @pytest.mark.unit
    def test_class_entity_creation(self) -> None:
        """Test creating a class entity."""
        cls = ClassEntity(
            id=EntityId(value="cls_001"),
            name="Calculator",
            location=Location(file="main.py", line=5),
            bases=["BaseClass"],
        )
        assert cls.name == "Calculator"
        assert cls.type == EntityType.CLASS
        assert cls.bases == ["BaseClass"]

    @pytest.mark.unit
    def test_class_with_methods(self) -> None:
        """Test class with method IDs."""
        cls = ClassEntity(
            id=EntityId(value="cls_001"),
            name="Calculator",
            location=Location(file="main.py", line=5),
            method_ids=[EntityId(value="method_001"), EntityId(value="method_002")],
        )
        assert len(cls.method_ids) == 2


class TestMethodEntity:
    """Test MethodEntity."""

    @pytest.mark.unit
    def test_method_entity_creation(self) -> None:
        """Test creating a method entity."""
        method = MethodEntity(
            id=EntityId(value="method_001"),
            name="add",
            location=Location(file="main.py", line=10),
            class_id=EntityId(value="cls_001"),
            parameters=[("self", None), ("a", "int"), ("b", "int")],
            return_type="int",
        )
        assert method.name == "add"
        assert method.type == EntityType.METHOD
        assert method.class_id.value == "cls_001"


class TestModuleEntity:
    """Test ModuleEntity."""

    @pytest.mark.unit
    def test_module_entity_creation(self) -> None:
        """Test creating a module entity."""
        mod = ModuleEntity(
            id=EntityId(value="mod_001"),
            name="calculator",
            location=Location(file="calculator/__init__.py", line=1),
            exports=["Calculator", "add", "subtract"],
        )
        assert mod.name == "calculator"
        assert mod.type == EntityType.MODULE
        assert "Calculator" in mod.exports


class TestTypeEntity:
    """Test TypeEntity."""

    @pytest.mark.unit
    def test_type_entity_creation(self) -> None:
        """Test creating a type entity."""
        type_ent = TypeEntity(
            id=EntityId(value="type_001"),
            name="UserId",
            location=Location(file="types.py", line=5),
            definition="NewType('UserId', int)",
        )
        assert type_ent.name == "UserId"
        assert type_ent.type == EntityType.TYPE


class TestRelationshipType:
    """Test RelationshipType enumeration."""

    @pytest.mark.unit
    def test_relationship_types_exist(self) -> None:
        """Test all required relationship types exist."""
        assert RelationshipType.INHERITS
        assert RelationshipType.IMPLEMENTS
        assert RelationshipType.CALLS
        assert RelationshipType.IMPORTS
        assert RelationshipType.USES_TYPE
        assert RelationshipType.CONTAINS


class TestRelationship:
    """Test Relationship class."""

    @pytest.mark.unit
    def test_relationship_creation(self) -> None:
        """Test creating a relationship."""
        rel = Relationship(
            source_id=EntityId(value="cls_001"),
            target_id=EntityId(value="cls_002"),
            type=RelationshipType.INHERITS,
        )
        assert rel.source_id.value == "cls_001"
        assert rel.target_id.value == "cls_002"
        assert rel.type == RelationshipType.INHERITS

    @pytest.mark.unit
    def test_relationship_with_metadata(self) -> None:
        """Test relationship with additional metadata."""
        rel = Relationship(
            source_id=EntityId(value="func_001"),
            target_id=EntityId(value="func_002"),
            type=RelationshipType.CALLS,
            metadata={"line": 42, "count": 3},
        )
        assert rel.metadata["line"] == 42
        assert rel.metadata["count"] == 3

    @pytest.mark.unit
    def test_relationship_equality(self) -> None:
        """Test relationship equality."""
        r1 = Relationship(
            source_id=EntityId(value="cls_001"),
            target_id=EntityId(value="cls_002"),
            type=RelationshipType.INHERITS,
        )
        r2 = Relationship(
            source_id=EntityId(value="cls_001"),
            target_id=EntityId(value="cls_002"),
            type=RelationshipType.INHERITS,
        )
        assert r1 == r2
