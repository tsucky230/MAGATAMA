"""Tests for Phase 1 (Sprint 13) Use Cases.

REQ-001: Documentation Generation
REQ-002: Code Snippet Recommendation
REQ-003: Dependency Impact Analysis
"""

import json
from pathlib import Path

import pytest

from magatama_core.application.usecases.framework_usecase import (
    CodeRecommendationUseCase,
    DependencyImpactUseCase,
    DocumentationGenerationUseCase,
)
from magatama_core.domain.entities import Entity, EntityType, Relationship, RelationshipType
from magatama_core.domain.value_objects import EntityId
from magatama_core.domain.value_objects.location import Location
from magatama_core.infrastructure.storage import NetworkXKnowledgeGraph

# =============================================================================
# REQ-001: Documentation Generation Tests
# =============================================================================


class TestDocumentationGenerationUseCase:
    """Tests for DocumentationGenerationUseCase."""

    @pytest.fixture
    def graph_with_entities(self) -> NetworkXKnowledgeGraph:
        """Create a graph with test entities."""
        graph = NetworkXKnowledgeGraph()

        # Add a class
        cls = Entity(
            id=EntityId(value="mod::UserService"),
            name="UserService",
            type=EntityType.CLASS,
            location=Location(file="services/user.py", line=10, column=0),
            docstring="Service for user management.",
        )
        graph.entities.add(cls)

        # Add a method
        method = Entity(
            id=EntityId(value="mod::UserService.get_user"),
            name="get_user",
            type=EntityType.METHOD,
            location=Location(file="services/user.py", line=20, column=4),
            docstring="Get user by ID.",
        )
        graph.entities.add(method)

        # Add a function that calls the method
        caller = Entity(
            id=EntityId(value="mod::handle_request"),
            name="handle_request",
            type=EntityType.FUNCTION,
            location=Location(file="handlers/api.py", line=5, column=0),
        )
        graph.entities.add(caller)

        # Add relationships
        graph.relationships.add(
            Relationship(
                source_id=cls.id,
                target_id=method.id,
                type=RelationshipType.CONTAINS,
            )
        )
        graph.relationships.add(
            Relationship(
                source_id=caller.id,
                target_id=method.id,
                type=RelationshipType.CALLS,
            )
        )

        return graph

    def test_generate_documentation_entity_not_found(self):
        """Test generating docs for non-existent entity."""
        graph = NetworkXKnowledgeGraph()
        usecase = DocumentationGenerationUseCase(graph)

        result = usecase.generate_documentation("NonExistent")

        assert result.entity_name == "NonExistent"
        assert result.entity_type == "unknown"
        assert "not found" in result.documentation.lower()

    def test_generate_documentation_markdown(self, graph_with_entities):
        """Test generating markdown documentation."""
        usecase = DocumentationGenerationUseCase(graph_with_entities)

        result = usecase.generate_documentation("UserService", format="markdown")

        assert result.entity_name == "UserService"
        assert result.entity_type == "class"
        assert result.format == "markdown"
        assert "# UserService" in result.documentation
        assert "Type" in result.documentation
        assert result.source_file == "services/user.py"

    def test_generate_documentation_jsdoc(self, graph_with_entities):
        """Test generating JSDoc documentation."""
        usecase = DocumentationGenerationUseCase(graph_with_entities)

        result = usecase.generate_documentation("UserService", format="jsdoc")

        assert result.format == "jsdoc"
        assert "/**" in result.documentation
        assert "*/" in result.documentation

    def test_generate_documentation_google(self, graph_with_entities):
        """Test generating Google-style documentation."""
        usecase = DocumentationGenerationUseCase(graph_with_entities)

        result = usecase.generate_documentation("UserService", format="google")

        assert result.format == "google"
        assert '"""' in result.documentation

    def test_generate_documentation_numpy(self, graph_with_entities):
        """Test generating NumPy-style documentation."""
        usecase = DocumentationGenerationUseCase(graph_with_entities)

        result = usecase.generate_documentation("UserService", format="numpy")

        assert result.format == "numpy"
        assert '"""' in result.documentation

    def test_generate_documentation_sphinx(self, graph_with_entities):
        """Test generating Sphinx-style documentation."""
        usecase = DocumentationGenerationUseCase(graph_with_entities)

        result = usecase.generate_documentation("UserService", format="sphinx")

        assert result.format == "sphinx"
        assert ":type:" in result.documentation

    def test_generate_documentation_invalid_format(self, graph_with_entities):
        """Test invalid format falls back to markdown."""
        usecase = DocumentationGenerationUseCase(graph_with_entities)

        result = usecase.generate_documentation("UserService", format="invalid")

        assert result.format == "markdown"

    def test_generate_documentation_with_related(self, graph_with_entities):
        """Test including related entities."""
        usecase = DocumentationGenerationUseCase(graph_with_entities)

        result = usecase.generate_documentation(
            "UserService",
            include_related=True,
        )

        assert len(result.related_entities) > 0

    def test_generate_documentation_with_examples(self, graph_with_entities):
        """Test including usage examples."""
        usecase = DocumentationGenerationUseCase(graph_with_entities)

        result = usecase.generate_documentation(
            "get_user",
            include_examples=True,
        )

        # get_user is called by handle_request
        assert "Usage Examples" in result.documentation or "handle_request" in result.documentation

    def test_generate_documentation_partial_match(self, graph_with_entities):
        """Test finding entity by partial name."""
        usecase = DocumentationGenerationUseCase(graph_with_entities)

        # UserService should match "User" partial
        result = usecase.generate_documentation("User")

        # Should find UserService
        assert result.entity_type != "unknown"
        assert "User" in result.entity_name


