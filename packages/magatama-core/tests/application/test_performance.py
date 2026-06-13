"""
Performance Tests - TASK-037

REQ-NFR-001: Indexing Performance (100K lines / 30 seconds)
REQ-NFR-002: Query Response Time (avg 200ms, p95 500ms)
REQ-NFR-003: Memory Usage (startup 100MB, runtime 500MB)
REQ-NFR-006: Startup Time (< 2 seconds)

These tests verify MAGATAMA meets performance requirements.
Mark tests with @pytest.mark.benchmark for selective execution.
"""

import gc
import tempfile
import time
from collections.abc import Generator
from pathlib import Path

import pytest

from magatama_core.application.services.benchmark import Benchmark, PerformanceProfiler
from magatama_core.domain.entities.base import EntityType
from magatama_core.infrastructure.parsers import PythonParser
from magatama_core.infrastructure.storage import NetworkXKnowledgeGraph, SQLiteKnowledgeGraph

# ============================================================================
# REQ-NFR-001: Indexing Performance
# ============================================================================


class TestIndexingPerformance:
    """Tests for indexing performance requirements.

    REQ-NFR-001: Indexing shall process at least 100,000 lines of code
    within 30 seconds.
    """

    @pytest.fixture
    def large_python_file(self) -> Generator[Path, None, None]:
        """Create a large Python file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            # Generate ~1000 lines per function, 100 functions = 100K lines
            for i in range(100):
                f.write(f'''
def function_{i}(arg1: int, arg2: str, arg3: float = 0.0) -> bool:
    """Function {i} with detailed docstring.
    
    This function performs operation {i} on the given arguments.
    It includes validation, computation, and result formatting.
    
    Args:
        arg1: First integer argument
        arg2: Second string argument
        arg3: Optional float argument
        
    Returns:
        True if operation succeeds
    """
    # Validation block
    if arg1 < 0:
        raise ValueError("arg1 must be non-negative")
    if not arg2:
        raise ValueError("arg2 must not be empty")
    
    # Computation block
    result = arg1 * len(arg2)
    for j in range({i + 1}):
        result += j * arg3
        if result > 1000000:
            break
    
    # Additional processing
    processed = {{
        "input": {{
            "arg1": arg1,
            "arg2": arg2,
            "arg3": arg3,
        }},
        "output": result,
        "metadata": {{
            "function_id": {i},
            "timestamp": "2025-01-01",
        }},
    }}
    
    return result > 0


class Class_{i}:
    """Class {i} with attributes and methods.
    
    This class represents entity {i} in the system.
    """
    
    def __init__(self, name: str, value: int) -> None:
        """Initialize instance."""
        self.name = name
        self.value = value
        self._cache: dict = {{}}
    
    def process(self) -> str:
        """Process the entity."""
        return f"{{self.name}}: {{self.value}}"
    
    def validate(self) -> bool:
        """Validate the entity."""
        return bool(self.name and self.value >= 0)

''')
            # ~50 lines per iteration, 100 iterations = 5000 lines
            # To reach 100K, we add more padding
            for _ in range(950):  # Add more functions to reach 100K lines
                f.write('''
def helper_function(x: int, y: int, z: int = 0) -> int:
    """Helper function for computation."""
    result = x + y + z
    for i in range(10):
        result *= 2
        if result > 10000:
            result = result % 10000
    return result

''')  # ~10 lines each, 950 * 10 + 100 * 50 = 14500 lines

            f.flush()
            yield Path(f.name)

    @pytest.fixture
    def many_small_files(self) -> Generator[Path, None, None]:
        """Create many small Python files (total 100K lines)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir)

            # Create 1000 files with ~100 lines each = 100K lines
            for i in range(1000):
                file_path = project / f"module_{i}.py"
                content = f'''"""Module {i}."""

def function_{i}_a(x: int) -> int:
    """Function A in module {i}."""
    return x * 2

def function_{i}_b(x: int, y: int) -> int:
    """Function B in module {i}."""
    return x + y

class Entity_{i}:
    """Entity class in module {i}."""
    
    def __init__(self, value: int) -> None:
        self.value = value
    
    def compute(self) -> int:
        """Compute something."""
        return self.value ** 2
    
    def validate(self) -> bool:
        """Validate."""
        return self.value >= 0

# Additional content
CONSTANT_{i} = {i}
DATA_{i} = {{"id": {i}, "name": "item_{i}"}}

'''  # ~25 lines per file
                file_path.write_text(content * 4)  # ~100 lines per file

            yield project

    def test_single_file_parsing_speed(self, large_python_file: Path) -> None:
        """Test parsing speed for a large single file."""
        parser = PythonParser()
        profiler = PerformanceProfiler()

        # Count lines
        with open(large_python_file) as f:
            line_count = sum(1 for _ in f)

        # Parse and measure
        with profiler.time_operation("parse_large_file"):
            result = parser.parse_file(large_python_file)

        summary = profiler.get_summary()
        parse_time_ms = summary["operations"]["parse_large_file"]["total_ms"]

        # Calculate rate
        lines_per_second = (line_count / parse_time_ms) * 1000

        # REQ-NFR-001: 100K lines in 30s = 3333 lines/sec minimum
        print(f"\nParsing: {line_count} lines in {parse_time_ms:.1f}ms")
        print(f"Rate: {lines_per_second:.0f} lines/second")
        print(f"Entities: {len(result.entities)}")

        # Should parse at least 3333 lines/second (100K/30s)
        assert lines_per_second >= 3333, (
            f"Parse rate {lines_per_second:.0f} below requirement of 3333 lines/sec"
        )

    def test_directory_parsing_speed(self, many_small_files: Path) -> None:
        """Test parsing speed for many small files."""
        from magatama_core.application.usecases.parse_usecase import (
            ParseDirectoryUseCase,
            ParseFileUseCase,
        )

        parser = PythonParser()
        graph = NetworkXKnowledgeGraph()

        parse_file = ParseFileUseCase(
            parsers={".py": parser},
            knowledge_graph=graph,
        )
        parse_dir = ParseDirectoryUseCase(parse_file_usecase=parse_file)

        # Count total lines
        total_lines = 0
        for f in many_small_files.rglob("*.py"):
            total_lines += sum(1 for _ in open(f))

        # Parse and measure
        start = time.perf_counter()
        result = parse_dir.execute(many_small_files)
        elapsed_ms = (time.perf_counter() - start) * 1000

        lines_per_second = (total_lines / elapsed_ms) * 1000

        print(f"\nDirectory parsing: {total_lines} lines in {elapsed_ms:.1f}ms")
        print(f"Files: {result.files_processed}")
        print(f"Rate: {lines_per_second:.0f} lines/second")

        # Should meet requirement
        assert lines_per_second >= 3333, f"Parse rate {lines_per_second:.0f} below requirement"


