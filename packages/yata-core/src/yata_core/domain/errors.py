"""
YATA Error Types

REQ-ERR-001: Structured error handling with rich context.
Provides a hierarchy of domain-specific exceptions.
"""

from __future__ import annotations

from typing import Any

from yata_core.domain.value_objects.ids import EntityId


class YataError(Exception):
    """
    Base exception for all YATA errors.
    
    Provides structured error handling with optional context.
    
    Attributes:
        message: Human-readable error message
        context: Additional context data for debugging
    """

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        """
        Initialize YataError.
        
        Args:
            message: Error message
            context: Optional context dictionary
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}

    def __str__(self) -> str:
        return self.message


class EntityError(YataError):
    """Base exception for entity-related errors."""


class EntityNotFoundError(EntityError):
    """
    Raised when an entity cannot be found.
    
    Attributes:
        entity_id: The ID that was not found
    """

    def __init__(self, entity_id: EntityId) -> None:
        """
        Initialize EntityNotFoundError.
        
        Args:
            entity_id: The entity ID that was not found
        """
        self.entity_id = entity_id
        super().__init__(
            f"Entity not found: {entity_id.value}",
            context={"entity_id": entity_id.value},
        )


class EntityAlreadyExistsError(EntityError):
    """
    Raised when trying to create an entity that already exists.
    
    Attributes:
        entity_id: The duplicate ID
    """

    def __init__(self, entity_id: EntityId) -> None:
        """
        Initialize EntityAlreadyExistsError.
        
        Args:
            entity_id: The duplicate entity ID
        """
        self.entity_id = entity_id
        super().__init__(
            f"Entity already exists: {entity_id.value}",
            context={"entity_id": entity_id.value},
        )


class ParsingError(YataError):
    """
    Raised when code parsing fails.
    
    Attributes:
        file: File being parsed
        line: Line number of error (optional)
        column: Column number of error (optional)
    """

    def __init__(
        self,
        message: str,
        file: str | None = None,
        line: int | None = None,
        column: int | None = None,
    ) -> None:
        """
        Initialize ParsingError.
        
        Args:
            message: Error message
            file: File path being parsed
            line: Line number where error occurred
            column: Column number where error occurred
        """
        self.file = file
        self.line = line
        self.column = column
        
        location_parts = []
        if file:
            location_parts.append(file)
        if line is not None:
            location_parts.append(f"line {line}")
        if column is not None:
            location_parts.append(f"column {column}")
        
        location = " at " + ":".join(location_parts) if location_parts else ""
        full_message = f"{message}{location}"
        
        super().__init__(
            full_message,
            context={"file": file, "line": line, "column": column},
        )


class ValidationError(YataError):
    """
    Raised when validation fails.
    
    Attributes:
        field: The field that failed validation
        value: The invalid value
    """

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any = None,
    ) -> None:
        """
        Initialize ValidationError.
        
        Args:
            message: Error message
            field: Name of the invalid field
            value: The invalid value
        """
        self.field = field
        self.value = value
        super().__init__(
            message,
            context={"field": field, "value": value},
        )


class StorageError(YataError):
    """
    Raised when storage operations fail.
    
    Attributes:
        path: Path involved in the operation
    """

    def __init__(self, message: str, path: str | None = None) -> None:
        """
        Initialize StorageError.
        
        Args:
            message: Error message
            path: Storage path involved
        """
        self.path = path
        super().__init__(
            message,
            context={"path": path},
        )


class ConfigurationError(YataError):
    """
    Raised when configuration is invalid.
    
    Attributes:
        key: The configuration key with issues
    """

    def __init__(self, message: str, key: str | None = None) -> None:
        """
        Initialize ConfigurationError.
        
        Args:
            message: Error message
            key: Configuration key that is invalid
        """
        self.key = key
        super().__init__(
            message,
            context={"key": key},
        )
