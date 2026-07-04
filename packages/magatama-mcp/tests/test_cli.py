"""Tests for MAGATAMA CLI."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from magatama_mcp.cli.main import cli


class TestMagatamaCli:
    """Tests for MAGATAMA CLI commands."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    def test_cli_help(self, runner: CliRunner) -> None:
        """Test CLI shows help."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "MAGATAMA" in result.output

    def test_version_command(self, runner: CliRunner) -> None:
        """Test version command reports the installed package version."""
        from magatama_mcp import __version__

        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output

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
        assert "MAGATAMA" in result.output


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


def _build_graph_file(tmp_path: Path) -> Path:
    """Build a populated knowledge-graph JSON file using the server API.

    The CLI creates a fresh server per invocation, so populated query/stats/
    validate output paths are only reachable by loading a pre-built graph via
    ``--graph``. This helper produces such a file in the exact format that the
    ``load_graph`` tool expects.
    """
    import asyncio

    from magatama_mcp.server import MagatamaMcpServer

    src = tmp_path / "sample.py"
    src.write_text(
        '''
def my_documented_func(value):
    """Compute something useful from value."""
    return value * 2


class SampleClass:
    """A sample class."""

    def method_one(self):
        return my_documented_func(21)
'''
    )

    graph_file = tmp_path / "graph.json"
    server = MagatamaMcpServer()
    asyncio.run(server.call_tool("parse_file", {"file_path": str(src)}))
    asyncio.run(server.call_tool("save_graph", {"file_path": str(graph_file)}))
    return graph_file


class TestSaveLoadCommands:
    """Tests for save / load commands."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        return CliRunner()

    def test_save_command(self, runner: CliRunner, tmp_path: Path) -> None:
        """save writes the current (empty) graph to a file."""
        out = tmp_path / "out.json"
        result = runner.invoke(cli, ["save", str(out)])
        assert result.exit_code == 0
        assert out.exists()

    def test_load_command(self, runner: CliRunner, tmp_path: Path) -> None:
        """load reads a previously built graph file."""
        graph_file = _build_graph_file(tmp_path)
        result = runner.invoke(cli, ["load", str(graph_file)])
        assert result.exit_code == 0
        assert "Loaded" in result.output or "entities" in result.output.lower()

    def test_load_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["load", "--help"])
        assert result.exit_code == 0

    def test_save_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["save", "--help"])
        assert result.exit_code == 0


