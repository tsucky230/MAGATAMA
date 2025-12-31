"""
Base Entity Classes

REQ-KGC-001: Core entity types for code analysis.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from yata_core.domain.value_objects.ids import EntityId
from yata_core.domain.value_objects.location import Location


class EntityType(str, Enum):
    """Types of code entities that can be extracted."""

    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    TYPE = "type"
    VARIABLE = "variable"
    INTERFACE = "interface"  # TypeScript/Go
    TRAIT = "trait"  # Rust
    STRUCT = "struct"  # Rust/Go
    ENUM = "enum"


class Entity(BaseModel):
    """
    Base class for all code entities.

    An entity represents a distinct code element with identity,
    such as a class, function, module, or type definition.

    Attributes:
        id: Unique identifier for this entity
        name: Name of the entity (e.g., class name, function name)
        type: Type of the entity
        location: Source code location
        docstring: Optional documentation string
        scope: Visibility scope (public, private, etc.)
    """

    model_config = {"frozen": True}

    id: EntityId = Field(..., description="Unique entity identifier")
    name: str = Field(..., min_length=1, description="Entity name")
    type: EntityType = Field(..., description="Entity type")
    location: Location = Field(..., description="Source code location")
    docstring: str | None = Field(default=None, description="Documentation string")
    scope: str | None = Field(default=None, description="Visibility scope")

    def __eq__(self, other: object) -> bool:
        """Entities are equal if they have the same ID."""
        if isinstance(other, Entity):
            return self.id == other.id
        return False

    def __hash__(self) -> int:
        """Hash based on entity ID."""
        return hash(self.id)

    def __str__(self) -> str:
        """Human-readable representation."""
        return f"{self.type.value}:{self.name}"

    def __repr__(self) -> str:
        """Debug representation."""
        return f"Entity(id={self.id}, name={self.name!r}, type={self.type.value})"
