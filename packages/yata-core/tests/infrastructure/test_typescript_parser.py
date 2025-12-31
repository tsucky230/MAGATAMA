"""Tests for TypeScript Parser."""

import pytest
from pathlib import Path
import tempfile

from yata_core.infrastructure.parsers.typescript_parser import TypeScriptParser
from yata_core.domain.entities import EntityType
from yata_core.domain.entities.relationships import RelationshipType


class TestTypeScriptParser:
    """Tests for TypeScriptParser."""

    @pytest.fixture
    def parser(self) -> TypeScriptParser:
        """Create parser instance."""
        return TypeScriptParser()

    def test_parser_initialization(self, parser: TypeScriptParser) -> None:
        """Test parser initializes correctly."""
        assert parser is not None

    def test_parse_simple_function(self, parser: TypeScriptParser) -> None:
        """Test parsing a simple function."""
        code = '''
function greet(name: string): string {
    return `Hello, ${name}!`;
}
'''
        result = parser.parse_string(code, "test.ts")

        functions = [e for e in result.entities if e.type == EntityType.FUNCTION]
        assert len(functions) >= 1
        assert any(f.name == "greet" for f in functions)

    def test_parse_arrow_function(self, parser: TypeScriptParser) -> None:
        """Test parsing arrow functions."""
        code = '''
const add = (a: number, b: number): number => a + b;

const multiply = (a: number, b: number): number => {
    return a * b;
};
'''
        result = parser.parse_string(code, "test.ts")

        # Arrow functions may be captured as variables or functions
        assert len(result.entities) >= 1

    def test_parse_class(self, parser: TypeScriptParser) -> None:
        """Test parsing a class."""
        code = '''
class Person {
    private name: string;
    
    constructor(name: string) {
        this.name = name;
    }
    
    greet(): string {
        return `Hello, I'm ${this.name}`;
    }
}
'''
        result = parser.parse_string(code, "test.ts")

        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) >= 1
        assert any(c.name == "Person" for c in classes)

        # Check for methods
        methods = [e for e in result.entities if e.type == EntityType.METHOD]
        assert len(methods) >= 1

    def test_parse_interface(self, parser: TypeScriptParser) -> None:
        """Test parsing interfaces."""
        code = '''
interface User {
    id: number;
    name: string;
    email?: string;
}

interface Admin extends User {
    permissions: string[];
}
'''
        result = parser.parse_string(code, "test.ts")

        interfaces = [e for e in result.entities if e.type == EntityType.INTERFACE]
        assert len(interfaces) >= 2
        assert any(i.name == "User" for i in interfaces)
        assert any(i.name == "Admin" for i in interfaces)

    def test_parse_type_alias(self, parser: TypeScriptParser) -> None:
        """Test parsing type aliases."""
        code = '''
type ID = string | number;
type UserRole = 'admin' | 'user' | 'guest';
'''
        result = parser.parse_string(code, "test.ts")

        types = [e for e in result.entities if e.type == EntityType.TYPE]
        assert len(types) >= 2

    def test_parse_enum(self, parser: TypeScriptParser) -> None:
        """Test parsing enums."""
        code = '''
enum Color {
    Red = 'RED',
    Green = 'GREEN',
    Blue = 'BLUE'
}

enum Status {
    Active,
    Inactive,
    Pending
}
'''
        result = parser.parse_string(code, "test.ts")

        enums = [e for e in result.entities if e.type == EntityType.ENUM]
        assert len(enums) >= 2

    def test_parse_async_function(self, parser: TypeScriptParser) -> None:
        """Test parsing async functions."""
        code = '''
async function fetchData(url: string): Promise<Response> {
    return await fetch(url);
}
'''
        result = parser.parse_string(code, "test.ts")

        functions = [e for e in result.entities if e.type == EntityType.FUNCTION]
        assert len(functions) >= 1
        assert any(f.name == "fetchData" for f in functions)

    def test_parse_exported_items(self, parser: TypeScriptParser) -> None:
        """Test parsing exported items."""
        code = '''
export function publicFunc(): void {}
export class PublicClass {}
export interface PublicInterface {}
export type PublicType = string;
'''
        result = parser.parse_string(code, "test.ts")

        assert len(result.entities) >= 4

    def test_parse_file(self, parser: TypeScriptParser) -> None:
        """Test parsing a TypeScript file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".ts", delete=False
        ) as f:
            f.write('''
interface Config {
    debug: boolean;
}

class App {
    constructor(private config: Config) {}
    
    run(): void {
        console.log("Running...");
    }
}
''')
            f.flush()
            file_path = Path(f.name)

        result = parser.parse_file(file_path)

        assert len(result.entities) >= 2
        assert result.file_path == str(file_path)

    def test_parse_tsx_file(self, parser: TypeScriptParser) -> None:
        """Test parsing a TSX file (React)."""
        code = '''
interface Props {
    name: string;
}

function Greeting({ name }: Props): JSX.Element {
    return <div>Hello, {name}!</div>;
}

export default Greeting;
'''
        result = parser.parse_string(code, "test.tsx")

        # Should parse interface and function
        assert len(result.entities) >= 2

    def test_parse_function_calls_relationship(self, parser: TypeScriptParser) -> None:
        """Test that function calls create CALLS relationships."""
        code = '''
function helper(): number {
    return 42;
}

function main(): number {
    const result = helper();
    return result;
}
'''
        result = parser.parse_string(code, "test.ts")
        
        # Should have CALLS relationship: main -> helper
        calls_relationships = [
            r for r in result.relationships 
            if r.type == RelationshipType.CALLS
        ]
        assert len(calls_relationships) >= 1
        
        # Verify the relationship
        functions = {e.name: e for e in result.entities if e.type == EntityType.FUNCTION}
        main_id = functions["main"].id
        helper_id = functions["helper"].id
        
        assert any(
            r.source_id == main_id and r.target_id == helper_id
            for r in calls_relationships
        )

    def test_parse_multiple_calls(self, parser: TypeScriptParser) -> None:
        """Test detection of multiple function calls."""
        code = '''
function foo(): void {}

function bar(): void {}

function baz(): void {
    foo();
    bar();
}
'''
        result = parser.parse_string(code, "test.ts")
        
        calls_relationships = [
            r for r in result.relationships 
            if r.type == RelationshipType.CALLS
        ]
        
        # baz should call both foo and bar
        functions = {e.name: e for e in result.entities if e.type == EntityType.FUNCTION}
        baz_id = functions["baz"].id
        foo_id = functions["foo"].id
        bar_id = functions["bar"].id
        
        baz_calls = [r for r in calls_relationships if r.source_id == baz_id]
        assert len(baz_calls) == 2
        
        target_ids = {r.target_id for r in baz_calls}
        assert foo_id in target_ids
        assert bar_id in target_ids

    def test_parse_imports_relationship(self, parser: TypeScriptParser) -> None:
        """Test that import statements create IMPORTS relationships."""
        code = '''
import { Component } from "react";
import * as fs from "fs";
import axios from "axios";
'''
        result = parser.parse_string(code, "test.ts")
        
        # Should have IMPORTS relationships
        imports_relationships = [
            r for r in result.relationships 
            if r.type == RelationshipType.IMPORTS
        ]
        assert len(imports_relationships) >= 3
        
        # Verify module names
        imported_modules = {r.metadata.get("module_name") for r in imports_relationships}
        assert "react" in imported_modules
        assert "fs" in imported_modules
        assert "axios" in imported_modules

    def test_parse_named_imports_relationship(self, parser: TypeScriptParser) -> None:
        """Test that named imports are captured in metadata."""
        code = '''
import { useState, useEffect } from "react";
'''
        result = parser.parse_string(code, "test.ts")
        
        imports_relationships = [
            r for r in result.relationships 
            if r.type == RelationshipType.IMPORTS
        ]
        assert len(imports_relationships) >= 1
        
        react_import = next(
            (r for r in imports_relationships if r.metadata.get("module_name") == "react"),
            None
        )
        assert react_import is not None
        assert "useState" in react_import.metadata.get("imported_names", [])
        assert "useEffect" in react_import.metadata.get("imported_names", [])