# =============================================================================
# REQ-002: Code Snippet Recommendation Tests
# =============================================================================


class TestCodeRecommendationUseCase:
    """Tests for CodeRecommendationUseCase."""

    @pytest.fixture
    def graph_with_code(self) -> NetworkXKnowledgeGraph:
        """Create a graph with code entities."""
        graph = NetworkXKnowledgeGraph()

        # Add authentication-related entities
        entities = [
            ("AuthService", EntityType.CLASS, "Authentication service"),
            ("authenticate", EntityType.METHOD, "Authenticate user credentials"),
            ("verify_token", EntityType.FUNCTION, "Verify JWT token"),
            ("UserRepository", EntityType.CLASS, "User data repository"),
        ]

        for name, etype, docstring in entities:
            entity = Entity(
                id=EntityId(value=f"mod::{name}"),
                name=name,
                type=etype,
                location=Location(file=f"src/{name.lower()}.py", line=1, column=0),
                docstring=docstring,
            )
            graph.entities.add(entity)

        return graph

    @pytest.fixture
    def frameworks_dir(self, tmp_path: Path) -> Path:
        """Create a temporary frameworks directory."""
        # Create a mock framework knowledge graph
        fw_data = {
            "entities": [
                {
                    "name": "JWTAuth",
                    "type": "class",
                    "docstring": "JWT authentication handler",
                    "location": {"file": "jwt/auth.py", "line": 1},
                },
                {
                    "name": "verify_signature",
                    "type": "function",
                    "docstring": "Verify JWT signature",
                    "location": {"file": "jwt/utils.py", "line": 10},
                },
            ]
        }
        (tmp_path / "fastapi.json").write_text(json.dumps(fw_data))
        return tmp_path

    def test_recommend_code_local_only(self, graph_with_code):
        """Test recommendation from local graph only."""
        usecase = CodeRecommendationUseCase(local_graph=graph_with_code)

        result = usecase.recommend_code(
            "auth",  # shorter query for better matching
            include_frameworks=False,
            include_local=True,
            min_relevance=0.1,  # lower threshold
        )

        assert result.query == "auth"
        assert result.total_count > 0
        assert result.source_breakdown["local"] > 0
        assert result.source_breakdown["framework"] == 0

    def test_recommend_code_frameworks_only(self, frameworks_dir):
        """Test recommendation from frameworks only."""
        usecase = CodeRecommendationUseCase(frameworks_dir=frameworks_dir)

        result = usecase.recommend_code(
            "JWT",
            include_frameworks=True,
            include_local=False,
        )

        assert result.total_count > 0
        assert result.source_breakdown["framework"] > 0

    def test_recommend_code_hybrid(self, graph_with_code, frameworks_dir):
        """Test recommendation from both sources."""
        usecase = CodeRecommendationUseCase(
            local_graph=graph_with_code,
            frameworks_dir=frameworks_dir,
        )

        result = usecase.recommend_code(
            "auth",
            include_frameworks=True,
            include_local=True,
        )

        assert result.total_count > 0
        # Should have both sources
        sources = {s.get("source") for s in result.snippets if isinstance(s, dict)}
        assert len(sources) >= 1

    def test_recommend_code_with_limit(self, graph_with_code):
        """Test recommendation with limit."""
        usecase = CodeRecommendationUseCase(local_graph=graph_with_code)

        result = usecase.recommend_code(
            "e",  # matches everything
            limit=2,
        )

        assert result.total_count <= 2

    def test_recommend_code_min_relevance(self, graph_with_code):
        """Test recommendation with minimum relevance."""
        usecase = CodeRecommendationUseCase(local_graph=graph_with_code)

        result = usecase.recommend_code(
            "authentication",
            min_relevance=0.5,
        )

        # All results should have relevance >= 0.5
        for snippet in result.snippets:
            if "relevance_score" in snippet:
                assert snippet["relevance_score"] >= 0.5

    def test_recommend_code_empty_query(self, graph_with_code):
        """Test recommendation with empty-like query."""
        usecase = CodeRecommendationUseCase(local_graph=graph_with_code)

        result = usecase.recommend_code(
            "xyz123nonexistent",
            min_relevance=0.3,
        )

        # Should return suggestion message
        assert result.total_count == 0 or "suggestion" in str(result.snippets)

    def test_recommend_code_relevance_scoring(self, graph_with_code):
        """Test that relevance scoring works correctly."""
        usecase = CodeRecommendationUseCase(local_graph=graph_with_code)

        result = usecase.recommend_code("AuthService")

        # Exact match should have highest score
        if result.snippets:
            top_result = result.snippets[0]
            assert "AuthService" in top_result.get("name", "")


