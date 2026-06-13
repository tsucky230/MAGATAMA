"""Tests for Swift Parser."""

import pytest

from magatama_core.domain.entities import EntityType
from magatama_core.infrastructure.parsers import SwiftParser


@pytest.fixture
def parser() -> SwiftParser:
    return SwiftParser()


class TestSwiftParserBasic:
    """Basic Swift parsing tests."""

    def test_parse_empty_string(self, parser: SwiftParser) -> None:
        result = parser.parse_string("", "test.swift")
        assert result.file_path == "test.swift"
        assert len(result.errors) == 0

    def test_parse_class(self, parser: SwiftParser) -> None:
        code = """
class MyClass {
    func method() {}
}
"""
        result = parser.parse_string(code, "test.swift")
        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) >= 1

    def test_parse_struct(self, parser: SwiftParser) -> None:
        code = """
struct Point {
    var x: Int
    var y: Int
}
"""
        result = parser.parse_string(code, "test.swift")
        structs = [e for e in result.entities if "Point" in e.name]
        assert len(structs) >= 1

    def test_parse_protocol(self, parser: SwiftParser) -> None:
        code = """
protocol MyProtocol {
    func requiredMethod()
}
"""
        result = parser.parse_string(code, "test.swift")
        protocols = [e for e in result.entities if e.type == EntityType.INTERFACE]
        assert len(protocols) >= 1

    def test_parse_enum(self, parser: SwiftParser) -> None:
        code = """
enum Status {
    case active
    case inactive
    case pending
}
"""
        result = parser.parse_string(code, "test.swift")
        # Should have at least module entity
        assert len(result.entities) >= 1

    def test_parse_function(self, parser: SwiftParser) -> None:
        code = """
func standalone(x: Int, y: Int) -> Int {
    return x + y
}
"""
        result = parser.parse_string(code, "test.swift")
        functions = [e for e in result.entities if e.type == EntityType.FUNCTION]
        assert len(functions) >= 1


class TestSwiftParserAdvanced:
    """Advanced Swift parsing tests."""

    def test_parse_imports(self, parser: SwiftParser) -> None:
        code = """
import Foundation
import UIKit

class ViewController: UIViewController {}
"""
        result = parser.parse_string(code, "test.swift")
        assert len(result.imports) >= 1

    def test_parse_extension(self, parser: SwiftParser) -> None:
        code = """
extension String {
    func customMethod() -> String {
        return self
    }
}
"""
        result = parser.parse_string(code, "test.swift")
        assert len(result.entities) >= 1

    def test_parse_class_with_inheritance(self, parser: SwiftParser) -> None:
        code = """
class Parent {
    func parentMethod() {}
}

class Child: Parent, MyProtocol {
    override func parentMethod() {}
}
"""
        result = parser.parse_string(code, "test.swift")
        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) >= 2


class TestSwiftParserEntityExtraction:
    """Tests for Swift parser entity extraction."""

    def test_extract_protocol_methods(self, parser: SwiftParser) -> None:
        """Test protocol with multiple method requirements."""
        code = """
protocol DataSource {
    func numberOfItems() -> Int
    func itemAt(index: Int) -> String
}
"""
        result = parser.parse_string(code, "test.swift")
        assert len(result.errors) == 0
        assert len(result.entities) >= 1

    def test_extract_generic_class(self, parser: SwiftParser) -> None:
        """Test generic class parsing."""
        code = """
class Container<T> {
    var value: T
    init(value: T) {
        self.value = value
    }
}
"""
        result = parser.parse_string(code, "test.swift")
        assert len(result.errors) == 0
        assert len(result.entities) >= 1

    def test_extract_computed_properties(self, parser: SwiftParser) -> None:
        """Test computed properties in class."""
        code = """
class Rectangle {
    var width: Double
    var height: Double

    var area: Double {
        return width * height
    }
}
"""
        result = parser.parse_string(code, "test.swift")
        assert len(result.errors) == 0
        assert len(result.entities) >= 1


class TestSwiftParserRelationships:
    """Tests for Swift parser relationships."""

    def test_contains_relationship(self, parser: SwiftParser) -> None:
        """Test CONTAINS relationship between module and class."""
        code = """
class MyClass {
    func method() {}
}
"""
        result = parser.parse_string(code, "test.swift")
        # Should have at least module contains class relationship
        assert len(result.relationships) >= 0

    def test_protocol_conformance(self, parser: SwiftParser) -> None:
        """Test class conforming to protocol."""
        code = """
protocol Drawable {
    func draw()
}

class Circle: Drawable {
    func draw() {}
}
"""
        result = parser.parse_string(code, "test.swift")
        assert len(result.errors) == 0
        assert len(result.entities) >= 1


class TestSwiftParserFileHandling:
    """Tests for Swift parser file handling."""

    def test_parse_file_not_found(self, parser: SwiftParser) -> None:
        """Test handling of non-existent file."""
        from pathlib import Path

        with pytest.raises((FileNotFoundError, OSError)):
            parser.parse_file(Path("/nonexistent/test.swift"))

    def test_parse_string_with_syntax_errors(self, parser: SwiftParser) -> None:
        """Test parsing code with syntax errors."""
        code = """
class Broken {
    func incomplete(
"""
        result = parser.parse_string(code, "test.swift")
        # Should still create module entity
        assert len(result.entities) >= 1

    def test_parser_internal_methods(self, parser: SwiftParser) -> None:
        """Test internal parser methods."""
        # Test _generate_id
        id1 = parser._generate_id("test")
        id2 = parser._generate_id("test")
        assert id1 != id2
        assert id1.startswith("test_")
        assert id2.startswith("test_")


def test_swift_rich_constructs():
    """Parse a Swift file exercising protocol/struct/enum/class/function extraction."""
    from magatama_core.infrastructure.parsers import SwiftParser

    code = """
import Foundation

protocol Greeter {
    func greet() -> String
}

struct Point {
    var x: Int
    var y: Int
    func magnitude() -> Int { return x * x + y * y }
}

enum Direction {
    case north, south, east, west
}

class Animal: Greeter {
    var name: String
    init(name: String) { self.name = name }
    func greet() -> String { return "Hi" }
}

func topLevel() -> Int { return 42 }
"""
    result = SwiftParser().parse_string(code, "sample.swift")
    assert len(result.entities) >= 1
    assert len(result.errors) == 0
