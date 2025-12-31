"""Tests for Julia Parser."""

import pytest
from yata_core.infrastructure.parsers import JuliaParser
from yata_core.domain.entities import EntityType


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
        code = '''
function add(x, y)
    return x + y
end
'''
        result = parser.parse_string(code, "test.jl")
        # Should have at least module entity
        assert len(result.entities) >= 1

    def test_parse_short_function(self, parser: JuliaParser) -> None:
        code = '''
square(x) = x^2
'''
        result = parser.parse_string(code, "test.jl")
        assert len(result.entities) >= 1

    def test_parse_struct(self, parser: JuliaParser) -> None:
        code = '''
struct Point
    x::Float64
    y::Float64
end
'''
        result = parser.parse_string(code, "test.jl")
        # Should have at least module entity
        assert len(result.entities) >= 1

    def test_parse_module(self, parser: JuliaParser) -> None:
        code = '''
module MyModule

export greet

function greet(name)
    println("Hello, $name")
end

end
'''
        result = parser.parse_string(code, "test.jl")
        modules = [e for e in result.entities if e.type == EntityType.MODULE]
        assert len(modules) >= 1


class TestJuliaParserAdvanced:
    """Advanced Julia parsing tests."""

    def test_parse_imports(self, parser: JuliaParser) -> None:
        code = '''
using LinearAlgebra
import Statistics: mean, std

function compute(x)
    return mean(x)
end
'''
        result = parser.parse_string(code, "test.jl")
        assert len(result.entities) >= 1

    def test_parse_abstract_type(self, parser: JuliaParser) -> None:
        code = '''
abstract type Animal end

struct Dog <: Animal
    name::String
end
'''
        result = parser.parse_string(code, "test.jl")
        assert len(result.entities) >= 1

    def test_parse_macro(self, parser: JuliaParser) -> None:
        code = '''
macro sayhello(name)
    return :( println("Hello, ", $name) )
end
'''
        result = parser.parse_string(code, "test.jl")
        assert len(result.entities) >= 1

    def test_parse_mutable_struct(self, parser: JuliaParser) -> None:
        code = '''
mutable struct Counter
    value::Int
end
'''
        result = parser.parse_string(code, "test.jl")
        assert len(result.entities) >= 1
