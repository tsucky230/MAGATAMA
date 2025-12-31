"""Unit tests for C parser."""

import pytest
from yata_core.infrastructure.parsers.c_parser import CParser
from yata_core.domain.entities import EntityType


class TestCParser:
    """Test suite for C parser."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return CParser()

    def test_parse_function(self, parser):
        """Test function parsing."""
        code = """
int add(int a, int b) {
    return a + b;
}
"""
        result = parser.parse_string(code, "test.c")
        
        assert len(result.entities) >= 2
        func = next((e for e in result.entities if e.name == "add"), None)
        assert func is not None
        assert func.type == EntityType.FUNCTION

    def test_parse_struct(self, parser):
        """Test struct parsing."""
        code = """
struct Point {
    int x;
    int y;
};
"""
        result = parser.parse_string(code, "test.c")
        
        struct = next((e for e in result.entities if e.name == "Point"), None)
        assert struct is not None
        assert struct.type == EntityType.CLASS

    def test_parse_enum(self, parser):
        """Test enum parsing."""
        code = """
enum Color {
    RED,
    GREEN,
    BLUE
};
"""
        result = parser.parse_string(code, "test.c")
        
        enum = next((e for e in result.entities if e.name == "Color"), None)
        assert enum is not None
        assert enum.type == EntityType.CLASS

    def test_parse_include(self, parser):
        """Test include parsing."""
        code = """
#include <stdio.h>
#include "myheader.h"
"""
        result = parser.parse_string(code, "test.c")
        
        assert "stdio.h" in result.imports
        assert "myheader.h" in result.imports

    def test_parse_typedef(self, parser):
        """Test typedef parsing."""
        code = """
typedef struct {
    int x;
    int y;
} Point;
"""
        result = parser.parse_string(code, "test.c")
        
        typedef = next((e for e in result.entities if e.name == "Point"), None)
        assert typedef is not None

    def test_parse_multiple_functions(self, parser):
        """Test multiple functions."""
        code = """
int add(int a, int b) { return a + b; }
int sub(int a, int b) { return a - b; }
int mul(int a, int b) { return a * b; }
"""
        result = parser.parse_string(code, "test.c")
        
        func_names = [e.name for e in result.entities if e.type == EntityType.FUNCTION]
        assert "add" in func_names
        assert "sub" in func_names
        assert "mul" in func_names

    def test_parse_function_with_parameters(self, parser):
        """Test function parameter extraction."""
        code = """
int calculate(int x, float y, char* str) {
    return 0;
}
"""
        result = parser.parse_string(code, "test.c")
        
        func = next((e for e in result.entities if e.name == "calculate"), None)
        assert func is not None
        assert len(func.parameters) == 3

    def test_parse_complex_code(self, parser):
        """Test parsing complex C code."""
        code = """
#include <stdio.h>
#include <stdlib.h>

struct Node {
    int data;
    struct Node* next;
};

typedef struct Node Node;

Node* createNode(int data) {
    Node* node = (Node*)malloc(sizeof(Node));
    node->data = data;
    node->next = NULL;
    return node;
}

void printList(Node* head) {
    while (head != NULL) {
        printf("%d ", head->data);
        head = head->next;
    }
}
"""
        result = parser.parse_string(code, "list.c")
        
        assert len(result.entities) >= 4
        assert "stdio.h" in result.imports
        assert "stdlib.h" in result.imports
        
        struct = next((e for e in result.entities if e.name == "Node"), None)
        assert struct is not None
        
        create_func = next((e for e in result.entities if e.name == "createNode"), None)
        assert create_func is not None
        
        print_func = next((e for e in result.entities if e.name == "printList"), None)
        assert print_func is not None
