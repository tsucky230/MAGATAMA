"""
Storage Adapters - Graph persistence.

ADR-004: NetworkX + SQLite storage
REQ-KGC-003: Graph storage
"""

from magatama_core.infrastructure.storage.comp_history_writer import append_history_record
from magatama_core.infrastructure.storage.comp_index_reader import (
    CompIndexData,
    CompIndexNotFoundError,
    CompIndexReader,
    CompSnapshot,
    read_comp_snapshot,
    resolve_db_path,
)
from magatama_core.infrastructure.storage.comp_session_reader import (
    CompSessionData,
    CompSessionReader,
    CompSessionsNotFoundError,
    SessionRecord,
    resolve_comp_dir,
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
    "CompSessionData",
    "CompSnapshot",
    "CompSessionReader",
    "CompSessionsNotFoundError",
    "SessionRecord",
    "InMemoryEntityRepository",
    "InMemoryRelationshipRepository",
    "NetworkXKnowledgeGraph",
    "SQLiteEntityRepository",
    "SQLiteKnowledgeGraph",
    "SQLiteRelationshipRepository",
    "append_history_record",
    "read_comp_snapshot",
    "resolve_comp_dir",
    "resolve_db_path",
]
