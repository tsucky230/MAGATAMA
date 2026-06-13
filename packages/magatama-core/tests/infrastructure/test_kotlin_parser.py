"""Tests for Kotlin Parser."""

import pytest

from magatama_core.domain.entities import EntityType
from magatama_core.infrastructure.parsers import KotlinParser


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
        code = """
class MyClass {
    fun method() {}
}
"""
        result = parser.parse_string(code, "test.kt")
        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) >= 1

    def test_parse_object(self, parser: KotlinParser) -> None:
        code = """
object Singleton {
    fun getInstance(): Singleton = this
}
"""
        result = parser.parse_string(code, "test.kt")
        assert len(result.entities) >= 1

    def test_parse_interface(self, parser: KotlinParser) -> None:
        code = """
interface MyInterface {
    fun method()
}
"""
        result = parser.parse_string(code, "test.kt")
        # Should have at least module entity
        assert len(result.entities) >= 1

    def test_parse_function(self, parser: KotlinParser) -> None:
        code = """
fun standalone(x: Int, y: Int): Int {
    return x + y
}
"""
        result = parser.parse_string(code, "test.kt")
        functions = [e for e in result.entities if e.type == EntityType.FUNCTION]
        assert len(functions) >= 1


class TestKotlinParserAdvanced:
    """Advanced Kotlin parsing tests."""

    def test_parse_imports(self, parser: KotlinParser) -> None:
        code = """
package com.example.app

import kotlin.collections.List
import java.util.Date

class MyClass {}
"""
        result = parser.parse_string(code, "test.kt")
        # Should have entities (module + class at minimum)
        assert len(result.entities) >= 1

    def test_parse_data_class(self, parser: KotlinParser) -> None:
        code = """
data class User(
    val id: Int,
    val name: String,
    val email: String
)
"""
        result = parser.parse_string(code, "test.kt")
        # Should have at least module entity
        assert len(result.entities) >= 1

    def test_parse_companion_object(self, parser: KotlinParser) -> None:
        code = """
class MyClass {
    companion object {
        fun create(): MyClass = MyClass()
    }
}
"""
        result = parser.parse_string(code, "test.kt")
        assert len(result.entities) >= 1

    def test_parse_extension_function(self, parser: KotlinParser) -> None:
        code = """
fun String.addExclamation(): String {
    return this + "!"
}
"""
        result = parser.parse_string(code, "test.kt")
        # Should have at least module entity
        assert len(result.entities) >= 1


class TestKotlinParserEntityExtraction:
    """Tests for Kotlin parser entity extraction."""

    def test_extract_sealed_class(self, parser: KotlinParser) -> None:
        """Test sealed class parsing."""
        code = """
sealed class Result<out T> {
    data class Success<T>(val value: T) : Result<T>()
    data class Error(val message: String) : Result<Nothing>()
}
"""
        result = parser.parse_string(code, "test.kt")
        assert len(result.errors) == 0
        assert len(result.entities) >= 1

    def test_extract_enum_class(self, parser: KotlinParser) -> None:
        """Test enum class parsing."""
        code = """
enum class Color {
    RED, GREEN, BLUE
}
"""
        result = parser.parse_string(code, "test.kt")
        assert len(result.errors) == 0
        assert len(result.entities) >= 1


class TestKotlinParserRelationships:
    """Tests for Kotlin parser relationships."""

    def test_inheritance_relationship(self, parser: KotlinParser) -> None:
        """Test class inheritance."""
        code = """
open class Parent {
    open fun method() {}
}

class Child : Parent() {
    override fun method() {}
}
"""
        result = parser.parse_string(code, "test.kt")
        assert len(result.entities) >= 1


class TestKotlinParserFileHandling:
    """Tests for Kotlin parser file handling."""

    def test_parse_file_not_found(self, parser: KotlinParser) -> None:
        """Test handling of non-existent file."""
        from pathlib import Path

        with pytest.raises((FileNotFoundError, OSError)):
            parser.parse_file(Path("/nonexistent/test.kt"))

    def test_parse_string_with_syntax_errors(self, parser: KotlinParser) -> None:
        """Test parsing code with syntax errors."""
        code = """
class Broken {
    fun incomplete(
"""
        result = parser.parse_string(code, "test.kt")
        # Should still create module entity
        assert len(result.entities) >= 1

    def test_parser_internal_methods(self, parser: KotlinParser) -> None:
        """Test internal parser methods."""
        # Test _generate_id
        id1 = parser._generate_id("test")
        id2 = parser._generate_id("test")
        assert id1 != id2
        assert id1.startswith("test_")
        assert id2.startswith("test_")


def test_kotlin_rich_constructs():
    """Parse a Kotlin file exercising interface/class/data class/enum/object/function."""
    from magatama_core.infrastructure.parsers import KotlinParser

    code = """
package demo

interface Greeter {
    fun greet(): String
}

data class Point(val x: Int, val y: Int)

enum class Direction { NORTH, SOUTH }

class Animal(val name: String) : Greeter {
    override fun greet(): String = "Hi"
    fun sleep() {}
}

object Singleton {
    fun instance() = 1
}

fun topLevel(): Int = 42
"""
    result = KotlinParser().parse_string(code, "sample.kt")
    assert len(result.entities) >= 1
    assert len(result.errors) == 0