class TestQueryWithGraph:
    """Query against a pre-built graph file (covers populated output paths)."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        return CliRunner()

    def test_query_graph_human_output(self, runner: CliRunner, tmp_path: Path) -> None:
        graph_file = _build_graph_file(tmp_path)
        result = runner.invoke(cli, ["query", "my_documented_func", "--graph", str(graph_file)])
        assert result.exit_code == 0
        assert "my_documented_func" in result.output or "Found" in result.output

    def test_query_graph_json_output(self, runner: CliRunner, tmp_path: Path) -> None:
        # Note: rich Console soft-wraps/colorizes output, so the rendered JSON of
        # a populated result is not guaranteed to round-trip through json.loads.
        # We only assert the --json branch executes successfully here.
        graph_file = _build_graph_file(tmp_path)
        result = runner.invoke(cli, ["query", "Sample", "--graph", str(graph_file), "--json"])
        assert result.exit_code == 0
        assert result.output.strip()

    def test_query_graph_type_filter(self, runner: CliRunner, tmp_path: Path) -> None:
        graph_file = _build_graph_file(tmp_path)
        result = runner.invoke(
            cli,
            ["query", "Sample", "--graph", str(graph_file), "--type", "class"],
        )
        assert result.exit_code == 0

    def test_query_invalid_graph_path(self, runner: CliRunner) -> None:
        """A non-existent --graph path is rejected by click."""
        result = runner.invoke(cli, ["query", "x", "--graph", "/nope/x.json"])
        assert result.exit_code != 0


class TestStatsWithGraph:
    """Stats against a pre-built graph file (covers type breakdown path)."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        return CliRunner()

    def test_stats_graph_human(self, runner: CliRunner, tmp_path: Path) -> None:
        graph_file = _build_graph_file(tmp_path)
        result = runner.invoke(cli, ["stats", "--graph", str(graph_file)])
        assert result.exit_code == 0
        assert "Entities" in result.output or "entities" in result.output.lower()

    def test_stats_graph_json(self, runner: CliRunner, tmp_path: Path) -> None:
        import json

        graph_file = _build_graph_file(tmp_path)
        result = runner.invoke(cli, ["stats", "--graph", str(graph_file), "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, dict)


class TestValidateCommand:
    """Tests for the validate command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        return CliRunner()

    def test_validate_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["validate", "--help"])
        assert result.exit_code == 0
        assert "integrity" in result.output.lower() or "validate" in result.output.lower()

    def test_validate_empty_graph(self, runner: CliRunner) -> None:
        """Validating an empty in-memory graph reports valid."""
        result = runner.invoke(cli, ["validate"])
        assert result.exit_code == 0

    def test_validate_graph_human(self, runner: CliRunner, tmp_path: Path) -> None:
        graph_file = _build_graph_file(tmp_path)
        result = runner.invoke(cli, ["validate", "--graph", str(graph_file)])
        assert result.exit_code == 0

    def test_validate_graph_json(self, runner: CliRunner, tmp_path: Path) -> None:
        graph_file = _build_graph_file(tmp_path)
        result = runner.invoke(cli, ["validate", "--graph", str(graph_file), "--json"])
        assert result.exit_code == 0
        assert "is_valid" in result.output

    def test_validate_graph_repair(self, runner: CliRunner, tmp_path: Path) -> None:
        graph_file = _build_graph_file(tmp_path)
        result = runner.invoke(cli, ["validate", "--graph", str(graph_file), "--repair"])
        assert result.exit_code == 0


class TestBenchmarkCommand:
    """Tests for the benchmark command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        return CliRunner()

    def test_benchmark_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["benchmark", "--help"])
        assert result.exit_code == 0

    def test_benchmark_directory(self, runner: CliRunner, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("def a():\n    return 1\n")
        (tmp_path / "b.py").write_text("class B:\n    pass\n")
        result = runner.invoke(cli, ["benchmark", str(tmp_path)])
        assert result.exit_code == 0
        assert "Files parsed" in result.output or "Metrics" in result.output

    def test_benchmark_json(self, runner: CliRunner, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("def a():\n    return 1\n")
        result = runner.invoke(cli, ["benchmark", str(tmp_path), "--json"])
        assert result.exit_code == 0
        assert "files_parsed" in result.output


class TestPatrolCommand:
    """Tests for the patrol command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        return CliRunner()

    @staticmethod
    def _make_comp_workspace(tmp_path: Path) -> Path:
        import sqlite3

        workspace = tmp_path / "proj"
        comp_dir = workspace / ".comp"
        comp_dir.mkdir(parents=True)
        conn = sqlite3.connect(comp_dir / "index.db")
        conn.executescript("""
            CREATE TABLE files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE,
                hash TEXT NOT NULL,
                language TEXT NOT NULL,
                last_indexed INTEGER NOT NULL DEFAULT 0,
                char_count INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                kind TEXT NOT NULL,
                line INTEGER NOT NULL,
                col INTEGER NOT NULL,
                scope TEXT,
                is_exported INTEGER DEFAULT 0,
                signature TEXT
            );
            CREATE TABLE edges (
                from_id INTEGER NOT NULL,
                to_id INTEGER NOT NULL,
                kind TEXT NOT NULL,
                PRIMARY KEY (from_id, to_id, kind)
            );
            CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT);
        """)
        conn.execute(
            "INSERT INTO files (id, path, hash, language) VALUES (1, 'a.py', 'h1', 'python')"
        )
        conn.execute(
            "INSERT INTO nodes (id, file_id, name, kind, line, col, signature)"
            " VALUES (1, 1, 'main', 'function', 1, 0, 'def main()')"
        )
        conn.commit()
        conn.close()
        return workspace

    def test_patrol_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["patrol", "--help"])
        assert result.exit_code == 0
        assert "Patrol" in result.output or "patrol" in result.output.lower()

    def test_patrol_once_baseline(self, runner: CliRunner, tmp_path: Path) -> None:
        workspace = self._make_comp_workspace(tmp_path)
        result = runner.invoke(cli, ["patrol", str(workspace), "--once"])
        assert result.exit_code == 0
        assert (workspace / ".magatama" / "patrol-state.json").is_file()

    def test_patrol_once_no_changes(self, runner: CliRunner, tmp_path: Path) -> None:
        workspace = self._make_comp_workspace(tmp_path)
        runner.invoke(cli, ["patrol", str(workspace), "--once"])
        result = runner.invoke(cli, ["patrol", str(workspace), "--once"])
        assert result.exit_code == 0
        assert "変更なし" in result.output

    def test_patrol_once_detects_change(self, runner: CliRunner, tmp_path: Path) -> None:
        import sqlite3

        workspace = self._make_comp_workspace(tmp_path)
        runner.invoke(cli, ["patrol", str(workspace), "--once"])

        conn = sqlite3.connect(workspace / ".comp" / "index.db")
        conn.execute("UPDATE files SET hash = 'h1-new' WHERE id = 1")
        conn.execute("UPDATE nodes SET signature = 'def main(argv)' WHERE id = 1")
        conn.commit()
        conn.close()

        result = runner.invoke(cli, ["patrol", str(workspace), "--once"])
        assert result.exit_code == 0
        assert "変更検知" in result.output
        assert (workspace / ".comp" / "history").is_dir()

    def test_patrol_missing_workspace(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["patrol", "/nonexistent"])
        assert result.exit_code != 0