# ============================================================================
# REQ-NFR-002: Query Response Time
# ============================================================================


class TestQueryPerformance:
    """Tests for query response time requirements.

    REQ-NFR-002: Query response shall be under 200ms average,
    with 95th percentile under 500ms.
    """

    @pytest.fixture
    def populated_graph(self) -> NetworkXKnowledgeGraph:
        """Create a graph with many entities for query testing."""
        from magatama_core.domain.entities.code_entities import (
            ClassEntity,
            FunctionEntity,
            MethodEntity,
        )
        from magatama_core.domain.entities.relationships import Relationship, RelationshipType
        from magatama_core.domain.value_objects import EntityId, Location

        graph = NetworkXKnowledgeGraph()

        # Add 10000 entities
        for i in range(5000):
            func = FunctionEntity(
                id=EntityId(value=f"func_{i}"),
                name=f"function_{i}",
                location=Location(file=f"module_{i % 100}.py", line=i % 1000 + 1),
                docstring=f"Function {i} docstring",
            )
            graph.entities.add(func)

        for i in range(3000):
            cls = ClassEntity(
                id=EntityId(value=f"class_{i}"),
                name=f"Class_{i}",
                location=Location(file=f"module_{i % 100}.py", line=i % 1000 + 1),
                docstring=f"Class {i} docstring",
            )
            graph.entities.add(cls)

        for i in range(2000):
            method = MethodEntity(
                id=EntityId(value=f"method_{i}"),
                name=f"method_{i}",
                location=Location(file=f"module_{i % 100}.py", line=i % 1000 + 1),
                class_id=EntityId(value=f"class_{i % 1000}"),
            )
            graph.entities.add(method)

        # Add relationships
        for i in range(5000):
            rel = Relationship(
                source_id=EntityId(value=f"class_{i % 3000}"),
                target_id=EntityId(value=f"method_{i % 2000}"),
                type=RelationshipType.CONTAINS,
            )
            graph.relationships.add(rel)

        return graph

    def test_entity_search_performance(self, populated_graph: NetworkXKnowledgeGraph) -> None:
        """Test search performance meets requirements."""
        bench = Benchmark()

        def search_by_name():
            # Search for entities containing "function"
            all_entities = list(populated_graph.entities.all())
            return [e for e in all_entities if "function" in e.name.lower()]

        bench.register("search", search_by_name)
        result = bench.run("search", iterations=50, warmup=5)

        print("\nSearch performance:")
        print(f"  Mean: {result.mean_time_ms:.2f}ms")
        print(f"  Min: {result.min_time_ms:.2f}ms")
        print(f"  Max: {result.max_time_ms:.2f}ms")

        # REQ-NFR-002: Average under 200ms
        assert result.mean_time_ms < 200, (
            f"Search mean {result.mean_time_ms:.1f}ms exceeds 200ms limit"
        )

    def test_entity_retrieval_performance(self, populated_graph: NetworkXKnowledgeGraph) -> None:
        """Test entity retrieval by ID performance."""
        from magatama_core.domain.value_objects import EntityId

        bench = Benchmark()

        def get_entity():
            return populated_graph.entities.get(EntityId(value="func_2500"))

        bench.register("get_by_id", get_entity)
        result = bench.run("get_by_id", iterations=100, warmup=10)

        print("\nEntity retrieval performance:")
        print(f"  Mean: {result.mean_time_ms:.4f}ms")
        print(f"  Max: {result.max_time_ms:.4f}ms")

        # Should be very fast - under 10ms
        assert result.mean_time_ms < 10, f"Retrieval mean {result.mean_time_ms:.2f}ms too slow"

    def test_graph_traversal_performance(self, populated_graph: NetworkXKnowledgeGraph) -> None:
        """Test graph traversal performance."""
        from magatama_core.domain.value_objects import EntityId

        bench = Benchmark()

        def traverse():
            return populated_graph.get_neighbors(
                EntityId(value="class_500"),
                depth=2,
            )

        bench.register("traverse", traverse)
        result = bench.run("traverse", iterations=20, warmup=3)

        print("\nTraversal performance (depth=2):")
        print(f"  Mean: {result.mean_time_ms:.2f}ms")
        print(f"  Max: {result.max_time_ms:.2f}ms")

        # Should complete under 200ms average
        assert result.mean_time_ms < 200, (
            f"Traversal mean {result.mean_time_ms:.1f}ms exceeds limit"
        )


