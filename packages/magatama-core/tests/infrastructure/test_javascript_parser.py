"""Tests for JavaScript Parser.

These tests verify JavaScript/JSX parsing capabilities.
"""

from pathlib import Path

import pytest

from magatama_core.domain.entities import (
    ClassEntity,
    EntityType,
    FunctionEntity,
    MethodEntity,
    ModuleEntity,
)
from magatama_core.infrastructure.parsers.javascript_parser import JavaScriptParser


class TestJavaScriptParser:
    """Tests for JavaScript parser."""

    @pytest.fixture
    def parser(self) -> JavaScriptParser:
        """Create a parser instance."""
        return JavaScriptParser()

    @pytest.mark.unit
    def test_parser_initialization(self, parser: JavaScriptParser) -> None:
        """Test parser initializes correctly."""
        assert parser is not None
        assert parser._js_language is not None

    @pytest.mark.unit
    def test_parse_simple_function(self, parser: JavaScriptParser) -> None:
        """Test parsing a simple function declaration."""
        code = """
function greet(name) {
    return "Hello, " + name;
}
"""
        result = parser.parse_string(code, "test.js")

        assert result.file_path == "test.js"
        assert len(result.errors) == 0

        # Find the function entity
        funcs = [e for e in result.entities if isinstance(e, FunctionEntity)]
        assert len(funcs) >= 1

        greet = next((f for f in funcs if f.name == "greet"), None)
        assert greet is not None
        assert greet.type == EntityType.FUNCTION
        assert len(greet.parameters) == 1
        assert greet.parameters[0][0] == "name"
        assert greet.parameters[0][1] is None  # No type in JS

    @pytest.mark.unit
    def test_parse_arrow_function(self, parser: JavaScriptParser) -> None:
        """Test parsing arrow functions."""
        code = """
const add = (a, b) => a + b;
const multiply = (x, y) => {
    return x * y;
};
"""
        result = parser.parse_string(code, "arrows.js")

        funcs = [e for e in result.entities if isinstance(e, FunctionEntity)]
        func_names = [f.name for f in funcs]

        assert "add" in func_names
        assert "multiply" in func_names

    @pytest.mark.unit
    def test_parse_class(self, parser: JavaScriptParser) -> None:
        """Test parsing a class declaration."""
        code = """
class Calculator {
    constructor(value) {
        this.value = value;
    }
    
    add(n) {
        return this.value + n;
    }
    
    static create() {
        return new Calculator(0);
    }
}
"""
        result = parser.parse_string(code, "calc.js")

        # Find class
        classes = [e for e in result.entities if isinstance(e, ClassEntity)]
        assert len(classes) == 1
        assert classes[0].name == "Calculator"

        # Find methods
        methods = [e for e in result.entities if isinstance(e, MethodEntity)]
        method_names = [m.name for m in methods]

        assert "constructor" in method_names
        assert "add" in method_names
        assert "create" in method_names

        # Check static method
        create_method = next((m for m in methods if m.name == "create"), None)
        assert create_method is not None
        assert create_method.is_static is True

    @pytest.mark.unit
    def test_parse_class_extends(self, parser: JavaScriptParser) -> None:
        """Test parsing class inheritance."""
        code = """
class Animal {
    speak() {}
}

class Dog extends Animal {
    bark() {}
}
"""
        result = parser.parse_string(code, "animals.js")

        classes = [e for e in result.entities if isinstance(e, ClassEntity)]
        dog = next((c for c in classes if c.name == "Dog"), None)

        assert dog is not None
        assert "Animal" in dog.bases

    @pytest.mark.unit
    def test_parse_async_function(self, parser: JavaScriptParser) -> None:
        """Test parsing async functions."""
        code = """
async function fetchData(url) {
    const response = await fetch(url);
    return response.json();
}
"""
        result = parser.parse_string(code, "async.js")

        funcs = [e for e in result.entities if isinstance(e, FunctionEntity)]
        fetch_func = next((f for f in funcs if f.name == "fetchData"), None)

        assert fetch_func is not None
        assert fetch_func.is_async is True

    @pytest.mark.unit
    def test_parse_exports(self, parser: JavaScriptParser) -> None:
        """Test parsing exported items."""
        code = """
export function publicFunc() {}

export class ExportedClass {
    method() {}
}

export default function main() {}
"""
        result = parser.parse_string(code, "exports.js")

        funcs = [e for e in result.entities if isinstance(e, FunctionEntity)]
        func_names = [f.name for f in funcs]

        assert "publicFunc" in func_names
        assert "main" in func_names

        classes = [e for e in result.entities if isinstance(e, ClassEntity)]
        assert any(c.name == "ExportedClass" for c in classes)

    @pytest.mark.unit
    def test_parse_imports(self, parser: JavaScriptParser) -> None:
        """Test parsing import statements."""
        code = """
import { useState, useEffect } from 'react';
import axios from 'axios';

function App() {}
"""
        result = parser.parse_string(code, "app.js")

        assert len(result.imports) >= 2
        assert any("react" in imp for imp in result.imports)
        assert any("axios" in imp for imp in result.imports)

    @pytest.mark.unit
    def test_parse_file(self, parser: JavaScriptParser, tmp_path: Path) -> None:
        """Test parsing from a file."""
        test_file = tmp_path / "module.js"
        test_file.write_text("""
function helper() {
    return 42;
}

class Service {
    call() {}
}
""")

        result = parser.parse_file(test_file)

        assert result.file_path == str(test_file)

        # Should have module, function, class, method
        modules = [e for e in result.entities if isinstance(e, ModuleEntity)]
        funcs = [e for e in result.entities if isinstance(e, FunctionEntity)]
        classes = [e for e in result.entities if isinstance(e, ClassEntity)]

        assert len(modules) >= 1
        assert len(funcs) >= 1
        assert len(classes) >= 1

    @pytest.mark.unit
    def test_parse_function_with_default_params(self, parser: JavaScriptParser) -> None:
        """Test parsing function with default parameters."""
        code = """
function greet(name = "World", greeting = "Hello") {
    return greeting + ", " + name;
}
"""
        result = parser.parse_string(code, "defaults.js")

        funcs = [e for e in result.entities if isinstance(e, FunctionEntity)]
        greet = next((f for f in funcs if f.name == "greet"), None)

        assert greet is not None
        assert len(greet.parameters) == 2

    @pytest.mark.unit
    def test_parse_rest_parameters(self, parser: JavaScriptParser) -> None:
        """Test parsing function with rest parameters."""
        code = """
function sum(...numbers) {
    return numbers.reduce((a, b) => a + b, 0);
}
"""
        result = parser.parse_string(code, "rest.js")

        funcs = [e for e in result.entities if isinstance(e, FunctionEntity)]
        sum_func = next((f for f in funcs if f.name == "sum"), None)

        assert sum_func is not None
        assert len(sum_func.parameters) >= 1
        assert "...numbers" in sum_func.parameters[0][0]

    @pytest.mark.unit
    def test_parse_function_calls_relationship(self, parser: JavaScriptParser) -> None:
        """Test that function calls create CALLS relationships."""
        from magatama_core.domain.entities.relationships import RelationshipType

        code = """
function helper() {
    return 42;
}

function main() {
    const result = helper();
    return result;
}
"""
        result = parser.parse_string(code, "test.js")

        # Should have CALLS relationship: main -> helper
        calls_relationships = [r for r in result.relationships if r.type == RelationshipType.CALLS]
        assert len(calls_relationships) >= 1

        # Verify the relationship
        functions = {e.name: e for e in result.entities if isinstance(e, FunctionEntity)}
        main_id = functions["main"].id
        helper_id = functions["helper"].id

        assert any(r.source_id == main_id and r.target_id == helper_id for r in calls_relationships)

    @pytest.mark.unit
    def test_parse_multiple_calls(self, parser: JavaScriptParser) -> None:
        """Test detection of multiple function calls."""
        from magatama_core.domain.entities.relationships import RelationshipType

        code = """
function foo() {}

function bar() {}

function baz() {
    foo();
    bar();
}
"""
        result = parser.parse_string(code, "test.js")

        calls_relationships = [r for r in result.relationships if r.type == RelationshipType.CALLS]

        # baz should call both foo and bar
        functions = {e.name: e for e in result.entities if isinstance(e, FunctionEntity)}
        baz_id = functions["baz"].id
        foo_id = functions["foo"].id
        bar_id = functions["bar"].id

        baz_calls = [r for r in calls_relationships if r.source_id == baz_id]
        assert len(baz_calls) == 2

        target_ids = {r.target_id for r in baz_calls}
        assert foo_id in target_ids
        assert bar_id in target_ids

    @pytest.mark.unit
    def test_parse_imports_relationship(self, parser: JavaScriptParser) -> None:
        """Test that import statements create IMPORTS relationships."""
        from magatama_core.domain.entities.relationships import RelationshipType

        code = """
import { useState } from "react";
import axios from "axios";
import * as path from "path";
"""
        result = parser.parse_string(code, "test.js")

        # Should have IMPORTS relationships
        imports_relationships = [
            r for r in result.relationships if r.type == RelationshipType.IMPORTS
        ]
        assert len(imports_relationships) >= 3

        # Verify module names
        imported_modules = {r.metadata.get("module_name") for r in imports_relationships}
        assert "react" in imported_modules
        assert "axios" in imported_modules
        assert "path" in imported_modules

    @pytest.mark.unit
    def test_parse_named_imports_relationship(self, parser: JavaScriptParser) -> None:
        """Test that named imports are captured in metadata."""
        from magatama_core.domain.entities.relationships import RelationshipType

        code = """
import { createElement, Fragment } from "react";
"""
        result = parser.parse_string(code, "test.js")

        imports_relationships = [
            r for r in result.relationships if r.type == RelationshipType.IMPORTS
        ]
        assert len(imports_relationships) >= 1

        react_import = next(
            (r for r in imports_relationships if r.metadata.get("module_name") == "react"), None
        )
        assert react_import is not None
        assert "createElement" in react_import.metadata.get("imported_names", [])
        assert "Fragment" in react_import.metadata.get("imported_names", [])
