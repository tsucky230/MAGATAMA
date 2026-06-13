"""Tests for Go Parser.

Tests REQ-LANG-005: Go support
ADR-003: Tree-sitter for multi-language support
"""

from pathlib import Path

import pytest

from magatama_core.domain.entities import EntityType
from magatama_core.domain.entities.relationships import RelationshipType
from magatama_core.infrastructure.parsers.go_parser import GoParser


class TestGoParser:
    """Tests for GoParser."""

    @pytest.fixture
    def parser(self) -> GoParser:
        """Create a GoParser instance."""
        return GoParser()

    def test_parser_initialization(self, parser: GoParser) -> None:
        """Test parser initializes correctly."""
        assert parser is not None

    def test_parse_simple_function(self, parser: GoParser) -> None:
        """Test parsing a simple function."""
        code = """package main

func greet(name string) string {
    return "Hello, " + name
}
"""
        result = parser.parse_string(code, "test.go")

        assert result.file_path == "test.go"
        assert len(result.errors) == 0

        # Find function entity
        functions = [e for e in result.entities if e.type == EntityType.FUNCTION]
        assert len(functions) == 1
        assert functions[0].name == "greet"

    def test_parse_exported_function(self, parser: GoParser) -> None:
        """Test parsing an exported function (starts with uppercase)."""
        code = """package main

func PublicFunction() int {
    return 42
}

func privateFunction() int {
    return 0
}
"""
        result = parser.parse_string(code, "test.go")
        functions = [e for e in result.entities if e.type == EntityType.FUNCTION]
        assert len(functions) == 2

        public = next(f for f in functions if f.name == "PublicFunction")
        private = next(f for f in functions if f.name == "privateFunction")

        assert public.scope == "public"
        assert private.scope == "private"

    def test_parse_struct(self, parser: GoParser) -> None:
        """Test parsing a struct."""
        code = """package main

type User struct {
    Name string
    Age  int
}
"""
        result = parser.parse_string(code, "test.go")
        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) == 1
        assert classes[0].name == "User"

    def test_parse_interface(self, parser: GoParser) -> None:
        """Test parsing an interface."""
        code = """package main

type Writer interface {
    Write(data []byte) (int, error)
    Close() error
}
"""
        result = parser.parse_string(code, "test.go")
        interfaces = [e for e in result.entities if e.type == EntityType.INTERFACE]
        assert len(interfaces) == 1
        assert interfaces[0].name == "Writer"
        assert "Write" in interfaces[0].method_signatures
        assert "Close" in interfaces[0].method_signatures

    def test_parse_method(self, parser: GoParser) -> None:
        """Test parsing methods with receivers."""
        code = """package main

type Point struct {
    X, Y float64
}

func (p Point) Distance() float64 {
    return p.X * p.X + p.Y * p.Y
}

func (p *Point) Scale(factor float64) {
    p.X *= factor
    p.Y *= factor
}
"""
        result = parser.parse_string(code, "test.go")
        methods = [e for e in result.entities if e.type == EntityType.METHOD]
        assert len(methods) == 2
        method_names = {m.name for m in methods}
        assert method_names == {"Distance", "Scale"}

    def test_parse_type_alias(self, parser: GoParser) -> None:
        """Test parsing a type alias."""
        code = """package main

type UserID int64
"""
        result = parser.parse_string(code, "test.go")
        types = [e for e in result.entities if e.type == EntityType.TYPE]
        assert len(types) == 1
        assert types[0].name == "UserID"

    def test_parse_imports(self, parser: GoParser) -> None:
        """Test parsing import statements."""
        code = """package main

import (
    "fmt"
    "net/http"
    "encoding/json"
)

func main() {}
"""
        result = parser.parse_string(code, "test.go")

        # Check imports list
        assert "fmt" in result.imports
        assert "net/http" in result.imports
        assert "encoding/json" in result.imports

    def test_parse_single_import(self, parser: GoParser) -> None:
        """Test parsing a single import statement."""
        code = """package main

import "fmt"

func main() {
    fmt.Println("hello")
}
"""
        result = parser.parse_string(code, "test.go")
        assert "fmt" in result.imports

    def test_parse_function_calls_relationship(self, parser: GoParser) -> None:
        """Test parsing function call relationships."""
        code = """package main

func helper() int {
    return 42
}

func main() {
    result := helper()
    _ = result
}
"""
        result = parser.parse_string(code, "test.go")

        calls = [r for r in result.relationships if r.type == RelationshipType.CALLS]
        # Should detect main -> helper call
        assert len(calls) >= 1

    def test_parse_module(self, parser: GoParser) -> None:
        """Test that module entity is created with package name."""
        code = """package mypackage

func Example() {}
"""
        result = parser.parse_string(code, "test.go")
        modules = [e for e in result.entities if e.type == EntityType.MODULE]
        assert len(modules) == 1
        assert modules[0].name == "mypackage"

    def test_parse_file(self, parser: GoParser, tmp_path: Path) -> None:
        """Test parsing a file from disk."""
        go_file = tmp_path / "example.go"
        go_file.write_text("""package main

func Add(a, b int) int {
    return a + b
}
""")

        result = parser.parse_file(go_file)

        assert str(go_file) in result.file_path
        functions = [e for e in result.entities if e.type == EntityType.FUNCTION]
        assert len(functions) == 1
        assert functions[0].name == "Add"

    def test_entity_locations(self, parser: GoParser) -> None:
        """Test that entity locations are correct."""
        code = """package main

func first() {}

func second() {}
"""
        result = parser.parse_string(code, "test.go")
        functions = [e for e in result.entities if e.type == EntityType.FUNCTION]

        first = next(f for f in functions if f.name == "first")
        second = next(f for f in functions if f.name == "second")

        assert first.location.line == 3
        assert second.location.line == 5

    def test_parse_multiple_return_values(self, parser: GoParser) -> None:
        """Test parsing functions with multiple return values."""
        code = """package main

func divmod(a, b int) (int, int) {
    return a / b, a % b
}
"""
        result = parser.parse_string(code, "test.go")
        functions = [e for e in result.entities if e.type == EntityType.FUNCTION]
        assert len(functions) == 1
        assert functions[0].name == "divmod"
        # Return type should be captured
        assert functions[0].return_type is not None
