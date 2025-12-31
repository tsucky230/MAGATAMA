"""
NetworkX Knowledge Graph Implementation

REQ-KGC-003: Graph storage using NetworkX.
REQ-CTX-002: Related entity retrieval via graph traversal.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence, Tuple

import networkx as nx

from yata_core.domain.entities.base import Entity, EntityType
from yata_core.domain.entities.code_entities import (
    FunctionEntity,
    ClassEntity,
    MethodEntity,
    ModuleEntity,
    TypeEntity,
)
from yata_core.domain.entities.relationships import Relationship, RelationshipType
from yata_core.domain.repositories.knowledge_graph_repository import KnowledgeGraphRepository
from yata_core.domain.repositories.entity_repository import EntityRepository
from yata_core.domain.repositories.relationship_repository import RelationshipRepository
from yata_core.domain.value_objects.ids import EntityId
from yata_core.domain.value_objects.location import Location
from yata_core.infrastructure.storage.in_memory_repository import (
    InMemoryEntityRepository,
    InMemoryRelationshipRepository,
)


class NetworkXKnowledgeGraph(KnowledgeGraphRepository):
    """
    Knowledge graph implementation using NetworkX.
    
    Combines entity/relationship repositories with graph
    traversal capabilities for context generation.
    """

    def __init__(self) -> None:
        """Initialize the knowledge graph."""
        self._entity_repo = InMemoryEntityRepository()
        self._relationship_repo = InMemoryRelationshipRepository()
        self._graph: nx.DiGraph = nx.DiGraph()
        self._file_hashes: dict[str, str] = {}  # file_path -> content_hash

    @property
    def entities(self) -> EntityRepository:
        """Access the entity repository."""
        return self._entity_repo

    @property
    def relationships(self) -> RelationshipRepository:
        """Access the relationship repository."""
        return _SyncedRelationshipRepository(self._relationship_repo, self._graph)

    def find_path(
        self,
        source_id: EntityId,
        target_id: EntityId,
        max_depth: int = 10,
    ) -> Sequence[EntityId] | None:
        """Find a path between two entities."""
        try:
            # NetworkX shortest_path with cutoff
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

        # BFS to find all nodes within depth
        visited: set[str] = set()
        current_level = {entity_id.value}
        
        for _ in range(depth):
            next_level: set[str] = set()
            for node in current_level:
                # Get both predecessors and successors (undirected neighbors)
                neighbors = set(self._graph.predecessors(node)) | set(self._graph.successors(node))
                for neighbor in neighbors:
                    if neighbor not in visited and neighbor != entity_id.value:
                        next_level.add(neighbor)
                        visited.add(neighbor)
            current_level = next_level

        # Convert to entities
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
        # Get entities
        entities: list[Entity] = []
        node_ids = {eid.value for eid in entity_ids}
        
        for eid in entity_ids:
            entity = self._entity_repo.get(eid)
            if entity:
                entities.append(entity)
        
        # Get relationships between these entities
        relationships: list[Relationship] = []
        for rel in self._relationship_repo.all():
            if rel.source_id.value in node_ids and rel.target_id.value in node_ids:
                relationships.append(rel)
        
        return entities, relationships

    def save(self, path: Path) -> None:
        """Persist the knowledge graph to storage."""
        data = {
            "entities": [self._entity_to_dict(e) for e in self._entity_repo.all()],
            "relationships": [self._relationship_to_dict(r) for r in self._relationship_repo.all()],
            "file_hashes": self._file_hashes,
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load(self, path: Path) -> None:
        """Load the knowledge graph from storage."""
        self.clear()
        
        data = json.loads(path.read_text(encoding="utf-8"))
        
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
        
        # Load file hashes
        self._file_hashes = data.get("file_hashes", {})

    def clear(self) -> None:
        """Remove all entities and relationships."""
        self._entity_repo = InMemoryEntityRepository()
        self._relationship_repo = InMemoryRelationshipRepository()
        self._graph.clear()
        self._file_hashes.clear()

    def remove_file(self, file_path: str) -> int:
        """
        Remove all entities and relationships from a specific file.
        
        Used for incremental updates when a file is modified or deleted.
        """
        # Find all entities from this file
        entities_to_remove: list[EntityId] = []
        for entity in self._entity_repo.all():
            if entity.location.file == file_path:
                entities_to_remove.append(entity.id)
        
        # Remove relationships involving these entities
        for entity_id in entities_to_remove:
            # Remove edges from graph
            if entity_id.value in self._graph:
                # Get all edges involving this node
                edges_to_remove = list(self._graph.in_edges(entity_id.value)) + \
                                  list(self._graph.out_edges(entity_id.value))
                self._graph.remove_edges_from(edges_to_remove)
                self._graph.remove_node(entity_id.value)
            
            # Remove from relationship repository
            self._relationship_repo.delete(source_id=entity_id)
            self._relationship_repo.delete(target_id=entity_id)
            
            # Remove entity
            self._entity_repo.delete(entity_id)
        
        # Remove file hash
        if file_path in self._file_hashes:
            del self._file_hashes[file_path]
        
        return len(entities_to_remove)

    def get_file_hash(self, file_path: str) -> str | None:
        """Get the stored hash for a file."""
        return self._file_hashes.get(file_path)

    def set_file_hash(self, file_path: str, hash_value: str) -> None:
        """Store the hash for a file."""
        self._file_hashes[file_path] = hash_value

    def get_tracked_files(self) -> Sequence[str]:
        """Get all tracked file paths."""
        return list(self._file_hashes.keys())

    def _entity_to_dict(self, entity: Entity) -> dict[str, Any]:
        """Convert entity to dictionary for serialization."""
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
        
        return base

    def _dict_to_entity(self, data: dict[str, Any]) -> Entity:
        """Convert dictionary to entity."""
        entity_type = EntityType(data["type"])
        location = Location(
            file=data["location"]["file"],
            line=data["location"]["line"],
            column=data["location"].get("column", 0),
        )
        
        if entity_type == EntityType.FUNCTION:
            return FunctionEntity(
                id=EntityId(value=data["id"]),
                name=data["name"],
                location=location,
                docstring=data.get("docstring"),
                parameters=[(p[0], p[1]) for p in data.get("parameters", [])],
                return_type=data.get("return_type"),
                decorators=data.get("decorators", []),
                is_async=data.get("is_async", False),
            )
        elif entity_type == EntityType.CLASS:
            return ClassEntity(
                id=EntityId(value=data["id"]),
                name=data["name"],
                location=location,
                docstring=data.get("docstring"),
                bases=data.get("bases", []),
                decorators=data.get("decorators", []),
            )
        elif entity_type == EntityType.METHOD:
            return MethodEntity(
                id=EntityId(value=data["id"]),
                name=data["name"],
                location=location,
                docstring=data.get("docstring"),
                class_id=EntityId(value=data["class_id"]),
                parameters=[(p[0], p[1]) for p in data.get("parameters", [])],
                return_type=data.get("return_type"),
                decorators=data.get("decorators", []),
                is_async=data.get("is_async", False),
            )
        elif entity_type == EntityType.MODULE:
            return ModuleEntity(
                id=EntityId(value=data["id"]),
                name=data["name"],
                location=location,
                docstring=data.get("docstring"),
                exports=data.get("exports", []),
            )
        else:
            # Default to base Entity for unknown types
            return Entity(
                id=EntityId(value=data["id"]),
                name=data["name"],
                type=entity_type,
                location=location,
                docstring=data.get("docstring"),
            )

    def _relationship_to_dict(self, rel: Relationship) -> dict[str, Any]:
        """Convert relationship to dictionary."""
        return {
            "source_id": rel.source_id.value,
            "target_id": rel.target_id.value,
            "type": rel.type.value,
            "metadata": rel.metadata,
        }

    def _dict_to_relationship(self, data: dict[str, Any]) -> Relationship:
        """Convert dictionary to relationship."""
        return Relationship(
            source_id=EntityId(value=data["source_id"]),
            target_id=EntityId(value=data["target_id"]),
            type=RelationshipType(data["type"]),
            metadata=data.get("metadata", {}),
        )


class _SyncedRelationshipRepository(RelationshipRepository):
    """
    Wrapper that syncs relationship additions to the NetworkX graph.
    """

    def __init__(
        self, 
        inner: InMemoryRelationshipRepository, 
        graph: nx.DiGraph
    ) -> None:
        self._inner = inner
        self._graph = graph

    def add(self, relationship: Relationship) -> None:
        """Add relationship and sync to graph."""
        self._inner.add(relationship)
        self._graph.add_edge(
            relationship.source_id.value,
            relationship.target_id.value,
        )

    def get_outgoing(self, source_id: EntityId) -> Sequence[Relationship]:
        return self._inner.get_outgoing(source_id)

    def get_incoming(self, target_id: EntityId) -> Sequence[Relationship]:
        return self._inner.get_incoming(target_id)

    def get_by_type(self, rel_type: RelationshipType) -> Sequence[Relationship]:
        return self._inner.get_by_type(rel_type)

    def delete(
        self,
        source_id: EntityId | None = None,
        target_id: EntityId | None = None,
        rel_type: RelationshipType | None = None,
    ) -> int:
        # Get relationships to delete first
        to_delete = []
        for r in self._inner.all():
            match = True
            if source_id is not None and r.source_id.value != source_id.value:
                match = False
            if target_id is not None and r.target_id.value != target_id.value:
                match = False
            if rel_type is not None and r.type != rel_type:
                match = False
            if match:
                to_delete.append(r)
        
        # Remove from graph
        for r in to_delete:
            if self._graph.has_edge(r.source_id.value, r.target_id.value):
                self._graph.remove_edge(r.source_id.value, r.target_id.value)
        
        return self._inner.delete(source_id, target_id, rel_type)

    def all(self) -> Sequence[Relationship]:
        return self._inner.all()
