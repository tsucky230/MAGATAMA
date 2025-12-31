"""
Domain Entities - Core business objects with identity.

REQ-KGC-001: Entity extraction from source code
REQ-KGC-002: Relationship extraction between entities
"""

from yata_core.domain.entities.base import Entity, EntityType
from yata_core.domain.entities.code_entities import (
    ClassEntity,
    EnumEntity,
    FunctionEntity,
    InterfaceEntity,
    MethodEntity,
    ModuleEntity,
    StructEntity,
    TraitEntity,
    TypeEntity,
)
from yata_core.domain.entities.relationships import Relationship, RelationshipType

__all__ = [
    # Base
    "Entity",
    "EntityType",
    # Code entities
    "ClassEntity",
    "EnumEntity",
    "FunctionEntity",
    "InterfaceEntity",
    "MethodEntity",
    "ModuleEntity",
    "StructEntity",
    "TraitEntity",
    "TypeEntity",
    # Relationships
    "Relationship",
    "RelationshipType",
]
