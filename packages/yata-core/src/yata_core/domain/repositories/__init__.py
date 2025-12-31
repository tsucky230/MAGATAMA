"""
Repository Interfaces - Ports for data access.

ADR-001: Clean Architecture with Ports & Adapters
REQ-KGC-003: Graph storage abstraction
REQ-KGC-007: Data persistence abstraction
"""

from yata_core.domain.repositories.entity_repository import EntityRepository
from yata_core.domain.repositories.relationship_repository import RelationshipRepository
from yata_core.domain.repositories.knowledge_graph_repository import KnowledgeGraphRepository

__all__ = [
    "EntityRepository",
    "RelationshipRepository",
    "KnowledgeGraphRepository",
]
