"""
Configuration Tests - RED Phase First (Article III)

REQ-CFG-001: Environment-based configuration
"""

import os
from pathlib import Path

import pytest

from magatama_core.infrastructure.config import (
    LogLevel,
    MagatamaConfig,
    MCPConfig,
    ParsingConfig,
    StorageConfig,
)


class TestLogLevel:
    """Test LogLevel enum."""

    @pytest.mark.unit
    def test_log_levels_exist(self) -> None:
        """Test all required log levels exist."""
        assert LogLevel.DEBUG
        assert LogLevel.INFO
        assert LogLevel.WARNING
        assert LogLevel.ERROR


class TestStorageConfig:
    """Test StorageConfig settings."""

    @pytest.mark.unit
    def test_storage_config_defaults(self) -> None:
        """Test StorageConfig has sensible defaults."""
        config = StorageConfig()
        assert config.cache_dir is not None
        assert config.max_cache_size_mb > 0

    @pytest.mark.unit
    def test_storage_config_custom_values(self) -> None:
        """Test StorageConfig with custom values."""
        config = StorageConfig(
            cache_dir=Path("/tmp/magatama-cache"),
            max_cache_size_mb=500,
        )
        assert config.cache_dir == Path("/tmp/magatama-cache")
        assert config.max_cache_size_mb == 500


class TestParsingConfig:
    """Test ParsingConfig settings."""

    @pytest.mark.unit
    def test_parsing_config_defaults(self) -> None:
        """Test ParsingConfig has sensible defaults."""
        config = ParsingConfig()
        assert len(config.supported_languages) > 0
        assert config.max_file_size_kb > 0

    @pytest.mark.unit
    def test_parsing_config_supported_languages(self) -> None:
        """Test default supported languages include Python."""
        config = ParsingConfig()
        assert "python" in config.supported_languages


class TestMCPConfig:
    """Test MCP server configuration."""

    @pytest.mark.unit
    def test_mcp_config_defaults(self) -> None:
        """Test MCPConfig has sensible defaults."""
        config = MCPConfig()
        assert config.server_name is not None
        assert config.version is not None

    @pytest.mark.unit
    def test_mcp_config_custom_values(self) -> None:
        """Test MCPConfig with custom values."""
        config = MCPConfig(
            server_name="custom-magatama",
            version="2.0.0",
        )
        assert config.server_name == "custom-magatama"
        assert config.version == "2.0.0"


class TestMagatamaConfig:
    """Test main MagatamaConfig."""

    @pytest.mark.unit
    def test_yata_config_defaults(self) -> None:
        """Test MagatamaConfig has all required sections."""
        config = MagatamaConfig()
        assert config.log_level is not None
        assert config.storage is not None
        assert config.parsing is not None
        assert config.mcp is not None

    @pytest.mark.unit
    def test_yata_config_from_env(self) -> None:
        """Test MagatamaConfig reads from environment variables."""
        os.environ["MAGATAMA_LOG_LEVEL"] = "DEBUG"
        try:
            config = MagatamaConfig()
            assert config.log_level == LogLevel.DEBUG
        finally:
            del os.environ["MAGATAMA_LOG_LEVEL"]

    @pytest.mark.unit
    def test_yata_config_nested_env(self) -> None:
        """Test nested config from environment."""
        os.environ["MAGATAMA_STORAGE__MAX_CACHE_SIZE_MB"] = "1000"
        try:
            config = MagatamaConfig()
            assert config.storage.max_cache_size_mb == 1000
        finally:
            del os.environ["MAGATAMA_STORAGE__MAX_CACHE_SIZE_MB"]
