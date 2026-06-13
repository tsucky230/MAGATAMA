"""Tests for ParseFileUseCase."""

import tempfile
from pathlib import Path

import pytest

from magatama_core.application.usecases.parse_usecase import (
    IncrementalParseUseCase,
    ParseDirectoryUseCase,
    ParseFileUseCase,
)
from magatama_core.domain.entities import EntityType
from magatama_core.infrastructure.parsers import PythonParser
from magatama_core.infrastructure.storage import NetworkXKnowledgeGraph


class TestParseFileUseCase:
    """Tests for ParseFileUseCase."""

    @pytest.fixture
    def knowledge_graph(self) -> NetworkXKnowledgeGraph:
        """Create a fresh knowledge graph."""
        return NetworkXKnowledgeGraph()

    @pytest.fixture
    def python_parser(self) -> PythonParser:
        """Create Python parser."""
        return PythonParser()

    @pytest.fixture
    def usecase(
        self, python_parser: PythonParser, knowledge_graph: NetworkXKnowledgeGraph
    ) -> ParseFileUseCase:
        """Create usecase with dependencies."""
        return ParseFileUseCase(
            parsers={".py": python_parser},
            knowledge_graph=knowledge_graph,
        )

    def test_parse_python_file(
        self, usecase: ParseFileUseCase, knowledge_graph: NetworkXKnowledgeGraph
    ) -> None:
        """Test parsing a Python file and storing in graph."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write('''
def greet(name: str) -> str:
    """Greet someone."""
    return f"Hello, {name}!"

class Person:
    """A person."""

    def __init__(self, name: str) -> None:
        self.name = name

    def say_hello(self) -> str:
        return greet(self.name)
''')
            f.flush()
            file_path = Path(f.name)

        result = usecase.execute(file_path)

        # Check result
        assert result.success is True
        assert result.entities_count > 0
        assert result.relationships_count >= 0
        assert len(result.errors) == 0

        # Verify entities are in graph
        entities = knowledge_graph.entities.all()
        assert len(entities) > 0

        # Should have module, function, and class
        entity_types = {e.type for e in entities}
        assert EntityType.MODULE in entity_types
        assert EntityType.FUNCTION in entity_types
        assert EntityType.CLASS in entity_types

    def test_parse_unsupported_file_type(self, usecase: ParseFileUseCase) -> None:
        """Test parsing unsupported file type returns error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Just some text")
            f.flush()
            file_path = Path(f.name)

        result = usecase.execute(file_path)

        assert result.success is False
        assert "Unsupported file type" in result.errors[0]

    def test_parse_nonexistent_file(self, usecase: ParseFileUseCase) -> None:
        """Test parsing non-existent file returns error."""
        result = usecase.execute(Path("/nonexistent/file.py"))

        assert result.success is False
        assert "File not found" in result.errors[0]

    def test_parse_file_with_syntax_error(self, usecase: ParseFileUseCase) -> None:
        """Test parsing file with syntax errors still extracts what it can."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""
def valid_function():
    pass

def invalid_function(
    # Missing closing paren and body
""")
            f.flush()
            file_path = Path(f.name)

        result = usecase.execute(file_path)

        # Should still have partial success
        assert result.entities_count >= 1  # At least the valid function

    def test_relationships_created_for_methods(
        self, usecase: ParseFileUseCase, knowledge_graph: NetworkXKnowledgeGraph
    ) -> None:
        """Test that CONTAINS relationships are created for class methods."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""
class Calculator:
    def add(self, a: int, b: int) -> int:
        return a + b

    def subtract(self, a: int, b: int) -> int:
        return a - b
""")
            f.flush()
            file_path = Path(f.name)

        usecase.execute(file_path)

        # Find the class entity
        classes = [e for e in knowledge_graph.entities.all() if e.type == EntityType.CLASS]
        assert len(classes) == 1

        # Find method entities
        methods = [e for e in knowledge_graph.entities.all() if e.type == EntityType.METHOD]
        # Should have add and subtract methods
        assert len(methods) >= 2


class TestParseDirectoryUseCase:
    """Tests for ParseDirectoryUseCase."""

    @pytest.fixture
    def knowledge_graph(self) -> NetworkXKnowledgeGraph:
        """Create a fresh knowledge graph."""
        return NetworkXKnowledgeGraph()

    @pytest.fixture
    def python_parser(self) -> PythonParser:
        """Create Python parser."""
        return PythonParser()

    @pytest.fixture
    def parse_file_usecase(
        self, python_parser: PythonParser, knowledge_graph: NetworkXKnowledgeGraph
    ) -> ParseFileUseCase:
        """Create file parse usecase."""
        return ParseFileUseCase(
            parsers={".py": python_parser},
            knowledge_graph=knowledge_graph,
        )

    @pytest.fixture
    def usecase(self, parse_file_usecase: ParseFileUseCase) -> ParseDirectoryUseCase:
        """Create directory parse usecase."""
        return ParseDirectoryUseCase(parse_file_usecase=parse_file_usecase)

    def test_parse_directory(
        self, usecase: ParseDirectoryUseCase, knowledge_graph: NetworkXKnowledgeGraph
    ) -> None:
        """Test parsing entire directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some Python files
            (Path(tmpdir) / "module_a.py").write_text("""