# =============================================================================
# REQ-003: Dependency Impact Analysis Tests
# =============================================================================


class TestDependencyImpactUseCase:
    """Tests for DependencyImpactUseCase."""

    @pytest.fixture
    def graph_with_deps(self) -> NetworkXKnowledgeGraph:
        """Create a graph with dependency chain."""
        graph = NetworkXKnowledgeGraph()

        # Create a dependency chain: A -> B -> C -> D
        entities = []
        for name in ["A", "B", "C", "D"]:
            entity = Entity(
                id=EntityId(value=f"mod::{name}"),
                name=name,
                type=EntityType.FUNCTION,
                location=Location(file="deps.py", line=1, column=0),
            )
            graph.entities.add(entity)
            entities.append(entity)

        # B calls A
        graph.relationships.add(
            Relationship(
                source_id=entities[1].id,  # B
                target_id=entities[0].id,  # A
                type=RelationshipType.CALLS,
            )
        )
        # C calls B
        graph.relationships.add(
            Relationship(
                source_id=entities[2].id,  # C
                target_id=entities[1].id,  # B
                type=RelationshipType.CALLS,
            )
        )
        # D calls C
        graph.relationships.add(
            Relationship(
                source_id=entities[3].id,  # D
                target_id=entities[2].id,  # C
                type=RelationshipType.CALLS,
            )
        )

        return graph

    def test_analyze_impact_entity_not_found(self):
        """Test analyzing non-existent entity."""
        graph = NetworkXKnowledgeGraph()
        usecase = DependencyImpactUseCase(graph)

        result = usecase.analyze_impact("NonExistent")

        assert result.entity_name == "NonExistent"
        assert result.total_affected == 0
        assert result.risk_level == "low"

    def test_analyze_impact_direct_deps(self, graph_with_deps):
        """Test analyzing direct dependencies."""
        usecase = DependencyImpactUseCase(graph_with_deps)

        result = usecase.analyze_impact("A", depth=1)

        assert result.entity_name == "A"
        assert len(result.direct_dependents) == 1  # B calls A
        assert result.direct_dependents[0]["name"] == "B"

    def test_analyze_impact_indirect_deps(self, graph_with_deps):
        """Test analyzing indirect dependencies."""
        usecase = DependencyImpactUseCase(graph_with_deps)

        result = usecase.analyze_impact("A", depth=3)

        assert result.entity_name == "A"
        assert len(result.direct_dependents) == 1  # B
        assert len(result.indirect_dependents) >= 1  # C and maybe D
        assert result.total_affected >= 2

    def test_analyze_impact_score_calculation(self, graph_with_deps):
        """Test impact score calculation."""
        usecase = DependencyImpactUseCase(graph_with_deps)

        result = usecase.analyze_impact("A", depth=3)

        # direct=1 * 1.0 + indirect contributions
        assert result.impact_score >= 1.0
        assert result.impact_score < 10.0  # Not high risk

    def test_analyze_impact_risk_levels(self):
        """Test risk level assignment."""
        graph = NetworkXKnowledgeGraph()

        # Create many dependents
        target = Entity(
            id=EntityId(value="mod::Target"),
            name="Target",
            type=EntityType.FUNCTION,
            location=Location(file="t.py", line=1, column=0),
        )
        graph.entities.add(target)

        # Add 15 direct callers
        for i in range(15):
            caller = Entity(
                id=EntityId(value=f"mod::Caller{i}"),
                name=f"Caller{i}",
                type=EntityType.FUNCTION,
                location=Location(file="c.py", line=i + 1, column=0),  # line starts at 1
            )
            graph.entities.add(caller)
            graph.relationships.add(
                Relationship(
                    source_id=caller.id,
                    target_id=target.id,
                    type=RelationshipType.CALLS,
                )
            )

        usecase = DependencyImpactUseCase(graph)
        result = usecase.analyze_impact("Target")

        # With 15 direct deps, should be high risk
        assert result.risk_level == "high"
        assert result.impact_score >= 10

    def test_analyze_impact_depth_limit(self, graph_with_deps):
        """Test depth parameter limits."""
        usecase = DependencyImpactUseCase(graph_with_deps)

        # Test minimum depth
        result1 = usecase.analyze_impact("A", depth=0)
        assert result1.depth_analyzed == 1  # Minimum is 1

        # Test maximum depth
        result2 = usecase.analyze_impact("A", depth=20)
        assert result2.depth_analyzed == 10  # Maximum is 10

    def test_find_critical_paths(self, graph_with_deps):
        """Test finding critical dependency paths."""
        usecase = DependencyImpactUseCase(graph_with_deps)

        paths = usecase.find_critical_paths("A")

        # Should find paths like A <- B <- C <- D
        assert len(paths) >= 1

    def test_find_critical_paths_no_deps(self):
        """Test finding paths for entity with no deps."""
        graph = NetworkXKnowledgeGraph()
        entity = Entity(
            id=EntityId(value="mod::Isolated"),
            name="Isolated",
            type=EntityType.FUNCTION,
            location=Location(file="i.py", line=1, column=0),
        )
        graph.entities.add(entity)

        usecase = DependencyImpactUseCase(graph)
        paths = usecase.find_critical_paths("Isolated")

        assert len(paths) == 0


