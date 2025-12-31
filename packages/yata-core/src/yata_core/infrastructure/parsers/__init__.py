"""
Parser Adapters - Tree-sitter based AST parsing.

ADR-003: Tree-sitter for multi-language support
REQ-LANG-001 to REQ-LANG-024: Multi-language support
"""
from yata_core.infrastructure.parsers.parse_result import ParseResult
from yata_core.infrastructure.parsers.python_parser import PythonParser
from yata_core.infrastructure.parsers.typescript_parser import TypeScriptParser
from yata_core.infrastructure.parsers.javascript_parser import JavaScriptParser
from yata_core.infrastructure.parsers.rust_parser import RustParser
from yata_core.infrastructure.parsers.go_parser import GoParser
from yata_core.infrastructure.parsers.ruby_parser import RubyParser
from yata_core.infrastructure.parsers.java_parser import JavaParser
from yata_core.infrastructure.parsers.csharp_parser import CSharpParser
from yata_core.infrastructure.parsers.cpp_parser import CppParser
from yata_core.infrastructure.parsers.objc_parser import ObjectiveCParser
from yata_core.infrastructure.parsers.php_parser import PhpParser
from yata_core.infrastructure.parsers.swift_parser import SwiftParser
from yata_core.infrastructure.parsers.kotlin_parser import KotlinParser
from yata_core.infrastructure.parsers.scala_parser import ScalaParser
from yata_core.infrastructure.parsers.lua_parser import LuaParser
from yata_core.infrastructure.parsers.haskell_parser import HaskellParser
from yata_core.infrastructure.parsers.elixir_parser import ElixirParser
from yata_core.infrastructure.parsers.julia_parser import JuliaParser
from yata_core.infrastructure.parsers.sql_parser import SqlParser
from yata_core.infrastructure.parsers.groovy_parser import GroovyParser
from yata_core.infrastructure.parsers.dart_parser import DartParser
from yata_core.infrastructure.parsers.c_parser import CParser
from yata_core.infrastructure.parsers.zig_parser import ZigParser
from yata_core.infrastructure.parsers.yaml_parser import YAMLParser

__all__ = [
    "ParseResult",
    "PythonParser",
    "TypeScriptParser",
    "JavaScriptParser",
    "RustParser",
    "GoParser",
    "RubyParser",
    "JavaParser",
    "CSharpParser",
    "CppParser",
    "ObjectiveCParser",
    "PhpParser",
    "SwiftParser",
    "KotlinParser",
    "ScalaParser",
    "LuaParser",
    "HaskellParser",
    "ElixirParser",
    "JuliaParser",
    "SqlParser",
    "GroovyParser",
    "DartParser",
    "CParser",
    "ZigParser",
    "YAMLParser",
]