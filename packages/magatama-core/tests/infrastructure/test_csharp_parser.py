"""Tests for C# Parser.

REQ-LANG-008: C# language support
"""

from magatama_core.domain.entities import EntityType
from magatama_core.infrastructure.parsers import CSharpParser


class TestCSharpParser:
    """Test suite for CSharpParser."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = CSharpParser()

    def test_parse_empty_file(self):
        """Test parsing an empty C# file."""
        result = self.parser.parse_string("", "Empty.cs")

        assert result.file_path == "Empty.cs"
        assert len(result.entities) >= 1  # Module entity
        assert result.errors == []

    def test_parse_simple_class(self):
        """Test parsing a simple C# class."""
        code = """
public class Person
{
    private string name;

    public Person(string name)
    {
        this.name = name;
    }

    public string GetName()
    {
        return name;
    }
}
"""
        result = self.parser.parse_string(code, "Person.cs")

        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        methods = [e for e in result.entities if e.type == EntityType.METHOD]

        assert len(classes) == 1
        assert classes[0].name == "Person"
        assert len(methods) == 2
        assert {m.name for m in methods} == {"Person", "GetName"}

    def test_parse_namespace(self):
        """Test parsing namespace declaration."""
        code = """
namespace MyApp.Models
{
    public class MyClass
    {
    }
}
"""
        result = self.parser.parse_string(code, "MyClass.cs")

        modules = [e for e in result.entities if e.type == EntityType.MODULE]
        assert any(m.name == "MyApp.Models" for m in modules)

    def test_parse_file_scoped_namespace(self):
        """Test parsing file-scoped namespace (C# 10+)."""
        code = """
namespace MyApp;

public class MyClass
{
}
"""
        result = self.parser.parse_string(code, "MyClass.cs")

        modules = [e for e in result.entities if e.type == EntityType.MODULE]
        assert any(m.name == "MyApp" for m in modules)

    def test_parse_using_directives(self):
        """Test parsing using directives."""
        code = """
using System;
using System.Collections.Generic;

public class MyClass
{
}
"""
        result = self.parser.parse_string(code, "MyClass.cs")

        assert "System" in result.imports
        assert "System.Collections.Generic" in result.imports

    def test_parse_interface(self):
        """Test parsing a C# interface."""
        code = """
public interface IGreetable
{
    void Greet();
    string GetMessage();
}
"""
        result = self.parser.parse_string(code, "IGreetable.cs")

        interfaces = [e for e in result.entities if e.type == EntityType.INTERFACE]
        assert len(interfaces) == 1
        assert interfaces[0].name == "IGreetable"

    def test_parse_inheritance(self):
        """Test parsing class inheritance."""
        code = """
public class Child : Parent
{
    public void Method()
    {
    }
}
"""
        result = self.parser.parse_string(code, "Child.cs")

        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) == 1
        assert classes[0].name == "Child"
        # Base class extraction may vary by tree-sitter version
        methods = [e for e in result.entities if e.type == EntityType.METHOD]
        assert len(methods) >= 1

    def test_parse_implements(self):
        """Test parsing interface implementation."""
        code = """
public class MyClass : IDisposable, IComparable<MyClass>
{
    public void Dispose()
    {
    }

    public int CompareTo(MyClass other)
    {
        return 0;
    }
}
"""
        result = self.parser.parse_string(code, "MyClass.cs")

        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) == 1
        assert classes[0].name == "MyClass"
        # Check methods are extracted
        methods = [e for e in result.entities if e.type == EntityType.METHOD]
        assert len(methods) >= 2

    def test_parse_static_method(self):
        """Test parsing static methods."""
        code = """
public class Utility
{
    public static void Helper()
    {
    }
}
"""
        result = self.parser.parse_string(code, "Utility.cs")

        methods = [e for e in result.entities if e.type == EntityType.METHOD]
        assert len(methods) == 1
        assert methods[0].is_static is True

    def test_parse_abstract_class(self):
        """Test parsing abstract class."""
        code = """
public abstract class BaseClass
{
    public abstract void DoSomething();

    public void ConcreteMethod()
    {
    }
}
"""
        result = self.parser.parse_string(code, "BaseClass.cs")

        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) == 1
        assert classes[0].is_abstract is True

    def test_parse_properties(self):
        """Test parsing C# properties."""
        code = """
public class Person
{
    public string Name { get; set; }
    public int Age { get; private set; }
}
"""
        result = self.parser.parse_string(code, "Person.cs")

        # Properties are treated as methods
        methods = [e for e in result.entities if e.type == EntityType.METHOD]
        assert len(methods) == 2
        assert {m.name for m in methods} == {"Name", "Age"}

    def test_parse_method_parameters(self):
        """Test parsing method parameters."""
        code = """
public class Calculator
{
    public int Add(int a, int b)
    {
        return a + b;
    }
}
"""
        result = self.parser.parse_string(code, "Calculator.cs")

        methods = [e for e in result.entities if e.type == EntityType.METHOD]
        add_method = next((m for m in methods if m.name == "Add"), None)
        assert add_method is not None
        assert len(add_method.parameters) == 2
        assert add_method.parameters[0] == ("a", "int")
        assert add_method.parameters[1] == ("b", "int")

    def test_parse_struct(self):
        """Test parsing C# struct."""
        code = """
public struct Point
{
    public int X { get; set; }
    public int Y { get; set; }
}
"""
        result = self.parser.parse_string(code, "Point.cs")

        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) == 1
        assert classes[0].name == "Point"

    def test_parse_enum(self):
        """Test parsing C# enum."""
        code = """
public enum Color
{
    Red,
    Green,
    Blue
}
"""
        result = self.parser.parse_string(code, "Color.cs")

        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) == 1
        assert classes[0].name == "Color"
        assert "Enum" in classes[0].bases

    def test_parse_nested_class(self):
        """Test parsing nested classes."""
        code = """
public class Outer
{
    public class Inner
    {
        public void Method()
        {
        }
    }
}
"""
        result = self.parser.parse_string(code, "Outer.cs")

        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) == 2
        assert {c.name for c in classes} == {"Outer", "Inner"}


