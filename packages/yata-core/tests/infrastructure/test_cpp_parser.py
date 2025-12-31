"""Tests for C++ Parser."""

import pytest
from yata_core.infrastructure.parsers import CppParser
from yata_core.domain.entities import EntityType


@pytest.fixture
def parser() -> CppParser:
    return CppParser()


class TestCppParserBasic:
    """Basic C++ parsing tests."""

    def test_parse_empty_string(self, parser: CppParser) -> None:
        result = parser.parse_string("", "test.cpp")
        assert result.file_path == "test.cpp"
        assert len(result.errors) == 0

    def test_parse_namespace(self, parser: CppParser) -> None:
        code = '''
namespace myapp {
    void helper() {}
}
'''
        result = parser.parse_string(code, "test.cpp")
        namespaces = [e for e in result.entities if "myapp" in e.name]
        assert len(namespaces) >= 1

    def test_parse_class(self, parser: CppParser) -> None:
        code = '''
class MyClass {
public:
    void method();
private:
    int value;
};
'''
        result = parser.parse_string(code, "test.cpp")
        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) >= 1
        assert any("MyClass" in c.name for c in classes)

    def test_parse_function(self, parser: CppParser) -> None:
        code = '''
void standalone_function(int x, int y) {
    return;
}
'''
        result = parser.parse_string(code, "test.cpp")
        functions = [e for e in result.entities if e.type == EntityType.FUNCTION]
        assert len(functions) >= 1

    def test_parse_struct(self, parser: CppParser) -> None:
        code = '''
struct Point {
    int x;
    int y;
};
'''
        result = parser.parse_string(code, "test.cpp")
        structs = [e for e in result.entities if "Point" in e.name]
        assert len(structs) >= 1

    def test_parse_includes(self, parser: CppParser) -> None:
        code = '''
#include <iostream>
#include <vector>
#include "myheader.h"

int main() { return 0; }
'''
        result = parser.parse_string(code, "test.cpp")
        assert len(result.imports) >= 1


class TestCppParserAdvanced:
    """Advanced C++ parsing tests."""

    def test_parse_template_class(self, parser: CppParser) -> None:
        code = '''
template<typename T>
class Container {
public:
    T getValue() { return value; }
private:
    T value;
};
'''
        result = parser.parse_string(code, "test.cpp")
        assert any("Container" in e.name for e in result.entities)

    def test_parse_inheritance(self, parser: CppParser) -> None:
        code = '''
class Base {
public:
    virtual void method() {}
};

class Derived : public Base {
public:
    void method() override {}
};
'''
        result = parser.parse_string(code, "test.cpp")
        classes = [e for e in result.entities if e.type == EntityType.CLASS]
        assert len(classes) >= 2
