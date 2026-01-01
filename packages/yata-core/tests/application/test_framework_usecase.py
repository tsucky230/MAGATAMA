"""Tests for Framework Knowledge Use Cases."""
import pytest
from pathlib import Path
import json
import tempfile

from yata_core.application.usecases.framework_usecase import (
    FrameworkKnowledgeUseCase,
    CodeContextUseCase,
    SemanticSearchUseCase,
    FrameworkInfo,
)
from yata_core.domain.entities import Entity, EntityType
from yata_core.domain.value_objects import EntityId
from yata_core.domain.value_objects.location import Location
from yata_core.infrastructure.storage import NetworkXKnowledgeGraph


class TestFrameworkKnowledgeUseCase:
    """Tests for FrameworkKnowledgeUseCase."""

    def test_list_frameworks_empty_dir(self, tmp_path: Path):
        """Test listing frameworks from empty directory."""
        usecase = FrameworkKnowledgeUseCase(tmp_path)
        frameworks = usecase.list_frameworks()
        assert frameworks == []

    def test_list_frameworks_with_summary(self, tmp_path: Path):
        """Test listing frameworks with summary.json."""
        summary = {
            "frameworks": {
                "react": {
                    "entities": 100,
                    "relationships": 200,
                    "entity_types": {"function": 50, "class": 30},
                },
                "django": {
                    "entities": 150,
                    "relationships": 300,
                    "entity_types": {"function": 80, "class": 40},
                },
            }
        }
        (tmp_path / "summary.json").write_text(json.dumps(summary))
        
        usecase = FrameworkKnowledgeUseCase(tmp_path)
        frameworks = usecase.list_frameworks()
        
        assert len(frameworks) == 2
        names = [fw.name for fw in frameworks]
        assert "react" in names
        assert "django" in names

    def test_get_framework_info(self, tmp_path: Path):
        """Test getting info for a specific framework."""
        summary = {
            "frameworks": {
                "flask": {
                    "entities": 80,
                    "relationships": 120,
                    "entity_types": {"function": 60, "class": 20},
                },
            }
        }
        (tmp_path / "summary.json").write_text(json.dumps(summary))
        
        usecase = FrameworkKnowledgeUseCase(tmp_path)
        info = usecase.get_framework_info("flask")
        
        assert info is not None
        assert info.name == "flask"
        assert info.entities_count == 80

    def test_search_framework_not_found(self, tmp_path: Path):
        """Test searching non-existent framework."""
        usecase = FrameworkKnowledgeUseCase(tmp_path)
        result = usecase.search_framework("nonexistent", "test")
        
        assert result.framework == "nonexistent"
        assert result.entities == []
        assert result.total_count == 0

    def test_search_framework_with_graph(self, tmp_path: Path):
        """Test searching framework with actual graph."""
        # Create a test graph
        graph = NetworkXKnowledgeGraph()
        entity = Entity(
            id=EntityId(value="test::TestClass"),
            name="TestClass",
            type=EntityType.CLASS,
            location=Location(file="test.py", line=1, column=0),
        )
        graph.entities.add(entity)
        
        graph_path = tmp_path / "testfw.json"
        graph.save(graph_path)
        
        usecase = FrameworkKnowledgeUseCase(tmp_path)
        result = usecase.search_framework("testfw", "Test")
        
        assert result.framework == "testfw"
        assert len(result.entities) == 1
        assert result.entities[0]["name"] == "TestClass"

    def test_find_similar_patterns(self, tmp_path: Path):
        """Test finding similar patterns."""
        # Create graphs for two frameworks
        for fw_name in ["fw1", "fw2"]:
            graph = NetworkXKnowledgeGraph()
            entity = Entity(
                id=EntityId(value=f"{fw_name}::UserController"),
                name="UserController",
                type=EntityType.CLASS,
                location=Location(file=f"{fw_name}/controller.py", line=1, column=0),
            )
            graph.entities.add(entity)
            graph.save(tmp_path / f"{fw_name}.json")
        
        usecase = FrameworkKnowledgeUseCase(tmp_path)
        # Must call list_frameworks first to scan for JSON files
        usecase.list_frameworks()
        result = usecase.find_similar_patterns("Controller")
        
        assert result.pattern_name == "Controller"
        assert len(result.examples) >= 1
        assert len(result.frameworks) >= 1