# ============================================================================
# REQ-NFR-003: Memory Usage
# ============================================================================


class TestMemoryUsage:
    """Tests for memory usage requirements.

    REQ-NFR-003: Memory usage shall not exceed 100MB at startup,
    and 500MB during operation.
    """

    def test_startup_memory(self) -> None:
        """Test that importing MAGATAMA uses under 100MB."""
        import tracemalloc

        tracemalloc.start()

        # Import core modules
        from magatama_core.infrastructure.parsers import PythonParser
        from magatama_core.infrastructure.storage import NetworkXKnowledgeGraph

        # Create basic instances
        parser = PythonParser()
        graph = NetworkXKnowledgeGraph()

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / (1024 * 1024)
        current_mb = current / (1024 * 1024)

        print("\nStartup memory:")
        print(f"  Current: {current_mb:.2f}MB")
        print(f"  Peak: {peak_mb:.2f}MB")

        # REQ-NFR-003: Under 100MB at startup
        assert peak_mb < 100, f"Startup memory {peak_mb:.1f}MB exceeds 100MB limit"

    def test_runtime_memory_with_large_graph(self) -> None:
        """Test memory usage with large graph under 500MB."""
        import tracemalloc

        gc.collect()
        tracemalloc.start()

        from magatama_core.domain.entities.code_entities import ClassEntity, FunctionEntity
        from magatama_core.domain.value_objects import EntityId, Location
        from magatama_core.infrastructure.storage import NetworkXKnowledgeGraph

        graph = NetworkXKnowledgeGraph()

        # Add 50000 entities (simulating large codebase)
        for i in range(30000):
            func = FunctionEntity(
                id=EntityId(value=f"func_{i}"),
                name=f"function_{i}",
                location=Location(file=f"module_{i % 500}.py", line=i % 1000 + 1),
                docstring=f"Docstring for function {i}",
            )
            graph.entities.add(func)

        for i in range(20000):
            cls = ClassEntity(
                id=EntityId(value=f"class_{i}"),
                name=f"Class_{i}",
                location=Location(file=f"module_{i % 500}.py", line=i % 1000 + 1),
                docstring=f"Class {i} documentation",
            )
            graph.entities.add(cls)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / (1024 * 1024)
        current_mb = current / (1024 * 1024)
        entity_count = graph.entities.count()

        print("\nRuntime memory (50K entities):")
        print(f"  Current: {current_mb:.2f}MB")
        print(f"  Peak: {peak_mb:.2f}MB")
        print(f"  Entities: {entity_count}")
        print(f"  Per entity: {(current_mb * 1024 * 1024) / entity_count:.0f} bytes")

        # REQ-NFR-003: Under 500MB during operation
        assert peak_mb < 500, f"Runtime memory {peak_mb:.1f}MB exceeds 500MB limit"