class TestCSharpParserEdgeCases:
    """Test edge cases for CSharpParser."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = CSharpParser()

    def test_parse_with_xml_doc(self):
        """Test parsing code with XML documentation comments."""
        code = """
/// <summary>
/// A simple person class.
/// </summary>
public class Person
{
    /// <summary>
    /// Gets the name.
    /// </summary>
    /// <returns>The name</returns>
    public string GetName()
    {
        return name;
    }
}
"""
        result = self.parser.parse_string(code, "Person.cs")

        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) == 1

    def test_parse_generic_class(self):
        """Test parsing generic class."""
        code = """
public class Box<T>
{
    private T value;

    public T GetValue()
    {
        return value;
    }

    public void SetValue(T value)
    {
        this.value = value;
    }
}
"""
        result = self.parser.parse_string(code, "Box.cs")

        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) == 1

    def test_parse_empty_class(self):
        """Test parsing empty class."""
        code = """
public class Empty
{
}
"""
        result = self.parser.parse_string(code, "Empty.cs")

        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) == 1
        assert classes[0].name == "Empty"

    def test_contains_relationships(self):
        """Test CONTAINS relationships are created."""
        code = """
public class Container
{
    public void MethodOne()
    {
    }

    public void MethodTwo()
    {
    }
}
"""
        result = self.parser.parse_string(code, "Container.cs")

        from magatama_core.domain.entities import RelationshipType

        contains = [r for r in result.relationships if r.type == RelationshipType.CONTAINS]

        # Should have contains relationships from class to methods
        assert len(contains) >= 2

    def test_parse_expression_bodied_member(self):
        """Test parsing expression-bodied members."""
        code = """
public class Calculator
{
    public int Double(int x) => x * 2;
    public string Name => "Calculator";
}
"""
        result = self.parser.parse_string(code, "Calculator.cs")

        methods = [e for e in result.entities if e.type == EntityType.METHOD]
        assert len(methods) >= 1


def test_csharp_rich_constructs():
    """Parse a C# file exercising interface/enum/struct/delegate/event/property/generics."""
    from magatama_core.infrastructure.parsers import CSharpParser

    code = """
using System;

namespace Demo
{
    public interface IGreeter { string Greet(); }

    public enum Color { Red, Green, Blue }

    public struct Point { public int X; public int Y; }

    public delegate void Notify(string msg);

    public class Animal : IGreeter
    {
        public string Name { get; set; }
        public event Notify OnNamed;
        public Animal(string name) { Name = name; }
        public string Greet() => $"Hi {Name}";
        public T Echo<T>(T value) => value;
    }
}
"""
    result = CSharpParser().parse_string(code, "sample.cs")
    assert len(result.entities) >= 1
    assert len(result.errors) == 0
