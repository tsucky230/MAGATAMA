"""Tests for Objective-C Parser."""

import pytest

from magatama_core.domain.entities import EntityType
from magatama_core.infrastructure.parsers import ObjectiveCParser


@pytest.fixture
def parser() -> ObjectiveCParser:
    return ObjectiveCParser()


class TestObjectiveCParserBasic:
    """Basic Objective-C parsing tests."""

    def test_parse_empty_string(self, parser: ObjectiveCParser) -> None:
        result = parser.parse_string("", "test.m")
        assert result.file_path == "test.m"
        assert len(result.errors) == 0

    def test_parse_class_interface(self, parser: ObjectiveCParser) -> None:
        code = """
@interface MyClass : NSObject
- (void)doSomething;
@end
"""
        result = parser.parse_string(code, "test.m")
        # Should have at least module entity
        assert len(result.entities) >= 1

    def test_parse_class_implementation(self, parser: ObjectiveCParser) -> None:
        code = """
@implementation MyClass
- (void)doSomething {
    NSLog(@"Hello");
}
@end
"""
        result = parser.parse_string(code, "test.m")
        assert len(result.entities) >= 1

    def test_parse_protocol(self, parser: ObjectiveCParser) -> None:
        code = """
@protocol MyProtocol <NSObject>
- (void)requiredMethod;
@optional
- (void)optionalMethod;
@end
"""
        result = parser.parse_string(code, "test.m")
        # Should have at least module entity
        assert len(result.entities) >= 1

    def test_parse_function(self, parser: ObjectiveCParser) -> None:
        code = """
void cStyleFunction(int x) {
    printf("%d", x);
}
"""
        result = parser.parse_string(code, "test.m")
        functions = [e for e in result.entities if e.type == EntityType.FUNCTION]
        assert len(functions) >= 1

    def test_parse_imports(self, parser: ObjectiveCParser) -> None:
        code = """
#import <Foundation/Foundation.h>
#import "MyHeader.h"

@interface Test : NSObject
@end
"""
        result = parser.parse_string(code, "test.m")
        # Should have at least module entity
        assert len(result.entities) >= 1


class TestObjectiveCParserAdvanced:
    """Advanced Objective-C parsing tests."""

    def test_parse_category(self, parser: ObjectiveCParser) -> None:
        code = """
@interface NSString (MyCategory)
- (NSString *)myCustomMethod;
@end
"""
        result = parser.parse_string(code, "test.m")
        assert len(result.entities) >= 1

    def test_parse_method_with_params(self, parser: ObjectiveCParser) -> None:
        code = """
@implementation Calculator
- (int)addNumber:(int)a toNumber:(int)b {
    return a + b;
}
@end
"""
        result = parser.parse_string(code, "test.m")
        # Should have at least module entity
        assert len(result.entities) >= 1


class TestObjectiveCParserEntityExtraction:
    """Tests for Objective-C parser entity extraction."""

    def test_extract_multiple_methods(self, parser: ObjectiveCParser) -> None:
        """Test extracting multiple methods from implementation."""
        code = """
@implementation MyClass
- (void)method1 {}
- (void)method2 {}
- (int)method3:(int)x { return x; }
@end
"""
        result = parser.parse_string(code, "test.m")
        assert len(result.errors) == 0
        assert len(result.entities) >= 1

    def test_extract_property_declarations(self, parser: ObjectiveCParser) -> None:
        """Test property declarations in interface."""
        code = """
@interface Person : NSObject
@property (nonatomic, strong) NSString *name;
@property (nonatomic, assign) NSInteger age;
@end
"""
        result = parser.parse_string(code, "test.m")
        assert len(result.errors) == 0
        assert len(result.entities) >= 1


class TestObjectiveCParserRelationships:
    """Tests for Objective-C parser relationships."""

    def test_inheritance_relationship(self, parser: ObjectiveCParser) -> None:
        """Test class inheritance."""
        code = """
@interface Child : Parent
@end
"""
        result = parser.parse_string(code, "test.m")
        assert len(result.entities) >= 1

    def test_protocol_adoption(self, parser: ObjectiveCParser) -> None:
        """Test protocol adoption in class."""
        code = """
@interface MyClass : NSObject <UITableViewDelegate, UITableViewDataSource>
@end
"""
        result = parser.parse_string(code, "test.m")
        assert len(result.entities) >= 1


class TestObjectiveCParserFileHandling:
    """Tests for Objective-C parser file handling."""

    def test_parse_file_not_found(self, parser: ObjectiveCParser) -> None:
        """Test handling of non-existent file."""
        from pathlib import Path

        with pytest.raises((FileNotFoundError, OSError)):
            parser.parse_file(Path("/nonexistent/test.m"))

    def test_parse_header_file(self, parser: ObjectiveCParser) -> None:
        """Test parsing header file (.h)."""
        code = """
@interface MyClass : NSObject
- (void)publicMethod;
@end
"""
        result = parser.parse_string(code, "test.h")
        assert len(result.entities) >= 1
        assert result.file_path == "test.h"

    def test_parser_internal_methods(self, parser: ObjectiveCParser) -> None:
        """Test internal parser methods."""
        # Test _generate_id
        id1 = parser._generate_id("test")
        id2 = parser._generate_id("test")
        assert id1 != id2
        assert id1.startswith("test_")
        assert id2.startswith("test_")


def test_objc_rich_constructs():
    """Parse an Objective-C file exercising interface/protocol/implementation/function."""
    from magatama_core.infrastructure.parsers import ObjectiveCParser

    code = """
#import <Foundation/Foundation.h>

@protocol Greeter
- (NSString *)greet;
@end

@interface Animal : NSObject <Greeter>
@property (nonatomic, strong) NSString *name;
- (NSString *)greet;
@end

@implementation Animal
- (NSString *)greet { return @"hi"; }
@end

void topLevel(void) {}
"""
    result = ObjectiveCParser().parse_string(code, "sample.m")
    assert len(result.entities) >= 1
    assert len(result.errors) == 0
