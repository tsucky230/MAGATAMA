"""
Parser Adapters - Tree-sitter based AST parsing.

ADR-003: Tree-sitter for multi-language support
REQ-LANG-001 to REQ-LANG-024: Multi-language support
"""

from magatama_core.infrastructure.parsers.c_parser import CParser
from magatama_core.infrastructure.parsers.cpp_parser import CppParser
from magatama_core.infrastructure.parsers.csharp_parser import CSharpParser
from magatama_core.infrastructure.parsers.dart_parser import DartParser
from magatama_core.infrastructure.parsers.elixir_parser import ElixirParser
from magatama_core.infrastructure.parsers.go_parser import GoParser
from magatama_core.infrastructure.parsers.groovy_parser import GroovyParser
from magatama_core.infrastructure.parsers.haskell_parser import HaskellParser
from magatama_core.infrastructure.parsers.java_parser import JavaParser
from magatama_core.infrastructure.parsers.javascript_parser import JavaScriptParser
from magatama_core.infrastructure.parsers.julia_parser import JuliaParser
from magatama_core.infrastructure.parsers.kotlin_parser import KotlinParser
from magatama_core.infrastructure.parsers.lua_parser import LuaParser
from magatama_core.infrastructure.parsers.objc_parser import ObjectiveCParser
from magatama_core.infrastructure.parsers.parse_result import ParseResult
from magatama_core.infrastructure.parsers.php_parser import PhpParser
from magatama_core.infrastructure.parsers.python_parser import PythonParser
from magatama_core.infrastructure.parsers.ruby_parser import RubyParser
from magatama_core.infrastructure.parsers.rust_parser import RustParser
from magatama_core.infrastructure.parsers.scala_parser import ScalaParser
from magatama_core.infrastructure.parsers.sql_parser import SqlParser
from magatama_core.infrastructure.parsers.swift_parser import SwiftParser
from magatama_core.infrastructure.parsers.typescript_parser import TypeScriptParser
from magatama_core.infrastructure.parsers.yaml_parser import YAMLParser
from magatama_core.infrastructure.parsers.zig_parser import ZigParser

__all__ = [
    "CParser",
    "CSharpParser",
    "CppParser",
    "DartParser",
    "ElixirParser",
    "GoParser",
    "GroovyParser",
    "HaskellParser",
    "JavaParser",
    "JavaScriptParser",
    "JuliaParser",
    "KotlinParser",
    "LuaParser",
    "ObjectiveCParser",
    "ParseResult",
    "PhpParser",
    "PythonParser",
    "RubyParser",
    "RustParser",
    "ScalaParser",
    "SqlParser",
    "SwiftParser",
    "TypeScriptParser",
    "YAMLParser",
    "ZigParser",
]
