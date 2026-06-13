"""
Location Value Object

REQ-KGC-001: File location (file, line, column) for entities.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class Location(BaseModel):
    """
    Immutable location in source code.

    Represents a specific position in a source file with file path,
    line number, and optional column number.

    Attributes:
        file: Path to the source file (relative or absolute)
        line: Line number (1-based, must be positive)
        column: Column number (0-based, must be non-negative)
    """

    model_config = {"frozen": True}  # Immutable

    file: str = Field(..., description="Path to the source file")
    line: int = Field(..., ge=1, description="Line number (1-based)")
    column: int = Field(default=0, ge=0, description="Column number (0-based)")

    @field_validator("line")
    @classmethod
    def validate_line(cls, v: int) -> int:
        """Ensure line is positive (1-based)."""
        if v < 1:
            raise ValueError("Line number must be positive (1-based)")
        return v

    @field_validator("column")
    @classmethod
    def validate_column(cls, v: int) -> int:
        """Ensure column is non-negative (0-based)."""
        if v < 0:
            raise ValueError("Column number must be non-negative (0-based)")
        return v

    def __str__(self) -> str:
        """Return human-readable location string."""
        return f"{self.file}:{self.line}:{self.column}"

    def __repr__(self) -> str:
        """Return debug representation."""
        return f"Location(file={self.file!r}, line={self.line}, column={self.column})"
