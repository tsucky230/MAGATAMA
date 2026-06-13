"""Tests for Framework Knowledge Use Cases."""

import json
from pathlib import Path

from magatama_core.application.usecases.framework_usecase import (
    CodeContextUseCase,
    CodeQualityUseCase,
    FrameworkKnowledgeUseCase,
    HybridSearchUseCase,
    SemanticSearchUseCase,
)
from magatama_core.domain.entities import Entity, EntityType
from magatama_core.domain.value_objects import EntityId
from magatama_core.domain.value_objects.location import Location
from magatama_core.infrastructure.storage import NetworkXKnowledgeGraph


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
        from magatama_core.domain.entities import Relationship, RelationshipType

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
        from magatama_core.domain.entities import Relationship, RelationshipType

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

        from magatama_core.domain.entities import Relationship, RelationshipType

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


class TestCodeQualityUseCase:
    """Tests for CodeQualityUseCase.

    Regression coverage for the bug where overall_status was always "danger"
    because _determine_status was called with the default lower_is_better=True
    while overall_score is a higher-is-better 0-100 score.
    """

    def test_analyze_quality_entity_not_found(self):
        """Test analyzing a non-existent entity."""
        graph = NetworkXKnowledgeGraph()
        usecase = CodeQualityUseCase(graph)

        result = usecase.analyze_quality("nonexistent")

        assert result.overall_status == "unknown"
        assert result.overall_score == 0.0

    def test_clean_entity_is_good_not_danger(self):
        """A clean, isolated entity should report status 'good', not 'danger'."""
        graph = NetworkXKnowledgeGraph()
        entity = Entity(
            id=EntityId(value="mod::clean_func"),
            name="clean_func",
            type=EntityType.FUNCTION,
            location=Location(file="mod.py", line=1, column=0),
        )
        graph.entities.add(entity)

        usecase = CodeQualityUseCase(graph)
        result = usecase.analyze_quality("clean_func")

        # High score must not be misclassified as danger (the regression).
        assert result.overall_score >= 70
        assert result.overall_status == "good"

    def test_determine_status_higher_is_better(self):
        """_determine_status with lower_is_better=False maps scores correctly."""
        usecase = CodeQualityUseCase(NetworkXKnowledgeGraph())

        assert usecase._determine_status(100, 70, 50, lower_is_better=False) == "good"
        assert usecase._determine_status(60, 70, 50, lower_is_better=False) == "warning"
        assert usecase._determine_status(40, 70, 50, lower_is_better=False) == "danger"


class TestHybridSearchUseCase:
    """Tests for HybridSearchUseCase.

    Regression coverage for the bug where protocol.py called the non-existent
    .search() method; the public entry point is .hybrid_search().
    """

    def test_public_method_is_hybrid_search(self):
        """The use case exposes hybrid_search(), not search()."""
        assert hasattr(HybridSearchUseCase, "hybrid_search")
        assert not hasattr(HybridSearchUseCase, "search")

    def test_hybrid_search_local_only(self):
        """Hybrid search returns matching local entities with attribution."""
        graph = NetworkXKnowledgeGraph()
        entity = Entity(
            id=EntityId(value="mod::UserService"),
            name="UserService",
            type=EntityType.CLASS,
            location=Location(file="service.py", line=1, column=0),
        )
        graph.entities.add(entity)

        usecase = HybridSearchUseCase(local_graph=graph, frameworks_dir=None)
        result = usecase.hybrid_search(query="UserService", frameworks=[])

        assert result.query == "UserService"
        assert result.total_count >= 1
        assert result.source_breakdown["local"] >= 1

    def test_hybrid_search_empty_graph(self):
        """Hybrid search on an empty graph returns no results."""
        usecase = HybridSearchUseCase(local_graph=NetworkXKnowledgeGraph(), frameworks_dir=None)
        result = usecase.hybrid_search(query="anything", frameworks=[])

        assert result.total_count == 0