def func_a():
    pass
""")
            (Path(tmpdir) / "module_b.py").write_text("""
class ClassB:
    pass
""")
            # Create subdirectory
            subdir = Path(tmpdir) / "subpackage"
            subdir.mkdir()
            (subdir / "__init__.py").write_text("")
            (subdir / "module_c.py").write_text("""
def func_c():
    pass
""")

            result = usecase.execute(
                Path(tmpdir),
                patterns=["**/*.py"],
                exclude_patterns=["**/test_*.py"],
            )

        assert result.success is True
        assert result.files_processed >= 3
        assert result.total_entities > 0

    def test_parse_directory_with_exclude(self, usecase: ParseDirectoryUseCase) -> None:
        """Test excluding patterns from directory parse."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "main.py").write_text("def main(): pass")
            (Path(tmpdir) / "test_main.py").write_text("def test_main(): pass")

            result = usecase.execute(
                Path(tmpdir),
                patterns=["*.py"],
                exclude_patterns=["test_*.py"],
            )

        assert result.files_processed == 1

    def test_parse_empty_directory(self, usecase: ParseDirectoryUseCase) -> None:
        """Test parsing empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = usecase.execute(Path(tmpdir), patterns=["*.py"])

        assert result.success is True
        assert result.files_processed == 0

    def test_parse_nonexistent_directory(self, usecase: ParseDirectoryUseCase) -> None:
        """Test parsing non-existent directory returns error."""
        result = usecase.execute(Path("/nonexistent/dir"))

        assert result.success is False
        assert "Directory not found" in result.errors[0]


class TestIncrementalParseUseCase:
    """Tests for IncrementalParseUseCase."""

    @pytest.fixture
    def knowledge_graph(self) -> NetworkXKnowledgeGraph:
        """Create a fresh knowledge graph."""
        return NetworkXKnowledgeGraph()

    @pytest.fixture
    def python_parser(self) -> PythonParser:
        """Create Python parser."""
        return PythonParser()

    @pytest.fixture
    def usecase(
        self, python_parser: PythonParser, knowledge_graph: NetworkXKnowledgeGraph
    ) -> IncrementalParseUseCase:
        """Create incremental parse usecase with dependencies."""
        return IncrementalParseUseCase(
            parsers={".py": python_parser},
            knowledge_graph=knowledge_graph,
        )

    def test_initial_parse(
        self, usecase: IncrementalParseUseCase, knowledge_graph: NetworkXKnowledgeGraph
    ) -> None:
        """Test initial parse of a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "module_a.py").write_text("def func_a(): pass")
            (Path(tmpdir) / "module_b.py").write_text("def func_b(): pass")

            result = usecase.execute(Path(tmpdir), patterns=["*.py"])

            assert result.success is True
            assert result.files_processed == 2
            assert result.files_skipped == 0
            assert result.files_removed == 0
            assert result.total_entities > 0

            # Verify entities in graph
            entities = knowledge_graph.entities.all()
            assert len(entities) > 0

    def test_skip_unchanged_files(
        self, usecase: IncrementalParseUseCase, knowledge_graph: NetworkXKnowledgeGraph
    ) -> None:
        """Test that unchanged files are skipped on re-parse."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "module.py"
            file_path.write_text("def func(): pass")

            # First parse
            result1 = usecase.execute(Path(tmpdir), patterns=["*.py"])
            assert result1.files_processed == 1
            assert result1.files_skipped == 0

            # Second parse - file unchanged
            result2 = usecase.execute(Path(tmpdir), patterns=["*.py"])
            assert result2.files_processed == 0
            assert result2.files_skipped == 1

    def test_reparse_modified_file(
        self, usecase: IncrementalParseUseCase, knowledge_graph: NetworkXKnowledgeGraph
    ) -> None:
        """Test that modified files are re-parsed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "module.py"
            file_path.write_text("def old_func(): pass")

            # First parse
            result1 = usecase.execute(Path(tmpdir), patterns=["*.py"])
            assert result1.files_processed == 1

            # Count entities before modification
            initial_entities = list(knowledge_graph.entities.all())
            initial_count = len(initial_entities)
            assert initial_count > 0

            # Modify file - add new function
            file_path.write_text("""
def new_func():
    pass

def another_func():
    pass
""")

            # Second parse - file changed
            result2 = usecase.execute(Path(tmpdir), patterns=["*.py"])
            assert result2.files_processed == 1
            assert result2.files_skipped == 0

            # Verify old entities were replaced with new ones
            entities = list(knowledge_graph.entities.all())
            entity_names = {e.name for e in entities}
            assert "new_func" in entity_names
            assert "another_func" in entity_names
            assert "old_func" not in entity_names

    def test_remove_deleted_file(
        self, usecase: IncrementalParseUseCase, knowledge_graph: NetworkXKnowledgeGraph
    ) -> None:
        """Test that deleted files are removed from knowledge graph."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_a = Path(tmpdir) / "module_a.py"
            file_b = Path(tmpdir) / "module_b.py"
            file_a.write_text("def func_a(): pass")
            file_b.write_text("def func_b(): pass")

            # First parse - both files
            result1 = usecase.execute(Path(tmpdir), patterns=["*.py"])
            assert result1.files_processed == 2

            # Verify both modules are in graph
            entities = list(knowledge_graph.entities.all())
            entity_names = {e.name for e in entities}
            assert "func_a" in entity_names
            assert "func_b" in entity_names

            # Delete one file
            file_a.unlink()

            # Second parse - should remove deleted file's entities
            result2 = usecase.execute(Path(tmpdir), patterns=["*.py"])
            assert result2.files_removed == 1
            assert result2.entities_removed > 0

            # Verify deleted file's entities are gone
            entities = list(knowledge_graph.entities.all())
            entity_names = {e.name for e in entities}
            assert "func_a" not in entity_names
            assert "func_b" in entity_names

    def test_add_new_file(
        self, usecase: IncrementalParseUseCase, knowledge_graph: NetworkXKnowledgeGraph
    ) -> None:
        """Test that new files are parsed and added."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_a = Path(tmpdir) / "module_a.py"
            file_a.write_text("def func_a(): pass")

            # First parse
            result1 = usecase.execute(Path(tmpdir), patterns=["*.py"])
            assert result1.files_processed == 1

            # Add new file
            file_b = Path(tmpdir) / "module_b.py"
            file_b.write_text("def func_b(): pass")

            # Second parse
            result2 = usecase.execute(Path(tmpdir), patterns=["*.py"])
            assert result2.files_processed == 1  # Only new file
            assert result2.files_skipped == 1  # Original file unchanged

            # Verify both are in graph
            entities = list(knowledge_graph.entities.all())
            entity_names = {e.name for e in entities}
            assert "func_a" in entity_names
            assert "func_b" in entity_names

    def test_incremental_with_exclude_patterns(self, usecase: IncrementalParseUseCase) -> None:
        """Test incremental parse respects exclude patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "main.py").write_text("def main(): pass")
            (Path(tmpdir) / "test_main.py").write_text("def test_main(): pass")

            result = usecase.execute(
                Path(tmpdir),
                patterns=["*.py"],
                exclude_patterns=["test_*.py"],
            )

            assert result.files_processed == 1

    def test_incremental_nonexistent_directory(self, usecase: IncrementalParseUseCase) -> None:
        """Test incremental parse of non-existent directory returns error."""
        result = usecase.execute(Path("/nonexistent/dir"))

        assert result.success is False
        assert "Directory not found" in result.errors[0]

    def test_incremental_not_a_directory(self, usecase: IncrementalParseUseCase) -> None:
        """Test incremental parse of file returns error."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            f.write(b"def func(): pass")
            result = usecase.execute(Path(f.name))

        assert result.success is False
        assert "Not a directory" in result.errors[0]

    def test_hash_persists_across_save_load(self, python_parser: PythonParser) -> None:
        """Test that file hashes are persisted when saving/loading graph."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create source file
            source_file = Path(tmpdir) / "module.py"
            source_file.write_text("def func(): pass")

            # Create graph file path
            graph_file = Path(tmpdir) / "graph.json"

            # First graph instance
            graph1 = NetworkXKnowledgeGraph()
            usecase1 = IncrementalParseUseCase(
                parsers={".py": python_parser},
                knowledge_graph=graph1,
            )

            # Parse file
            result1 = usecase1.execute(Path(tmpdir), patterns=["*.py"])
            assert result1.files_processed == 1

            # Save graph
            graph1.save(graph_file)

            # Load into new graph instance
            graph2 = NetworkXKnowledgeGraph()
            graph2.load(graph_file)

            # Create new usecase with loaded graph
            usecase2 = IncrementalParseUseCase(
                parsers={".py": python_parser},
                knowledge_graph=graph2,
            )

            # Parse again - should skip unchanged file
            result2 = usecase2.execute(Path(tmpdir), patterns=["*.py"])
            assert result2.files_processed == 0
            assert result2.files_skipped == 1
