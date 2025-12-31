"""Tests for PHP Parser."""

import pytest
from yata_core.infrastructure.parsers import PhpParser
from yata_core.domain.entities import EntityType


@pytest.fixture
def parser() -> PhpParser:
    return PhpParser()


class TestPhpParserBasic:
    """Basic PHP parsing tests."""

    def test_parse_empty_string(self, parser: PhpParser) -> None:
        result = parser.parse_string("", "test.php")
        assert result.file_path == "test.php"
        assert len(result.errors) == 0

    def test_parse_class(self, parser: PhpParser) -> None:
        code = '''<?php
class MyClass {
    public function method() {}
}
'''
        result = parser.parse_string(code, "test.php")
        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) >= 1

    def test_parse_interface(self, parser: PhpParser) -> None:
        code = '''<?php
interface MyInterface {
    public function method();
}
'''
        result = parser.parse_string(code, "test.php")
        interfaces = [e for e in result.entities if e.type == EntityType.INTERFACE]
        assert len(interfaces) >= 1

    def test_parse_trait(self, parser: PhpParser) -> None:
        code = '''<?php
trait MyTrait {
    public function traitMethod() {}
}
'''
        result = parser.parse_string(code, "test.php")
        assert len(result.entities) >= 1

    def test_parse_function(self, parser: PhpParser) -> None:
        code = '''<?php
function standalone_function($x, $y) {
    return $x + $y;
}
'''
        result = parser.parse_string(code, "test.php")
        functions = [e for e in result.entities if e.type == EntityType.FUNCTION]
        assert len(functions) >= 1

    def test_parse_namespace(self, parser: PhpParser) -> None:
        code = '''<?php
namespace App\\Services;

class UserService {}
'''
        result = parser.parse_string(code, "test.php")
        assert len(result.entities) >= 1


class TestPhpParserAdvanced:
    """Advanced PHP parsing tests."""

    def test_parse_use_statements(self, parser: PhpParser) -> None:
        code = '''<?php
use App\\Models\\User;
use Illuminate\\Support\\Collection;

class MyClass {}
'''
        result = parser.parse_string(code, "test.php")
        assert len(result.imports) >= 1

    def test_parse_abstract_class(self, parser: PhpParser) -> None:
        code = '''<?php
abstract class AbstractHandler {
    abstract public function handle();
    
    public function common() {}
}
'''
        result = parser.parse_string(code, "test.php")
        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) >= 1

    def test_parse_class_with_inheritance(self, parser: PhpParser) -> None:
        code = '''<?php
class Parent {
    public function parentMethod() {}
}

class Child extends Parent implements MyInterface {
    public function childMethod() {}
}
'''
        result = parser.parse_string(code, "test.php")
        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) >= 2
