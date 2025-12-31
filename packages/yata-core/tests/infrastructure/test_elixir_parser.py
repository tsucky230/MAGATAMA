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
