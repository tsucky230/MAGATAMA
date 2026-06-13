"""
Infrastructure Layer - External system integrations.

This layer contains adapters for:
- Parsers: Tree-sitter AST parsing
- Storage: SQLite + NetworkX graph storage
- GitHub: Repository fetching
- Config: Environment-based configuration
- Logging: Structured logging with structlog
"""

from magatama_core.infrastructure.config import (
    LogLevel,
    MagatamaConfig,
    MCPConfig,
    ParsingConfig,
    StorageConfig,
)
from magatama_core.infrastructure.logging import (
    LogContext,
    configure_logging,
    get_correlation_id,
    get_logger,
    get_request_id,
    log_timing,
    set_correlation_id,
    set_request_id,
)

__all__ = [
    "LogContext",
    "LogLevel",
    "MCPConfig",
    "MagatamaConfig",
    "ParsingConfig",
    "StorageConfig",
    "configure_logging",
    "get_correlation_id",
    "get_logger",
    "get_request_id",
    "log_timing",
    "set_correlation_id",
    "set_request_id",
]
