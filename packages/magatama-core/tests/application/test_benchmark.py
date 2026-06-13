"""Tests for performance benchmarking."""

import time

import pytest

from magatama_core.application.services.benchmark import (
    Benchmark,
    BenchmarkResult,
    PerformanceProfiler,
)


class TestBenchmark:
    """Tests for Benchmark class."""

    def test_register_and_run_benchmark(self) -> None:
        """Test registering and running a benchmark."""
        bench = Benchmark()
        counter = [0]  # Use list for mutability

        def increment():
            counter[0] += 1

        bench.register("increment", increment)
        result = bench.run("increment", iterations=5, warmup=0)

        assert result.name == "increment"
        assert result.iterations == 5
        assert counter[0] == 5  # Should have run 5 times
        assert result.mean_time_ms > 0
        assert result.min_time_ms <= result.mean_time_ms <= result.max_time_ms

    def test_measure_decorator(self) -> None:
        """Test measure decorator for registering benchmarks."""
        bench = Benchmark()

        @bench.measure("test_func")
        def test_func():
            return sum(range(100))

        result = bench.run("test_func", iterations=3, warmup=0)

        assert result.name == "test_func"
        assert result.iterations == 3

    def test_benchmark_with_warmup(self) -> None:
        """Test that warmup iterations are not counted."""
        bench = Benchmark()
        call_count = [0]

        def counted_func():
            call_count[0] += 1

        bench.register("counted", counted_func)
        result = bench.run("counted", iterations=3, warmup=2)

        # 2 warmup + 3 iterations = 5 total calls
        assert call_count[0] == 5
        assert result.iterations == 3  # But only 3 counted

    def test_benchmark_throughput_calculation(self) -> None:
        """Test throughput calculation with items_count."""
        bench = Benchmark()

        def fast_func():
            pass

        bench.register("fast", fast_func)
        result = bench.run("fast", iterations=10, items_count=100)

        assert result.throughput is not None
        assert result.throughput > 0

    def test_run_once(self) -> None:
        """Test run_once for single measurement."""
        bench = Benchmark()

        result_val, time_ms = bench.run_once(lambda: 42 * 2)

        assert result_val == 84
        assert time_ms >= 0

    def test_get_and_clear_results(self) -> None:
        """Test getting and clearing results."""
        bench = Benchmark()
        bench.register("test", lambda: None)

        bench.run("test", iterations=1, warmup=0)
        results = bench.get_results()

        assert len(results) == 1

        bench.clear_results()
        assert len(bench.get_results()) == 0

    def test_unregistered_benchmark_raises(self) -> None:
        """Test that running unregistered benchmark raises KeyError."""
        bench = Benchmark()

        with pytest.raises(KeyError, match="not registered"):
            bench.run("nonexistent")


class TestBenchmarkResult:
    """Tests for BenchmarkResult dataclass."""

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        result = BenchmarkResult(
            name="test",
            iterations=10,
            total_time_ms=100.1234,
            mean_time_ms=10.1234,
            std_dev_ms=1.5678,
            min_time_ms=8.5,
            max_time_ms=12.5,
            throughput=100.5678,
            metadata={"key": "value"},
        )

        d = result.to_dict()

        assert d["name"] == "test"
        assert d["iterations"] == 10
        assert d["total_time_ms"] == 100.123  # Rounded
        assert d["mean_time_ms"] == 10.123
        assert d["throughput"] == 100.57
        assert d["metadata"] == {"key": "value"}


class TestPerformanceProfiler:
    """Tests for PerformanceProfiler class."""

    def test_start_stop_timing(self) -> None:
        """Test start/stop timing."""
        profiler = PerformanceProfiler()

        profiler.start("operation")
        time.sleep(0.01)  # 10ms
        elapsed = profiler.stop()

        assert elapsed >= 10  # At least 10ms

        summary = profiler.get_summary()
        assert "operation" in summary["operations"]
        assert summary["operations"]["operation"]["count"] == 1

    def test_time_operation_context_manager(self) -> None:
        """Test context manager for timing."""
        profiler = PerformanceProfiler()

        with profiler.time_operation("test_op"):
            time.sleep(0.01)

        summary = profiler.get_summary()
        assert "test_op" in summary["operations"]
        assert summary["operations"]["test_op"]["total_ms"] >= 10

    def test_multiple_timings_same_operation(self) -> None:
        """Test multiple timings of same operation."""
        profiler = PerformanceProfiler()

        for _ in range(3):
            with profiler.time_operation("repeated"):
                pass

        summary = profiler.get_summary()
        assert summary["operations"]["repeated"]["count"] == 3

    def test_increment_counter(self) -> None:
        """Test counter incrementing."""
        profiler = PerformanceProfiler()

        profiler.increment("files_processed")
        profiler.increment("files_processed")
        profiler.increment("entities_found", 5)

        summary = profiler.get_summary()
        assert summary["counters"]["files_processed"] == 2
        assert summary["counters"]["entities_found"] == 5

    def test_reset(self) -> None:
        """Test resetting profiler."""
        profiler = PerformanceProfiler()

        profiler.increment("counter")
        with profiler.time_operation("op"):
            pass

        profiler.reset()
        summary = profiler.get_summary()

        assert len(summary["operations"]) == 0
        assert len(summary["counters"]) == 0

    def test_stop_without_start(self) -> None:
        """Test stop without start returns 0."""
        profiler = PerformanceProfiler()

        elapsed = profiler.stop()
        assert elapsed == 0.0

    def test_get_summary_statistics(self) -> None:
        """Test that summary includes proper statistics."""
        profiler = PerformanceProfiler()

        # Create varied timings
        with profiler.time_operation("varied"):
            pass  # Very fast
        with profiler.time_operation("varied"):
            time.sleep(0.01)

        summary = profiler.get_summary()
        op = summary["operations"]["varied"]

        assert "mean_ms" in op
        assert "min_ms" in op
        assert "max_ms" in op
        assert op["min_ms"] <= op["mean_ms"] <= op["max_ms"]
