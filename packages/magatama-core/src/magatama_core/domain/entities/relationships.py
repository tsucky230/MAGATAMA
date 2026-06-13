"""
Relationship Classes

REQ-KGC-002: Relationships between entities.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from magatama_core.domain.value_objects.ids import EntityId


class RelationshipType(str, Enum):
    """Types of relationships between entities."""

    # Inheritance/Implementation
    INHERITS = "inherits"  # Class extends another class
    IMPLEMENTS = "implements"  # Class implements interface/trait

    # Usage
    CALLS = "calls"  # Function/method calls another
    IMPORTS = "imports"  # Module imports another
    USES_TYPE = "uses_type"  # Uses a type definition

    # Containment
    CONTAINS = "contains"  # Module contains class, class contains method

    # Dependencies
    DEPENDS_ON = "depends_on"  # General dependency

    # References
    REFERENCES = "references"  # References another entity
    RETURNS = "returns"  # Returns a type


class Relationship(BaseModel):
    """
    Relationship between two entities.

    Represents a directed edge in the knowledge graph from
    source entity to target entity.

    Attributes:
        source_id: ID of the source entity
        target_id: ID of the target entity
        type: Type of relationship
        metadata: Additional relationship metadata
    """

    model_config = {"frozen": True}

    source_id: EntityId = Field(..., description="Source entity ID")
    target_id: EntityId = Field(..., description="Target entity ID")
    type: RelationshipType = Field(..., description="Relationship type")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def __eq__(self, other: object) -> bool:
        """Relationships are equal if source, target, and type match."""
        if isinstance(other, Relationship):
            return (
                self.source_id == other.source_id
                and self.target_id == other.target_id
                and self.type == other.type
            )
        return False

    def __hash__(self) -> int:
        """Hash for use in sets."""
        return hash((self.source_id, self.target_id, self.type))

    def __str__(self) -> str:
        """Human-readable representation."""
        return f"{self.source_id} --[{self.type.value}]--> {self.target_id}"

    def __repr__(self) -> str:
        """Debug representation."""
        return (
            f"Relationship(source={self.source_id}, "
            f"target={self.target_id}, type={self.type.value})"
        )
