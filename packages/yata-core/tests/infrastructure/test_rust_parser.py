"""Tests for Rust Parser.

Tests REQ-LANG-004: Rust support
ADR-003: Tree-sitter for multi-language support
"""

from pathlib import Path

import pytest

from yata_core.domain.entities import EntityType
from yata_core.domain.entities.relationships import RelationshipType
from yata_core.infrastructure.parsers.rust_parser import RustParser


class TestRustParser:
    """Tests for RustParser."""

    @pytest.fixture
    def parser(self) -> RustParser:
        """Create a RustParser instance."""
        return RustParser()

    def test_parser_initialization(self, parser: RustParser) -> None:
        """Test parser initializes correctly."""
        assert parser is not None

    def test_parse_simple_function(self, parser: RustParser) -> None:
        """Test parsing a simple function."""
        code = '''
fn greet(name: &str) -> String {
    format!("Hello, {}!", name)
}
'''
        result = parser.parse_string(code, "test.rs")

        assert result.file_path == "test.rs"
        assert len(result.errors) == 0

        # Find function entity
        functions = [e for e in result.entities if e.type == EntityType.FUNCTION]
        assert len(functions) == 1
        assert functions[0].name == "greet"

    def test_parse_pub_function(self, parser: RustParser) -> None:
        """Test parsing a public function."""
        code = '''
pub fn public_function() -> i32 {
    42
}
'''
        result = parser.parse_string(code, "test.rs")
        functions = [e for e in result.entities if e.type == EntityType.FUNCTION]
        assert len(functions) == 1
        assert functions[0].name == "public_function"
        assert functions[0].scope == "public"

    def test_parse_async_function(self, parser: RustParser) -> None:
        """Test parsing an async function."""
        code = '''
async fn fetch_data() -> Result<String, Error> {
    Ok("data".to_string())
}
'''
        result = parser.parse_string(code, "test.rs")
        functions = [e for e in result.entities if e.type == EntityType.FUNCTION]
        assert len(functions) == 1
        assert functions[0].name == "fetch_data"
        assert functions[0].is_async is True

    def test_parse_struct(self, parser: RustParser) -> None:
        """Test parsing a struct."""
        code = '''
pub struct User {
    name: String,
    age: u32,
}
'''
        result = parser.parse_string(code, "test.rs")
        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) == 1
        assert classes[0].name == "User"

    def test_parse_enum(self, parser: RustParser) -> None:
        """Test parsing an enum."""
        code = '''
pub enum Status {
    Active,
    Inactive,
    Pending,
}
'''
        result = parser.parse_string(code, "test.rs")
        enums = [e for e in result.entities if e.type == EntityType.ENUM]
        assert len(enums) == 1
        assert enums[0].name == "Status"

    def test_parse_trait(self, parser: RustParser) -> None:
        """Test parsing a trait."""
        code = '''
pub trait Drawable {
    fn draw(&self);
    fn resize(&mut self, width: u32, height: u32);
}
'''
        result = parser.parse_string(code, "test.rs")
        interfaces = [e for e in result.entities if e.type == EntityType.INTERFACE]
        assert len(interfaces) == 1
        assert interfaces[0].name == "Drawable"

    def test_parse_impl_methods(self, parser: RustParser) -> None:
        """Test parsing impl block methods."""
        code = '''
struct Point {
    x: f64,
    y: f64,
}

impl Point {
    pub fn new(x: f64, y: f64) -> Self {
        Point { x, y }
    }

    pub fn distance(&self, other: &Point) -> f64 {
        ((self.x - other.x).powi(2) + (self.y - other.y).powi(2)).sqrt()
    }
}
'''
        result = parser.parse_string(code, "test.rs")
        methods = [e for e in result.entities if e.type == EntityType.METHOD]
        assert len(methods) == 2
        method_names = {m.name for m in methods}
        assert method_names == {"new", "distance"}

    def test_parse_type_alias(self, parser: RustParser) -> None:
        """Test parsing a type alias."""
        code = '''
type UserId = u64;
'''
        result = parser.parse_string(code, "test.rs")
        types = [e for e in result.entities if e.type == EntityType.TYPE]
        assert len(types) == 1
        assert types[0].name == "UserId"

    def test_parse_use_statements(self, parser: RustParser) -> None:
        """Test parsing use statements (imports)."""
        code = '''
use std::collections::HashMap;
use std::io::{Read, Write};
'''
        result = parser.parse_string(code, "test.rs")
        
        # Check imports list
        assert "std::collections::HashMap" in result.imports
        # The full use path is preserved, including braced imports
        assert any("std::io" in imp for imp in result.imports)

    def test_parse_function_calls_relationship(self, parser: RustParser) -> None:
        """Test parsing function call relationships."""
        code = '''
fn helper() -> i32 {
    42
}

fn main() {
    let result = helper();
    println!("{}", result);
}
'''
        result = parser.parse_string(code, "test.rs")
        
        calls = [r for r in result.relationships if r.type == RelationshipType.CALLS]
        # Should detect main -> helper call
        assert len(calls) >= 1

    def test_parse_module(self, parser: RustParser) -> None:
        """Test that module entity is created."""
        code = '''
fn example() {}
'''
        result = parser.parse_string(code, "test.rs")
        modules = [e for e in result.entities if e.type == EntityType.MODULE]
        assert len(modules) == 1

    def test_parse_file(self, parser: RustParser, tmp_path: Path) -> None:
        """Test parsing a file from disk."""
        rust_file = tmp_path / "example.rs"
        rust_file.write_text('''
pub fn add(a: i32, b: i32) -> i32 {
    a + b
}
''')
        
        result = parser.parse_file(rust_file)
        
        assert str(rust_file) in result.file_path
        functions = [e for e in result.entities if e.type == EntityType.FUNCTION]
        assert len(functions) == 1
        assert functions[0].name == "add"

    def test_entity_locations(self, parser: RustParser) -> None:
        """Test that entity locations are correct."""
        code = '''fn first() {}

fn second() {}
'''
        result = parser.parse_string(code, "test.rs")
        functions = [e for e in result.entities if e.type == EntityType.FUNCTION]
        
        first = next(f for f in functions if f.name == "first")
        second = next(f for f in functions if f.name == "second")
        
        assert first.location.line == 1
        assert second.location.line == 3