class TestCodeContextUseCase:
    """Tests for CodeContextUseCase."""

    def test_generate_context_entity_not_found(self):
        """Test generating context for non-existent entity."""
        graph = NetworkXKnowledgeGraph()
        usecase = CodeContextUseCase(graph)
        
        result = usecase.generate_context("nonexistent::entity")
        assert "error" in result

    def test_generate_context_success(self):
        """Test generating context successfully."""
        graph = NetworkXKnowledgeGraph()
        
        entity = Entity(
            id=EntityId(value="test::MyClass"),
            name="MyClass",
            type=EntityType.CLASS,
            location=Location(file="test.py", line=10, column=0),
            docstring="A test class",
        )
        graph.entities.add(entity)
        
        usecase = CodeContextUseCase(graph)
        result = usecase.generate_context("test::MyClass")
        
        assert "entity" in result
        assert result["entity"]["name"] == "MyClass"
        assert "calls" in result
        assert "called_by" in result

    def test_find_usage_examples_none(self):
        """Test finding usage when none exist."""
        graph = NetworkXKnowledgeGraph()
        usecase = CodeContextUseCase(graph)
        
        examples = usecase.find_usage_examples("NonExistent")
        assert examples == []

    def test_find_usage_examples_with_callers(self):
        """Test finding usage with callers."""
        graph = NetworkXKnowledgeGraph()
        
        # Create target entity
        target = Entity(
            id=EntityId(value="mod::target_func"),
            name="target_func",
            type=EntityType.FUNCTION,
            location=Location(file="mod.py", line=1, column=0),
        )
        graph.entities.add(target)
        
        # Create caller entity
        caller = Entity(
            id=EntityId(value="mod::caller_func"),
            name="caller_func",
            type=EntityType.FUNCTION,
            location=Location(file="mod.py", line=10, column=0),
        )
        graph.entities.add(caller)
        
        # Create relationship
        from yata_core.domain.entities import Relationship, RelationshipType
        rel = Relationship(
            source_id=caller.id,
            target_id=target.id,
            type=RelationshipType.CALLS,
        )
        graph.relationships.add(rel)
        
        usecase = CodeContextUseCase(graph)
        examples = usecase.find_usage_examples("target_func")
        
        assert len(examples) == 1
        assert examples[0]["caller"]["name"] == "caller_func"


