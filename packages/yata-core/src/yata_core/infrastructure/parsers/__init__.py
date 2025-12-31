"""
Parser Adapters - Tree-sitter based AST parsing.

ADR-003: Tree-sitter for multi-language support
REQ-LANG-001 to REQ-LANG-005: Language support
"""
from yata_core.infrastructure.parsers.parse_result import ParseResult
from yata_core.infrastructure.parsers.python_parser import PythonParser
from yata_core.infrastructure.parsers.typescript_parser import TypeScriptParser
from yata_core.infrastructure.parsers.javascript_parser import JavaScriptParser
from yata_core.infrastructure.parsers.rust_parser import RustParser
from yata_core.infrastructure.parsers.go_parser import GoParser

__all__ = [
    "ParseResult",
    "PythonParser",
    "TypeScriptParser",
    "JavaScriptParser",
    "RustParser",
    "GoParser",
]