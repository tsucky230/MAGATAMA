"""
Parse Result Data Structure

Holds the output of parsing operations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from yata_core.domain.entities.base import Entity
from yata_core.domain.entities.relationships import Relationship


@dataclass
class ParseResult:
    """
    Result of parsing a source file.
    
    Contains extracted entities, relationships, and metadata.
    
    Attributes:
        file_path: Path to the parsed file
        entities: List of extracted entities
        relationships: List of extracted relationships
        imports: List of imported module names
        errors: List of parsing errors encountered
    """
    
    file_path: Path
    entities: list[Entity] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
