"""
Storage Adapters - Graph persistence.

ADR-004: NetworkX + SQLite storage
REQ-KGC-003: Graph storage
"""

from magatama_core.infrastructure.storage.comp_index_reader import (
    CompIndexData,
    CompIndexNotFoundError,
    CompIndexReader,
    resolve_db_path,
)
from magatama_core.infrastructure.storage.in_memory_repository import (
    InMemoryEntityRepository,
    InMemoryRelationshipRepository,
)
from magatama_core.infrastructure.storage.networkx_graph import NetworkXKnowledgeGraph
from magatama_core.infrastructure.storage.sqlite_storage import (
    SQLiteEntityRepository,
    SQLiteKnowledgeGraph,
    SQLiteRelationshipRepository,
)

__all__ = [
    "CompIndexData",
    "CompIndexNotFoundError",
    "CompIndexReader",
    "InMemoryEntityRepository",
    "InMemoryRelationshipRepository",
    "NetworkXKnowledgeGraph",
    "SQLiteEntityRepository",
    "SQLiteKnowledgeGraph",
    "SQLiteRelationshipRepository",
    "resolve_db_path",
]