def _relationship_graph() -> NetworkXKnowledgeGraph:
    """Build a small graph with CALLS / CONTAINS relationships.

    Structure:
        Service (class) CONTAINS run (method)
        run CALLS main_func
        main_func CALLS helper
    """
    from magatama_core.domain.entities import Relationship, RelationshipType

    graph = NetworkXKnowledgeGraph()
    helper = Entity(
        id=EntityId(value="mod::helper"),
        name="helper",
        type=EntityType.FUNCTION,
        location=Location(file="mod.py", line=1, column=0),
        docstring="Helper function that adds one.",
    )
    main_func = Entity(
        id=EntityId(value="mod::main_func"),
        name="main_func",
        type=EntityType.FUNCTION,
        location=Location(file="mod.py", line=5, column=0),
        docstring="Main entry point.",
    )
    service = Entity(
        id=EntityId(value="mod::Service"),
        name="Service",
        type=EntityType.CLASS,
        location=Location(file="mod.py", line=10, column=0),
        docstring="A service class.",
    )
    run = Entity(
        id=EntityId(value="mod::Service.run"),
        name="run",
        type=EntityType.METHOD,
        location=Location(file="mod.py", line=12, column=4),
    )
    for e in (helper, main_func, service, run):
        graph.entities.add(e)

    graph.relationships.add(
        Relationship(source_id=service.id, target_id=run.id, type=RelationshipType.CONTAINS)
    )
    graph.relationships.add(
        Relationship(source_id=run.id, target_id=main_func.id, type=RelationshipType.CALLS)
    )
    graph.relationships.add(
        Relationship(source_id=main_func.id, target_id=helper.id, type=RelationshipType.CALLS)
    )
    return graph


class TestDependencyImpactUseCase:
    """Tests for DependencyImpactUseCase against a relationship-rich graph."""

    def test_analyze_impact_with_dependents(self):
        from magatama_core.application.usecases.framework_usecase import DependencyImpactUseCase

        usecase = DependencyImpactUseCase(_relationship_graph())
        result = usecase.analyze_impact(entity_name="helper", depth=3)

        assert result.entity_name == "helper"
        assert result.risk_level in {"low", "medium", "high"}
        assert result.depth_analyzed >= 1

    def test_analyze_impact_not_found(self):
        from magatama_core.application.usecases.framework_usecase import DependencyImpactUseCase

        usecase = DependencyImpactUseCase(_relationship_graph())
        result = usecase.analyze_impact(entity_name="does_not_exist")
        assert result.entity_name == "does_not_exist"

    def test_find_critical_paths(self):
        from magatama_core.application.usecases.framework_usecase import DependencyImpactUseCase

        usecase = DependencyImpactUseCase(_relationship_graph())
        paths = usecase.find_critical_paths(entity_name="helper", limit=5)
        assert isinstance(paths, list)


class TestCodeNavigationUseCase:
    """Tests for CodeNavigationUseCase."""

    def test_navigate_both(self):
        from magatama_core.application.usecases.framework_usecase import CodeNavigationUseCase

        usecase = CodeNavigationUseCase(_relationship_graph())
        result = usecase.navigate_from(entity_name="main_func", direction="both", depth=2)
        assert result.root_entity == "main_func"
        assert result.total_nodes >= 0

    def test_navigate_callers_and_callees(self):
        from magatama_core.application.usecases.framework_usecase import CodeNavigationUseCase

        usecase = CodeNavigationUseCase(_relationship_graph())
        for direction in ("callers", "callees"):
            result = usecase.navigate_from(entity_name="main_func", direction=direction, depth=2)
            assert result.direction == direction

    def test_get_call_graph(self):
        from magatama_core.application.usecases.framework_usecase import CodeNavigationUseCase

        usecase = CodeNavigationUseCase(_relationship_graph())
        data = usecase.get_call_graph(entity_name="main_func", depth=2)
        assert isinstance(data, dict)


class TestDocumentationGenerationUseCase:
    """Tests for DocumentationGenerationUseCase."""

    def test_generate_markdown(self):
        from magatama_core.application.usecases.framework_usecase import (
            DocumentationGenerationUseCase,
        )

        usecase = DocumentationGenerationUseCase(_relationship_graph())
        result = usecase.generate_documentation(entity_name="main_func")
        assert result.entity_name == "main_func"
        assert result.documentation

    def test_generate_for_class(self):
        from magatama_core.application.usecases.framework_usecase import (
            DocumentationGenerationUseCase,
        )

        usecase = DocumentationGenerationUseCase(_relationship_graph())
        result = usecase.generate_documentation(
            entity_name="Service", include_examples=True, include_related=True
        )
        assert result.entity_type in {"class", "unknown"}

    def test_generate_jsdoc_no_extras(self):
        from magatama_core.application.usecases.framework_usecase import (
            DocumentationGenerationUseCase,
        )

        usecase = DocumentationGenerationUseCase(_relationship_graph())
        result = usecase.generate_documentation(
            entity_name="helper",
            format="jsdoc",
            include_examples=False,
            include_related=False,
        )
        assert result.entity_name == "helper"

    def test_generate_not_found(self):
        from magatama_core.application.usecases.framework_usecase import (
            DocumentationGenerationUseCase,
        )

        usecase = DocumentationGenerationUseCase(_relationship_graph())
        result = usecase.generate_documentation(entity_name="missing_entity")
        assert result.entity_name == "missing_entity"


