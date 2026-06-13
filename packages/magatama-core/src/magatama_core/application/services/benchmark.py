"""Performance benchmarking for MAGATAMA operations.

This module provides tools for measuring and tracking performance
of indexing, querying, and graph operations.
"""

import statistics
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class BenchmarkResult:
    """Result of a benchmark run.

    Attributes:
        name: Name of the benchmark
        iterations: Number of iterations run
        total_time_ms: Total time in milliseconds
        mean_time_ms: Mean time per iteration
        std_dev_ms: Standard deviation
        min_time_ms: Minimum time
        max_time_ms: Maximum time
        throughput: Operations per second (if applicable)
        metadata: Additional context data
    """

    name: str
    iterations: int
    total_time_ms: float
    mean_time_ms: float
    std_dev_ms: float
    min_time_ms: float
    max_time_ms: float
    throughput: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "iterations": self.iterations,
            "total_time_ms": round(self.total_time_ms, 3),
            "mean_time_ms": round(self.mean_time_ms, 3),
            "std_dev_ms": round(self.std_dev_ms, 3),
            "min_time_ms": round(self.min_time_ms, 3),
            "max_time_ms": round(self.max_time_ms, 3),
            "throughput": round(self.throughput, 2) if self.throughput else None,
            "metadata": self.metadata,
        }


class Benchmark:
    """Benchmark runner for measuring operation performance.

    Usage:
        bench = Benchmark()

        @bench.measure("parse_file")
        def parse():
            parser.parse(code)

        result = bench.run("parse_file", iterations=100)
    """

    def __init__(self) -> None:
        """Initialize benchmark runner."""
        self._benchmarks: dict[str, Callable[[], Any]] = {}
        self._results: list[BenchmarkResult] = []

    def register(self, name: str, func: Callable[[], Any]) -> None:
        """Register a benchmark function.

        Args:
            name: Benchmark name
            func: Function to benchmark (should take no arguments)
        """
        self._benchmarks[name] = func

    def measure(self, name: str) -> Callable[[Callable[[], Any]], Callable[[], Any]]:
        """Decorator to register a benchmark function.

        Args:
            name: Benchmark name

        Returns:
            Decorator function
        """

        def decorator(func: Callable[[], Any]) -> Callable[[], Any]:
            self.register(name, func)
            return func

        return decorator

    def run(
        self,
        name: str,
        iterations: int = 10,
        warmup: int = 2,
        items_count: int | None = None,
    ) -> BenchmarkResult:
        """Run a registered benchmark.

        Args:
            name: Benchmark name
            iterations: Number of iterations to run
            warmup: Number of warmup iterations (not counted)
            items_count: Number of items processed (for throughput calculation)

        Returns:
            BenchmarkResult with timing statistics

        Raises:
            KeyError: If benchmark name not registered
        """
        if name not in self._benchmarks:
            raise KeyError(f"Benchmark '{name}' not registered")

        func = self._benchmarks[name]

        # Warmup
        for _ in range(warmup):
            func()

        # Measure
        times_ms: list[float] = []
        start_total = time.perf_counter()

        for _ in range(iterations):
            start = time.perf_counter()
            func()
            end = time.perf_counter()
            times_ms.append((end - start) * 1000)

        end_total = time.perf_counter()
        total_time_ms = (end_total - start_total) * 1000

        # Calculate statistics
        mean_time = statistics.mean(times_ms)
        std_dev = statistics.stdev(times_ms) if len(times_ms) > 1 else 0.0

        # Calculate throughput if items_count provided
        throughput = None
        if items_count is not None and mean_time > 0:
            throughput = (items_count / mean_time) * 1000  # items/second

        result = BenchmarkResult(
            name=name,
            iterations=iterations,
            total_time_ms=total_time_ms,
            mean_time_ms=mean_time,
            std_dev_ms=std_dev,
            min_time_ms=min(times_ms),
            max_time_ms=max(times_ms),
            throughput=throughput,
        )

        self._results.append(result)
        return result

    def run_once(
        self,
        func: Callable[[], Any],
        name: str | None = None,
    ) -> tuple[Any, float]:
        """Run a function once and measure time.

        Args:
            func: Function to run
            name: Optional name for tracking

        Returns:
            Tuple of (result, time_ms)
        """
        start = time.perf_counter()
        result = func()
        end = time.perf_counter()
        time_ms = (end - start) * 1000

        return result, time_ms

    def get_results(self) -> list[BenchmarkResult]:
        """Get all recorded results."""
        return self._results.copy()

    def clear_results(self) -> None:
        """Clear recorded results."""
        self._results.clear()


