"""Tests for Haskell Parser."""

import pytest
from yata_core.infrastructure.parsers import HaskellParser
from yata_core.domain.entities import EntityType


@pytest.fixture
def parser() -> HaskellParser:
    return HaskellParser()


class TestHaskellParserBasic:
    """Basic Haskell parsing tests."""

    def test_parse_empty_string(self, parser: HaskellParser) -> None:
        result = parser.parse_string("", "test.hs")
        assert result.file_path == "test.hs"
        assert len(result.errors) == 0

    def test_parse_function(self, parser: HaskellParser) -> None:
        code = '''
add :: Int -> Int -> Int
add x y = x + y
'''
        result = parser.parse_string(code, "test.hs")
        # Should have module entity at minimum
        assert len(result.entities) >= 1

    def test_parse_data_type(self, parser: HaskellParser) -> None:
        code = '''
data Person = Person String Int
'''
        result = parser.parse_string(code, "test.hs")
        assert len(result.entities) >= 1

    def test_parse_newtype(self, parser: HaskellParser) -> None:
        code = '''
newtype UserId = UserId Int
'''
        result = parser.parse_string(code, "test.hs")
        assert len(result.entities) >= 1

    def test_parse_module_entity(self, parser: HaskellParser) -> None:
        code = '''
module Main where

main :: IO ()
main = putStrLn "Hello"
'''
        result = parser.parse_string(code, "test.hs")
        modules = [e for e in result.entities if e.type == EntityType.MODULE]
        assert len(modules) >= 1


class TestHaskellParserAdvanced:
    """Advanced Haskell parsing tests."""

    def test_parse_imports(self, parser: HaskellParser) -> None:
        code = '''
import Data.List
import qualified Data.Map as Map

main = print "Hello"
'''
        result = parser.parse_string(code, "test.hs")
        assert len(result.entities) >= 1

    def test_parse_type_class(self, parser: HaskellParser) -> None:
        code = '''
class Printable a where
    printIt :: a -> String
'''
        result = parser.parse_string(code, "test.hs")
        assert len(result.entities) >= 1

    def test_parse_algebraic_data_type(self, parser: HaskellParser) -> None:
        code = '''
data Tree a = Empty | Node a (Tree a) (Tree a)
'''
        result = parser.parse_string(code, "test.hs")
        assert len(result.entities) >= 1

    def test_parse_record_syntax(self, parser: HaskellParser) -> None:
        code = '''
data Person = Person {
    name :: String,
    age :: Int
}
'''
        result = parser.parse_string(code, "test.hs")
        assert len(result.entities) >= 1