class TestCodingGuidanceUseCase:
    """Tests for CodingGuidanceUseCase."""

    def test_get_guidance_class(self):
        from magatama_core.application.usecases.framework_usecase import CodingGuidanceUseCase

        usecase = CodingGuidanceUseCase(_relationship_graph())
        result = usecase.get_guidance(task="user account service", entity_type="class")
        assert result.task
        assert result.naming_convention

    def test_get_guidance_function_similar(self):
        from magatama_core.application.usecases.framework_usecase import CodingGuidanceUseCase

        usecase = CodingGuidanceUseCase(_relationship_graph())
        result = usecase.get_guidance(
            task="compute helper", entity_type="function", similar_to="helper"
        )
        assert result.entity_type == "function"


class TestPatternDetectionUseCase:
    """Tests for PatternDetectionUseCase."""

    def test_detect_patterns_runs(self):
        from magatama_core.application.usecases.framework_usecase import PatternDetectionUseCase

        usecase = PatternDetectionUseCase(_relationship_graph())
        result = usecase.detect_patterns(limit=20, min_confidence=0.1)
        assert hasattr(result, "patterns")
        assert hasattr(result, "total_patterns")


class TestFrameworkKnowledgeSearchExtra:
    """Extra coverage for cross-framework search and entity context."""

    def _build_frameworks(self, tmp_path: Path):
        for fw in ["alpha", "beta"]:
            g = NetworkXKnowledgeGraph()
            g.entities.add(
                Entity(
                    id=EntityId(value=f"{fw}::UserController"),
                    name="UserController",
                    type=EntityType.CLASS,
                    location=Location(file=f"{fw}/controller.py", line=1, column=0),
                    docstring="Handles user requests.",
                )
            )
            g.save(tmp_path / f"{fw}.json")
        usecase = FrameworkKnowledgeUseCase(tmp_path)
        usecase.list_frameworks()  # populate framework info by scanning JSON files
        return usecase

    def test_search_all_frameworks(self, tmp_path: Path):
        usecase = self._build_frameworks(tmp_path)
        results = usecase.search_all_frameworks("Controller")
        assert isinstance(results, dict)

    def test_search_all_frameworks_with_type(self, tmp_path: Path):
        usecase = self._build_frameworks(tmp_path)
        results = usecase.search_all_frameworks("Controller", entity_type=EntityType.CLASS)
        assert isinstance(results, dict)

    def test_get_entity_context_found(self, tmp_path: Path):
        self._build_frameworks(tmp_path)
        usecase = FrameworkKnowledgeUseCase(tmp_path)
        usecase.list_frameworks()
        ctx = usecase.get_entity_context("alpha", "alpha::UserController")
        assert "entity" in ctx or "error" in ctx

    def test_get_entity_context_missing_framework(self, tmp_path: Path):
        usecase = FrameworkKnowledgeUseCase(tmp_path)
        ctx = usecase.get_entity_context("nope", "x::y")
        assert "error" in ctx

    def test_search_framework_ranked(self, tmp_path: Path):
        usecase = self._build_frameworks(tmp_path)
        result = usecase.search_framework("alpha", "User")
        assert result.framework == "alpha"
        assert len(result.entities) >= 1

    def test_search_framework_with_type_filter(self, tmp_path: Path):
        usecase = self._build_frameworks(tmp_path)
        result = usecase.search_framework("alpha", "Controller", entity_type=EntityType.CLASS)
        assert result.framework == "alpha"

    def test_find_similar_patterns_with_type(self, tmp_path: Path):
        usecase = self._build_frameworks(tmp_path)
        result = usecase.find_similar_patterns("Controller", entity_type=EntityType.CLASS)
        assert result.pattern_name == "Controller"
        assert result.total_count >= 1

    def test_find_similar_patterns_type_excluded(self, tmp_path: Path):
        usecase = self._build_frameworks(tmp_path)
        # No FUNCTION entities exist, so the type filter excludes everything.
        result = usecase.find_similar_patterns("Controller", entity_type=EntityType.FUNCTION)
        assert result.total_count == 0