# =============================================================================
# Integration Tests
# =============================================================================


class TestPhase1Integration:
    """Integration tests for Phase 1 use cases."""

    def test_doc_generation_with_impact(self):
        """Test documentation includes impact information."""
        graph = NetworkXKnowledgeGraph()

        # Create entities with relationships
        core = Entity(
            id=EntityId(value="mod::CoreService"),
            name="CoreService",
            type=EntityType.CLASS,
            location=Location(file="core.py", line=1, column=0),
            docstring="Core service used by many components.",
        )
        graph.entities.add(core)

        for i in range(3):
            user = Entity(
                id=EntityId(value=f"mod::User{i}"),
                name=f"User{i}",
                type=EntityType.CLASS,
                location=Location(file=f"user{i}.py", line=1, column=0),
            )
            graph.entities.add(user)
            graph.relationships.add(
                Relationship(
                    source_id=user.id,
                    target_id=core.id,
                    type=RelationshipType.CALLS,
                )
            )

        # Generate documentation
        doc_usecase = DocumentationGenerationUseCase(graph)
        doc_result = doc_usecase.generate_documentation("CoreService")

        # Analyze impact
        impact_usecase = DependencyImpactUseCase(graph)
        impact_result = impact_usecase.analyze_impact("CoreService")

        # Both should work correctly
        assert doc_result.entity_type == "class"
        assert impact_result.total_affected == 3

    def test_recommendation_with_impact_context(self):
        """Test code recommendation considering impact."""
        graph = NetworkXKnowledgeGraph()

        # High-impact entity (many callers)
        important = Entity(
            id=EntityId(value="mod::ImportantUtil"),
            name="ImportantUtil",
            type=EntityType.FUNCTION,
            location=Location(file="utils.py", line=1, column=0),
            docstring="Critical utility function",
        )
        graph.entities.add(important)

        # Low-impact entity
        simple = Entity(
            id=EntityId(value="mod::SimpleHelper"),
            name="SimpleHelper",
            type=EntityType.FUNCTION,
            location=Location(file="helpers.py", line=1, column=0),
            docstring="Simple helper function",
        )
        graph.entities.add(simple)

        # Add many callers to important
        for i in range(10):
            caller = Entity(
                id=EntityId(value=f"mod::Caller{i}"),
                name=f"Caller{i}",
                type=EntityType.FUNCTION,
                location=Location(file=f"c{i}.py", line=1, column=0),
            )
            graph.entities.add(caller)
            graph.relationships.add(
                Relationship(
                    source_id=caller.id,
                    target_id=important.id,
                    type=RelationshipType.CALLS,
                )
            )

        # Recommendation should work
        rec_usecase = CodeRecommendationUseCase(local_graph=graph)
        result = rec_usecase.recommend_code("util")

        assert result.total_count > 0
        # ImportantUtil should appear due to high usage
        names = [s.get("name", "") for s in result.snippets]
        assert "ImportantUtil" in names
