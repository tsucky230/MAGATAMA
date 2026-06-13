"""
Version Value Object

REQ-KGC-005: Semantic versioning for library versions.
"""

from __future__ import annotations

import re
from functools import total_ordering

from pydantic import BaseModel, Field

# Module-level regex pattern for parsing semver strings (avoid Pydantic treating it as ModelPrivateAttr)
_SEMVER_PATTERN = re.compile(
    r"^v?"  # Optional 'v' prefix
    r"(?P<major>0|[1-9]\d*)"
    r"\.(?P<minor>0|[1-9]\d*)"
    r"\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+(?P<build>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)


@total_ordering
class Version(BaseModel):
    """
    Immutable semantic version.

    Follows Semantic Versioning 2.0.0 (https://semver.org/).

    Attributes:
        major: Major version (breaking changes)
        minor: Minor version (new features, backwards compatible)
        patch: Patch version (bug fixes, backwards compatible)
        prerelease: Optional prerelease identifier (e.g., "alpha.1", "beta.2")
        build: Optional build metadata
    """

    model_config = {"frozen": True}  # Immutable

    major: int = Field(..., ge=0, description="Major version number")
    minor: int = Field(..., ge=0, description="Minor version number")
    patch: int = Field(..., ge=0, description="Patch version number")
    prerelease: str | None = Field(default=None, description="Prerelease identifier")
    build: str | None = Field(default=None, description="Build metadata")

    @classmethod
    def from_string(cls, version_str: str) -> Version:
        """
        Parse a version string into a Version object.

        Args:
            version_str: Version string (e.g., "1.2.3", "v1.2.3-alpha.1")

        Returns:
            Version object

        Raises:
            ValueError: If the version string is invalid
        """
        match = _SEMVER_PATTERN.match(version_str.strip())
        if not match:
            raise ValueError(f"Invalid version string: {version_str}")

        return cls(
            major=int(match.group("major")),
            minor=int(match.group("minor")),
            patch=int(match.group("patch")),
            prerelease=match.group("prerelease"),
            build=match.group("build"),
        )

    def __str__(self) -> str:
        """Return version as semver string."""
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build:
            version += f"+{self.build}"
        return version

    def __repr__(self) -> str:
        """Return debug representation."""
        return f"Version({self})"

    def _comparison_tuple(self) -> tuple[int, int, int, tuple[str, ...], int]:
        """
        Return tuple for comparison.

        Prerelease versions have lower precedence than normal versions.
        """
        # If no prerelease, use empty tuple with high precedence (1)
        # If prerelease, split and compare parts with low precedence (0)
        if self.prerelease is None:
            prerelease_tuple: tuple[str, ...] = ()
            prerelease_precedence = 1
        else:
            prerelease_tuple = tuple(self.prerelease.split("."))
            prerelease_precedence = 0

        return (
            self.major,
            self.minor,
            self.patch,
            prerelease_tuple,
            prerelease_precedence,
        )

    def __eq__(self, other: object) -> bool:
        """Check version equality (build metadata is ignored)."""
        if not isinstance(other, Version):
            return NotImplemented
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
            and self.prerelease == other.prerelease
        )

    def __lt__(self, other: object) -> bool:
        """Compare versions for ordering."""
        if not isinstance(other, Version):
            return NotImplemented
        return self._comparison_tuple() < other._comparison_tuple()

    def __hash__(self) -> int:
        """Hash for use in sets/dicts."""
        return hash((self.major, self.minor, self.patch, self.prerelease))
