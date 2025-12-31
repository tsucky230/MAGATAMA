"""Tests for graph validation and integrity checking."""

import pytest
from pathlib import Path

from yata_core.application.services.graph_validator import (
    GraphValidator,
    ValidationResult,
    ValidationIssue,
    RepairResult,
)
from yata_core.domain.entities import Entity, EntityType, Relationship, RelationshipType
from yata_core.domain.value_objects import EntityId, Location
from yata_core.infrastructure.storage import NetworkXKnowledgeGraph


class TestGraphValidator:
    """Tests for GraphValidator."""

    @pytest.fixture
    def graph(self) -> NetworkXKnowledgeGraph:
        """Create a fresh knowledge graph."""
        return NetworkXKnowledgeGraph()

    @pytest.fixture
    def validator(self, graph: NetworkXKnowledgeGraph) -> GraphValidator:
        """Create a validator with the graph."""
        return GraphValidator(graph)

    def test_validate_empty_graph(self, validator: GraphValidator) -> None:
        """Test validating an empty graph."""
        result = validator.validate()
        
        assert result.is_valid is True
        assert result.entities_checked == 0
        assert result.relationships_checked == 0
        assert len(result.issues) == 0

    def test_validate_valid_graph(
        self, graph: NetworkXKnowledgeGraph, validator: GraphValidator
    ) -> None:
        """Test validating a valid graph with proper relationships."""
        # Create entities
        module = Entity(
            id=EntityId(value="module_1"),
            name="test_module",
            type=EntityType.MODULE,
            location=Location(file="/test.py", line=1, column=0),
        )
        func = Entity(
            id=EntityId(value="func_1"),
            name="test_func",
            type=EntityType.FUNCTION,
            location=Location(file="/test.py", line=5, column=0),
        )
        
        graph.entities.add(module)
        graph.entities.add(func)
        
        # Create relationship
        rel = Relationship(
            source_id=module.id,
            target_id=func.id,
            type=RelationshipType.CONTAINS,
        )
        graph.relationships.add(rel)
        
        result = validator.validate()
        
        assert result.is_valid is True
        assert result.entities_checked == 2
        assert result.relationships_checked == 1
        assert result.error_count == 0

    def test_validate_detects_invalid_source_reference(
        self, graph: NetworkXKnowledgeGraph, validator: GraphValidator
    ) -> None:
        """Test that validator detects relationships with invalid source."""
        # Create only target entity
        func = Entity(
            id=EntityId(value="func_1"),
            name="test_func",
            type=EntityType.FUNCTION,
            location=Location(file="/test.py", line=5, column=0),
        )
        graph.entities.add(func)
        
        # Create relationship with non-existent source
        # We need to add it directly to the graph
        rel = Relationship(
            source_id=EntityId(value="nonexistent"),
            target_id=func.id,
            type=RelationshipType.CONTAINS,
        )
        graph.relationships.add(rel)
        
        result = validator.validate()
        
        assert result.is_valid is False
        assert result.error_count >= 1
        assert any(i.issue_type == "invalid_source_reference" for i in result.issues)

    def test_validate_detects_invalid_target_reference(
        self, graph: NetworkXKnowledgeGraph, validator: GraphValidator
    ) -> None:
        """Test that validator detects relationships with invalid target."""
        # Create only source entity
        module = Entity(
            id=EntityId(value="module_1"),
            name="test_module",
            type=EntityType.MODULE,
            location=Location(file="/test.py", line=1, column=0),
        )
        graph.entities.add(module)
        
        # Create relationship with non-existent target
        rel = Relationship(
            source_id=module.id,
            target_id=EntityId(value="nonexistent"),
            type=RelationshipType.CONTAINS,
        )
        graph.relationships.add(rel)
        
        result = validator.validate()
        
        assert result.is_valid is False
        assert result.error_count >= 1
        assert any(i.issue_type == "invalid_target_reference" for i in result.issues)

    def test_validate_detects_orphaned_entities(
        self, graph: NetworkXKnowledgeGraph, validator: GraphValidator
    ) -> None:
        """Test that validator detects orphaned (non-module) entities."""
        # Create entity with no relationships
        func = Entity(
            id=EntityId(value="func_1"),
            name="orphan_func",
            type=EntityType.FUNCTION,
            location=Location(file="/test.py", line=5, column=0),
        )
        graph.entities.add(func)
        
        result = validator.validate()
        
        assert result.warning_count >= 1
        assert any(i.issue_type == "orphaned_entity" for i in result.issues)

    def test_validate_allows_orphaned_modules(
        self, graph: NetworkXKnowledgeGraph, validator: GraphValidator
    ) -> None:
        """Test that modules without relationships are OK."""
        # Create module with no relationships (this is normal)
        module = Entity(
            id=EntityId(value="module_1"),
            name="empty_module",
            type=EntityType.MODULE,
            location=Location(file="/test.py", line=1, column=0),
        )
        graph.entities.add(module)
        
        result = validator.validate()
        
        # Module orphans should not be flagged
        orphan_issues = [i for i in result.issues if i.issue_type == "orphaned_entity"]
        assert len(orphan_issues) == 0

    def test_repair_removes_invalid_relationships(
        self, graph: NetworkXKnowledgeGraph, validator: GraphValidator
    ) -> None:
        """Test that repair removes relationships with invalid references."""
        # Create one entity
        func = Entity(
            id=EntityId(value="func_1"),
            name="test_func",
            type=EntityType.FUNCTION,
            location=Location(file="/test.py", line=5, column=0),
        )
        graph.entities.add(func)
        
        # Add invalid relationship
        rel = Relationship(
            source_id=EntityId(value="nonexistent"),
            target_id=func.id,
            type=RelationshipType.CALLS,
        )
        graph.relationships.add(rel)
        
        # Verify invalid relationship exists
        before_result = validator.validate()
        assert before_result.is_valid is False
        
        # Repair
        repair_result = validator.repair(remove_invalid_refs=True)
        
        assert repair_result.success is True
        assert repair_result.invalid_relationships_removed >= 1
        
        # Verify graph is now valid
        after_result = validator.validate()
        assert after_result.error_count == 0

    def test_get_statistics(
        self, graph: NetworkXKnowledgeGraph, validator: GraphValidator
    ) -> None:
        """Test getting graph statistics."""
        # Create some entities
        module = Entity(
            id=EntityId(value="module_1"),
            name="test_module",
            type=EntityType.MODULE,
            location=Location(file="/test.py", line=1, column=0),
        )
        func1 = Entity(
            id=EntityId(value="func_1"),
            name="func1",
            type=EntityType.FUNCTION,
            location=Location(file="/test.py", line=5, column=0),
        )
        func2 = Entity(
            id=EntityId(value="func_2"),
            name="func2",
            type=EntityType.FUNCTION,
            location=Location(file="/test.py", line=10, column=0),
        )
        
        graph.entities.add(module)
        graph.entities.add(func1)
        graph.entities.add(func2)
        
        graph.relationships.add(Relationship(
            source_id=module.id,
            target_id=func1.id,
            type=RelationshipType.CONTAINS,
        ))
        graph.relationships.add(Relationship(
            source_id=func1.id,
            target_id=func2.id,
            type=RelationshipType.CALLS,
        ))
        
        stats = validator.get_statistics()
        
        assert stats["total_entities"] == 3
        assert stats["total_relationships"] == 2
        assert stats["entity_module"] == 1
        assert stats["entity_function"] == 2
        assert stats["relationship_contains"] == 1
        assert stats["relationship_calls"] == 1


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_error_count(self) -> None:
        """Test error_count property."""
        result = ValidationResult(
            is_valid=False,
            issues=[
                ValidationIssue("a", "error", "desc1"),
                ValidationIssue("b", "warning", "desc2"),
                ValidationIssue("c", "error", "desc3"),
            ],
        )
        
        assert result.error_count == 2
        assert result.warning_count == 1

    def test_valid_result(self) -> None:
        """Test creating a valid result."""
        result = ValidationResult(is_valid=True, entities_checked=10)
        
        assert result.is_valid is True
        assert result.entities_checked == 10
        assert result.error_count == 0
