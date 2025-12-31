"""
SQLite Knowledge Graph Storage Implementation

REQ-KGC-003: Persistent graph storage using SQLite.
TASK-015: SQLite storage implementation.

Provides persistent storage for knowledge graph with:
- Efficient querying and indexing
- Transaction support
- Incremental updates
- JSON export capability
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Sequence, Tuple

import networkx as nx

from yata_core.domain.entities.base import Entity, EntityType
from yata_core.domain.entities.code_entities import (
    ClassEntity,
    EnumEntity,
    FunctionEntity,
    InterfaceEntity,
    MethodEntity,
    ModuleEntity,
    TypeEntity,
)
from yata_core.domain.entities.relationships import Relationship, RelationshipType
from yata_core.domain.repositories.entity_repository import EntityRepository
from yata_core.domain.repositories.knowledge_graph_repository import KnowledgeGraphRepository
from yata_core.domain.repositories.relationship_repository import RelationshipRepository
from yata_core.domain.value_objects.ids import EntityId
from yata_core.domain.value_objects.location import Location


# SQL Schema
SCHEMA = """
-- Entities table
CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    line INTEGER NOT NULL,
    column INTEGER,
    docstring TEXT,
    scope TEXT,
    extra_data TEXT,  -- JSON for type-specific fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Relationships table
CREATE TABLE IF NOT EXISTS relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    type TEXT NOT NULL,
    metadata TEXT,  -- JSON for additional data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES entities(id) ON DELETE CASCADE
);

-- File hashes for incremental updates
CREATE TABLE IF NOT EXISTS file_hashes (
    file_path TEXT PRIMARY KEY,
    hash_value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type);
CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
CREATE INDEX IF NOT EXISTS idx_entities_file ON entities(file_path);
CREATE INDEX IF NOT EXISTS idx_relationships_source ON relationships(source_id);
CREATE INDEX IF NOT EXISTS idx_relationships_target ON relationships(target_id);
CREATE INDEX IF NOT EXISTS idx_relationships_type ON relationships(type);
"""


class SQLiteEntityRepository(EntityRepository):
    """SQLite-backed entity repository."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        """Initialize with database connection."""
        self._conn = connection

    def add(self, entity: Entity) -> None:
        """Add an entity to the repository."""
        extra_data = self._entity_to_extra_data(entity)
        self._conn.execute(
            """
            INSERT INTO entities (id, name, type, file_path, line, column, docstring, scope, extra_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entity.id.value,
                entity.name,
                entity.type.value,
                entity.location.file,
                entity.location.line,
                entity.location.column,
                entity.docstring,
                getattr(entity, "scope", None),
                json.dumps(extra_data) if extra_data else None,
            ),
        )

    def get(self, entity_id: EntityId) -> Entity | None:
        """Retrieve an entity by its ID."""
        cursor = self._conn.execute(
            "SELECT * FROM entities WHERE id = ?",
            (entity_id.value,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_entity(row)

    def get_by_type(self, entity_type: EntityType) -> Sequence[Entity]:
        """Get all entities of a specific type."""
        cursor = self._conn.execute(
            "SELECT * FROM entities WHERE type = ?",
            (entity_type.value,),
        )
        return [self._row_to_entity(row) for row in cursor.fetchall()]

    def get_by_name(self, name: str) -> Sequence[Entity]:
        """Get all entities with a specific name."""
        cursor = self._conn.execute(
            "SELECT * FROM entities WHERE name = ?",
            (name,),
        )
        return [self._row_to_entity(row) for row in cursor.fetchall()]

    def update(self, entity: Entity) -> None:
        """Update an existing entity."""
        extra_data = self._entity_to_extra_data(entity)
        self._conn.execute(
            """
            UPDATE entities
            SET name = ?, type = ?, file_path = ?, line = ?, column = ?,
                docstring = ?, scope = ?, extra_data = ?
            WHERE id = ?
            """,
            (
                entity.name,
                entity.type.value,
                entity.location.file,
                entity.location.line,
                entity.location.column,
                entity.docstring,
                getattr(entity, "scope", None),
                json.dumps(extra_data) if extra_data else None,
                entity.id.value,
            ),
        )

    def delete(self, entity_id: EntityId) -> bool:
        """Delete an entity by its ID."""
        cursor = self._conn.execute(
            "DELETE FROM entities WHERE id = ?",
            (entity_id.value,),
        )
        return cursor.rowcount > 0

    def all(self) -> Sequence[Entity]:
        """Get all entities in the repository."""
        cursor = self._conn.execute("SELECT * FROM entities")
        return [self._row_to_entity(row) for row in cursor.fetchall()]

    def count(self) -> int:
        """Get the total number of entities."""
        cursor = self._conn.execute("SELECT COUNT(*) FROM entities")
        return cursor.fetchone()[0]

    def _entity_to_extra_data(self, entity: Entity) -> dict[str, Any] | None:
        """Extract type-specific fields to extra_data."""
        extra: dict[str, Any] = {}

        if isinstance(entity, FunctionEntity):
            extra["parameters"] = entity.parameters
            extra["return_type"] = entity.return_type
            extra["decorators"] = entity.decorators
            extra["is_async"] = entity.is_async
        elif isinstance(entity, ClassEntity):
            extra["bases"] = entity.bases
            extra["decorators"] = entity.decorators
        elif isinstance(entity, MethodEntity):
            extra["class_id"] = entity.class_id.value
            extra["parameters"] = entity.parameters
            extra["return_type"] = entity.return_type
            extra["decorators"] = entity.decorators
            extra["is_async"] = entity.is_async
        elif isinstance(entity, ModuleEntity):
            extra["exports"] = entity.exports
        elif isinstance(entity, InterfaceEntity):
            extra["method_signatures"] = entity.method_signatures
            extra["extends"] = entity.extends
        elif isinstance(entity, TypeEntity):
            extra["definition"] = entity.definition
        elif isinstance(entity, EnumEntity):
            extra["variants"] = entity.variants

        return extra if extra else None

    def _row_to_entity(self, row: tuple) -> Entity:
        """Convert database row to entity."""
        (
            entity_id,
            name,
            entity_type,
            file_path,
            line,
            column,
            docstring,
            scope,
            extra_data_json,
            _created_at,
        ) = row

        location = Location(file=file_path, line=line, column=column)
        extra = json.loads(extra_data_json) if extra_data_json else {}
        etype = EntityType(entity_type)

        base_args = {
            "id": EntityId(value=entity_id),
            "name": name,
            "location": location,
            "docstring": docstring,
        }

        # Add scope if supported
        if scope is not None:
            base_args["scope"] = scope

        if etype == EntityType.FUNCTION:
            return FunctionEntity(
                **base_args,
                parameters=extra.get("parameters", []),
                return_type=extra.get("return_type"),
                decorators=extra.get("decorators", []),
                is_async=extra.get("is_async", False),
            )
        elif etype == EntityType.CLASS:
            return ClassEntity(
                **base_args,
                bases=extra.get("bases", []),
                decorators=extra.get("decorators", []),
            )
        elif etype == EntityType.METHOD:
            return MethodEntity(
                **base_args,
                class_id=EntityId(value=extra["class_id"]),
                parameters=extra.get("parameters", []),
                return_type=extra.get("return_type"),
                decorators=extra.get("decorators", []),
                is_async=extra.get("is_async", False),
            )
        elif etype == EntityType.MODULE:
            return ModuleEntity(
                **base_args,
                exports=extra.get("exports", []),
            )
        elif etype == EntityType.INTERFACE:
            return InterfaceEntity(
                **base_args,
                method_signatures=extra.get("method_signatures", []),
                extends=extra.get("extends", []),
            )
        elif etype == EntityType.TYPE:
            return TypeEntity(
                **base_args,
                definition=extra.get("definition"),
            )
        elif etype == EntityType.ENUM:
            return EnumEntity(
                **base_args,
                variants=extra.get("variants", []),
            )
        else:
            # Generic entity - shouldn't happen but handle gracefully
            raise ValueError(f"Unknown entity type: {etype}")


class SQLiteRelationshipRepository(RelationshipRepository):
    """SQLite-backed relationship repository."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        """Initialize with database connection."""
        self._conn = connection

    def add(self, relationship: Relationship) -> None:
        """Add a relationship to the repository."""
        metadata = json.dumps(relationship.metadata) if relationship.metadata else None
        self._conn.execute(
            """
            INSERT INTO relationships (source_id, target_id, type, metadata)
            VALUES (?, ?, ?, ?)
            """,
            (
                relationship.source_id.value,
                relationship.target_id.value,
                relationship.type.value,
                metadata,
            ),
        )

    def get_outgoing(self, source_id: EntityId) -> Sequence[Relationship]:
        """Get all relationships originating from an entity."""
        cursor = self._conn.execute(
            "SELECT source_id, target_id, type, metadata FROM relationships WHERE source_id = ?",
            (source_id.value,),
        )
        return [self._row_to_relationship(row) for row in cursor.fetchall()]

    def get_incoming(self, target_id: EntityId) -> Sequence[Relationship]:
        """Get all relationships pointing to an entity."""
        cursor = self._conn.execute(
            "SELECT source_id, target_id, type, metadata FROM relationships WHERE target_id = ?",
            (target_id.value,),
        )
        return [self._row_to_relationship(row) for row in cursor.fetchall()]

    def get_by_type(self, rel_type: RelationshipType) -> Sequence[Relationship]:
        """Get all relationships of a specific type."""
        cursor = self._conn.execute(
            "SELECT source_id, target_id, type, metadata FROM relationships WHERE type = ?",
            (rel_type.value,),
        )
        return [self._row_to_relationship(row) for row in cursor.fetchall()]

    def delete(
        self,
        source_id: EntityId | None = None,
        target_id: EntityId | None = None,
        rel_type: RelationshipType | None = None,
    ) -> int:
        """Delete relationships matching criteria."""
        conditions: list[str] = []
        params: list[str] = []

        if source_id is not None:
            conditions.append("source_id = ?")
            params.append(source_id.value)
        if target_id is not None:
            conditions.append("target_id = ?")
            params.append(target_id.value)
        if rel_type is not None:
            conditions.append("type = ?")
            params.append(rel_type.value)

        if not conditions:
            return 0

        query = f"DELETE FROM relationships WHERE {' AND '.join(conditions)}"
        cursor = self._conn.execute(query, params)
        return cursor.rowcount

    def all(self) -> Sequence[Relationship]:
        """Get all relationships in the repository."""
        cursor = self._conn.execute(
            "SELECT source_id, target_id, type, metadata FROM relationships"
        )
        return [self._row_to_relationship(row) for row in cursor.fetchall()]

    def count(self) -> int:
        """Get the total number of relationships."""
        cursor = self._conn.execute("SELECT COUNT(*) FROM relationships")
        return cursor.fetchone()[0]

    def _row_to_relationship(self, row: tuple) -> Relationship:
        """Convert database row to relationship."""
        source_id, target_id, rel_type, metadata_json = row
        metadata = json.loads(metadata_json) if metadata_json else {}

        return Relationship(
            source_id=EntityId(value=source_id),
            target_id=EntityId(value=target_id),
            type=RelationshipType(rel_type),
            metadata=metadata,
        )


class SQLiteKnowledgeGraph(KnowledgeGraphRepository):
    """
    SQLite-backed knowledge graph implementation.

    Provides persistent storage with transaction support
    and efficient querying via indexes.

    TASK-015 Implementation.
    """

    def __init__(self, db_path: Path | str = ":memory:") -> None:
        """
        Initialize SQLite knowledge graph.

        Args:
            db_path: Path to SQLite database file, or ":memory:" for in-memory
        """
        self._db_path = Path(db_path) if isinstance(db_path, str) and db_path != ":memory:" else db_path
        self._conn: sqlite3.Connection | None = None
        self._entity_repo: SQLiteEntityRepository | None = None
        self._relationship_repo: SQLiteRelationshipRepository | None = None
        self._graph: nx.DiGraph = nx.DiGraph()  # In-memory graph for traversal

        # Initialize database
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database connection and schema."""
        if isinstance(self._db_path, Path):
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        else:
            self._conn = sqlite3.connect(":memory:", check_same_thread=False)

        # Enable foreign keys
        self._conn.execute("PRAGMA foreign_keys = ON")

        # Create schema
        self._conn.executescript(SCHEMA)
        self._conn.commit()

        # Initialize repositories
        self._entity_repo = SQLiteEntityRepository(self._conn)
        self._relationship_repo = SQLiteRelationshipRepository(self._conn)

        # Build in-memory graph from existing data
        self._rebuild_graph()

    def _rebuild_graph(self) -> None:
        """Rebuild NetworkX graph from database."""
        self._graph.clear()

        # Add nodes
        for entity in self._entity_repo.all():
            self._graph.add_node(entity.id.value)

        # Add edges
        for rel in self._relationship_repo.all():
            self._graph.add_edge(rel.source_id.value, rel.target_id.value)

    @property
    def entities(self) -> EntityRepository:
        """Access the entity repository."""
        return _SyncedSQLiteEntityRepository(self._entity_repo, self._graph, self._conn)

    @property
    def relationships(self) -> RelationshipRepository:
        """Access the relationship repository."""
        return _SyncedSQLiteRelationshipRepository(self._relationship_repo, self._graph, self._conn)

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Context manager for transactions."""
        try:
            yield
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    def find_path(
        self,
        source_id: EntityId,
        target_id: EntityId,
        max_depth: int = 10,
    ) -> Sequence[EntityId] | None:
        """Find a path between two entities."""
        try:
            path = nx.shortest_path(
                self._graph.to_undirected(),
                source=source_id.value,
                target=target_id.value,
            )
            if len(path) - 1 > max_depth:
                return None
            return [EntityId(value=node_id) for node_id in path]
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def get_neighbors(
        self,
        entity_id: EntityId,
        depth: int = 1,
    ) -> Sequence[Entity]:
        """Get all entities within N hops."""
        if entity_id.value not in self._graph:
            return []

        visited: set[str] = set()
        current_level = {entity_id.value}

        for _ in range(depth):
            next_level: set[str] = set()
            for node in current_level:
                neighbors = set(self._graph.predecessors(node)) | set(self._graph.successors(node))
                for neighbor in neighbors:
                    if neighbor not in visited and neighbor != entity_id.value:
                        next_level.add(neighbor)
                        visited.add(neighbor)
            current_level = next_level

        entities: list[Entity] = []
        for node_id in visited:
            entity = self._entity_repo.get(EntityId(value=node_id))
            if entity:
                entities.append(entity)

        return entities

    def get_subgraph(
        self,
        entity_ids: Sequence[EntityId],
    ) -> Tuple[Sequence[Entity], Sequence[Relationship]]:
        """Extract a subgraph containing specified entities."""
        entities: list[Entity] = []
        node_ids = {eid.value for eid in entity_ids}

        for eid in entity_ids:
            entity = self._entity_repo.get(eid)
            if entity:
                entities.append(entity)

        relationships: list[Relationship] = []
        for rel in self._relationship_repo.all():
            if rel.source_id.value in node_ids and rel.target_id.value in node_ids:
                relationships.append(rel)

        return entities, relationships

    def save(self, path: Path) -> None:
        """
        Export the knowledge graph to JSON file.

        Note: For SQLite storage, data is already persisted.
        This method exports to JSON for compatibility.
        """
        data = {
            "entities": [self._entity_to_dict(e) for e in self._entity_repo.all()],
            "relationships": [self._rel_to_dict(r) for r in self._relationship_repo.all()],
            "file_hashes": dict(self._get_all_file_hashes()),
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load(self, path: Path) -> None:
        """
        Import knowledge graph from JSON file.

        Clears existing data and loads from JSON.
        """
        self.clear()

        data = json.loads(path.read_text(encoding="utf-8"))

        with self.transaction():
            # Load file hashes first
            for file_path, hash_value in data.get("file_hashes", {}).items():
                self.set_file_hash(file_path, hash_value)

            # Load entities
            for entity_data in data.get("entities", []):
                entity = self._dict_to_entity(entity_data)
                self._entity_repo.add(entity)
                self._graph.add_node(entity.id.value)

            # Load relationships
            for rel_data in data.get("relationships", []):
                rel = self._dict_to_relationship(rel_data)
                self._relationship_repo.add(rel)
                self._graph.add_edge(rel.source_id.value, rel.target_id.value)

    def clear(self) -> None:
        """Remove all entities and relationships."""
        self._conn.execute("DELETE FROM relationships")
        self._conn.execute("DELETE FROM entities")
        self._conn.execute("DELETE FROM file_hashes")
        self._conn.commit()
        self._graph.clear()

    def remove_file(self, file_path: str) -> int:
        """Remove all entities and relationships from a specific file."""
        # Get entity IDs from this file
        cursor = self._conn.execute(
            "SELECT id FROM entities WHERE file_path = ?",
            (file_path,),
        )
        entity_ids = [row[0] for row in cursor.fetchall()]

        if not entity_ids:
            # Still remove file hash
            self._conn.execute("DELETE FROM file_hashes WHERE file_path = ?", (file_path,))
            self._conn.commit()
            return 0

        # Delete relationships involving these entities
        placeholders = ",".join("?" * len(entity_ids))
        self._conn.execute(
            f"DELETE FROM relationships WHERE source_id IN ({placeholders}) OR target_id IN ({placeholders})",
            entity_ids + entity_ids,
        )

        # Delete entities
        self._conn.execute(
            f"DELETE FROM entities WHERE id IN ({placeholders})",
            entity_ids,
        )

        # Delete file hash
        self._conn.execute("DELETE FROM file_hashes WHERE file_path = ?", (file_path,))

        self._conn.commit()

        # Update graph
        for entity_id in entity_ids:
            if entity_id in self._graph:
                self._graph.remove_node(entity_id)

        return len(entity_ids)

    def get_file_hash(self, file_path: str) -> str | None:
        """Get the stored hash for a file."""
        cursor = self._conn.execute(
            "SELECT hash_value FROM file_hashes WHERE file_path = ?",
            (file_path,),
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def set_file_hash(self, file_path: str, hash_value: str) -> None:
        """Store the hash for a file."""
        self._conn.execute(
            """
            INSERT INTO file_hashes (file_path, hash_value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(file_path) DO UPDATE SET
                hash_value = excluded.hash_value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (file_path, hash_value),
        )
        self._conn.commit()

    def get_tracked_files(self) -> Sequence[str]:
        """Get all tracked file paths."""
        cursor = self._conn.execute("SELECT file_path FROM file_hashes")
        return [row[0] for row in cursor.fetchall()]

    def _get_all_file_hashes(self) -> Sequence[tuple[str, str]]:
        """Get all file hashes as (path, hash) pairs."""
        cursor = self._conn.execute("SELECT file_path, hash_value FROM file_hashes")
        return cursor.fetchall()

    def export_json(self, path: Path) -> None:
        """Export to JSON format (alias for save)."""
        self.save(path)

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the knowledge graph."""
        entity_count = self._entity_repo.count()
        rel_count = self._relationship_repo.count()
        file_count = len(self.get_tracked_files())

        # Entity type breakdown
        type_counts = {}
        for etype in EntityType:
            count = len(self._entity_repo.get_by_type(etype))
            if count > 0:
                type_counts[etype.value] = count

        return {
            "total_entities": entity_count,
            "total_relationships": rel_count,
            "tracked_files": file_count,
            "entity_types": type_counts,
        }

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "SQLiteKnowledgeGraph":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()

    # Serialization helpers
    def _entity_to_dict(self, entity: Entity) -> dict[str, Any]:
        """Convert entity to dictionary."""
        base = {
            "id": entity.id.value,
            "name": entity.name,
            "type": entity.type.value,
            "location": {
                "file": entity.location.file,
                "line": entity.location.line,
                "column": entity.location.column,
            },
            "docstring": entity.docstring,
        }

        if hasattr(entity, "scope"):
            base["scope"] = entity.scope

        if isinstance(entity, FunctionEntity):
            base["parameters"] = entity.parameters
            base["return_type"] = entity.return_type
            base["decorators"] = entity.decorators
            base["is_async"] = entity.is_async
        elif isinstance(entity, ClassEntity):
            base["bases"] = entity.bases
            base["decorators"] = entity.decorators
        elif isinstance(entity, MethodEntity):
            base["class_id"] = entity.class_id.value
            base["parameters"] = entity.parameters
            base["return_type"] = entity.return_type
            base["decorators"] = entity.decorators
            base["is_async"] = entity.is_async
        elif isinstance(entity, ModuleEntity):
            base["exports"] = entity.exports
        elif isinstance(entity, InterfaceEntity):
            base["method_signatures"] = entity.method_signatures
            base["extends"] = entity.extends
        elif isinstance(entity, TypeEntity):
            base["definition"] = entity.definition
        elif isinstance(entity, EnumEntity):
            base["variants"] = entity.variants

        return base

    def _rel_to_dict(self, rel: Relationship) -> dict[str, Any]:
        """Convert relationship to dictionary."""
        return {
            "source_id": rel.source_id.value,
            "target_id": rel.target_id.value,
            "type": rel.type.value,
            "metadata": rel.metadata,
        }

    def _dict_to_entity(self, data: dict[str, Any]) -> Entity:
        """Convert dictionary to entity."""
        location = Location(
            file=data["location"]["file"],
            line=data["location"]["line"],
            column=data["location"].get("column"),
        )

        base_args = {
            "id": EntityId(value=data["id"]),
            "name": data["name"],
            "location": location,
            "docstring": data.get("docstring"),
        }

        if "scope" in data:
            base_args["scope"] = data["scope"]

        etype = EntityType(data["type"])

        if etype == EntityType.FUNCTION:
            return FunctionEntity(
                **base_args,
                parameters=data.get("parameters", []),
                return_type=data.get("return_type"),
                decorators=data.get("decorators", []),
                is_async=data.get("is_async", False),
            )
        elif etype == EntityType.CLASS:
            return ClassEntity(
                **base_args,
                bases=data.get("bases", []),
                decorators=data.get("decorators", []),
            )
        elif etype == EntityType.METHOD:
            return MethodEntity(
                **base_args,
                class_id=EntityId(value=data["class_id"]),
                parameters=data.get("parameters", []),
                return_type=data.get("return_type"),
                decorators=data.get("decorators", []),
                is_async=data.get("is_async", False),
            )
        elif etype == EntityType.MODULE:
            return ModuleEntity(
                **base_args,
                exports=data.get("exports", []),
            )
        elif etype == EntityType.INTERFACE:
            return InterfaceEntity(
                **base_args,
                method_signatures=data.get("method_signatures", []),
                extends=data.get("extends", []),
            )
        elif etype == EntityType.TYPE:
            return TypeEntity(
                **base_args,
                definition=data.get("definition"),
            )
        elif etype == EntityType.ENUM:
            return EnumEntity(
                **base_args,
                variants=data.get("variants", []),
            )
        else:
            raise ValueError(f"Unknown entity type: {etype}")

    def _dict_to_relationship(self, data: dict[str, Any]) -> Relationship:
        """Convert dictionary to relationship."""
        return Relationship(
            source_id=EntityId(value=data["source_id"]),
            target_id=EntityId(value=data["target_id"]),
            type=RelationshipType(data["type"]),
            metadata=data.get("metadata"),
        )


class _SyncedSQLiteEntityRepository(EntityRepository):
    """Wrapper that syncs entity operations with NetworkX graph."""

    def __init__(
        self,
        repo: SQLiteEntityRepository,
        graph: nx.DiGraph,
        conn: sqlite3.Connection,
    ) -> None:
        self._repo = repo
        self._graph = graph
        self._conn = conn

    def add(self, entity: Entity) -> None:
        self._repo.add(entity)
        self._graph.add_node(entity.id.value)
        self._conn.commit()

    def get(self, entity_id: EntityId) -> Entity | None:
        return self._repo.get(entity_id)

    def get_by_type(self, entity_type: EntityType) -> Sequence[Entity]:
        return self._repo.get_by_type(entity_type)

    def get_by_name(self, name: str) -> Sequence[Entity]:
        return self._repo.get_by_name(name)

    def update(self, entity: Entity) -> None:
        self._repo.update(entity)
        self._conn.commit()

    def delete(self, entity_id: EntityId) -> bool:
        result = self._repo.delete(entity_id)
        if result and entity_id.value in self._graph:
            self._graph.remove_node(entity_id.value)
        self._conn.commit()
        return result

    def all(self) -> Sequence[Entity]:
        return self._repo.all()

    def count(self) -> int:
        return self._repo.count()


class _SyncedSQLiteRelationshipRepository(RelationshipRepository):
    """Wrapper that syncs relationship operations with NetworkX graph."""

    def __init__(
        self,
        repo: SQLiteRelationshipRepository,
        graph: nx.DiGraph,
        conn: sqlite3.Connection,
    ) -> None:
        self._repo = repo
        self._graph = graph
        self._conn = conn

    def add(self, relationship: Relationship) -> None:
        self._repo.add(relationship)
        self._graph.add_edge(relationship.source_id.value, relationship.target_id.value)
        self._conn.commit()

    def get_outgoing(self, source_id: EntityId) -> Sequence[Relationship]:
        return self._repo.get_outgoing(source_id)

    def get_incoming(self, target_id: EntityId) -> Sequence[Relationship]:
        return self._repo.get_incoming(target_id)

    def get_by_type(self, rel_type: RelationshipType) -> Sequence[Relationship]:
        return self._repo.get_by_type(rel_type)

    def delete(
        self,
        source_id: EntityId | None = None,
        target_id: EntityId | None = None,
        rel_type: RelationshipType | None = None,
    ) -> int:
        # Get relationships before deletion to update graph
        to_remove = []
        for rel in self._repo.all():
            matches = True
            if source_id is not None and rel.source_id != source_id:
                matches = False
            if target_id is not None and rel.target_id != target_id:
                matches = False
            if rel_type is not None and rel.type != rel_type:
                matches = False
            if matches:
                to_remove.append(rel)

        count = self._repo.delete(source_id, target_id, rel_type)

        for rel in to_remove:
            if self._graph.has_edge(rel.source_id.value, rel.target_id.value):
                self._graph.remove_edge(rel.source_id.value, rel.target_id.value)

        self._conn.commit()
        return count

    def all(self) -> Sequence[Relationship]:
        return self._repo.all()

    def count(self) -> int:
        return self._repo.count()
