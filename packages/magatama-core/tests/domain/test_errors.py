"""
Error Types Tests - RED Phase First (Article III)

REQ-ERR-001: Structured error handling
"""

import pytest

from magatama_core.domain.errors import (
    ConfigurationError,
    EntityAlreadyExistsError,
    EntityError,
    EntityNotFoundError,
    MagatamaError,
    ParsingError,
    StorageError,
    ValidationError,
)
from magatama_core.domain.value_objects.ids import EntityId


class TestMagatamaError:
    """Test base MagatamaError class."""

    @pytest.mark.unit
    def test_yata_error_is_exception(self) -> None:
        """Test MagatamaError inherits from Exception."""
        assert issubclass(MagatamaError, Exception)

    @pytest.mark.unit
    def test_yata_error_creation(self) -> None:
        """Test creating a MagatamaError with message."""
        error = MagatamaError("Something went wrong")
        assert str(error) == "Something went wrong"

    @pytest.mark.unit
    def test_yata_error_with_context(self) -> None:
        """Test MagatamaError with additional context."""
        error = MagatamaError("Error occurred", context={"file": "main.py", "line": 42})
        assert error.context["file"] == "main.py"
        assert error.context["line"] == 42


class TestEntityErrors:
    """Test entity-related errors."""

    @pytest.mark.unit
    def test_entity_error_is_yata_error(self) -> None:
        """Test EntityError inherits from MagatamaError."""
        assert issubclass(EntityError, MagatamaError)

    @pytest.mark.unit
    def test_entity_not_found_error(self) -> None:
        """Test EntityNotFoundError creation."""
        entity_id = EntityId(value="func_001")
        error = EntityNotFoundError(entity_id)
        assert issubclass(EntityNotFoundError, EntityError)
        assert error.entity_id == entity_id
        assert "func_001" in str(error)

    @pytest.mark.unit
    def test_entity_already_exists_error(self) -> None:
        """Test EntityAlreadyExistsError creation."""
        entity_id = EntityId(value="func_001")
        error = EntityAlreadyExistsError(entity_id)
        assert issubclass(EntityAlreadyExistsError, EntityError)
        assert error.entity_id == entity_id
        assert "func_001" in str(error)


class TestParsingError:
    """Test parsing-related errors."""

    @pytest.mark.unit
    def test_parsing_error_is_yata_error(self) -> None:
        """Test ParsingError inherits from MagatamaError."""
        assert issubclass(ParsingError, MagatamaError)

    @pytest.mark.unit
    def test_parsing_error_with_location(self) -> None:
        """Test ParsingError with file location."""
        error = ParsingError(
            "Syntax error",
            file="main.py",
            line=42,
            column=10,
        )
        assert error.file == "main.py"
        assert error.line == 42
        assert error.column == 10
        assert "main.py" in str(error)


class TestValidationError:
    """Test validation errors."""

    @pytest.mark.unit
    def test_validation_error_is_yata_error(self) -> None:
        """Test ValidationError inherits from MagatamaError."""
        assert issubclass(ValidationError, MagatamaError)

    @pytest.mark.unit
    def test_validation_error_with_field(self) -> None:
        """Test ValidationError with field information."""
        error = ValidationError("Invalid value", field="version", value="not-semver")
        assert error.field == "version"
        assert error.value == "not-semver"


class TestStorageError:
    """Test storage-related errors."""

    @pytest.mark.unit
    def test_storage_error_is_yata_error(self) -> None:
        """Test StorageError inherits from MagatamaError."""
        assert issubclass(StorageError, MagatamaError)

    @pytest.mark.unit
    def test_storage_error_with_path(self) -> None:
        """Test StorageError with path information."""
        error = StorageError("Failed to save", path="/tmp/graph.json")
        assert error.path == "/tmp/graph.json"


class TestConfigurationError:
    """Test configuration errors."""

    @pytest.mark.unit
    def test_configuration_error_is_yata_error(self) -> None:
        """Test ConfigurationError inherits from MagatamaError."""
        assert issubclass(ConfigurationError, MagatamaError)

    @pytest.mark.unit
    def test_configuration_error_with_key(self) -> None:
        """Test ConfigurationError with config key."""
        error = ConfigurationError("Invalid config", key="api_endpoint")
        assert error.key == "api_endpoint"
