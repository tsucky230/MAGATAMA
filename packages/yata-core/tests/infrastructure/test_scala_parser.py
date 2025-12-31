"""Tests for Scala Parser."""

import pytest
from yata_core.infrastructure.parsers import ScalaParser
from yata_core.domain.entities import EntityType


@pytest.fixture
def parser() -> ScalaParser:
    return ScalaParser()


class TestScalaParserBasic:
    """Basic Scala parsing tests."""

    def test_parse_empty_string(self, parser: ScalaParser) -> None:
        result = parser.parse_string("", "test.scala")
        assert result.file_path == "test.scala"
        assert len(result.errors) == 0

    def test_parse_class(self, parser: ScalaParser) -> None:
        code = '''
class MyClass {
  def method(): Unit = {}
}
'''
        result = parser.parse_string(code, "test.scala")
        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) >= 1

    def test_parse_object(self, parser: ScalaParser) -> None:
        code = '''
object Singleton {
  def getInstance: Singleton.type = this
}
'''
        result = parser.parse_string(code, "test.scala")
        assert len(result.entities) >= 1

    def test_parse_trait(self, parser: ScalaParser) -> None:
        code = '''
trait MyTrait {
  def method(): Unit
}
'''
        result = parser.parse_string(code, "test.scala")
        traits = [e for e in result.entities if e.type == EntityType.INTERFACE]
        assert len(traits) >= 1

    def test_parse_function(self, parser: ScalaParser) -> None:
        code = '''
def standalone(x: Int, y: Int): Int = {
  x + y
}
'''
        result = parser.parse_string(code, "test.scala")
        functions = [e for e in result.entities if e.type == EntityType.FUNCTION]
        assert len(functions) >= 1


class TestScalaParserAdvanced:
    """Advanced Scala parsing tests."""

    def test_parse_imports(self, parser: ScalaParser) -> None:
        code = '''
package com.example.app

import scala.collection.mutable.ListBuffer
import java.util.Date

class MyClass {}
'''
        result = parser.parse_string(code, "test.scala")
        # Should have entities
        assert len(result.entities) >= 1

    def test_parse_case_class(self, parser: ScalaParser) -> None:
        code = '''
case class User(id: Int, name: String, email: String)
'''
        result = parser.parse_string(code, "test.scala")
        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) >= 1

    def test_parse_companion_object(self, parser: ScalaParser) -> None:
        code = '''
class MyClass(val value: Int)

object MyClass {
  def apply(value: Int): MyClass = new MyClass(value)
}
'''
        result = parser.parse_string(code, "test.scala")
        assert len(result.entities) >= 2

    def test_parse_sealed_trait(self, parser: ScalaParser) -> None:
        code = '''
sealed trait Animal
case class Dog(name: String) extends Animal
case class Cat(name: String) extends Animal
'''
        result = parser.parse_string(code, "test.scala")
        assert len(result.entities) >= 3
