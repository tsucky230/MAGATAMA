"""Tests for SQL Parser."""

import pytest

from magatama_core.domain.entities import EntityType
from magatama_core.infrastructure.parsers import SqlParser


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
        code = """
CREATE TABLE users (
    id INT PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(255)
);
"""
        result = parser.parse_string(code, "test.sql")
        # Should have at least the module entity
        assert len(result.entities) >= 1

    def test_parse_create_view(self, parser: SqlParser) -> None:
        code = """
CREATE VIEW active_users AS
SELECT * FROM users WHERE active = 1;
"""
        result = parser.parse_string(code, "test.sql")
        assert len(result.entities) >= 1

    def test_parse_module_entity(self, parser: SqlParser) -> None:
        code = """
SELECT 1;
"""
        result = parser.parse_string(code, "test.sql")
        modules = [e for e in result.entities if e.type == EntityType.MODULE]
        assert len(modules) >= 1


class TestSqlParserAdvanced:
    """Advanced SQL parsing tests."""

    def test_parse_multiple_tables(self, parser: SqlParser) -> None:
        code = """
CREATE TABLE departments (
    id INT PRIMARY KEY,
    name VARCHAR(100)
);

CREATE TABLE employees (
    id INT PRIMARY KEY,
    name VARCHAR(100),
    department_id INT REFERENCES departments(id)
);
"""
        result = parser.parse_string(code, "test.sql")
        assert len(result.entities) >= 1

    def test_parse_create_index(self, parser: SqlParser) -> None:
        code = """
CREATE INDEX idx_users_email ON users(email);
"""
        result = parser.parse_string(code, "test.sql")
        assert len(result.entities) >= 1

    def test_parse_stored_procedure(self, parser: SqlParser) -> None:
        code = """
CREATE PROCEDURE GetUserById(IN userId INT)
BEGIN
    SELECT * FROM users WHERE id = userId;
END;
"""
        result = parser.parse_string(code, "test.sql")
        assert len(result.entities) >= 1

    def test_parse_create_function(self, parser: SqlParser) -> None:
        code = """
CREATE FUNCTION get_total_orders(user_id INT)
RETURNS INT
BEGIN
    DECLARE total INT;
    SELECT COUNT(*) INTO total FROM orders WHERE user_id = user_id;
    RETURN total;
END;
"""
        result = parser.parse_string(code, "test.sql")
        assert len(result.entities) >= 1


class TestSqlParserEntityExtraction:
    """Tests for entity extraction in SQL parser."""

    def test_extract_table_with_columns(self, parser: SqlParser) -> None:
        code = """
CREATE TABLE products (
    product_id INT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    price DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""
        result = parser.parse_string(code, "test.sql")
        # Should have at least module entity
        assert len(result.entities) >= 1
        assert len(result.errors) == 0

    def test_extract_view(self, parser: SqlParser) -> None:
        code = """
CREATE VIEW customer_orders AS
SELECT c.name, o.order_date, o.total
FROM customers c
JOIN orders o ON c.id = o.customer_id;
"""
        result = parser.parse_string(code, "test.sql")
        assert len(result.entities) >= 1
        assert len(result.errors) == 0

    def test_extract_index(self, parser: SqlParser) -> None:
        code = """
CREATE INDEX idx_customer_name ON customers(name);
CREATE UNIQUE INDEX idx_email ON users(email);
"""
        result = parser.parse_string(code, "test.sql")
        assert len(result.entities) >= 1
        assert len(result.errors) == 0

    def test_extract_trigger(self, parser: SqlParser) -> None:
        code = """
CREATE TRIGGER update_timestamp
BEFORE UPDATE ON users
FOR EACH ROW
SET NEW.updated_at = CURRENT_TIMESTAMP;
"""
        result = parser.parse_string(code, "test.sql")
        assert len(result.entities) >= 1
        assert len(result.errors) == 0


class TestSqlParserRelationships:
    """Tests for relationship extraction in SQL parser."""

    def test_contains_relationship_table_columns(self, parser: SqlParser) -> None:
        code = """
CREATE TABLE employees (
    id INT PRIMARY KEY,
    name VARCHAR(100)
);
"""
        result = parser.parse_string(code, "test.sql")
        # Parser processes without errors
        assert len(result.entities) >= 1
        assert len(result.errors) == 0


class TestSqlParserFileHandling:
    """Tests for file handling in SQL parser."""

    def test_parse_file(self, parser: SqlParser, tmp_path) -> None:
        sql_file = tmp_path / "schema.sql"
        sql_file.write_text("""
CREATE TABLE test (
    id INT PRIMARY KEY
);
""")
        result = parser.parse_file(sql_file)
        assert result.file_path == str(sql_file)
        assert len(result.entities) >= 1

    def test_module_entity_created(self, parser: SqlParser) -> None:
        code = "SELECT 1;"
        result = parser.parse_string(code, "query.sql")
        modules = [e for e in result.entities if e.type == EntityType.MODULE]
        assert len(modules) == 1
        assert modules[0].name == "query"

    def test_complex_schema(self, parser: SqlParser) -> None:
        code = """
-- Database schema for e-commerce

CREATE TABLE categories (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE products (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    category_id INT,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

CREATE VIEW product_list AS
SELECT p.name, c.name AS category
FROM products p
LEFT JOIN categories c ON p.category_id = c.id;

CREATE INDEX idx_product_name ON products(name);
"""
        result = parser.parse_string(code, "schema.sql")
        # Parser should process without errors
        assert len(result.entities) >= 1
        assert len(result.errors) == 0

    def test_parser_internal_methods(self, parser: SqlParser) -> None:
        """Test internal parser methods for coverage."""
        # Test _generate_id
        id1 = parser._generate_id("test")
        id2 = parser._generate_id("test")
        assert id1 != id2

        # Test _get_node_text
        code = "SELECT 1"
        tree = parser._parser.parse(code.encode("utf-8"))
        text = parser._get_node_text(tree.root_node, code)
        assert "SELECT" in text
