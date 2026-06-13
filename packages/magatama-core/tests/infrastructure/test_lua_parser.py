"""Tests for Lua Parser."""

import pytest

from magatama_core.domain.entities import EntityType
from magatama_core.infrastructure.parsers import LuaParser


@pytest.fixture
def parser() -> LuaParser:
    return LuaParser()


class TestLuaParserBasic:
    """Basic Lua parsing tests."""

    def test_parse_empty_string(self, parser: LuaParser) -> None:
        result = parser.parse_string("", "test.lua")
        assert result.file_path == "test.lua"
        assert len(result.errors) == 0

    def test_parse_function(self, parser: LuaParser) -> None:
        code = """
function greet(name)
    print("Hello, " .. name)
end
"""
        result = parser.parse_string(code, "test.lua")
        functions = [e for e in result.entities if e.type == EntityType.FUNCTION]
        assert len(functions) >= 1

    def test_parse_local_function(self, parser: LuaParser) -> None:
        code = """
local function helper(x, y)
    return x + y
end
"""
        result = parser.parse_string(code, "test.lua")
        functions = [e for e in result.entities if e.type == EntityType.FUNCTION]
        assert len(functions) >= 1

    def test_parse_module_entity(self, parser: LuaParser) -> None:
        code = """
-- Simple module
local M = {}
return M
"""
        result = parser.parse_string(code, "test.lua")
        modules = [e for e in result.entities if e.type == EntityType.MODULE]
        assert len(modules) >= 1


class TestLuaParserAdvanced:
    """Advanced Lua parsing tests."""

    def test_parse_require(self, parser: LuaParser) -> None:
        code = """
local json = require("json")
local http = require("socket.http")

function main()
    print("Hello")
end
"""
        result = parser.parse_string(code, "test.lua")
        # require calls should be captured as imports
        assert len(result.entities) >= 1

    def test_parse_nested_functions(self, parser: LuaParser) -> None:
        code = """
function outer()
    local function inner()
        return 42
    end
    return inner()
end
"""
        result = parser.parse_string(code, "test.lua")
        functions = [e for e in result.entities if e.type == EntityType.FUNCTION]
        assert len(functions) >= 2

    def test_parse_method_style_function(self, parser: LuaParser) -> None:
        code = """
local obj = {}

function obj:method(x)
    return self.value + x
end

function obj.staticMethod(x)
    return x * 2
end
"""
        result = parser.parse_string(code, "test.lua")
        assert len(result.entities) >= 1
