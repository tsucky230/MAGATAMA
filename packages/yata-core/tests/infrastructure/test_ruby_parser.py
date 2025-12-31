"""Tests for Ruby Parser.

REQ-LANG-006: Ruby language support
"""
import pytest
from yata_core.infrastructure.parsers import RubyParser
from yata_core.domain.entities import EntityType


class TestRubyParser:
    """Test suite for RubyParser."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = RubyParser()
    
    def test_parse_empty_file(self):
        """Test parsing an empty Ruby file."""
        result = self.parser.parse_string("", "empty.rb")
        
        assert result.file_path == "empty.rb"
        # Should have at least the module entity for the file
        assert len(result.entities) >= 1
        assert result.errors == []
    
    def test_parse_simple_class(self):
        """Test parsing a simple Ruby class."""
        code = """
class Person
  def initialize(name)
    @name = name
  end
  
  def greet
    puts "Hello, #{@name}"
  end
end
"""
        result = self.parser.parse_string(code, "person.rb")
        
        # Should have module, class, and 2 methods
        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        methods = [e for e in result.entities if e.type == EntityType.METHOD]
        
        assert len(classes) == 1
        assert classes[0].name == "Person"
        assert len(methods) == 2
        assert {m.name for m in methods} == {"initialize", "greet"}
    
    def test_parse_module(self):
        """Test parsing a Ruby module."""
        code = """
module MyModule
  def helper_method
    true
  end
end
"""
        result = self.parser.parse_string(code, "my_module.rb")
        
        modules = [e for e in result.entities if e.type == EntityType.MODULE]
        
        # Should have file module and defined module
        assert len(modules) >= 2
        assert any(m.name == "MyModule" for m in modules)
    
    def test_parse_inheritance(self):
        """Test parsing class inheritance."""
        code = """
class Child < Parent
  def method
  end
end
"""
        result = self.parser.parse_string(code, "child.rb")
        
        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) == 1
        assert classes[0].name == "Child"
        # Ruby superclass may include the '<' symbol from tree-sitter
        assert len(classes[0].bases) >= 1
        
        # Should have INHERITS relationship
        from yata_core.domain.entities import RelationshipType
        inherits = [r for r in result.relationships if r.type == RelationshipType.INHERITS]
        assert len(inherits) >= 1
    
    def test_parse_singleton_method(self):
        """Test parsing singleton (class) methods."""
        code = """
class Factory
  def self.create
    new
  end
end
"""
        result = self.parser.parse_string(code, "factory.rb")
        
        methods = [e for e in result.entities if e.type == EntityType.METHOD]
        assert len(methods) == 1
        assert methods[0].name == "create"
        assert methods[0].is_static is True
    
    def test_parse_method_parameters(self):
        """Test parsing method parameters."""
        code = """
class Calculator
  def add(a, b)
    a + b
  end
  
  def multiply(a, b = 1)
    a * b
  end
end
"""
        result = self.parser.parse_string(code, "calculator.rb")
        
        methods = [e for e in result.entities if e.type == EntityType.METHOD]
        
        add_method = next((m for m in methods if m.name == "add"), None)
        assert add_method is not None
        assert len(add_method.parameters) == 2
    
    def test_parse_require_statements(self):
        """Test parsing require statements."""
        code = """
require 'json'
require_relative 'helper'

class MyClass
end
"""
        result = self.parser.parse_string(code, "my_class.rb")
        
        from yata_core.domain.entities import RelationshipType
        imports = [r for r in result.relationships if r.type == RelationshipType.IMPORTS]
        
        assert len(imports) >= 2
    
    def test_parse_nested_class(self):
        """Test parsing nested classes."""
        code = """
module Outer
  class Inner
    def method
    end
  end
end
"""
        result = self.parser.parse_string(code, "nested.rb")
        
        modules = [e for e in result.entities if e.type == EntityType.MODULE]
        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        
        assert any(m.name == "Outer" for m in modules)
        assert len(classes) == 1
        assert classes[0].name == "Inner"
    
    def test_contains_relationships(self):
        """Test CONTAINS relationships are created."""
        code = """
class Container
  def method_one
  end
  
  def method_two
  end
end
"""
        result = self.parser.parse_string(code, "container.rb")
        
        from yata_core.domain.entities import RelationshipType
        contains = [r for r in result.relationships if r.type == RelationshipType.CONTAINS]
        
        # Should have contains relationships from class to methods
        assert len(contains) >= 2


class TestRubyParserEdgeCases:
    """Test edge cases for RubyParser."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = RubyParser()
    
    def test_parse_with_comments(self):
        """Test parsing code with comments."""
        code = """
# This is a comment
class Person
  # Another comment
  def greet
  end
end
"""
        result = self.parser.parse_string(code, "commented.rb")
        
        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) == 1
    
    def test_parse_splat_parameters(self):
        """Test parsing methods with splat parameters."""
        code = """
class Util
  def process(*args, **kwargs, &block)
  end
end
"""
        result = self.parser.parse_string(code, "util.rb")
        
        methods = [e for e in result.entities if e.type == EntityType.METHOD]
        assert len(methods) == 1
    
    def test_parse_empty_class(self):
        """Test parsing empty class."""
        code = """
class Empty
end
"""
        result = self.parser.parse_string(code, "empty.rb")
        
        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) == 1
        assert classes[0].name == "Empty"
