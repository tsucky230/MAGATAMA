"""
ID Value Objects

Type-safe identifiers for entities and libraries.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class EntityId(BaseModel):
    """
    Immutable entity identifier.

    Provides type-safe entity IDs that can be used as dictionary keys.

    Attributes:
        value: The underlying string identifier
    """

    model_config = {"frozen": True}

    value: str = Field(..., min_length=1, description="Entity identifier")

    @classmethod
    def generate(cls) -> EntityId:
        """
        Generate a unique entity ID.

        Returns:
            New EntityId with UUID-based value
        """
        return cls(value=f"ent_{uuid.uuid4().hex[:12]}")

    def __str__(self) -> str:
        """Return the ID value."""
        return self.value

    def __repr__(self) -> str:
        """Return debug representation."""
        return f"EntityId({self.value!r})"

    def __eq__(self, other: object) -> bool:
        """Check equality based on value."""
        if isinstance(other, EntityId):
            return self.value == other.value
        return False

    def __hash__(self) -> int:
        """Hash for use in sets/dicts."""
        return hash(self.value)


class LibraryId(BaseModel):
    """
    Immutable library identifier.

    Identifies a specific library, optionally with version.

    Attributes:
        value: The underlying string identifier
    """

    model_config = {"frozen": True}

    value: str = Field(..., min_length=1, description="Library identifier")

    @classmethod
    def from_name_version(cls, name: str, version: str) -> LibraryId:
        """
        Create a library ID from name and version.

        Args:
            name: Library name (e.g., "requests")
            version: Version string (e.g., "2.31.0")

        Returns:
            LibraryId combining name and version
        """
        return cls(value=f"{name}@{version}")

    def __str__(self) -> str:
        """Return the ID value."""
        return self.value

    def __repr__(self) -> str:
        """Return debug representation."""
        return f"LibraryId({self.value!r})"

    def __eq__(self, other: object) -> bool:
        """Check equality based on value."""
        if isinstance(other, LibraryId):
            return self.value == other.value
        return False

    def __hash__(self) -> int:
        """Hash for use in sets/dicts."""
        return hash(self.value)