# ============================================================================
# REQ-NFR-006: Startup Time
# ============================================================================


class TestStartupTime:
    """Tests for startup time requirements.

    REQ-NFR-006: Server startup shall complete within 2 seconds.
    """

    def test_mcp_server_startup_time(self) -> None:
        """Test MCP server instantiation time."""
        start = time.perf_counter()

        from magatama_mcp.server.mcp_server import MagatamaMcpServer

        server = MagatamaMcpServer()

        # List tools to ensure full initialization
        _ = server.list_tools()
        _ = server.list_resources()

        elapsed_ms = (time.perf_counter() - start) * 1000

        print(f"\nMCP Server startup: {elapsed_ms:.1f}ms")

        # REQ-NFR-006: Under 2 seconds
        assert elapsed_ms < 2000, f"Server startup {elapsed_ms:.1f}ms exceeds 2000ms limit"

    def test_parser_initialization_time(self) -> None:
        """Test parser initialization time."""
        start = time.perf_counter()

        from magatama_core.infrastructure.parsers import (
            GoParser,
            JavaScriptParser,
            PythonParser,
            RustParser,
            TypeScriptParser,
        )

        # Initialize all parsers
        parsers = [
            PythonParser(),
            TypeScriptParser(),
            JavaScriptParser(),
            RustParser(),
            GoParser(),
        ]

        elapsed_ms = (time.perf_counter() - start) * 1000

        print(f"\nAll parsers initialization: {elapsed_ms:.1f}ms")

        # Should be fast - under 1 second
        assert elapsed_ms < 1000, f"Parser init {elapsed_ms:.1f}ms exceeds 1000ms limit"

    def test_cold_start_full_workflow(self) -> None:
        """Test cold start for complete workflow."""
        start = time.perf_counter()

        # Simulate cold start - fresh imports
        from magatama_mcp.server.mcp_server import MagatamaMcpServer

        server = MagatamaMcpServer()

        # Ensure ready to serve
        tools = server.list_tools()
        resources = server.list_resources()

        elapsed_ms = (time.perf_counter() - start) * 1000

        print(f"\nCold start workflow: {elapsed_ms:.1f}ms")
        print(f"  Tools: {len(tools)}")
        print(f"  Resources: {len(resources)}")

        # REQ-NFR-006: Under 2 seconds
        assert elapsed_ms < 2000, f"Cold start {elapsed_ms:.1f}ms exceeds 2000ms limit"


# ============================================================================
# SQLite Performance Tests
# ============================================================================


