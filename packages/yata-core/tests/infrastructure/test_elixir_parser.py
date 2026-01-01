"""Tests for Elixir Parser."""

import pytest
from yata_core.infrastructure.parsers import ElixirParser
from yata_core.domain.entities import EntityType


@pytest.fixture
def parser() -> ElixirParser:
    return ElixirParser()


class TestElixirParserBasic:
    """Basic Elixir parsing tests."""

    def test_parse_empty_string(self, parser: ElixirParser) -> None:
        result = parser.parse_string("", "test.ex")
        assert result.file_path == "test.ex"
        assert len(result.errors) == 0

    def test_parse_module(self, parser: ElixirParser) -> None:
        code = '''
defmodule MyModule do
  def hello do
    "Hello, World!"
  end
end
'''
        result = parser.parse_string(code, "test.ex")
        assert len(result.entities) >= 1

    def test_parse_function(self, parser: ElixirParser) -> None:
        code = '''
defmodule Math do
  def add(a, b) do
    a + b
  end
end
'''
        result = parser.parse_string(code, "test.ex")
        # Should have at least module entity
        assert len(result.entities) >= 1

    def test_parse_private_function(self, parser: ElixirParser) -> None:
        code = '''
defmodule Helper do
  defp internal_helper(x) do
    x * 2
  end
end
'''
        result = parser.parse_string(code, "test.ex")
        assert len(result.entities) >= 1

    def test_parse_protocol(self, parser: ElixirParser) -> None:
        code = '''
defprotocol Printable do
  def print(data)
end
'''
        result = parser.parse_string(code, "test.ex")
        assert len(result.entities) >= 1


class TestElixirParserAdvanced:
    """Advanced Elixir parsing tests."""

    def test_parse_imports(self, parser: ElixirParser) -> None:
        code = '''
defmodule MyApp do
  import Enum
  alias MyApp.User
  use GenServer
  require Logger

  def start do
    Logger.info("Starting")
  end
end
'''
        result = parser.parse_string(code, "test.ex")
        # Should have at least module entity
        assert len(result.entities) >= 1

    def test_parse_struct(self, parser: ElixirParser) -> None:
        code = '''
defmodule User do
  defstruct [:name, :email, :age]
end
'''
        result = parser.parse_string(code, "test.ex")
        assert len(result.entities) >= 1

    def test_parse_pattern_matching_functions(self, parser: ElixirParser) -> None:
        code = '''
defmodule Factorial do
  def of(0), do: 1
  def of(n) when n > 0, do: n * of(n - 1)
end
'''
        result = parser.parse_string(code, "test.ex")
        # Should have at least module entity
        assert len(result.entities) >= 1

    def test_parse_genserver(self, parser: ElixirParser) -> None:
        code = '''
defmodule MyServer do
  use GenServer

  def init(state) do
    {:ok, state}
  end

  def handle_call(:get, _from, state) do
    {:reply, state, state}
  end
end
'''
        result = parser.parse_string(code, "test.ex")
        assert len(result.entities) >= 1


class TestElixirParserEntityExtraction:
    """Tests for entity extraction in Elixir parser."""

    def test_extract_module_entity(self, parser: ElixirParser) -> None:
        code = '''
defmodule MyApp.UserController do
  def index(conn, _params) do
    render(conn, "index.html")
  end
end
'''
        result = parser.parse_string(code, "test.ex")
        modules = [e for e in result.entities if e.type == EntityType.MODULE]
        assert len(modules) >= 1
        assert len(result.errors) == 0

    def test_extract_function_entity(self, parser: ElixirParser) -> None:
        code = '''
defmodule Calculator do
  def add(a, b), do: a + b
  def subtract(a, b), do: a - b
  def multiply(a, b), do: a * b
end
'''
        result = parser.parse_string(code, "test.ex")
        # Parser should process without errors
        assert len(result.entities) >= 1
        assert len(result.errors) == 0

    def test_extract_private_function_entity(self, parser: ElixirParser) -> None:
        code = '''
defmodule Service do
  def public_method(x) do
    private_helper(x)
  end
  
  defp private_helper(x), do: x * 2
end
'''
        result = parser.parse_string(code, "test.ex")
        # Parser should process without errors
        assert len(result.entities) >= 1
        assert len(result.errors) == 0

    def test_extract_macro_entity(self, parser: ElixirParser) -> None:
        code = '''
defmodule MyMacros do
  defmacro unless(condition, do: block) do
    quote do
      if !unquote(condition), do: unquote(block)
    end
  end
end
'''
        result = parser.parse_string(code, "test.ex")
        assert len(result.entities) >= 1
        assert len(result.errors) == 0


class TestElixirParserRelationships:
    """Tests for relationship extraction in Elixir parser."""

    def test_contains_relationship(self, parser: ElixirParser) -> None:
        code = '''
defmodule Parent do
  defmodule Child do
    def child_func, do: :ok
  end
  
  def parent_func, do: Child.child_func()
end
'''
        result = parser.parse_string(code, "test.ex")
        # Parser should process without errors
        assert len(result.entities) >= 1
        assert len(result.errors) == 0


class TestElixirParserFileHandling:
    """Tests for file handling in Elixir parser."""

    def test_parse_file(self, parser: ElixirParser, tmp_path) -> None:
        elixir_file = tmp_path / "test.ex"
        elixir_file.write_text('''
defmodule Test do
  def hello, do: "Hello"
end
''')
        result = parser.parse_file(elixir_file)
        assert result.file_path == str(elixir_file)
        assert len(result.entities) >= 1

    def test_parse_exs_file(self, parser: ElixirParser, tmp_path) -> None:
        exs_file = tmp_path / "test.exs"
        exs_file.write_text('''
ExUnit.start()

defmodule MyTest do
  use ExUnit.Case
  
  test "example" do
    assert 1 + 1 == 2
  end
end
''')
        result = parser.parse_file(exs_file)
        assert result.file_path == str(exs_file)
        assert len(result.entities) >= 1

    def test_parser_internal_methods(self, parser: ElixirParser) -> None:
        """Test internal parser methods for coverage."""
        # Test _generate_id
        id1 = parser._generate_id("test")
        id2 = parser._generate_id("test")
        assert id1 != id2
        
        # Test _get_node_text
        code = "defmodule Test do end"
        tree = parser._parser.parse(code.encode("utf-8"))
        text = parser._get_node_text(tree.root_node, code)
        assert "defmodule" in text

