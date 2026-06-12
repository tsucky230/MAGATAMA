"""
Storage Adapters - Graph persistence.

ADR-004: NetworkX + SQLite storage
REQ-KGC-003: Graph storage
"""
from yata_core.infrastructure.storage.in_memory_repository import (
    InMemoryEntityRepository,
    InMemoryRelationshipRepository,
)
from yata_core.infrastructure.storage.networkx_graph import NetworkXKnowledgeGraph
from yata_core.infrastructure.storage.sqlite_storage import (
    SQLiteKnowledgeGraph,
    SQLiteEntityRepository,
    SQLiteRelationshipRepository,
)
from yata_core.infrastructure.storage.comp_index_reader import (
    CompIndexReader,
    CompIndexData,
    CompIndexNotFoundError,
    resolve_db_path,
)

__all__ = [
    "InMemoryEntityRepository",
    "InMemoryRelationshipRepository",
    "NetworkXKnowledgeGraph",
    "SQLiteKnowledgeGraph",
    "SQLiteEntityRepository",
    "SQLiteRelationshipRepository",
    "CompIndexReader",
    "CompIndexData",
    "CompIndexNotFoundError",
    "resolve_db_path",
]