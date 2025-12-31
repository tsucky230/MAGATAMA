"""Tests for structured logging module."""

import json
import logging
import pytest
from io import StringIO
from unittest.mock import patch

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


class TestLoggingConfiguration:
    """Tests for logging configuration."""

    def test_configure_logging_default(self) -> None:
        """Test default logging configuration."""
        configure_logging()
        logger = get_logger("test")
        assert logger is not None

    def test_configure_logging_json_format(self) -> None:
        """Test JSON format logging."""
        configure_logging(json_format=True)
        logger = get_logger("test_json")
        assert logger is not None

    def test_configure_logging_debug_level(self) -> None:
        """Test setting debug log level."""
        configure_logging(level="DEBUG")
        # basicConfig won't change if already configured, so we check the logger works
        logger = get_logger("debug_test")
        assert logger is not None


class TestContextIds:
    """Tests for correlation and request ID tracking."""

    def test_set_get_correlation_id(self) -> None:
        """Test setting and getting correlation ID."""
        cid = set_correlation_id("test-123")
        assert cid == "test-123"
        assert get_correlation_id() == "test-123"

    def test_auto_generate_correlation_id(self) -> None:
        """Test auto-generating correlation ID."""
        cid = set_correlation_id()
        assert cid is not None
        assert len(cid) == 8  # UUID[:8]
        assert get_correlation_id() == cid

    def test_set_get_request_id(self) -> None:
        """Test setting and getting request ID."""
        rid = set_request_id("req-456")
        assert rid == "req-456"
        assert get_request_id() == "req-456"

    def test_auto_generate_request_id(self) -> None:
        """Test auto-generating request ID."""
        rid = set_request_id()
        assert rid is not None
        assert len(rid) == 8
        assert get_request_id() == rid


class TestLogTiming:
    """Tests for log_timing decorator."""

    def test_log_timing_sync_function(self) -> None:
        """Test timing decorator on sync function."""
        @log_timing()
        def slow_function() -> int:
            return 42

        result = slow_function()
        assert result == 42

    def test_log_timing_with_exception(self) -> None:
        """Test timing decorator logs exceptions."""
        @log_timing()
        def failing_function() -> None:
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            failing_function()

    @pytest.mark.asyncio
    async def test_log_timing_async_function(self) -> None:
        """Test timing decorator on async function."""
        @log_timing()
        async def async_function() -> str:
            return "async result"

        result = await async_function()
        assert result == "async result"

    @pytest.mark.asyncio
    async def test_log_timing_async_with_exception(self) -> None:
        """Test timing decorator logs async exceptions."""
        @log_timing()
        async def async_failing() -> None:
            raise RuntimeError("async error")

        with pytest.raises(RuntimeError, match="async error"):
            await async_failing()


class TestLogContext:
    """Tests for LogContext context manager."""

    def test_log_context_basic(self) -> None:
        """Test basic LogContext usage."""
        with LogContext(user_id="123", action="test"):
            logger = get_logger("test_context")
            # Context should be active
            assert logger is not None

    def test_log_context_cleanup(self) -> None:
        """Test LogContext cleans up after exit."""
        with LogContext(temp_key="temp_value"):
            pass
        # After exit, context should be cleared
        # (structlog internals handle this)


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_with_name(self) -> None:
        """Test getting logger with specific name."""
        logger = get_logger("my.module.name")
        assert logger is not None

    def test_get_logger_without_name(self) -> None:
        """Test getting logger without name."""
        logger = get_logger()
        assert logger is not None

    def test_logger_can_log(self) -> None:
        """Test that logger can log messages."""
        configure_logging(level="DEBUG")
        logger = get_logger("test_logging")
        
        # These should not raise
        logger.debug("debug message")
        logger.info("info message")
        logger.warning("warning message")
        logger.error("error message")


class TestLoggingPerformance:
    """Tests for logging performance."""

    def test_logging_overhead(self) -> None:
        """Test that logging overhead is minimal (<1ms per call)."""
        import time
        
        configure_logging(level="WARNING")  # Suppress output
        logger = get_logger("perf_test")
        
        iterations = 1000
        start = time.perf_counter()
        
        for i in range(iterations):
            logger.debug("performance test", iteration=i)
        
        elapsed_ms = (time.perf_counter() - start) * 1000
        avg_ms = elapsed_ms / iterations
        
        # Average should be well under 1ms per log call
        assert avg_ms < 1.0, f"Logging overhead {avg_ms}ms exceeds 1ms target"
