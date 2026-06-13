"""Tests for Julia Parser."""

import pytest

from magatama_core.domain.entities import EntityType
from magatama_core.infrastructure.parsers import JuliaParser


@pytest.fixture
def parser() -> JuliaParser:
    return JuliaParser()


class TestJuliaParserBasic:
    """Basic Julia parsing tests."""

    def test_parse_empty_string(self, parser: JuliaParser) -> None:
        result = parser.parse_string("", "test.jl")
        assert result.file_path == "test.jl"
        assert len(result.errors) == 0

    def test_parse_function(self, parser: JuliaParser) -> None:
        code = """
function add(x, y)
    return x + y
end
"""
        result = parser.parse_string(code, "test.jl")
        # Should have at least module entity
        assert len(result.entities) >= 1

    def test_parse_short_function(self, parser: JuliaParser) -> None:
        code = """
square(x) = x^2
"""
        result = parser.parse_string(code, "test.jl")
        assert len(result.entities) >= 1

    def test_parse_struct(self, parser: JuliaParser) -> None:
        code = """
struct Point
    x::Float64
    y::Float64
end
"""
        result = parser.parse_string(code, "test.jl")
        # Should have at least module entity
        assert len(result.entities) >= 1

    def test_parse_module(self, parser: JuliaParser) -> None:
        code = """
module MyModule

export greet

function greet(name)
    println("Hello, $name")
end

end
"""
        result = parser.parse_string(code, "test.jl")
        modules = [e for e in result.entities if e.type == EntityType.MODULE]
        assert len(modules) >= 1


class TestJuliaParserAdvanced:
    """Advanced Julia parsing tests."""

    def test_parse_imports(self, parser: JuliaParser) -> None:
        code = """
using LinearAlgebra
import Statistics: mean, std

function compute(x)
    return mean(x)
end
"""
        result = parser.parse_string(code, "test.jl")
        assert len(result.entities) >= 1

    def test_parse_abstract_type(self, parser: JuliaParser) -> None:
        code = """
abstract type Animal end

struct Dog <: Animal
    name::String
end
"""
        result = parser.parse_string(code, "test.jl")
        assert len(result.entities) >= 1

    def test_parse_macro(self, parser: JuliaParser) -> None:
        code = """
macro sayhello(name)
    return :( println("Hello, ", $name) )
end
"""
        result = parser.parse_string(code, "test.jl")
        assert len(result.entities) >= 1

    def test_parse_mutable_struct(self, parser: JuliaParser) -> None:
        code = """
mutable struct Counter
    value::Int
end
"""
        result = parser.parse_string(code, "test.jl")
        assert len(result.entities) >= 1


class TestJuliaParserEntityExtraction:
    """Tests for Julia parser entity extraction."""

    def test_extract_multiple_functions(self, parser: JuliaParser) -> None:
        """Test extracting multiple functions."""
        code = """
function add(x, y)
    return x + y
end

function sub(x, y)
    return x - y
end

function mul(x, y)
    return x * y
end
"""
        result = parser.parse_string(code, "test.jl")
        assert len(result.errors) == 0
        assert len(result.entities) >= 1

    def test_extract_parametric_types(self, parser: JuliaParser) -> None:
        """Test parametric type parsing."""
        code = """
struct Container{T}
    value::T
end
"""
        result = parser.parse_string(code, "test.jl")
        assert len(result.errors) == 0
        assert len(result.entities) >= 1


class TestJuliaParserRelationships:
    """Tests for Julia parser relationships."""

    def test_module_structure(self, parser: JuliaParser) -> None:
        """Test module structure parsing."""
        code = """
module MyMath
    export add
    function add(x, y)
        return x + y
    end
end
"""
        result = parser.parse_string(code, "test.jl")
        assert len(result.entities) >= 1


class TestJuliaParserFileHandling:
    """Tests for Julia parser file handling."""

    def test_parse_file_not_found(self, parser: JuliaParser) -> None:
        """Test handling of non-existent file."""
        from pathlib import Path

        with pytest.raises((FileNotFoundError, OSError)):
            parser.parse_file(Path("/nonexistent/test.jl"))

    def test_parse_string_with_syntax_errors(self, parser: JuliaParser) -> None:
        """Test parsing code with syntax errors."""
        code = """
function broken(
"""
        result = parser.parse_string(code, "test.jl")
        # Should still create module entity
        assert len(result.entities) >= 1

    def test_parser_internal_methods(self, parser: JuliaParser) -> None:
        """Test internal parser methods."""
        # Test _generate_id
        id1 = parser._generate_id("test")
        id2 = parser._generate_id("test")
        assert id1 != id2
        assert id1.startswith("test_")
        assert id2.startswith("test_")


def test_julia_rich_constructs():
    """Parse a Julia file exercising module/struct/abstract/function extraction."""
    from magatama_core.infrastructure.parsers import JuliaParser

    code = """
module MyModule

struct Point
    x::Int
    y::Int
end

abstract type Shape end

function area(s)
    return 0
end

add(a, b) = a + b

end
"""
    result = JuliaParser().parse_string(code, "sample.jl")
    assert len(result.entities) >= 1
    assert len(result.errors) == 0
