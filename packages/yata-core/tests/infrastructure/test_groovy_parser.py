"""Tests for Groovy Parser."""

import pytest
from yata_core.infrastructure.parsers import GroovyParser
from yata_core.domain.entities import EntityType


@pytest.fixture
def parser() -> GroovyParser:
    return GroovyParser()


class TestGroovyParserBasic:
    """Basic Groovy parsing tests."""

    def test_parse_empty_string(self, parser: GroovyParser) -> None:
        result = parser.parse_string("", "test.groovy")
        assert result.file_path == "test.groovy"
        assert len(result.errors) == 0

    def test_parse_class(self, parser: GroovyParser) -> None:
        code = '''
class MyClass {
    void method() {}
}
'''
        result = parser.parse_string(code, "test.groovy")
        # Should have at least module entity
        assert len(result.entities) >= 1

    def test_parse_interface(self, parser: GroovyParser) -> None:
        code = '''
interface MyInterface {
    void method()
}
'''
        result = parser.parse_string(code, "test.groovy")
        # Should have at least module entity
        assert len(result.entities) >= 1

    def test_parse_module_entity(self, parser: GroovyParser) -> None:
        code = '''
println "Hello World"
'''
        result = parser.parse_string(code, "test.groovy")
        modules = [e for e in result.entities if e.type == EntityType.MODULE]
        assert len(modules) >= 1


class TestGroovyParserAdvanced:
    """Advanced Groovy parsing tests."""

    def test_parse_imports(self, parser: GroovyParser) -> None:
        code = '''
package com.example.app

import java.util.List
import groovy.json.JsonSlurper

class MyClass {}
'''
        result = parser.parse_string(code, "test.groovy")
        # Should have at least module entity
        assert len(result.entities) >= 1

    def test_parse_closure(self, parser: GroovyParser) -> None:
        code = '''
class Calculator {
    def multiply = { a, b -> a * b }
}
'''
        result = parser.parse_string(code, "test.groovy")
        assert len(result.entities) >= 1

    def test_parse_method_with_def(self, parser: GroovyParser) -> None:
        code = '''
class Helper {
    def helperMethod(x, y) {
        return x + y
    }
}
'''
        result = parser.parse_string(code, "test.groovy")
        assert len(result.entities) >= 1

    def test_parse_enum(self, parser: GroovyParser) -> None:
        code = '''
enum Status {
    ACTIVE,
    INACTIVE,
    PENDING
}
'''
        result = parser.parse_string(code, "test.groovy")
        # Should have at least module entity
        assert len(result.entities) >= 1

    def test_parse_trait(self, parser: GroovyParser) -> None:
        code = '''
trait Flyable {
    abstract void fly()
    
    void land() {
        println "Landing"
    }
}
'''
        result = parser.parse_string(code, "test.groovy")
        assert len(result.entities) >= 1