class TestSemanticSearchUseCase:
    """Tests for SemanticSearchUseCase."""

    def test_search_empty_graph(self):
        """Test searching empty graph."""
        graph = NetworkXKnowledgeGraph()
        usecase = SemanticSearchUseCase(graph)
        
        results = usecase.search("anything")
        assert results == []

    def test_search_exact_match(self):
        """Test search with exact name match."""
        graph = NetworkXKnowledgeGraph()
        entity = Entity(
            id=EntityId(value="mod::UserService"),
            name="UserService",
            type=EntityType.CLASS,
            location=Location(file="service.py", line=1, column=0),
        )
        graph.entities.add(entity)
        
        usecase = SemanticSearchUseCase(graph)
        results = usecase.search("UserService")
        
        assert len(results) == 1
        assert results[0]["name"] == "UserService"
        assert results[0]["relevance_score"] > 5  # Exact match bonus

    def test_search_partial_match(self):
        """Test search with partial match."""
        graph = NetworkXKnowledgeGraph()
        entity = Entity(
            id=EntityId(value="mod::AuthenticationService"),
            name="AuthenticationService",
            type=EntityType.CLASS,
            location=Location(file="auth.py", line=1, column=0),
        )
        graph.entities.add(entity)
        
        usecase = SemanticSearchUseCase(graph)
        results = usecase.search("auth")
        
        assert len(results) == 1
        assert "Authentication" in results[0]["name"]

    def test_search_with_type_filter(self):
        """Test search with entity type filter."""
        graph = NetworkXKnowledgeGraph()
        
        # Add class
        class_entity = Entity(
            id=EntityId(value="mod::TestClass"),
            name="TestClass",
            type=EntityType.CLASS,
            location=Location(file="test.py", line=1, column=0),
        )
        graph.entities.add(class_entity)
        
        # Add function
        func_entity = Entity(
            id=EntityId(value="mod::test_function"),
            name="test_function",
            type=EntityType.FUNCTION,
            location=Location(file="test.py", line=10, column=0),
        )
        graph.entities.add(func_entity)
        
        usecase = SemanticSearchUseCase(graph)
        results = usecase.search("test", entity_types=[EntityType.CLASS])
        
        assert len(results) == 1
        assert results[0]["type"] == "class"

    def test_find_by_pattern_wildcard(self):
        """Test finding by pattern with wildcard."""
        graph = NetworkXKnowledgeGraph()
        
        for name in ["UserController", "AuthController", "UserService"]:
            entity = Entity(
                id=EntityId(value=f"mod::{name}"),
                name=name,
                type=EntityType.CLASS,
                location=Location(file="app.py", line=1, column=0),
            )
            graph.entities.add(entity)
        
        usecase = SemanticSearchUseCase(graph)
        results = usecase.find_by_pattern("*Controller")
        
        assert len(results) == 2
        names = [r["name"] for r in results]
        assert "UserController" in names
        assert "AuthController" in names
        assert "UserService" not in names

    def test_find_by_pattern_prefix(self):
        """Test finding by prefix pattern."""
        graph = NetworkXKnowledgeGraph()
        
        for name in ["getUser", "getData", "setUser"]:
            entity = Entity(
                id=EntityId(value=f"mod::{name}"),
                name=name,
                type=EntityType.FUNCTION,
                location=Location(file="api.py", line=1, column=0),
            )
            graph.entities.add(entity)
        
        usecase = SemanticSearchUseCase(graph)
        results = usecase.find_by_pattern("get*")
        
        assert len(results) == 2
        names = [r["name"] for r in results]
        assert "getUser" in names
        assert "getData" in names


class TestFrameworkKnowledgeUseCaseExtended:
    """Extended tests for FrameworkKnowledgeUseCase."""

    def test_load_graph_success(self, tmp_path: Path):
        """Test loading a framework graph successfully."""
        graph = NetworkXKnowledgeGraph()
        entity = Entity(
            id=EntityId(value="test::MyClass"),
            name="MyClass",
            type=EntityType.CLASS,
            location=Location(file="test.py", line=1, column=0),
        )
        graph.entities.add(entity)
        graph.save(tmp_path / "myfw.json")
        
        usecase = FrameworkKnowledgeUseCase(tmp_path)
        loaded = usecase._load_graph("myfw")
        
        assert loaded is not None

    def test_load_graph_cached(self, tmp_path: Path):
        """Test that loaded graphs are cached."""
        graph = NetworkXKnowledgeGraph()
        graph.save(tmp_path / "cached_fw.json")
        
        usecase = FrameworkKnowledgeUseCase(tmp_path)
        
        # Load twice
        first_load = usecase._load_graph("cached_fw")
        second_load = usecase._load_graph("cached_fw")
        
        # Should be the same object
        assert first_load is second_load

    def test_list_frameworks_with_json_files(self, tmp_path: Path):
        """Test listing frameworks by scanning JSON files."""
        # Create some framework JSON files
        for fw_name in ["react", "vue", "angular"]:
            graph = NetworkXKnowledgeGraph()
            graph.save(tmp_path / f"{fw_name}.json")
        
        usecase = FrameworkKnowledgeUseCase(tmp_path)
        frameworks = usecase.list_frameworks()
        
        assert len(frameworks) >= 3

    def test_get_framework_info_not_found(self, tmp_path: Path):
        """Test getting info for non-existent framework."""
        usecase = FrameworkKnowledgeUseCase(tmp_path)
        info = usecase.get_framework_info("nonexistent")
        
        assert info is None


