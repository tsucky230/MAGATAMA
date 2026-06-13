"""
MAGATAMA Core - Knowledge Graph Engine Library

MAGATAMA (勾玉) is a knowledge graph engine for code analysis,
providing AST parsing and graph-based code understanding.

Article I Compliance: This is an independent library.
"""

from magatama_core.domain.entities import (
    ClassEntity,
    Entity,
    EntityType,
    FunctionEntity,
    MethodEntity,
    ModuleEntity,
    Relationship,
    RelationshipType,
    TypeEntity,
)
from magatama_core.domain.value_objects import EntityId, LibraryId, Location, Version

__version__ = "0.1.0"
__all__ = [
    # Entities
    "Entity",
    "EntityType",
    "ClassEntity",
    "FunctionEntity",
    "MethodEntity",
    "ModuleEntity",
    "TypeEntity",
    # Relationships
    "Relationship",
    "RelationshipType",
    # Value Objects
    "EntityId",
    "LibraryId",
    "Location",
    "Version",
]
