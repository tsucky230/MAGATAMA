"""Tests for Objective-C Parser."""

import pytest
from yata_core.infrastructure.parsers import ObjectiveCParser
from yata_core.domain.entities import EntityType


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
        code = '''
@interface MyClass : NSObject
- (void)doSomething;
@end
'''
        result = parser.parse_string(code, "test.m")
        # Should have at least module entity
        assert len(result.entities) >= 1

    def test_parse_class_implementation(self, parser: ObjectiveCParser) -> None:
        code = '''
@implementation MyClass
- (void)doSomething {
    NSLog(@"Hello");
}
@end
'''
        result = parser.parse_string(code, "test.m")
        assert len(result.entities) >= 1

    def test_parse_protocol(self, parser: ObjectiveCParser) -> None:
        code = '''
@protocol MyProtocol <NSObject>
- (void)requiredMethod;
@optional
- (void)optionalMethod;
@end
'''
        result = parser.parse_string(code, "test.m")
        # Should have at least module entity
        assert len(result.entities) >= 1

    def test_parse_function(self, parser: ObjectiveCParser) -> None:
        code = '''
void cStyleFunction(int x) {
    printf("%d", x);
}
'''
        result = parser.parse_string(code, "test.m")
        functions = [e for e in result.entities if e.type == EntityType.FUNCTION]
        assert len(functions) >= 1

    def test_parse_imports(self, parser: ObjectiveCParser) -> None:
        code = '''
#import <Foundation/Foundation.h>
#import "MyHeader.h"

@interface Test : NSObject
@end
'''
        result = parser.parse_string(code, "test.m")
        # Should have at least module entity
        assert len(result.entities) >= 1


class TestObjectiveCParserAdvanced:
    """Advanced Objective-C parsing tests."""

    def test_parse_category(self, parser: ObjectiveCParser) -> None:
        code = '''
@interface NSString (MyCategory)
- (NSString *)myCustomMethod;
@end
'''
        result = parser.parse_string(code, "test.m")
        assert len(result.entities) >= 1

    def test_parse_method_with_params(self, parser: ObjectiveCParser) -> None:
        code = '''
@implementation Calculator
- (int)addNumber:(int)a toNumber:(int)b {
    return a + b;
}
@end
'''
        result = parser.parse_string(code, "test.m")
        # Should have at least module entity  
        assert len(result.entities) >= 1
