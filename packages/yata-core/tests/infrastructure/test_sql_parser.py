"""Tests for SQL Parser."""

import pytest
from yata_core.infrastructure.parsers import SqlParser
from yata_core.domain.entities import EntityType


@pytest.fixture
def parser() -> SqlParser:
    return SqlParser()


class TestSqlParserBasic:
    """Basic SQL parsing tests."""

    def test_parse_empty_string(self, parser: SqlParser) -> None:
        result = parser.parse_string("", "test.sql")
        assert result.file_path == "test.sql"
        assert len(result.errors) == 0

    def test_parse_create_table(self, parser: SqlParser) -> None:
        code = '''
CREATE TABLE users (
    id INT PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(255)
);
'''
        result = parser.parse_string(code, "test.sql")
        # Should have at least the module entity
        assert len(result.entities) >= 1

    def test_parse_create_view(self, parser: SqlParser) -> None:
        code = '''
CREATE VIEW active_users AS
SELECT * FROM users WHERE active = 1;
'''
        result = parser.parse_string(code, "test.sql")
        assert len(result.entities) >= 1

    def test_parse_module_entity(self, parser: SqlParser) -> None:
        code = '''
SELECT 1;
'''
        result = parser.parse_string(code, "test.sql")
        modules = [e for e in result.entities if e.type == EntityType.MODULE]
        assert len(modules) >= 1


class TestSqlParserAdvanced:
    """Advanced SQL parsing tests."""

    def test_parse_multiple_tables(self, parser: SqlParser) -> None:
        code = '''
CREATE TABLE departments (
    id INT PRIMARY KEY,
    name VARCHAR(100)
);

CREATE TABLE employees (
    id INT PRIMARY KEY,
    name VARCHAR(100),
    department_id INT REFERENCES departments(id)
);
'''
        result = parser.parse_string(code, "test.sql")
        assert len(result.entities) >= 1

    def test_parse_create_index(self, parser: SqlParser) -> None:
        code = '''
CREATE INDEX idx_users_email ON users(email);
'''
        result = parser.parse_string(code, "test.sql")
        assert len(result.entities) >= 1

    def test_parse_stored_procedure(self, parser: SqlParser) -> None:
        code = '''
CREATE PROCEDURE GetUserById(IN userId INT)
BEGIN
    SELECT * FROM users WHERE id = userId;
END;
'''
        result = parser.parse_string(code, "test.sql")
        assert len(result.entities) >= 1

    def test_parse_create_function(self, parser: SqlParser) -> None:
        code = '''
CREATE FUNCTION get_total_orders(user_id INT)
RETURNS INT
BEGIN
    DECLARE total INT;
    SELECT COUNT(*) INTO total FROM orders WHERE user_id = user_id;
    RETURN total;
END;
'''
        result = parser.parse_string(code, "test.sql")
        assert len(result.entities) >= 1
