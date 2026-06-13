"""
Value Objects - Immutable domain primitives.

REQ-KGC-001: Location (file, line, column)
REQ-KGC-005: Version (semver)
"""

from magatama_core.domain.value_objects.ids import EntityId, LibraryId
from magatama_core.domain.value_objects.location import Location
from magatama_core.domain.value_objects.version import Version

__all__ = [
    "EntityId",
    "LibraryId",
    "Location",
    "Version",
]
