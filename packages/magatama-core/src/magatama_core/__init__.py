"""
MAGATAMA Core - Knowledge Graph Engine Library

MAGATAMA (勾玉) is a knowledge graph engine for code analysis,
providing AST parsing and graph-based code understanding.

Article I Compliance: This is an independent library.
"""

from importlib.metadata import PackageNotFoundError, version

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

try:
    # Single source of truth: the distribution version in pyproject.toml.
    __version__ = version("magatama-core")
except PackageNotFoundError:  # pragma: no cover - e.g. running from a source tree
    __version__ = "0.0.0+unknown"

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
