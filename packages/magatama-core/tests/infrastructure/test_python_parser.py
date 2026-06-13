"""
Python Parser Tests - RED Phase First (Article III)

REQ-KGC-001: Entity extraction from Python code
Uses Tree-sitter for AST parsing.
"""

from pathlib import Path
from textwrap import dedent

import pytest

from magatama_core.domain.entities.base import EntityType
from magatama_core.domain.entities.code_entities import (
    ClassEntity,
    FunctionEntity,
    ModuleEntity,
)
from magatama_core.infrastructure.parsers.python_parser import PythonParser


class TestPythonParser:
    """Test Python code parser using Tree-sitter."""

    @pytest.fixture
    def parser(self) -> PythonParser:
        """Create a PythonParser instance."""
        return PythonParser()

    @pytest.mark.unit
    def test_parser_initialization(self, parser: PythonParser) -> None:
        """Test parser initializes correctly."""
        assert parser is not None
        assert parser.language == "python"

    @pytest.mark.unit
    def test_parse_simple_function(self, parser: PythonParser) -> None:
        """Test parsing a simple function."""
        code = dedent('''
            def hello(name: str) -> str:
                """Say hello."""
                return f"Hello, {name}!"
        ''').strip()

        result = parser.parse_string(code, file_path="test.py")

        functions = [e for e in result.entities if e.type == EntityType.FUNCTION]
        assert len(functions) == 1

        func = functions[0]
        assert isinstance(func, FunctionEntity)
        assert func.name == "hello"
        assert func.parameters == [("name", "str")]
        assert func.return_type == "str"
        assert func.docstring == "Say hello."

    @pytest.mark.unit
    def test_parse_function_without_types(self, parser: PythonParser) -> None:
        """Test parsing function without type hints."""
        code = dedent("""
            def add(a, b):
                return a + b
        """).strip()

        result = parser.parse_string(code, file_path="test.py")

        functions = [e for e in result.entities if e.type == EntityType.FUNCTION]
        assert len(functions) == 1

        func = functions[0]
        assert func.name == "add"
        assert func.parameters == [("a", None), ("b", None)]
        assert func.return_type is None

    @pytest.mark.unit
    def test_parse_simple_class(self, parser: PythonParser) -> None:
        """Test parsing a simple class."""
        code = dedent('''
            class Calculator:
                """A simple calculator."""
                
                def add(self, a: int, b: int) -> int:
                    return a + b
        ''').strip()

        result = parser.parse_string(code, file_path="test.py")

        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) == 1

        cls = classes[0]
        assert isinstance(cls, ClassEntity)
        assert cls.name == "Calculator"
        assert cls.docstring == "A simple calculator."

    @pytest.mark.unit
    def test_parse_class_with_inheritance(self, parser: PythonParser) -> None:
        """Test parsing class with base classes."""
        code = dedent("""
            class ChildClass(ParentClass, Mixin):
                pass
        """).strip()

        result = parser.parse_string(code, file_path="test.py")

        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) == 1

        cls = classes[0]
        assert "ParentClass" in cls.bases
        assert "Mixin" in cls.bases

    @pytest.mark.unit
    def test_parse_class_methods(self, parser: PythonParser) -> None:
        """Test parsing class methods."""
        code = dedent("""
            class MyClass:
                def __init__(self, value: int) -> None:
                    self.value = value
                
                def get_value(self) -> int:
                    return self.value
                
                @staticmethod
                def static_method() -> str:
                    return "static"
                
                @classmethod
                def class_method(cls) -> str:
                    return "class"
        """).strip()

        result = parser.parse_string(code, file_path="test.py")

        methods = [e for e in result.entities if e.type == EntityType.METHOD]
        assert len(methods) == 4

        method_names = {m.name for m in methods}
        assert "__init__" in method_names
        assert "get_value" in method_names
        assert "static_method" in method_names
        assert "class_method" in method_names

    @pytest.mark.unit
    def test_parse_decorated_function(self, parser: PythonParser) -> None:
        """Test parsing function with decorators."""
        code = dedent("""
            @decorator1
            @decorator2("arg")
            def decorated_func():
                pass
        """).strip()

        result = parser.parse_string(code, file_path="test.py")

        functions = [e for e in result.entities if e.type == EntityType.FUNCTION]
        assert len(functions) == 1

        func = functions[0]
        assert "decorator1" in func.decorators
        assert "decorator2" in func.decorators

    @pytest.mark.unit
    def test_parse_async_function(self, parser: PythonParser) -> None:
        """Test parsing async function."""
        code = dedent('''
            async def fetch_data(url: str) -> dict:
                """Fetch data from URL."""
                pass
        ''').strip()

        result = parser.parse_string(code, file_path="test.py")

        functions = [e for e in result.entities if e.type == EntityType.FUNCTION]
        assert len(functions) == 1

        func = functions[0]
        assert func.name == "fetch_data"
        assert func.is_async is True

    @pytest.mark.unit
    def test_parse_module_imports(self, parser: PythonParser) -> None:
        """Test parsing imports creates relationships."""
        code = dedent("""
            import os
            from pathlib import Path
            from typing import List, Optional
        """).strip()

        result = parser.parse_string(code, file_path="test.py")

        # Should have import relationships
        assert len(result.imports) >= 3
        assert "os" in result.imports
        assert "pathlib" in result.imports

    @pytest.mark.unit
    def test_parse_file(self, parser: PythonParser, tmp_path: Path) -> None:
        """Test parsing from file path."""
        code = dedent("""
            def greet():
                return "Hello"
        """).strip()

        test_file = tmp_path / "test_module.py"
        test_file.write_text(code)

        result = parser.parse_file(test_file)

        assert result.file_path == test_file
        functions = [e for e in result.entities if e.type == EntityType.FUNCTION]
        assert len(functions) == 1

    @pytest.mark.unit
    def test_parse_result_has_module_entity(self, parser: PythonParser) -> None:
        """Test parse result includes module entity."""
        code = dedent('''
            """Module docstring."""
            
            def func():
                pass
        ''').strip()

        result = parser.parse_string(code, file_path="mymodule.py")

        modules = [e for e in result.entities if e.type == EntityType.MODULE]
        assert len(modules) == 1

        mod = modules[0]
        assert isinstance(mod, ModuleEntity)
        assert mod.name == "mymodule"
        assert mod.docstring == "Module docstring."

    @pytest.mark.unit
    def test_entity_locations(self, parser: PythonParser) -> None:
        """Test entities have correct locations."""
        code = dedent("""
            def first_func():
                pass
            
            def second_func():
                pass
        """).strip()

        result = parser.parse_string(code, file_path="test.py")

        functions = [e for e in result.entities if e.type == EntityType.FUNCTION]
        assert len(functions) == 2

        # First function at line 1
        first = next(f for f in functions if f.name == "first_func")
        assert first.location.line == 1

        # Second function at line 4
        second = next(f for f in functions if f.name == "second_func")
        assert second.location.line == 4

    @pytest.mark.unit
    def test_parse_function_calls_relationship(self, parser: PythonParser) -> None:
        """Test that function calls create CALLS relationships."""
        from magatama_core.domain.entities.relationships import RelationshipType

        code = dedent("""
            def helper():
                return 42
            
            def main():
                result = helper()
                return result
        """).strip()

        result = parser.parse_string(code, file_path="test.py")

        # Should have CALLS relationship: main -> helper
        calls_relationships = [r for r in result.relationships if r.type == RelationshipType.CALLS]
        assert len(calls_relationships) >= 1

        # Verify the relationship
        functions = {e.name: e for e in result.entities if e.type == EntityType.FUNCTION}
        main_id = functions["main"].id
        helper_id = functions["helper"].id

        assert any(r.source_id == main_id and r.target_id == helper_id for r in calls_relationships)

    @pytest.mark.unit
    def test_parse_multiple_calls(self, parser: PythonParser) -> None:
        """Test detection of multiple function calls."""
        from magatama_core.domain.entities.relationships import RelationshipType

        code = dedent("""
            def foo():
                pass
            
            def bar():
                pass
            
            def baz():
                foo()
                bar()
        """).strip()

        result = parser.parse_string(code, file_path="test.py")

        calls_relationships = [r for r in result.relationships if r.type == RelationshipType.CALLS]

        # baz should call both foo and bar
        functions = {e.name: e for e in result.entities if e.type == EntityType.FUNCTION}
        baz_id = functions["baz"].id
        foo_id = functions["foo"].id
        bar_id = functions["bar"].id

        baz_calls = [r for r in calls_relationships if r.source_id == baz_id]
        assert len(baz_calls) == 2

        target_ids = {r.target_id for r in baz_calls}
        assert foo_id in target_ids
        assert bar_id in target_ids

    @pytest.mark.unit
    def test_parse_nested_calls(self, parser: PythonParser) -> None:
        """Test detection of nested function calls."""
        from magatama_core.domain.entities.relationships import RelationshipType

        code = dedent("""
            def inner():
                return 1
            
            def outer():
                return inner() + inner()
        """).strip()

        result = parser.parse_string(code, file_path="test.py")

        calls_relationships = [r for r in result.relationships if r.type == RelationshipType.CALLS]

        # outer should call inner (only one unique relationship)
        functions = {e.name: e for e in result.entities if e.type == EntityType.FUNCTION}
        outer_id = functions["outer"].id
        inner_id = functions["inner"].id

        # Should not duplicate
        outer_to_inner = [
            r for r in calls_relationships if r.source_id == outer_id and r.target_id == inner_id
        ]
        assert len(outer_to_inner) == 1

    @pytest.mark.unit
    def test_parse_method_calls_within_class(self, parser: PythonParser) -> None:
        """Test detection of method calls via self."""
        from magatama_core.domain.entities.relationships import RelationshipType

        code = dedent("""
            class MyClass:
                def helper(self):
                    return 42
                
                def main(self):
                    return self.helper()
        """).strip()

        result = parser.parse_string(code, file_path="test.py")

        calls_relationships = [r for r in result.relationships if r.type == RelationshipType.CALLS]

        # main should call helper
        methods = {e.name: e for e in result.entities if e.type == EntityType.METHOD}
        main_id = methods["main"].id
        helper_id = methods["helper"].id

        assert any(r.source_id == main_id and r.target_id == helper_id for r in calls_relationships)

    @pytest.mark.unit
    def test_no_self_calls_relationship(self, parser: PythonParser) -> None:
        """Test that recursive calls don't create self-referencing relationships."""
        from magatama_core.domain.entities.relationships import RelationshipType

        code = dedent("""
            def recursive(n):
                if n <= 0:
                    return 0
                return recursive(n - 1)
        """).strip()

        result = parser.parse_string(code, file_path="test.py")

        # Should NOT have self-referencing CALLS
        calls_relationships = [r for r in result.relationships if r.type == RelationshipType.CALLS]

        # No relationship where source == target
        assert all(r.source_id != r.target_id for r in calls_relationships)

    @pytest.mark.unit
    def test_parse_imports_relationship(self, parser: PythonParser) -> None:
        """Test that import statements create IMPORTS relationships."""
        from magatama_core.domain.entities.relationships import RelationshipType

        code = dedent("""
            import os
            import sys
            
            def main():
                pass
        """).strip()

        result = parser.parse_string(code, file_path="test.py")

        # Should have IMPORTS relationships for os and sys
        imports_relationships = [
            r for r in result.relationships if r.type == RelationshipType.IMPORTS
        ]
        assert len(imports_relationships) >= 2

        # Verify module names in metadata
        imported_modules = {r.metadata.get("module_name") for r in imports_relationships}
        assert "os" in imported_modules
        assert "sys" in imported_modules

    @pytest.mark.unit
    def test_parse_from_imports_relationship(self, parser: PythonParser) -> None:
        """Test that 'from x import y' creates IMPORTS relationships."""
        from magatama_core.domain.entities.relationships import RelationshipType

        code = dedent("""
            from pathlib import Path
            from typing import List, Optional
        """).strip()

        result = parser.parse_string(code, file_path="test.py")

        imports_relationships = [
            r for r in result.relationships if r.type == RelationshipType.IMPORTS
        ]
        assert len(imports_relationships) >= 2

        # Verify module names in metadata
        imported_modules = {r.metadata.get("module_name") for r in imports_relationships}
        assert "pathlib" in imported_modules
        assert "typing" in imported_modules

        # Check imported names in metadata
        pathlib_import = next(
            (r for r in imports_relationships if r.metadata.get("module_name") == "pathlib"), None
        )
        assert pathlib_import is not None
        assert "Path" in pathlib_import.metadata.get("imported_names", [])

    @pytest.mark.unit
    def test_imports_relationship_source_is_module(self, parser: PythonParser) -> None:
        """Test that IMPORTS relationship source is the module entity."""
        from magatama_core.domain.entities.relationships import RelationshipType

        code = dedent("""
            import json
        """).strip()

        result = parser.parse_string(code, file_path="mymodule.py")

        # Get module entity
        modules = [e for e in result.entities if e.type == EntityType.MODULE]
        assert len(modules) == 1
        module = modules[0]

        # Check import relationship source
        imports_relationships = [
            r for r in result.relationships if r.type == RelationshipType.IMPORTS
        ]
        assert len(imports_relationships) >= 1

        # All imports should have module as source
        assert all(r.source_id == module.id for r in imports_relationships)
