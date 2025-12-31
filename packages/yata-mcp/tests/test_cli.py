"""Tests for YATA CLI."""

import pytest
from click.testing import CliRunner
from pathlib import Path

from yata_mcp.cli.main import cli


class TestYataCli:
    """Tests for YATA CLI commands."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    def test_cli_help(self, runner: CliRunner) -> None:
        """Test CLI shows help."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "YATA" in result.output

    def test_version_command(self, runner: CliRunner) -> None:
        """Test version command."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_parse_command_help(self, runner: CliRunner) -> None:
        """Test parse command help."""
        result = runner.invoke(cli, ["parse", "--help"])
        assert result.exit_code == 0
        assert "Parse source files" in result.output

    def test_parse_file(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test parse command with a file."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass")

        result = runner.invoke(cli, ["parse", str(test_file)])
        assert result.exit_code == 0
        assert "Parsed" in result.output or "entities" in result.output.lower()

    def test_parse_directory(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test parse command with a directory."""
        (tmp_path / "a.py").write_text("def a(): pass")
        (tmp_path / "b.py").write_text("class B: pass")

        result = runner.invoke(cli, ["parse", str(tmp_path)])
        assert result.exit_code == 0

    def test_parse_nonexistent_path(self, runner: CliRunner) -> None:
        """Test parse command with non-existent path."""
        result = runner.invoke(cli, ["parse", "/nonexistent/path"])
        assert result.exit_code != 0

    def test_serve_command_help(self, runner: CliRunner) -> None:
        """Test serve command help."""
        result = runner.invoke(cli, ["serve", "--help"])
        assert result.exit_code == 0
        assert "Start the MCP server" in result.output or "server" in result.output.lower()

    def test_info_command(self, runner: CliRunner) -> None:
        """Test info command shows server information."""
        result = runner.invoke(cli, ["info"])
        assert result.exit_code == 0
        assert "YATA" in result.output


class TestQueryCommand:
    """Tests for query command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    def test_query_help(self, runner: CliRunner) -> None:
        """Test query command help."""
        result = runner.invoke(cli, ["query", "--help"])
        assert result.exit_code == 0
        assert "Search entities" in result.output

    def test_query_no_results(self, runner: CliRunner) -> None:
        """Test query with no matching results."""
        result = runner.invoke(cli, ["query", "nonexistent_entity_xyz"])
        assert result.exit_code == 0
        assert "No entities found" in result.output

    def test_query_with_parsed_file(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test query after parsing a file."""
        test_file = tmp_path / "module.py"
        test_file.write_text("def my_search_function(): pass")

        # Parse first
        runner.invoke(cli, ["parse", str(test_file)])

        # Then query
        result = runner.invoke(cli, ["query", "my_search_function"])
        assert result.exit_code == 0
        assert "my_search_function" in result.output or "Found" in result.output

    def test_query_json_output(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test query with JSON output."""
        test_file = tmp_path / "module.py"
        test_file.write_text("def json_test_func(): pass")

        runner.invoke(cli, ["parse", str(test_file)])
        result = runner.invoke(cli, ["query", "json_test_func", "--json"])
        
        assert result.exit_code == 0
        # Should be valid JSON (either [] or [{...}])
        import json
        data = json.loads(result.output)
        assert isinstance(data, list)

    def test_query_with_type_filter(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test query with type filter."""
        test_file = tmp_path / "module.py"
        test_file.write_text("""
def func_test(): pass
class ClassTest: pass
""")

        runner.invoke(cli, ["parse", str(test_file)])
        
        # Query for functions only
        result = runner.invoke(cli, ["query", "test", "--type", "function"])
        assert result.exit_code == 0


class TestStatsCommand:
    """Tests for stats command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    def test_stats_help(self, runner: CliRunner) -> None:
        """Test stats command help."""
        result = runner.invoke(cli, ["stats", "--help"])
        assert result.exit_code == 0
        assert "statistics" in result.output.lower()

    def test_stats_empty_graph(self, runner: CliRunner) -> None:
        """Test stats on empty graph."""
        result = runner.invoke(cli, ["stats"])
        assert result.exit_code == 0
        assert "0" in result.output  # Should show 0 entities

    def test_stats_after_parse(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test stats after parsing files."""
        test_file = tmp_path / "module.py"
        test_file.write_text("""
def func1(): pass
def func2(): pass
class MyClass:
    def method1(self): pass
""")

        runner.invoke(cli, ["parse", str(test_file)])
        result = runner.invoke(cli, ["stats"])
        
        assert result.exit_code == 0
        # Should show some entities
        assert "Entities" in result.output or "entities" in result.output.lower()

    def test_stats_json_output(self, runner: CliRunner, tmp_path: Path) -> None:
        """Test stats with JSON output."""
        test_file = tmp_path / "module.py"
        test_file.write_text("def func(): pass")

        runner.invoke(cli, ["parse", str(test_file)])
        result = runner.invoke(cli, ["stats", "--json"])
        
        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        assert "entity_count" in data or "total_entities" in data


class TestWatchCommand:
    """Tests for watch command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    def test_watch_help(self, runner: CliRunner) -> None:
        """Test watch command help."""
        result = runner.invoke(cli, ["watch", "--help"])
        assert result.exit_code == 0
        assert "Watch" in result.output or "watch" in result.output.lower()
        assert "directory" in result.output.lower()

    def test_watch_nonexistent_directory(self, runner: CliRunner) -> None:
        """Test watch with non-existent directory."""
        result = runner.invoke(cli, ["watch", "/nonexistent/dir"])
        assert result.exit_code != 0
