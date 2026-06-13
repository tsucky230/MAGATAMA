"""
NetworkX Knowledge Graph Tests - RED Phase First (Article III)

REQ-KGC-003: Graph storage
REQ-CTX-002: Related entity retrieval
"""

from pathlib import Path

import pytest

from magatama_core.domain.entities.code_entities import ClassEntity, FunctionEntity
from magatama_core.domain.entities.relationships import Relationship, RelationshipType
from magatama_core.domain.value_objects.ids import EntityId
from magatama_core.domain.value_objects.location import Location
from magatama_core.infrastructure.storage.networkx_graph import NetworkXKnowledgeGraph


class TestNetworkXKnowledgeGraph:
    """Test NetworkX-based knowledge graph implementation."""

    @pytest.fixture
    def graph(self) -> NetworkXKnowledgeGraph:
        """Create a fresh knowledge graph."""
        return NetworkXKnowledgeGraph()

    @pytest.fixture
    def populated_graph(self) -> NetworkXKnowledgeGraph:
        """Create a graph with sample data."""
        graph = NetworkXKnowledgeGraph()

        # Add some entities
        func_a = FunctionEntity(
            id=EntityId(value="func_a"),
            name="function_a",
            location=Location(file="test.py", line=10),
        )
        func_b = FunctionEntity(
            id=EntityId(value="func_b"),
            name="function_b",
            location=Location(file="test.py", line=20),
        )
        cls = ClassEntity(
            id=EntityId(value="cls_x"),
            name="ClassX",
            location=Location(file="test.py", line=1),
        )

        graph.entities.add(func_a)
        graph.entities.add(func_b)
        graph.entities.add(cls)

        # Add relationships
        graph.relationships.add(
            Relationship(
                source_id=EntityId(value="func_a"),
                target_id=EntityId(value="func_b"),
                type=RelationshipType.CALLS,
            )
        )
        graph.relationships.add(
            Relationship(
                source_id=EntityId(value="cls_x"),
                target_id=EntityId(value="func_a"),
                type=RelationshipType.CONTAINS,
            )
        )

        return graph

    @pytest.mark.unit
    def test_graph_initialization(self, graph: NetworkXKnowledgeGraph) -> None:
        """Test graph initializes correctly."""
        assert graph.entities is not None
        assert graph.relationships is not None
        assert graph.entities.count() == 0

    @pytest.mark.unit
    def test_find_path_exists(self, populated_graph: NetworkXKnowledgeGraph) -> None:
        """Test finding path between connected entities."""
        path = populated_graph.find_path(
            EntityId(value="cls_x"),
            EntityId(value="func_b"),
        )
        assert path is not None
        assert len(path) == 3  # cls_x -> func_a -> func_b

    @pytest.mark.unit
    def test_find_path_not_exists(self, populated_graph: NetworkXKnowledgeGraph) -> None:
        """Test finding path when none exists."""
        # Add disconnected entity
        func_c = FunctionEntity(
            id=EntityId(value="func_c"),
            name="function_c",
            location=Location(file="other.py", line=1),
        )
        populated_graph.entities.add(func_c)

        path = populated_graph.find_path(
            EntityId(value="cls_x"),
            EntityId(value="func_c"),
        )
        assert path is None

    @pytest.mark.unit
    def test_get_neighbors_depth_1(self, populated_graph: NetworkXKnowledgeGraph) -> None:
        """Test getting immediate neighbors."""
        neighbors = populated_graph.get_neighbors(EntityId(value="func_a"), depth=1)

        # func_a is connected to func_b and cls_x
        assert len(neighbors) == 2
        neighbor_names = {n.name for n in neighbors}
        assert "function_b" in neighbor_names
        assert "ClassX" in neighbor_names

    @pytest.mark.unit
    def test_get_neighbors_depth_2(self, populated_graph: NetworkXKnowledgeGraph) -> None:
        """Test getting neighbors within 2 hops."""
        neighbors = populated_graph.get_neighbors(EntityId(value="cls_x"), depth=2)

        # cls_x -> func_a -> func_b (all reachable within 2 hops)
        assert len(neighbors) >= 2

    @pytest.mark.unit
    def test_get_subgraph(self, populated_graph: NetworkXKnowledgeGraph) -> None:
        """Test extracting a subgraph."""
        entities, relationships = populated_graph.get_subgraph(
            [
                EntityId(value="func_a"),
                EntityId(value="func_b"),
            ]
        )

        assert len(entities) == 2
        # Should include the CALLS relationship between them
        assert len(relationships) >= 1

    @pytest.mark.unit
    def test_save_and_load(self, populated_graph: NetworkXKnowledgeGraph, tmp_path: Path) -> None:
        """Test saving and loading the graph."""
        save_path = tmp_path / "graph.json"

        # Save
        populated_graph.save(save_path)
        assert save_path.exists()

        # Load into new graph
        new_graph = NetworkXKnowledgeGraph()
        new_graph.load(save_path)

        # Verify data
        assert new_graph.entities.count() == populated_graph.entities.count()
        assert len(new_graph.relationships.all()) == len(populated_graph.relationships.all())

    @pytest.mark.unit
    def test_clear(self, populated_graph: NetworkXKnowledgeGraph) -> None:
        """Test clearing the graph."""
        assert populated_graph.entities.count() > 0

        populated_graph.clear()

        assert populated_graph.entities.count() == 0
        assert len(populated_graph.relationships.all()) == 0

    @pytest.mark.unit
    def test_max_depth_limit(self, populated_graph: NetworkXKnowledgeGraph) -> None:
        """Test path finding respects max depth."""
        # Try to find with depth 1 (won't reach func_b from cls_x)
        path = populated_graph.find_path(
            EntityId(value="cls_x"),
            EntityId(value="func_b"),
            max_depth=1,
        )
        # Path requires 2 hops, so with max_depth=1 should fail
        assert path is None
