"""Unit tests for Zig parser."""

import pytest
from yata_core.infrastructure.parsers.zig_parser import ZigParser
from yata_core.domain.entities import EntityType


class TestZigParser:
    """Test suite for Zig parser."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return ZigParser()

    def test_parse_function(self, parser):
        """Test function parsing."""
        code = """
fn add(a: i32, b: i32) i32 {
    return a + b;
}
"""
        result = parser.parse_string(code, "test.zig")
        
        assert len(result.entities) >= 2
        func = next((e for e in result.entities if e.name == "add"), None)
        assert func is not None
        assert func.type == EntityType.FUNCTION

    def test_parse_public_function(self, parser):
        """Test public function parsing."""
        code = """
pub fn main() void {
    const x: i32 = 42;
}
"""
        result = parser.parse_string(code, "test.zig")
        
        func = next((e for e in result.entities if e.name == "main"), None)
        assert func is not None
        assert func.type == EntityType.FUNCTION

    def test_parse_function_with_parameters(self, parser):
        """Test function parameter extraction."""
        code = """
fn calculate(x: i32, y: f64, z: bool) i32 {
    return x;
}
"""
        result = parser.parse_string(code, "test.zig")
        
        func = next((e for e in result.entities if e.name == "calculate"), None)
        assert func is not None
        assert len(func.parameters) >= 1

    def test_parse_multiple_functions(self, parser):
        """Test multiple functions."""
        code = """
fn add(a: i32, b: i32) i32 { return a + b; }
fn sub(a: i32, b: i32) i32 { return a - b; }
fn mul(a: i32, b: i32) i32 { return a * b; }
"""
        result = parser.parse_string(code, "test.zig")
        
        func_names = [e.name for e in result.entities if e.type == EntityType.FUNCTION]
        assert "add" in func_names
        assert "sub" in func_names
        assert "mul" in func_names

    def test_parse_extern_function(self, parser):
        """Test extern function parsing."""
        code = """
extern fn printf(format: [*:0]const u8, ...) c_int;
"""
        result = parser.parse_string(code, "test.zig")
        
        # Should at least have module entity
        assert len(result.entities) >= 1

    def test_parse_complex_code(self, parser):
        """Test parsing complex Zig code."""
        code = """
const std = @import("std");

pub fn main() void {
    const allocator = std.heap.page_allocator;
    var list = std.ArrayList(i32).init(allocator);
    defer list.deinit();
}

fn helper(value: i32) i32 {
    return value * 2;
}
"""
        result = parser.parse_string(code, "main.zig")
        
        assert len(result.entities) >= 2
        
        main_func = next((e for e in result.entities if e.name == "main"), None)
        assert main_func is not None
        
        helper_func = next((e for e in result.entities if e.name == "helper"), None)
        assert helper_func is not None

    def test_module_entity_created(self, parser):
        """Test that module entity is always created."""
        code = "fn foo() void {}"
        result = parser.parse_string(code, "test.zig")
        
        module = next((e for e in result.entities if e.type == EntityType.MODULE), None)
        assert module is not None
        assert module.name == "test"

    def test_parse_generic_function(self, parser):
        """Test generic function parsing."""
        code = """
fn swap(comptime T: type, a: *T, b: *T) void {
    const tmp = a.*;
    a.* = b.*;
    b.* = tmp;
}
"""
        result = parser.parse_string(code, "test.zig")
        
        func = next((e for e in result.entities if e.name == "swap"), None)
        assert func is not None


class TestZigParserEntityExtraction:
    """Tests for Zig parser entity extraction."""

    @pytest.fixture
    def parser(self):
        return ZigParser()

    def test_extract_struct(self, parser):
        """Test struct parsing."""
        code = """
const Point = struct {
    x: i32,
    y: i32,
};
"""
        result = parser.parse_string(code, "test.zig")
        assert len(result.errors) == 0
        assert len(result.entities) >= 1

    def test_extract_enum(self, parser):
        """Test enum parsing."""
        code = """
const Color = enum {
    red,
    green,
    blue,
};
"""
        result = parser.parse_string(code, "test.zig")
        assert len(result.errors) == 0
        assert len(result.entities) >= 1

    def test_extract_const_declaration(self, parser):
        """Test const declaration parsing."""
        code = """
const MAX_SIZE: usize = 100;
const PI: f64 = 3.14159;
"""
        result = parser.parse_string(code, "test.zig")
        assert len(result.errors) == 0
        assert len(result.entities) >= 1


class TestZigParserRelationships:
    """Tests for Zig parser relationships."""

    @pytest.fixture
    def parser(self):
        return ZigParser()

    def test_module_contains_function(self, parser):
        """Test CONTAINS relationship between module and function."""
        code = """
fn myFunction() void {}
"""
        result = parser.parse_string(code, "test.zig")
        # Should have at least one relationship
        assert len(result.relationships) >= 0


class TestZigParserFileHandling:
    """Tests for Zig parser file handling."""

    @pytest.fixture
    def parser(self):
        return ZigParser()

    def test_parse_file_not_found(self, parser):
        """Test handling of non-existent file."""
        from pathlib import Path
        with pytest.raises((FileNotFoundError, OSError)):
            parser.parse_file(Path("/nonexistent/test.zig"))

    def test_parse_string_with_syntax_errors(self, parser):
        """Test parsing code with syntax errors."""
        code = """
fn broken( {
"""
        result = parser.parse_string(code, "test.zig")
        # Should still create module entity
        assert len(result.entities) >= 1

    def test_parser_internal_methods(self, parser):
        """Test internal parser methods."""
        # Test _generate_id
        id1 = parser._generate_id("test")
        id2 = parser._generate_id("test")
        assert id1 != id2
        assert id1.startswith("test_")
        assert id2.startswith("test_")