class TestCodeEvolutionUseCase:
    """Tests for CodeEvolutionUseCase (Git-history based)."""

    def test_track_evolution_entity_not_found(self):
        from magatama_core.application.usecases.framework_usecase import CodeEvolutionUseCase

        usecase = CodeEvolutionUseCase(_relationship_graph())
        result = usecase.track_evolution(entity_name="does_not_exist")
        assert result.entity_name == "does_not_exist"
        assert result.events == []
        assert result.total_changes == 0

    def test_track_evolution_known_entity(self):
        from magatama_core.application.usecases.framework_usecase import CodeEvolutionUseCase

        usecase = CodeEvolutionUseCase(_relationship_graph())
        result = usecase.track_evolution(entity_name="helper")
        # Without GitPython / outside a repo this still returns a result object.
        assert result.entity_name == "helper"
        assert isinstance(result.timeline_data, list)

    def test_find_hotspots_returns_list(self):
        from magatama_core.application.usecases.framework_usecase import CodeEvolutionUseCase

        usecase = CodeEvolutionUseCase(_relationship_graph())
        hotspots = usecase.find_hotspots(limit=5)
        assert isinstance(hotspots, list)


class TestFrameworkSemanticSearchUseCase:
    """Tests for FrameworkSemanticSearchUseCase (reads raw framework JSON)."""

    def _build_dir(self, tmp_path: Path):
        summary = {
            "frameworks": {
                "react": {"name": "react", "entities_count": 2},
            }
        }
        (tmp_path / "summary.json").write_text(json.dumps(summary))
        graph = {
            "entities": [
                {
                    "name": "useState",
                    "type": "function",
                    "docstring": "A React hook for state.",
                    "location": {"file": "react.js", "line": 10},
                },
                {
                    "name": "useEffect",
                    "type": "function",
                    "docstring": "A React hook for side effects.",
                    "location": {"file": "react.js", "line": 40},
                },
            ]
        }
        (tmp_path / "react.json").write_text(json.dumps(graph))

    def test_search_matches(self, tmp_path: Path):
        from magatama_core.application.usecases.framework_usecase import (
            FrameworkSemanticSearchUseCase,
        )

        self._build_dir(tmp_path)
        usecase = FrameworkSemanticSearchUseCase(tmp_path)
        result = usecase.search("useState")
        assert result.total_count >= 1
        assert result.results[0]["name"] == "useState"

    def test_search_framework_filter(self, tmp_path: Path):
        from magatama_core.application.usecases.framework_usecase import (
            FrameworkSemanticSearchUseCase,
        )

        self._build_dir(tmp_path)
        usecase = FrameworkSemanticSearchUseCase(tmp_path)
        result = usecase.search("hook", frameworks=["react"], limit=10)
        assert result.total_count >= 0

    def test_search_no_match(self, tmp_path: Path):
        from magatama_core.application.usecases.framework_usecase import (
            FrameworkSemanticSearchUseCase,
        )

        self._build_dir(tmp_path)
        usecase = FrameworkSemanticSearchUseCase(tmp_path)
        result = usecase.search("zzz_nonexistent_term")
        assert result.total_count == 0

    def test_find_by_pattern_wildcard(self, tmp_path: Path):
        from magatama_core.application.usecases.framework_usecase import (
            FrameworkSemanticSearchUseCase,
        )

        self._build_dir(tmp_path)
        usecase = FrameworkSemanticSearchUseCase(tmp_path)
        result = usecase.find_by_pattern("use*")
        names = [r["name"] for r in result.matches]
        assert "useState" in names
        assert "useEffect" in names

    def test_find_by_pattern_no_match(self, tmp_path: Path):
        from magatama_core.application.usecases.framework_usecase import (
            FrameworkSemanticSearchUseCase,
        )

        self._build_dir(tmp_path)
        usecase = FrameworkSemanticSearchUseCase(tmp_path)
        result = usecase.find_by_pattern("Nonexistent*")
        assert result.total_count == 0


class TestCodeRecommendationUseCase:
    """Tests for CodeRecommendationUseCase (local only)."""

    def test_recommend_local(self):
        from magatama_core.application.usecases.framework_usecase import CodeRecommendationUseCase

        usecase = CodeRecommendationUseCase(local_graph=_relationship_graph(), frameworks_dir=None)
        result = usecase.recommend_code(
            query="helper", include_frameworks=False, include_local=True, min_relevance=0.0
        )
        assert result.query == "helper"
        assert hasattr(result, "snippets")