class PerformanceProfiler:
    """Profile performance of multiple operations.

    Provides a context manager for timing blocks of code
    and collecting detailed metrics.
    """

    def __init__(self) -> None:
        """Initialize profiler."""
        self._timings: dict[str, list[float]] = {}
        self._counters: dict[str, int] = {}
        self._current_operation: str | None = None
        self._operation_start: float = 0

    def start(self, operation: str) -> None:
        """Start timing an operation.

        Args:
            operation: Operation name
        """
        self._current_operation = operation
        self._operation_start = time.perf_counter()

    def stop(self) -> float:
        """Stop timing current operation.

        Returns:
            Elapsed time in milliseconds
        """
        if self._current_operation is None:
            return 0.0

        elapsed = (time.perf_counter() - self._operation_start) * 1000

        if self._current_operation not in self._timings:
            self._timings[self._current_operation] = []
        self._timings[self._current_operation].append(elapsed)

        self._current_operation = None
        return elapsed

    def increment(self, counter: str, amount: int = 1) -> None:
        """Increment a counter.

        Args:
            counter: Counter name
            amount: Amount to increment
        """
        if counter not in self._counters:
            self._counters[counter] = 0
        self._counters[counter] += amount

    def time_operation(self, operation: str):
        """Context manager for timing an operation.

        Usage:
            with profiler.time_operation("parse"):
                do_parsing()
        """
        return _TimingContext(self, operation)

    def get_summary(self) -> dict[str, Any]:
        """Get profiling summary.

        Returns:
            Dictionary with timing statistics and counters
        """
        summary: dict[str, Any] = {
            "operations": {},
            "counters": self._counters.copy(),
        }

        for op, times in self._timings.items():
            if times:
                summary["operations"][op] = {
                    "count": len(times),
                    "total_ms": round(sum(times), 3),
                    "mean_ms": round(statistics.mean(times), 3),
                    "min_ms": round(min(times), 3),
                    "max_ms": round(max(times), 3),
                }

        return summary

    def reset(self) -> None:
        """Reset all timings and counters."""
        self._timings.clear()
        self._counters.clear()
        self._current_operation = None


class _TimingContext:
    """Context manager for timing operations."""

    def __init__(self, profiler: PerformanceProfiler, operation: str) -> None:
        self._profiler = profiler
        self._operation = operation

    def __enter__(self) -> "_TimingContext":
        self._profiler.start(self._operation)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._profiler.stop()


def measure_indexing_performance(
    directory: Path,
    patterns: list[str] | None = None,
) -> dict[str, Any]:
    """Measure performance of indexing a directory.

    Args:
        directory: Directory to index
        patterns: File patterns to include

    Returns:
        Performance metrics dictionary
    """
    from magatama_core.application.usecases.parse_usecase import (
        ParseDirectoryUseCase,
        ParseFileUseCase,
    )
    from magatama_core.infrastructure.parsers import GoParser, PythonParser, RustParser
    from magatama_core.infrastructure.parsers.javascript_parser import JavaScriptParser
    from magatama_core.infrastructure.parsers.typescript_parser import TypeScriptParser
    from magatama_core.infrastructure.storage import NetworkXKnowledgeGraph

    if patterns is None:
        patterns = ["**/*.py", "**/*.ts", "**/*.tsx", "**/*.js", "**/*.jsx", "**/*.rs", "**/*.go"]

    # Setup
    kg = NetworkXKnowledgeGraph()
    parsers = {
        ".py": PythonParser(),
        ".ts": TypeScriptParser(),
        ".tsx": TypeScriptParser(),
        ".js": JavaScriptParser(),
        ".jsx": JavaScriptParser(),
        ".rs": RustParser(),
        ".go": GoParser(),
    }
    parse_file = ParseFileUseCase(parsers=parsers, knowledge_graph=kg)
    parse_dir = ParseDirectoryUseCase(parse_file_usecase=parse_file)

    # Measure
    start = time.perf_counter()
    result = parse_dir.execute(
        directory=directory,
        patterns=patterns,
    )
    elapsed = (time.perf_counter() - start) * 1000

    # Calculate metrics
    files_parsed = result.files_processed
    entities_count = len(kg.entities.all())
    relationships_count = len(kg.relationships.all())

    throughput = (files_parsed / elapsed) * 1000 if elapsed > 0 else 0

    return {
        "directory": str(directory),
        "files_parsed": files_parsed,
        "entities_extracted": entities_count,
        "relationships_extracted": relationships_count,
        "total_time_ms": round(elapsed, 3),
        "time_per_file_ms": round(elapsed / files_parsed, 3) if files_parsed > 0 else 0,
        "files_per_second": round(throughput, 2),
        "entities_per_file": round(entities_count / files_parsed, 2) if files_parsed > 0 else 0,
    }


def measure_query_performance(
    kg,
    query: str,
    iterations: int = 100,
) -> dict[str, Any]:
    """Measure performance of entity queries.

    Args:
        kg: Knowledge graph to query
        query: Search query string
        iterations: Number of iterations

    Returns:
        Performance metrics dictionary
    """
    bench = Benchmark()

    @bench.measure("search")
    def search():
        return kg.entities.search(query, limit=100)

    result = bench.run("search", iterations=iterations)

    return result.to_dict()
