"""Tests for Java Parser.

REQ-LANG-007: Java language support
"""

from magatama_core.domain.entities import EntityType
from magatama_core.infrastructure.parsers import JavaParser


class TestJavaParser:
    """Test suite for JavaParser."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = JavaParser()

    def test_parse_empty_file(self):
        """Test parsing an empty Java file."""
        result = self.parser.parse_string("", "Empty.java")

        assert result.file_path == "Empty.java"
        assert len(result.entities) >= 1  # Module entity
        assert result.errors == []

    def test_parse_simple_class(self):
        """Test parsing a simple Java class."""
        code = """
public class Person {
    private String name;

    public Person(String name) {
        this.name = name;
    }

    public String getName() {
        return name;
    }
}
"""
        result = self.parser.parse_string(code, "Person.java")

        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        methods = [e for e in result.entities if e.type == EntityType.METHOD]

        assert len(classes) == 1
        assert classes[0].name == "Person"
        assert len(methods) == 2
        assert {m.name for m in methods} == {"Person", "getName"}

    def test_parse_package_declaration(self):
        """Test parsing package declaration."""
        code = """
package com.example.app;

public class MyClass {
}
"""
        result = self.parser.parse_string(code, "MyClass.java")

        modules = [e for e in result.entities if e.type == EntityType.MODULE]
        assert any(m.name == "com.example.app" for m in modules)

    def test_parse_import_statements(self):
        """Test parsing import statements."""
        code = """
package com.example;

import java.util.List;
import java.util.Map;

public class MyClass {
}
"""
        result = self.parser.parse_string(code, "MyClass.java")

        assert "java.util.List" in result.imports
        assert "java.util.Map" in result.imports

    def test_parse_interface(self):
        """Test parsing a Java interface."""
        code = """
public interface Greetable {
    void greet();
    String getMessage();
}
"""
        result = self.parser.parse_string(code, "Greetable.java")

        interfaces = [e for e in result.entities if e.type == EntityType.INTERFACE]
        assert len(interfaces) == 1
        assert interfaces[0].name == "Greetable"

    def test_parse_inheritance(self):
        """Test parsing class inheritance."""
        code = """
public class Child extends Parent {
    public void method() {
    }
}
"""
        result = self.parser.parse_string(code, "Child.java")

        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) == 1
        assert "Parent" in classes[0].bases

    def test_parse_implements(self):
        """Test parsing interface implementation."""
        code = """
public class MyClass implements Runnable, Comparable<MyClass> {
    public void run() {
    }

    public int compareTo(MyClass other) {
        return 0;
    }
}
"""
        result = self.parser.parse_string(code, "MyClass.java")

        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) == 1
        # Check that methods are extracted correctly
        methods = [e for e in result.entities if e.type == EntityType.METHOD]
        assert len(methods) >= 2

    def test_parse_static_method(self):
        """Test parsing static methods."""
        code = """
public class Utility {
    public static void helper() {
    }
}
"""
        result = self.parser.parse_string(code, "Utility.java")

        methods = [e for e in result.entities if e.type == EntityType.METHOD]
        assert len(methods) == 1
        assert methods[0].is_static is True

    def test_parse_abstract_class(self):
        """Test parsing abstract class."""
        code = """
public abstract class BaseClass {
    public abstract void doSomething();

    public void concreteMethod() {
    }
}
"""
        result = self.parser.parse_string(code, "BaseClass.java")

        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) == 1
        assert classes[0].is_abstract is True

    def test_parse_method_parameters(self):
        """Test parsing method parameters."""
        code = """
public class Calculator {
    public int add(int a, int b) {
        return a + b;
    }
}
"""
        result = self.parser.parse_string(code, "Calculator.java")

        methods = [e for e in result.entities if e.type == EntityType.METHOD]
        assert len(methods) == 1
        assert len(methods[0].parameters) == 2
        assert methods[0].parameters[0] == ("a", "int")
        assert methods[0].parameters[1] == ("b", "int")
        assert methods[0].return_type == "int"

    def test_parse_enum(self):
        """Test parsing Java enum."""
        code = """
public enum Color {
    RED, GREEN, BLUE;

    public String getHex() {
        return "#000000";
    }
}
"""
        result = self.parser.parse_string(code, "Color.java")

        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) == 1
        assert classes[0].name == "Color"
        assert "Enum" in classes[0].bases

    def test_parse_nested_class(self):
        """Test parsing nested classes."""
        code = """
public class Outer {
    public class Inner {
        public void method() {
        }
    }
}
"""
        result = self.parser.parse_string(code, "Outer.java")

        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) == 2
        assert {c.name for c in classes} == {"Outer", "Inner"}


class TestJavaParserEdgeCases:
    """Test edge cases for JavaParser."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = JavaParser()

    def test_parse_with_javadoc(self):
        """Test parsing code with Javadoc comments."""
        code = """
/**
 * A simple person class.
 */
public class Person {
    /**
     * Gets the name.
     * @return the name
     */
    public String getName() {
        return name;
    }
}
"""
        result = self.parser.parse_string(code, "Person.java")

        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) == 1
        # Docstring should be extracted
        assert classes[0].docstring is not None

    def test_parse_generic_class(self):
        """Test parsing generic class."""
        code = """
public class Box<T> {
    private T value;

    public T getValue() {
        return value;
    }

    public void setValue(T value) {
        this.value = value;
    }
}
"""
        result = self.parser.parse_string(code, "Box.java")

        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) == 1

    def test_parse_empty_class(self):
        """Test parsing empty class."""
        code = """
public class Empty {
}
"""
        result = self.parser.parse_string(code, "Empty.java")

        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) == 1
        assert classes[0].name == "Empty"

    def test_contains_relationships(self):
        """Test CONTAINS relationships are created."""
        code = """
public class Container {
    public void methodOne() {
    }

    public void methodTwo() {
    }
}
"""
        result = self.parser.parse_string(code, "Container.java")

        from magatama_core.domain.entities import RelationshipType

        contains = [r for r in result.relationships if r.type == RelationshipType.CONTAINS]

        # Should have contains relationships from class to methods
        assert len(contains) >= 2
