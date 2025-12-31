"""
Repository Interface Tests - RED Phase First (Article III)

REQ-KGC-007: Data persistence abstraction
"""

from abc import ABC
from typing import TYPE_CHECKING

import pytest

from yata_core.domain.repositories.entity_repository import EntityRepository
from yata_core.domain.repositories.relationship_repository import RelationshipRepository
from yata_core.domain.repositories.knowledge_graph_repository import KnowledgeGraphRepository
from yata_core.domain.entities.base import Entity, EntityType
from yata_core.domain.entities.code_entities import FunctionEntity
from yata_core.domain.entities.relationships import Relationship, RelationshipType
from yata_core.domain.value_objects.ids import EntityId
from yata_core.domain.value_objects.location import Location


class TestEntityRepository:
    """Test EntityRepository interface."""

    @pytest.mark.unit
    def test_entity_repository_is_abstract(self) -> None:
        """Test EntityRepository is an abstract base class."""
        assert issubclass(EntityRepository, ABC)
        # Should not be instantiable directly
        with pytest.raises(TypeError):
            EntityRepository()  # type: ignore

    @pytest.mark.unit
    def test_entity_repository_has_add_method(self) -> None:
        """Test EntityRepository has add method."""
        assert hasattr(EntityRepository, "add")
        assert callable(getattr(EntityRepository, "add"))

    @pytest.mark.unit
    def test_entity_repository_has_get_method(self) -> None:
        """Test EntityRepository has get method."""
        assert hasattr(EntityRepository, "get")
        assert callable(getattr(EntityRepository, "get"))

    @pytest.mark.unit
    def test_entity_repository_has_get_by_type_method(self) -> None:
        """Test EntityRepository has get_by_type method."""
        assert hasattr(EntityRepository, "get_by_type")
        assert callable(getattr(EntityRepository, "get_by_type"))

    @pytest.mark.unit
    def test_entity_repository_has_get_by_name_method(self) -> None:
        """Test EntityRepository has get_by_name method."""
        assert hasattr(EntityRepository, "get_by_name")
        assert callable(getattr(EntityRepository, "get_by_name"))

    @pytest.mark.unit
    def test_entity_repository_has_update_method(self) -> None:
        """Test EntityRepository has update method."""
        assert hasattr(EntityRepository, "update")
        assert callable(getattr(EntityRepository, "update"))

    @pytest.mark.unit
    def test_entity_repository_has_delete_method(self) -> None:
        """Test EntityRepository has delete method."""
        assert hasattr(EntityRepository, "delete")
        assert callable(getattr(EntityRepository, "delete"))

    @pytest.mark.unit
    def test_entity_repository_has_all_method(self) -> None:
        """Test EntityRepository has all method to list entities."""
        assert hasattr(EntityRepository, "all")
        assert callable(getattr(EntityRepository, "all"))

    @pytest.mark.unit
    def test_entity_repository_has_count_method(self) -> None:
        """Test EntityRepository has count method."""
        assert hasattr(EntityRepository, "count")
        assert callable(getattr(EntityRepository, "count"))