class TestCodeContextUseCaseExtended:
    """Extended tests for CodeContextUseCase."""

    def test_generate_context_with_relationships(self):
        """Test generating context with relationships."""
        graph = NetworkXKnowledgeGraph()
        
        # Create entities
        parent = Entity(
            id=EntityId(value="test::ParentClass"),
            name="ParentClass",
            type=EntityType.CLASS,
            location=Location(file="test.py", line=1, column=0),
        )
        child = Entity(
            id=EntityId(value="test::ChildClass"),
            name="ChildClass",
            type=EntityType.CLASS,
            location=Location(file="test.py", line=10, column=0),
        )
        graph.entities.add(parent)
        graph.entities.add(child)
        
        # Create relationship
        from yata_core.domain.entities import Relationship, RelationshipType
        rel = Relationship(
            source_id=child.id,
            target_id=parent.id,
            type=RelationshipType.INHERITS,
        )
        graph.relationships.add(rel)
        
        usecase = CodeContextUseCase(graph)
        result = usecase.generate_context("test::ChildClass")
        
        assert "entity" in result

    def test_find_dependent_entities(self):
        """Test finding entities that depend on a target."""
        graph = NetworkXKnowledgeGraph()
        
        target = Entity(
            id=EntityId(value="mod::base_func"),
            name="base_func",
            type=EntityType.FUNCTION,
            location=Location(file="mod.py", line=1, column=0),
        )
        dependent = Entity(
            id=EntityId(value="mod::derived_func"),
            name="derived_func",
            type=EntityType.FUNCTION,
            location=Location(file="mod.py", line=20, column=0),
        )
        graph.entities.add(target)
        graph.entities.add(dependent)
        
        from yata_core.domain.entities import Relationship, RelationshipType
        rel = Relationship(
            source_id=dependent.id,
            target_id=target.id,
            type=RelationshipType.CALLS,
        )
        graph.relationships.add(rel)
        
        usecase = CodeContextUseCase(graph)
        # Finding usage examples should find the dependent
        examples = usecase.find_usage_examples("base_func")
        
        assert len(examples) >= 1


class TestSemanticSearchUseCaseExtended:
    """Extended tests for SemanticSearchUseCase."""

    def test_search_by_docstring(self):
        """Test search matching docstring."""
        graph = NetworkXKnowledgeGraph()
        entity = Entity(
            id=EntityId(value="mod::calculate"),
            name="calculate",
            type=EntityType.FUNCTION,
            location=Location(file="math.py", line=1, column=0),
            docstring="Calculate the sum of two numbers",
        )
        graph.entities.add(entity)
        
        usecase = SemanticSearchUseCase(graph)
        results = usecase.search("sum numbers")
        
        assert len(results) >= 1

    def test_search_with_limit(self):
        """Test search with result limit."""
        graph = NetworkXKnowledgeGraph()
        
        # Add many entities
        for i in range(20):
            entity = Entity(
                id=EntityId(value=f"mod::item_{i}"),
                name=f"item_{i}",
                type=EntityType.FUNCTION,
                location=Location(file="items.py", line=i + 1, column=0),
            )
            graph.entities.add(entity)
        
        usecase = SemanticSearchUseCase(graph)
        results = usecase.search("item", limit=5)
        
        assert len(results) <= 5

    def test_find_by_pattern_exact(self):
        """Test finding by exact pattern without wildcards."""
        graph = NetworkXKnowledgeGraph()
        entity = Entity(
            id=EntityId(value="mod::ExactMatch"),
            name="ExactMatch",
            type=EntityType.CLASS,
            location=Location(file="exact.py", line=1, column=0),
        )
        graph.entities.add(entity)
        
        usecase = SemanticSearchUseCase(graph)
        results = usecase.find_by_pattern("ExactMatch")
        
        assert len(results) == 1
        assert results[0]["name"] == "ExactMatch"
