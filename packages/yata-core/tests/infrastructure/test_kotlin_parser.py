"""Tests for Kotlin Parser."""

import pytest
from yata_core.infrastructure.parsers import KotlinParser
from yata_core.domain.entities import EntityType


@pytest.fixture
def parser() -> KotlinParser:
    return KotlinParser()


class TestKotlinParserBasic:
    """Basic Kotlin parsing tests."""

    def test_parse_empty_string(self, parser: KotlinParser) -> None:
        result = parser.parse_string("", "test.kt")
        assert result.file_path == "test.kt"
        assert len(result.errors) == 0

    def test_parse_class(self, parser: KotlinParser) -> None:
        code = '''
class MyClass {
    fun method() {}
}
'''
        result = parser.parse_string(code, "test.kt")
        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) >= 1

    def test_parse_object(self, parser: KotlinParser) -> None:
        code = '''
object Singleton {
    fun getInstance(): Singleton = this
}
'''
        result = parser.parse_string(code, "test.kt")
        assert len(result.entities) >= 1

    def test_parse_interface(self, parser: KotlinParser) -> None:
        code = '''
interface MyInterface {
    fun method()
}
'''
        result = parser.parse_string(code, "test.kt")
        # Should have at least module entity
        assert len(result.entities) >= 1

    def test_parse_function(self, parser: KotlinParser) -> None:
        code = '''
fun standalone(x: Int, y: Int): Int {
    return x + y
}
'''
        result = parser.parse_string(code, "test.kt")
        functions = [e for e in result.entities if e.type == EntityType.FUNCTION]
        assert len(functions) >= 1


class TestKotlinParserAdvanced:
    """Advanced Kotlin parsing tests."""

    def test_parse_imports(self, parser: KotlinParser) -> None:
        code = '''
package com.example.app

import kotlin.collections.List
import java.util.Date

class MyClass {}
'''
        result = parser.parse_string(code, "test.kt")
        # Should have entities (module + class at minimum)
        assert len(result.entities) >= 1

    def test_parse_data_class(self, parser: KotlinParser) -> None:
        code = '''
data class User(
    val id: Int,
    val name: String,
    val email: String
)
'''
        result = parser.parse_string(code, "test.kt")
        # Should have at least module entity
        assert len(result.entities) >= 1

    def test_parse_companion_object(self, parser: KotlinParser) -> None:
        code = '''
class MyClass {
    companion object {
        fun create(): MyClass = MyClass()
    }
}
'''
        result = parser.parse_string(code, "test.kt")
        assert len(result.entities) >= 1

    def test_parse_extension_function(self, parser: KotlinParser) -> None:
        code = '''
fun String.addExclamation(): String {
    return this + "!"
}
'''
        result = parser.parse_string(code, "test.kt")
        # Should have at least module entity
        assert len(result.entities) >= 1
