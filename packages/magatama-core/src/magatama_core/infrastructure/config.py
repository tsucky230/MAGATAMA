"""
MAGATAMA Configuration Module

REQ-CFG-001: Environment-based configuration using pydantic-settings.
Provides type-safe configuration with environment variable support.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(str, Enum):
    """Logging levels for MAGATAMA."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class StorageConfig(BaseSettings):
    """
    Storage configuration.

    Controls caching and persistence behavior.
    """

    model_config = SettingsConfigDict(
        env_prefix="MAGATAMA_STORAGE__",
        env_nested_delimiter="__",
    )

    cache_dir: Path = Field(
        default=Path.home() / ".cache" / "magatama",
        description="Directory for cached data",
    )
    max_cache_size_mb: int = Field(
        default=100,
        ge=1,
        description="Maximum cache size in megabytes",
    )
    graph_file: str = Field(
        default="knowledge_graph.json",
        description="Filename for persisted knowledge graph",
    )


class ParsingConfig(BaseSettings):
    """
    Code parsing configuration.

    Controls which languages and files are parsed.
    """

    model_config = SettingsConfigDict(
        env_prefix="MAGATAMA_PARSING__",
        env_nested_delimiter="__",
    )

    supported_languages: list[str] = Field(
        default=["python", "typescript", "javascript"],
        description="Languages supported for parsing",
    )
    max_file_size_kb: int = Field(
        default=1024,
        ge=1,
        description="Maximum file size to parse in kilobytes",
    )
    ignore_patterns: list[str] = Field(
        default=[
            "*.pyc",
            "__pycache__",
            "node_modules",
            ".git",
            ".venv",
            "venv",
            "dist",
            "build",
        ],
        description="File patterns to ignore during parsing",
    )
    follow_imports: bool = Field(
        default=True,
        description="Whether to follow and parse imported files",
    )


class MCPConfig(BaseSettings):
    """
    MCP Server configuration.

    Controls the Model Context Protocol server behavior.
    """

    model_config = SettingsConfigDict(
        env_prefix="MAGATAMA_MCP__",
        env_nested_delimiter="__",
    )

    server_name: str = Field(
        default="magatama",
        description="MCP server name",
    )
    version: str = Field(
        default="0.1.0",
        description="Server version",
    )
    max_context_tokens: int = Field(
        default=4000,
        ge=100,
        description="Maximum tokens in context response",
    )
    include_docstrings: bool = Field(
        default=True,
        description="Include docstrings in context",
    )


class MagatamaConfig(BaseSettings):
    """
    Main MAGATAMA configuration.

    Aggregates all configuration sections with environment variable support.
    Environment variables are prefixed with MAGATAMA_ and use __ for nesting.

    Examples:
        MAGATAMA_LOG_LEVEL=DEBUG
        MAGATAMA_STORAGE__MAX_CACHE_SIZE_MB=500
        MAGATAMA_MCP__SERVER_NAME=my-magatama
    """

    model_config = SettingsConfigDict(
        env_prefix="MAGATAMA_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    log_level: LogLevel = Field(
        default=LogLevel.INFO,
        description="Logging level",
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )
    storage: StorageConfig = Field(
        default_factory=StorageConfig,
        description="Storage configuration",
    )
    parsing: ParsingConfig = Field(
        default_factory=ParsingConfig,
        description="Parsing configuration",
    )
    mcp: MCPConfig = Field(
        default_factory=MCPConfig,
        description="MCP server configuration",
    )