class TestSQLitePerformance:
    """Performance tests specific to SQLite storage."""

    def test_sqlite_bulk_insert_performance(self) -> None:
        """Test SQLite bulk insert performance."""
        from magatama_core.domain.entities.code_entities import FunctionEntity
        from magatama_core.domain.value_objects import EntityId, Location

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        try:
            bench = Benchmark()

            def bulk_insert():
                with SQLiteKnowledgeGraph(db_path) as graph:
                    graph.clear()
                    for i in range(1000):
                        entity = FunctionEntity(
                            id=EntityId(value=f"func_{i}"),
                            name=f"function_{i}",
                            location=Location(file="test.py", line=i + 1),
                        )
                        graph.entities.add(entity)

            bench.register("bulk_insert", bulk_insert)
            result = bench.run("bulk_insert", iterations=3, warmup=1)

            print("\nSQLite bulk insert (1000 entities):")
            print(f"  Mean: {result.mean_time_ms:.1f}ms")
            print(f"  Rate: {1000 / result.mean_time_ms * 1000:.0f} entities/sec")

            # Should insert at reasonable rate
            assert result.mean_time_ms < 5000, "SQLite insert too slow"

        finally:
            db_path.unlink(missing_ok=True)

    def test_sqlite_query_performance(self) -> None:
        """Test SQLite query performance."""
        from magatama_core.domain.entities.code_entities import FunctionEntity
        from magatama_core.domain.value_objects import EntityId, Location

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        try:
            # Populate database
            with SQLiteKnowledgeGraph(db_path) as graph:
                for i in range(10000):
                    entity = FunctionEntity(
                        id=EntityId(value=f"func_{i}"),
                        name=f"function_{i}",
                        location=Location(file=f"module_{i % 100}.py", line=i % 1000 + 1),
                    )
                    graph.entities.add(entity)

            bench = Benchmark()

            def query():
                with SQLiteKnowledgeGraph(db_path) as graph:
                    return list(graph.entities.get_by_type(EntityType.FUNCTION))

            bench.register("query", query)
            result = bench.run("query", iterations=10, warmup=2)

            print("\nSQLite query (10K entities by type):")
            print(f"  Mean: {result.mean_time_ms:.1f}ms")

            # Should be reasonably fast
            assert result.mean_time_ms < 1000, "SQLite query too slow"

        finally:
            db_path.unlink(missing_ok=True)


# ============================================================================
# Benchmark Suite Runner
# ============================================================================


class TestBenchmarkSuite:
    """Aggregate benchmark suite for reporting."""

    def test_generate_benchmark_report(self) -> None:
        """Generate a comprehensive benchmark report."""
        from magatama_core.domain.entities.code_entities import FunctionEntity
        from magatama_core.domain.value_objects import EntityId, Location

        bench = Benchmark()
        results = []

        # Test 1: Entity creation
        def create_entity():
            return FunctionEntity(
                id=EntityId(value="test"),
                name="test",
                location=Location(file="test.py", line=1),
            )

        bench.register("entity_creation", create_entity)
        results.append(bench.run("entity_creation", iterations=1000, warmup=100))

        # Test 2: Graph operations
        from magatama_core.infrastructure.storage import NetworkXKnowledgeGraph

        graph = NetworkXKnowledgeGraph()

        counter = [0]  # Use list for closure

        def add_entity():
            entity = FunctionEntity(
                id=EntityId(value=f"test_{counter[0]}"),
                name=f"test_{counter[0]}",
                location=Location(file="test.py", line=counter[0] + 1),
            )
            counter[0] += 1
            graph.entities.add(entity)

        bench.register("graph_add", add_entity)
        results.append(bench.run("graph_add", iterations=100, warmup=10))

        # Print report
        print("\n" + "=" * 60)
        print("MAGATAMA Performance Benchmark Report")
        print("=" * 60)
        for r in results:
            print(f"\n{r.name}:")
            print(f"  Iterations: {r.iterations}")
            print(f"  Mean: {r.mean_time_ms:.4f}ms")
            print(f"  Std Dev: {r.std_dev_ms:.4f}ms")
            print(f"  Min: {r.min_time_ms:.4f}ms")
            print(f"  Max: {r.max_time_ms:.4f}ms")
        print("\n" + "=" * 60)

        # Basic sanity check
        assert all(r.mean_time_ms >= 0 for r in results)
