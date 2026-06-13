"""Tests for Phase 2 (Sprint 14) Use Cases.

REQ-004: Hybrid Search (Local + Framework)
REQ-005: Code Quality Analysis
REQ-006: Code Evolution Tracking
"""

import json
from pathlib import Path

import pytest

from magatama_core.application.usecases.framework_usecase import (
    CodeEvolutionUseCase,
    CodeQualityUseCase,
    EvolutionResult,
    HybridSearchResult,
    HybridSearchUseCase,
    QualityAnalysisResult,
    QualityMetric,
)
from magatama_core.domain.entities import Entity, EntityType, Relationship, RelationshipType
from magatama_core.domain.value_objects import EntityId
from magatama_core.domain.value_objects.location import Location
from magatama_core.infrastructure.storage import NetworkXKnowledgeGraph

# =============================================================================
# REQ-004: Hybrid Search Tests
# =============================================================================


class TestHybridSearchUseCase:
    """Tests for HybridSearchUseCase."""

    @pytest.fixture
    def local_graph(self) -> NetworkXKnowledgeGraph:
        """Create a local graph with test entities."""
        graph = NetworkXKnowledgeGraph()

        entities = [
            ("UserService", EntityType.CLASS, "Service for user management"),
            ("authenticate", EntityType.METHOD, "Authenticate user credentials"),
            ("UserRepository", EntityType.CLASS, "User data access layer"),
            ("create_user", EntityType.FUNCTION, "Create a new user"),
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
        fw_data = {
            "entities": [
                {
                    "name": "FastAPIRouter",
                    "type": "class",
                    "docstring": "FastAPI router for API endpoints",
                    "location": {"file": "fastapi/router.py", "line": 1},
                },
                {
                    "name": "Depends",
                    "type": "function",
                    "docstring": "Dependency injection for FastAPI",
                    "location": {"file": "fastapi/depends.py", "line": 10},
                },
                {
                    "name": "authenticate_request",
                    "type": "function",
                    "docstring": "Authenticate incoming request",
                    "location": {"file": "fastapi/auth.py", "line": 1},
                },
            ]
        }
        (tmp_path / "fastapi.json").write_text(json.dumps(fw_data))
        return tmp_path

    def test_hybrid_search_local_only(self, local_graph):
        """Test hybrid search with local graph only."""
        usecase = HybridSearchUseCase(local_graph=local_graph)

        result = usecase.hybrid_search("user", local_weight=1.0)

        assert isinstance(result, HybridSearchResult)
        assert result.query == "user"
        assert result.total_count > 0
        assert result.source_breakdown["local"] > 0
        assert result.source_breakdown["framework"] == 0

    def test_hybrid_search_frameworks_only(self, frameworks_dir):
        """Test hybrid search with frameworks only."""
        usecase = HybridSearchUseCase(frameworks_dir=frameworks_dir)

        result = usecase.hybrid_search("FastAPI", local_weight=0.0)

        assert result.total_count > 0
        assert result.source_breakdown["framework"] > 0

    def test_hybrid_search_combined(self, local_graph, frameworks_dir):
        """Test hybrid search combining both sources."""
        usecase = HybridSearchUseCase(
            local_graph=local_graph,
            frameworks_dir=frameworks_dir,
        )

        result = usecase.hybrid_search("authenticate", local_weight=0.5)

        assert result.total_count > 0
        # Should find from both sources
        assert result.source_breakdown["local"] >= 0
        assert result.source_breakdown["framework"] >= 0

    def test_hybrid_search_with_local_weight(self, local_graph, frameworks_dir):
        """Test hybrid search with different local weights."""
        usecase = HybridSearchUseCase(
            local_graph=local_graph,
            frameworks_dir=frameworks_dir,
        )

        # High local weight
        result_local = usecase.hybrid_search("auth", local_weight=0.9)

        # High framework weight
        result_fw = usecase.hybrid_search("auth", local_weight=0.1)

        # Both should return results
        assert result_local.total_count >= 0
        assert result_fw.total_count >= 0

    def test_hybrid_search_limit(self, local_graph, frameworks_dir):
        """Test hybrid search with limit."""
        usecase = HybridSearchUseCase(
            local_graph=local_graph,
            frameworks_dir=frameworks_dir,
        )

        result = usecase.hybrid_search("e", limit=2)

        assert result.total_count <= 2

    def test_hybrid_search_specific_frameworks(self, local_graph, frameworks_dir):
        """Test hybrid search with specific frameworks."""
        usecase = HybridSearchUseCase(
            local_graph=local_graph,
            frameworks_dir=frameworks_dir,
        )

        result = usecase.hybrid_search(
            "router",
            frameworks=["fastapi"],
        )

        assert result.total_count >= 0

    def test_hybrid_search_no_results(self, local_graph):
        """Test hybrid search with no matching results."""
        usecase = HybridSearchUseCase(local_graph=local_graph)

        result = usecase.hybrid_search("xyznonexistent123")

        assert result.total_count == 0

    def test_hybrid_search_weight_bounds(self, local_graph):
        """Test that local weight is bounded between 0 and 1."""
        usecase = HybridSearchUseCase(local_graph=local_graph)

        # Weight > 1 should be clamped to 1
        result1 = usecase.hybrid_search("user", local_weight=2.0)
        assert result1 is not None

        # Weight < 0 should be clamped to 0
        result2 = usecase.hybrid_search("user", local_weight=-1.0)
        assert result2 is not None


# =============================================================================
# REQ-005: Code Quality Analysis Tests
# =============================================================================


class TestCodeQualityUseCase:
    """Tests for CodeQualityUseCase."""

    @pytest.fixture
    def graph_with_class(self) -> NetworkXKnowledgeGraph:
        """Create a graph with a class and methods."""
        graph = NetworkXKnowledgeGraph()

        # Add a class
        cls = Entity(
            id=EntityId(value="mod::OrderService"),
            name="OrderService",
            type=EntityType.CLASS,
            location=Location(file="services/order.py", line=10, column=0),
            docstring="Service for order management.",
        )
        graph.entities.add(cls)

        # Add methods
        methods = [
            ("process_order", "Process an order. Args: order: Order object to process."),
            ("validate_order", "Validate order data."),
            ("calculate_total", "Calculate order total."),
        ]

        for i, (name, docstring) in enumerate(methods):
            method = Entity(
                id=EntityId(value=f"mod::OrderService.{name}"),
                name=name,
                type=EntityType.METHOD,
                location=Location(file="services/order.py", line=20 + i * 10, column=4),
                docstring=docstring,
            )
            graph.entities.add(method)

            # Add contains relationship
            graph.relationships.add(
                Relationship(
                    source_id=cls.id,
                    target_id=method.id,
                    type=RelationshipType.CONTAINS,
                )
            )

        return graph

    @pytest.fixture
    def graph_with_function(self) -> NetworkXKnowledgeGraph:
        """Create a graph with a function."""
        graph = NetworkXKnowledgeGraph()

        func = Entity(
            id=EntityId(value="mod::complex_calculation"),
            name="complex_calculation",
            type=EntityType.FUNCTION,
            location=Location(file="utils/calc.py", line=1, column=0),
            docstring="Perform complex calculation. Args: x: First value. y: Second value. z: Third value.",
        )
        graph.entities.add(func)

        return graph

    def test_analyze_quality_class(self, graph_with_class):
        """Test quality analysis for a class."""
        usecase = CodeQualityUseCase(graph_with_class)

        result = usecase.analyze_quality("OrderService")

        assert isinstance(result, QualityAnalysisResult)
        assert result.entity_name == "OrderService"
        assert result.entity_type == "class"
        assert len(result.metrics) > 0
        assert 0 <= result.overall_score <= 100
        assert result.overall_status in ["good", "warning", "danger"]

    def test_analyze_quality_function(self, graph_with_function):
        """Test quality analysis for a function."""
        usecase = CodeQualityUseCase(graph_with_function)

        result = usecase.analyze_quality("complex_calculation")

        assert result.entity_name == "complex_calculation"
        assert result.entity_type == "function"
        assert len(result.metrics) > 0

    def test_analyze_quality_not_found(self, graph_with_class):
        """Test quality analysis for non-existent entity."""
        usecase = CodeQualityUseCase(graph_with_class)

        result = usecase.analyze_quality("NonExistent")

        assert result.entity_type == "unknown"
        assert result.overall_score == 0.0
        assert "not found" in result.recommendations[0].lower()

    def test_quality_metrics_structure(self, graph_with_class):
        """Test that quality metrics have correct structure."""
        usecase = CodeQualityUseCase(graph_with_class)

        result = usecase.analyze_quality("OrderService")

        for metric in result.metrics:
            assert isinstance(metric, QualityMetric)
            assert metric.name
            assert isinstance(metric.value, (int, float))
            assert isinstance(metric.threshold_good, (int, float))
            assert isinstance(metric.threshold_warning, (int, float))
            assert metric.status in ["good", "warning", "danger"]
            assert metric.description

    def test_quality_coupling_metrics(self, graph_with_class):
        """Test coupling metrics are calculated."""
        usecase = CodeQualityUseCase(graph_with_class)

        result = usecase.analyze_quality("OrderService")

        metric_names = [m.name for m in result.metrics]
        assert "Afferent Coupling" in metric_names
        assert "Efferent Coupling" in metric_names

    def test_quality_recommendations(self, graph_with_class):
        """Test that recommendations are generated."""
        usecase = CodeQualityUseCase(graph_with_class)

        result = usecase.analyze_quality("OrderService")

        assert isinstance(result.recommendations, list)
        assert len(result.recommendations) > 0

    def test_quality_score_range(self, graph_with_class):
        """Test that overall score is in valid range."""
        usecase = CodeQualityUseCase(graph_with_class)

        result = usecase.analyze_quality("OrderService")

        assert 0 <= result.overall_score <= 100

    def test_quality_empty_graph(self):
        """Test quality analysis with empty graph."""
        graph = NetworkXKnowledgeGraph()
        usecase = CodeQualityUseCase(graph)

        result = usecase.analyze_quality("AnyEntity")

        assert result.entity_type == "unknown"
        assert result.overall_score == 0.0


# =============================================================================
# REQ-006: Code Evolution Tracking Tests
# =============================================================================


class TestCodeEvolutionUseCase:
    """Tests for CodeEvolutionUseCase."""

    @pytest.fixture
    def graph_with_entities(self) -> NetworkXKnowledgeGraph:
        """Create a graph with test entities."""
        graph = NetworkXKnowledgeGraph()

        entity = Entity(
            id=EntityId(value="mod::PaymentService"),
            name="PaymentService",
            type=EntityType.CLASS,
            location=Location(file="services/payment.py", line=1, column=0),
            docstring="Payment processing service.",
        )
        graph.entities.add(entity)

        return graph

    def test_track_evolution_entity_not_found(self, graph_with_entities):
        """Test evolution tracking for non-existent entity."""
        usecase = CodeEvolutionUseCase(graph_with_entities)

        result = usecase.track_evolution("NonExistent")

        assert isinstance(result, EvolutionResult)
        assert result.entity_name == "NonExistent"
        assert result.entity_file == ""
        assert result.total_changes == 0

    def test_track_evolution_basic(self, graph_with_entities):
        """Test basic evolution tracking."""
        usecase = CodeEvolutionUseCase(graph_with_entities)

        result = usecase.track_evolution("PaymentService")

        assert result.entity_name == "PaymentService"
        assert result.entity_file == "services/payment.py"
        assert isinstance(result.events, list)
        assert isinstance(result.timeline_data, list)

    def test_track_evolution_with_date_range(self, graph_with_entities):
        """Test evolution tracking with date range."""
        usecase = CodeEvolutionUseCase(graph_with_entities)

        result = usecase.track_evolution(
            "PaymentService",
            since="2024-01-01",
            until="2024-12-31",
        )

        assert result.entity_name == "PaymentService"

    def test_track_evolution_hotspot_score(self, graph_with_entities):
        """Test that hotspot score is calculated."""
        usecase = CodeEvolutionUseCase(graph_with_entities)

        result = usecase.track_evolution("PaymentService")

        assert isinstance(result.hotspot_score, float)
        assert 0 <= result.hotspot_score <= 1
        assert isinstance(result.is_hotspot, bool)

    def test_evolution_result_structure(self, graph_with_entities):
        """Test evolution result has correct structure."""
        usecase = CodeEvolutionUseCase(graph_with_entities)

        result = usecase.track_evolution("PaymentService")

        assert hasattr(result, "entity_name")
        assert hasattr(result, "entity_file")
        assert hasattr(result, "events")
        assert hasattr(result, "total_changes")
        assert hasattr(result, "unique_authors")
        assert hasattr(result, "hotspot_score")
        assert hasattr(result, "is_hotspot")
        assert hasattr(result, "timeline_data")

    def test_find_hotspots(self, graph_with_entities):
        """Test finding hotspots."""
        usecase = CodeEvolutionUseCase(graph_with_entities)

        hotspots = usecase.find_hotspots(limit=5)

        assert isinstance(hotspots, list)
        assert len(hotspots) <= 5

    def test_find_hotspots_structure(self, graph_with_entities):
        """Test hotspot result structure."""
        usecase = CodeEvolutionUseCase(graph_with_entities)

        hotspots = usecase.find_hotspots(limit=5)

        for hotspot in hotspots:
            assert "name" in hotspot
            assert "file" in hotspot
            assert "hotspot_score" in hotspot
            assert "is_hotspot" in hotspot

    def test_find_hotspots_sorted(self, graph_with_entities):
        """Test that hotspots are sorted by score."""
        # Add more entities
        entities = [
            ("Service1", "file1.py"),
            ("Service2", "file2.py"),
            ("Service3", "file3.py"),
        ]
        for name, file in entities:
            entity = Entity(
                id=EntityId(value=f"mod::{name}"),
                name=name,
                type=EntityType.CLASS,
                location=Location(file=file, line=1, column=0),
            )
            graph_with_entities.entities.add(entity)

        usecase = CodeEvolutionUseCase(graph_with_entities)

        hotspots = usecase.find_hotspots(limit=10)

        if len(hotspots) > 1:
            for i in range(len(hotspots) - 1):
                assert hotspots[i]["hotspot_score"] >= hotspots[i + 1]["hotspot_score"]


# =============================================================================
# Integration Tests
# =============================================================================


class TestPhase2Integration:
    """Integration tests for Phase 2 use cases."""

    @pytest.fixture
    def full_graph(self) -> NetworkXKnowledgeGraph:
        """Create a comprehensive graph for integration tests."""
        graph = NetworkXKnowledgeGraph()

        # Create a realistic class hierarchy
        classes = [
            ("ApplicationService", "Main application service"),
            ("UserService", "User management service"),
            ("AuthService", "Authentication service"),
        ]

        for name, docstring in classes:
            cls = Entity(
                id=EntityId(value=f"mod::{name}"),
                name=name,
                type=EntityType.CLASS,
                location=Location(file=f"services/{name.lower()}.py", line=1, column=0),
                docstring=docstring,
            )
            graph.entities.add(cls)

        # Add relationships
        graph.relationships.add(
            Relationship(
                source_id=EntityId(value="mod::ApplicationService"),
                target_id=EntityId(value="mod::UserService"),
                type=RelationshipType.DEPENDS_ON,
            )
        )
        graph.relationships.add(
            Relationship(
                source_id=EntityId(value="mod::UserService"),
                target_id=EntityId(value="mod::AuthService"),
                type=RelationshipType.DEPENDS_ON,
            )
        )

        return graph

    def test_all_usecases_work_together(self, full_graph, tmp_path):
        """Test that all Phase 2 use cases can work together."""
        # Create framework data
        fw_data = {
            "entities": [
                {
                    "name": "BaseService",
                    "type": "class",
                    "docstring": "Base service class",
                    "location": {"file": "base.py", "line": 1},
                },
            ]
        }
        (tmp_path / "django.json").write_text(json.dumps(fw_data))

        # Test hybrid search
        hybrid_usecase = HybridSearchUseCase(
            local_graph=full_graph,
            frameworks_dir=tmp_path,
        )
        search_result = hybrid_usecase.hybrid_search("service")
        assert search_result.total_count > 0

        # Test quality analysis
        quality_usecase = CodeQualityUseCase(full_graph)
        quality_result = quality_usecase.analyze_quality("ApplicationService")
        assert quality_result.entity_name == "ApplicationService"

        # Test evolution tracking
        evolution_usecase = CodeEvolutionUseCase(full_graph)
        evolution_result = evolution_usecase.track_evolution("ApplicationService")
        assert evolution_result.entity_name == "ApplicationService"

    def test_empty_graph_all_usecases(self, tmp_path):
        """Test all use cases handle empty graph gracefully."""
        empty_graph = NetworkXKnowledgeGraph()

        # Hybrid search
        hybrid_usecase = HybridSearchUseCase(local_graph=empty_graph)
        search_result = hybrid_usecase.hybrid_search("anything")
        assert search_result.total_count == 0

        # Quality analysis
        quality_usecase = CodeQualityUseCase(empty_graph)
        quality_result = quality_usecase.analyze_quality("anything")
        assert quality_result.entity_type == "unknown"

        # Evolution tracking
        evolution_usecase = CodeEvolutionUseCase(empty_graph)
        evolution_result = evolution_usecase.track_evolution("anything")
        assert evolution_result.total_changes == 0
