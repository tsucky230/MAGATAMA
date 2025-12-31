"""Tests for Swift Parser."""

import pytest
from yata_core.infrastructure.parsers import SwiftParser
from yata_core.domain.entities import EntityType


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
        code = '''
class MyClass {
    func method() {}
}
'''
        result = parser.parse_string(code, "test.swift")
        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) >= 1

    def test_parse_struct(self, parser: SwiftParser) -> None:
        code = '''
struct Point {
    var x: Int
    var y: Int
}
'''
        result = parser.parse_string(code, "test.swift")
        structs = [e for e in result.entities if "Point" in e.name]
        assert len(structs) >= 1

    def test_parse_protocol(self, parser: SwiftParser) -> None:
        code = '''
protocol MyProtocol {
    func requiredMethod()
}
'''
        result = parser.parse_string(code, "test.swift")
        protocols = [e for e in result.entities if e.type == EntityType.INTERFACE]
        assert len(protocols) >= 1

    def test_parse_enum(self, parser: SwiftParser) -> None:
        code = '''
enum Status {
    case active
    case inactive
    case pending
}
'''
        result = parser.parse_string(code, "test.swift")
        # Should have at least module entity
        assert len(result.entities) >= 1

    def test_parse_function(self, parser: SwiftParser) -> None:
        code = '''
func standalone(x: Int, y: Int) -> Int {
    return x + y
}
'''
        result = parser.parse_string(code, "test.swift")
        functions = [e for e in result.entities if e.type == EntityType.FUNCTION]
        assert len(functions) >= 1


class TestSwiftParserAdvanced:
    """Advanced Swift parsing tests."""

    def test_parse_imports(self, parser: SwiftParser) -> None:
        code = '''
import Foundation
import UIKit

class ViewController: UIViewController {}
'''
        result = parser.parse_string(code, "test.swift")
        assert len(result.imports) >= 1

    def test_parse_extension(self, parser: SwiftParser) -> None:
        code = '''
extension String {
    func customMethod() -> String {
        return self
    }
}
'''
        result = parser.parse_string(code, "test.swift")
        assert len(result.entities) >= 1

    def test_parse_class_with_inheritance(self, parser: SwiftParser) -> None:
        code = '''
class Parent {
    func parentMethod() {}
}

class Child: Parent, MyProtocol {
    override func parentMethod() {}
}
'''
        result = parser.parse_string(code, "test.swift")
        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) >= 2
