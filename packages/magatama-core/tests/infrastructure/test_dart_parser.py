"""Tests for DartParser."""

from magatama_core.domain.entities import EntityType
from magatama_core.infrastructure.parsers import DartParser


class TestDartParserBasic:
    """Basic tests for DartParser."""

    def test_parse_empty_string(self):
        """Test parsing empty string."""
        parser = DartParser()
        result = parser.parse_string("", "test.dart")
        # Should have at least module entity
        assert len(result.entities) >= 1

    def test_parse_class(self):
        """Test parsing a simple class."""
        parser = DartParser()
        code = """
class MyClass {
  void doSomething() {}
}
"""
        result = parser.parse_string(code, "test.dart")
        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) >= 1
        assert any(c.name == "MyClass" for c in classes)

    def test_parse_abstract_class(self):
        """Test parsing an abstract class."""
        parser = DartParser()
        code = """
abstract class Widget {
  Widget build(BuildContext context);
}
"""
        result = parser.parse_string(code, "test.dart")
        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert any(c.name == "Widget" for c in classes)

    def test_parse_class_with_extends(self):
        """Test parsing class with inheritance."""
        parser = DartParser()
        code = """
class MyWidget extends StatelessWidget {
  Widget build(BuildContext context) {
    return Container();
  }
}
"""
        result = parser.parse_string(code, "test.dart")
        classes = [
            e for e in result.entities if e.type == EntityType.CLASS and e.name == "MyWidget"
        ]
        assert len(classes) == 1
        assert "StatelessWidget" in classes[0].bases

    def test_parse_class_with_implements(self):
        """Test parsing class with interface implementation."""
        parser = DartParser()
        code = """
class MyService implements Disposable, Serializable {
  void dispose() {}
}
"""
        result = parser.parse_string(code, "test.dart")
        classes = [
            e for e in result.entities if e.type == EntityType.CLASS and e.name == "MyService"
        ]
        assert len(classes) == 1
        assert "Disposable" in classes[0].bases
        assert "Serializable" in classes[0].bases

    def test_parse_mixin(self):
        """Test parsing a mixin."""
        parser = DartParser()
        code = """
mixin TickerProviderMixin on State {
  Ticker createTicker(TickerCallback callback) {
    return Ticker(callback);
  }
}
"""
        result = parser.parse_string(code, "test.dart")
        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert any(c.name == "TickerProviderMixin" for c in classes)

    def test_parse_enum(self):
        """Test parsing an enum."""
        parser = DartParser()
        code = """
enum AppState {
  loading,
  ready,
  error,
}
"""
        result = parser.parse_string(code, "test.dart")
        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert any(c.name == "AppState" for c in classes)

    def test_parse_function(self):
        """Test parsing a top-level function."""
        parser = DartParser()
        code = """
void main() {
  runApp(MyApp());
}
"""
        result = parser.parse_string(code, "test.dart")
        functions = [e for e in result.entities if e.type == EntityType.FUNCTION]
        assert any(f.name == "main" for f in functions)


class TestDartParserAdvanced:
    """Advanced tests for DartParser."""

    def test_parse_imports(self):
        """Test parsing import statements."""
        parser = DartParser()
        code = """
import 'package:flutter/material.dart';
import 'dart:async';
import 'package:http/http.dart' as http;

void main() {}
"""
        result = parser.parse_string(code, "test.dart")
        assert "package:flutter/material.dart" in result.imports
        assert "dart:async" in result.imports

    def test_parse_async_function(self):
        """Test parsing async functions."""
        parser = DartParser()
        code = """
Future<void> fetchData() async {
  await Future.delayed(Duration(seconds: 1));
}
"""
        result = parser.parse_string(code, "test.dart")
        functions = [e for e in result.entities if e.type == EntityType.FUNCTION]
        assert any(f.name == "fetchData" for f in functions)

    def test_parse_extension(self):
        """Test parsing extension methods."""
        parser = DartParser()
        code = """
extension StringExtension on String {
  String capitalize() {
    return this[0].toUpperCase() + substring(1);
  }
}
"""
        result = parser.parse_string(code, "test.dart")
        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert any(c.name == "StringExtension" for c in classes)

    def test_parse_typedef(self):
        """Test parsing typedef."""
        parser = DartParser()
        code = """
typedef VoidCallback = void Function();
typedef JsonMap = Map<String, dynamic>;
"""
        result = parser.parse_string(code, "test.dart")
        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert any(c.name == "VoidCallback" for c in classes)

    def test_parse_methods(self):
        """Test parsing methods within a class."""
        parser = DartParser()
        code = """
class Calculator {
  int add(int a, int b) {
    return a + b;
  }
  
  int subtract(int a, int b) {
    return a - b;
  }
}
"""
        result = parser.parse_string(code, "test.dart")
        methods = [e for e in result.entities if e.type == EntityType.METHOD]
        method_names = [m.name for m in methods]
        assert "add" in method_names
        assert "subtract" in method_names

    def test_parse_contains_relationships(self):
        """Test that CONTAINS relationships are created."""
        parser = DartParser()
        code = """
class MyClass {
  void myMethod() {}
}
"""
        result = parser.parse_string(code, "test.dart")
        contains_rels = [r for r in result.relationships if r.type.value == "contains"]
        assert len(contains_rels) >= 1

    def test_parse_generic_class(self):
        """Test parsing generic class."""
        parser = DartParser()
        code = """
class Box<T> {
  T value;
  Box(this.value);
}
"""
        result = parser.parse_string(code, "test.dart")
        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert any(c.name == "Box" for c in classes)
