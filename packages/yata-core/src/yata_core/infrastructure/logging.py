"""Structured logging module for YATA.

This module provides structured logging using structlog with support for:
- JSON format output for production
- Human-readable console output for development
- Request/correlation ID tracking
- Performance timing

REQ-NFR-009: Logging output requirements.
"""

import logging
import sys
import time
import uuid
from contextvars import ContextVar
from functools import wraps
from typing import Any, Callable, TypeVar

import structlog
from structlog.typing import FilteringBoundLogger


# Context variables for request tracking
_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_correlation_id() -> str | None:
    """Get current correlation ID from context."""
    return _correlation_id.get()


def set_correlation_id(correlation_id: str | None = None) -> str:
    """Set correlation ID in context.
    
    Args:
        correlation_id: ID to set, or None to generate new UUID
        
    Returns:
        The correlation ID that was set
    """
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())[:8]
    _correlation_id.set(correlation_id)
    return correlation_id


def get_request_id() -> str | None:
    """Get current request ID from context."""
    return _request_id.get()


def set_request_id(request_id: str | None = None) -> str:
    """Set request ID in context.
    
    Args:
        request_id: ID to set, or None to generate new UUID
        
    Returns:
        The request ID that was set
    """
    if request_id is None:
        request_id = str(uuid.uuid4())[:8]
    _request_id.set(request_id)
    return request_id


def add_context_ids(
    logger: FilteringBoundLogger,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Add correlation and request IDs to log events."""
    correlation_id = get_correlation_id()
    request_id = get_request_id()
    
    if correlation_id:
        event_dict["correlation_id"] = correlation_id
    if request_id:
        event_dict["request_id"] = request_id
    
    return event_dict


def configure_logging(
    level: str = "INFO",
    json_format: bool = False,
    log_file: str | None = None,
) -> None:
    """Configure structured logging.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: If True, output JSON format; otherwise console format
        log_file: Optional file path to write logs to
    """
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper()),
    )
    
    # Common processors
    shared_processors: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        add_context_ids,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]
    
    if json_format:
        # JSON output for production
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Console output for development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, level.upper()))
        logging.getLogger().addHandler(file_handler)


def get_logger(name: str | None = None) -> FilteringBoundLogger:
    """Get a structured logger.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


# Type variable for decorated functions
F = TypeVar("F", bound=Callable[..., Any])


def log_timing(logger: FilteringBoundLogger | None = None) -> Callable[[F], F]:
    """Decorator to log function execution time.
    
    Args:
        logger: Logger to use, or None to create one
        
    Returns:
        Decorator function
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            nonlocal logger
            if logger is None:
                logger = get_logger(func.__module__)
            
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                logger.debug(
                    "function_completed",
                    function=func.__name__,
                    elapsed_ms=round(elapsed_ms, 2),
                )
                return result
            except Exception as e:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                logger.error(
                    "function_failed",
                    function=func.__name__,
                    elapsed_ms=round(elapsed_ms, 2),
                    error=str(e),
                    exc_info=True,
                )
                raise
        
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            nonlocal logger
            if logger is None:
                logger = get_logger(func.__module__)
            
            start_time = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                logger.debug(
                    "async_function_completed",
                    function=func.__name__,
                    elapsed_ms=round(elapsed_ms, 2),
                )
                return result
            except Exception as e:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                logger.error(
                    "async_function_failed",
                    function=func.__name__,
                    elapsed_ms=round(elapsed_ms, 2),
                    error=str(e),
                    exc_info=True,
                )
                raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return wrapper  # type: ignore
    
    return decorator


class LogContext:
    """Context manager for adding temporary log context.
    
    Example:
        with LogContext(user_id="123", action="parse"):
            logger.info("processing file")
    """
    
    def __init__(self, **context: Any) -> None:
        """Initialize with context key-value pairs."""
        self._context = context
        self._token: Any = None
    
    def __enter__(self) -> "LogContext":
        """Enter context and bind variables."""
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(**self._context)
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context and unbind variables."""
        structlog.contextvars.unbind_contextvars(*self._context.keys())


# Default logger for the package
logger = get_logger("yata")
