"""
Infrastructure Layer - External system integrations.

This layer contains adapters for:
- Parsers: Tree-sitter AST parsing
- Storage: SQLite + NetworkX graph storage
- GitHub: Repository fetching
- Config: Environment-based configuration
- Logging: Structured logging with structlog
"""

from yata_core.infrastructure.config import (
    YataConfig,
    LogLevel,
    StorageConfig,
    ParsingConfig,
    MCPConfig,
)
from yata_core.infrastructure.logging import (
    configure_logging,
    get_logger,
    log_timing,
    LogContext,
    set_correlation_id,
    get_correlation_id,
    set_request_id,
    get_request_id,
)

__all__ = [
    "YataConfig",
    "LogLevel",
    "StorageConfig",
    "ParsingConfig",
    "MCPConfig",
    "configure_logging",
    "get_logger",
    "log_timing",
    "LogContext",
    "set_correlation_id",
    "get_correlation_id",
    "set_request_id",
    "get_request_id",
]