class TestRelationshipRepository:
    """Test RelationshipRepository interface."""

    @pytest.mark.unit
    def test_relationship_repository_is_abstract(self) -> None:
        """Test RelationshipRepository is an abstract base class."""
        assert issubclass(RelationshipRepository, ABC)
        with pytest.raises(TypeError):
            RelationshipRepository()  # type: ignore

    @pytest.mark.unit
    def test_relationship_repository_has_add_method(self) -> None:
        """Test RelationshipRepository has add method."""
        assert hasattr(RelationshipRepository, "add")
        assert callable(getattr(RelationshipRepository, "add"))

    @pytest.mark.unit
    def test_relationship_repository_has_get_outgoing_method(self) -> None:
        """Test RelationshipRepository has get_outgoing method."""
        assert hasattr(RelationshipRepository, "get_outgoing")
        assert callable(getattr(RelationshipRepository, "get_outgoing"))

    @pytest.mark.unit
    def test_relationship_repository_has_get_incoming_method(self) -> None:
        """Test RelationshipRepository has get_incoming method."""
        assert hasattr(RelationshipRepository, "get_incoming")
        assert callable(getattr(RelationshipRepository, "get_incoming"))

    @pytest.mark.unit
    def test_relationship_repository_has_get_by_type_method(self) -> None:
        """Test RelationshipRepository has get_by_type method."""
        assert hasattr(RelationshipRepository, "get_by_type")
        assert callable(getattr(RelationshipRepository, "get_by_type"))

    @pytest.mark.unit
    def test_relationship_repository_has_delete_method(self) -> None:
        """Test RelationshipRepository has delete method."""
        assert hasattr(RelationshipRepository, "delete")
        assert callable(getattr(RelationshipRepository, "delete"))

    @pytest.mark.unit
    def test_relationship_repository_has_all_method(self) -> None:
        """Test RelationshipRepository has all method."""
        assert hasattr(RelationshipRepository, "all")
        assert callable(getattr(RelationshipRepository, "all"))


class TestKnowledgeGraphRepository:
    """Test KnowledgeGraphRepository interface (aggregate repository)."""

    @pytest.mark.unit
    def test_knowledge_graph_repository_is_abstract(self) -> None:
        """Test KnowledgeGraphRepository is an abstract base class."""
        assert issubclass(KnowledgeGraphRepository, ABC)
        with pytest.raises(TypeError):
            KnowledgeGraphRepository()  # type: ignore

    @pytest.mark.unit
    def test_knowledge_graph_repository_has_entity_repository(self) -> None:
        """Test KnowledgeGraphRepository provides entity repository access."""
        assert hasattr(KnowledgeGraphRepository, "entities")

    @pytest.mark.unit
    def test_knowledge_graph_repository_has_relationship_repository(self) -> None:
        """Test KnowledgeGraphRepository provides relationship repository access."""
        assert hasattr(KnowledgeGraphRepository, "relationships")

    @pytest.mark.unit
    def test_knowledge_graph_repository_has_find_path_method(self) -> None:
        """Test KnowledgeGraphRepository has find_path method for graph traversal."""
        assert hasattr(KnowledgeGraphRepository, "find_path")
        assert callable(getattr(KnowledgeGraphRepository, "find_path"))

    @pytest.mark.unit
    def test_knowledge_graph_repository_has_get_neighbors_method(self) -> None:
        """Test KnowledgeGraphRepository has get_neighbors method."""
        assert hasattr(KnowledgeGraphRepository, "get_neighbors")
        assert callable(getattr(KnowledgeGraphRepository, "get_neighbors"))

    @pytest.mark.unit
    def test_knowledge_graph_repository_has_get_subgraph_method(self) -> None:
        """Test KnowledgeGraphRepository has get_subgraph method."""
        assert hasattr(KnowledgeGraphRepository, "get_subgraph")
        assert callable(getattr(KnowledgeGraphRepository, "get_subgraph"))

    @pytest.mark.unit
    def test_knowledge_graph_repository_has_save_method(self) -> None:
        """Test KnowledgeGraphRepository has save method for persistence."""
        assert hasattr(KnowledgeGraphRepository, "save")
        assert callable(getattr(KnowledgeGraphRepository, "save"))

    @pytest.mark.unit
    def test_knowledge_graph_repository_has_load_method(self) -> None:
        """Test KnowledgeGraphRepository has load method for persistence."""
        assert hasattr(KnowledgeGraphRepository, "load")
        assert callable(getattr(KnowledgeGraphRepository, "load"))

    @pytest.mark.unit
    def test_knowledge_graph_repository_has_clear_method(self) -> None:
        """Test KnowledgeGraphRepository has clear method."""
        assert hasattr(KnowledgeGraphRepository, "clear")
        assert callable(getattr(KnowledgeGraphRepository, "clear"))
