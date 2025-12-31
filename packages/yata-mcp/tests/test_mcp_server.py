"""Tests for YATA MCP Server."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from yata_mcp.server.mcp_server import YataMcpServer


class TestYataMcpServer:
    """Tests for YataMcpServer."""

    @pytest.fixture
    def server(self) -> YataMcpServer:
        """Create a server instance."""
        return YataMcpServer(name="yata-test")

    def test_server_initialization(self, server: YataMcpServer) -> None:
        """Test server initializes with correct name."""
        assert server.name == "yata-test"
        assert server._knowledge_graph is not None

    def test_server_has_tools(self, server: YataMcpServer) -> None:
        """Test server registers expected tools."""
        tools = server.list_tools()
        tool_names = [t.name for t in tools]
        
        # Core tools that should be registered
        assert "parse_file" in tool_names
        assert "parse_directory" in tool_names
        assert "search_entities" in tool_names
        assert "get_entity" in tool_names
        assert "get_related_entities" in tool_names

    def test_server_has_resources(self, server: YataMcpServer) -> None:
        """Test server provides resources."""
        resources = server.list_resources()
        resource_uris = [r.uri for r in resources]
        
        # Should have graph stats resource
        assert any("stats" in uri for uri in resource_uris)

    @pytest.mark.asyncio
    async def test_parse_file_tool(self, server: YataMcpServer, tmp_path) -> None:
        """Test parse_file tool works."""
        # Create a test file
        test_file = tmp_path / "test_module.py"
        test_file.write_text('''
def hello(name: str) -> str:
    """Say hello."""
    return f"Hello, {name}!"
''')

        result = await server.call_tool(
            "parse_file",
            {"file_path": str(test_file)}
        )

        assert result["success"] is True
        assert result["entities_count"] >= 1

    @pytest.mark.asyncio
    async def test_parse_directory_tool(self, server: YataMcpServer, tmp_path) -> None:
        """Test parse_directory tool works."""
        # Create test files
        (tmp_path / "module_a.py").write_text("def func_a(): pass")
        (tmp_path / "module_b.py").write_text("class ClassB: pass")

        result = await server.call_tool(
            "parse_directory",
            {
                "directory": str(tmp_path),
                "patterns": ["*.py"],
            }
        )

        assert result["success"] is True
        assert result["files_processed"] >= 2

    @pytest.mark.asyncio
    async def test_search_entities_tool(self, server: YataMcpServer, tmp_path) -> None:
        """Test search_entities tool works."""
        # First parse a file
        test_file = tmp_path / "search_test.py"
        test_file.write_text('''
def calculate_sum(a: int, b: int) -> int:
    return a + b

class Calculator:
    def multiply(self, a: int, b: int) -> int:
        return a * b
''')
        await server.call_tool("parse_file", {"file_path": str(test_file)})

        # Search for entities
        result = await server.call_tool(
            "search_entities",
            {"query": "calculate", "entity_type": "function"}
        )

        assert len(result["entities"]) >= 1
        assert any("calculate" in e["name"].lower() for e in result["entities"])

    @pytest.mark.asyncio
    async def test_get_entity_tool(self, server: YataMcpServer, tmp_path) -> None:
        """Test get_entity tool works."""
        # Parse a file first
        test_file = tmp_path / "entity_test.py"
        test_file.write_text("def my_function(): pass")
        await server.call_tool("parse_file", {"file_path": str(test_file)})

        # Get all entities and find one
        search_result = await server.call_tool(
            "search_entities",
            {"query": "my_function"}
        )
        
        if search_result["entities"]:
            entity_id = search_result["entities"][0]["id"]
            result = await server.call_tool(
                "get_entity",
                {"entity_id": entity_id}
            )
            assert result["entity"] is not None
            assert result["entity"]["name"] == "my_function"

    @pytest.mark.asyncio
    async def test_get_related_entities_tool(self, server: YataMcpServer, tmp_path) -> None:
        """Test get_related_entities tool works."""
        # Parse a file with relationships
        test_file = tmp_path / "related_test.py"
        test_file.write_text('''
class Parent:
    def method_a(self):
        pass
    
    def method_b(self):
        pass
''')
        await server.call_tool("parse_file", {"file_path": str(test_file)})

        # Find the class
        search_result = await server.call_tool(
            "search_entities",
            {"query": "Parent", "entity_type": "class"}
        )
        
        if search_result["entities"]:
            entity_id = search_result["entities"][0]["id"]
            result = await server.call_tool(
                "get_related_entities",
                {"entity_id": entity_id, "depth": 1}
            )
            # Should find related methods
            assert "related_entities" in result

    @pytest.mark.asyncio
    async def test_unknown_tool_raises_error(self, server: YataMcpServer) -> None:
        """Test calling unknown tool raises error."""
        with pytest.raises(ValueError, match="Unknown tool"):
            await server.call_tool("nonexistent_tool", {})


class TestMcpServerResources:
    """Tests for MCP Server resources."""

    @pytest.fixture
    def server(self) -> YataMcpServer:
        """Create a server instance."""
        return YataMcpServer(name="yata-test")

    @pytest.mark.asyncio
    async def test_read_stats_resource(self, server: YataMcpServer, tmp_path) -> None:
        """Test reading graph stats resource."""
        # Parse some files first
        test_file = tmp_path / "stats_test.py"
        test_file.write_text('''
def func1(): pass
def func2(): pass
class MyClass: pass
''')
        await server.call_tool("parse_file", {"file_path": str(test_file)})

        # Read stats resource
        content = await server.read_resource("yata://graph/stats")

        assert "entity_count" in content
        assert content["entity_count"] >= 3


class TestMcpServerPersistence:
    """Tests for MCP Server persistence features."""

    @pytest.fixture
    def server(self) -> YataMcpServer:
        """Create a server instance."""
        return YataMcpServer(name="yata-test")

    @pytest.mark.asyncio
    async def test_save_graph_tool(self, server: YataMcpServer, tmp_path) -> None:
        """Test save_graph tool."""
        # Parse some files first
        test_file = tmp_path / "save_test.py"
        test_file.write_text("def my_func(): pass")
        await server.call_tool("parse_file", {"file_path": str(test_file)})

        # Save the graph
        save_path = tmp_path / "graph.json"
        result = await server.call_tool(
            "save_graph",
            {"file_path": str(save_path)}
        )

        assert result["success"] is True
        assert result["entities_count"] >= 1
        assert save_path.exists()

    @pytest.mark.asyncio
    async def test_load_graph_tool(self, server: YataMcpServer, tmp_path) -> None:
        """Test load_graph tool."""
        # Parse and save first
        test_file = tmp_path / "load_test.py"
        test_file.write_text("class LoadTest: pass")
        await server.call_tool("parse_file", {"file_path": str(test_file)})
        
        save_path = tmp_path / "graph.json"
        await server.call_tool("save_graph", {"file_path": str(save_path)})

        # Create new server and load
        new_server = YataMcpServer(name="yata-new")
        result = await new_server.call_tool(
            "load_graph",
            {"file_path": str(save_path)}
        )

        assert result["success"] is True
        assert result["entities_count"] >= 1

        # Verify entity is searchable
        search_result = await new_server.call_tool(
            "search_entities",
            {"query": "LoadTest"}
        )
        assert len(search_result["entities"]) >= 1

    @pytest.mark.asyncio
    async def test_load_nonexistent_file(self, server: YataMcpServer, tmp_path) -> None:
        """Test load_graph with non-existent file."""
        result = await server.call_tool(
            "load_graph",
            {"file_path": str(tmp_path / "nonexistent.json")}
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()


class TestIncrementalParse:
    """Tests for incremental parsing tool."""

    @pytest.fixture
    def server(self) -> YataMcpServer:
        """Create a server instance."""
        return YataMcpServer(name="yata-incremental-test")

    @pytest.mark.asyncio
    async def test_incremental_parse_initial(self, server: YataMcpServer, tmp_path) -> None:
        """Test incremental_parse on first run."""
        (tmp_path / "module_a.py").write_text("def func_a(): pass")
        (tmp_path / "module_b.py").write_text("def func_b(): pass")

        result = await server.call_tool(
            "incremental_parse",
            {"directory": str(tmp_path), "patterns": ["*.py"]}
        )

        assert result["success"] is True
        assert result["files_processed"] == 2
        assert result["files_skipped"] == 0
        assert result["total_entities"] > 0

    @pytest.mark.asyncio
    async def test_incremental_parse_skip_unchanged(self, server: YataMcpServer, tmp_path) -> None:
        """Test incremental_parse skips unchanged files."""
        (tmp_path / "module.py").write_text("def func(): pass")

        # First parse
        result1 = await server.call_tool(
            "incremental_parse",
            {"directory": str(tmp_path), "patterns": ["*.py"]}
        )
        assert result1["files_processed"] == 1

        # Second parse - should skip
        result2 = await server.call_tool(
            "incremental_parse",
            {"directory": str(tmp_path), "patterns": ["*.py"]}
        )
        assert result2["files_processed"] == 0
        assert result2["files_skipped"] == 1

    @pytest.mark.asyncio
    async def test_incremental_parse_reparse_modified(self, server: YataMcpServer, tmp_path) -> None:
        """Test incremental_parse re-parses modified files."""
        module_file = tmp_path / "module.py"
        module_file.write_text("def old_func(): pass")

        # First parse
        result1 = await server.call_tool(
            "incremental_parse",
            {"directory": str(tmp_path), "patterns": ["*.py"]}
        )
        assert result1["files_processed"] == 1

        # Modify file
        module_file.write_text("def new_func(): pass")

        # Second parse - should re-parse
        result2 = await server.call_tool(
            "incremental_parse",
            {"directory": str(tmp_path), "patterns": ["*.py"]}
        )
        assert result2["files_processed"] == 1
        assert result2["files_skipped"] == 0

    @pytest.mark.asyncio
    async def test_incremental_parse_removes_deleted_files(self, server: YataMcpServer, tmp_path) -> None:
        """Test incremental_parse removes deleted files from graph."""
        module_a = tmp_path / "module_a.py"
        module_b = tmp_path / "module_b.py"
        module_a.write_text("def func_a(): pass")
        module_b.write_text("def func_b(): pass")

        # First parse
        result1 = await server.call_tool(
            "incremental_parse",
            {"directory": str(tmp_path), "patterns": ["*.py"]}
        )
        assert result1["files_processed"] == 2

        # Delete one file
        module_a.unlink()

        # Second parse - should detect deletion
        result2 = await server.call_tool(
            "incremental_parse",
            {"directory": str(tmp_path), "patterns": ["*.py"]}
        )
        assert result2["files_removed"] == 1
        assert result2["entities_removed"] > 0

    @pytest.mark.asyncio
    async def test_incremental_parse_tool_registered(self, server: YataMcpServer) -> None:
        """Test incremental_parse tool is registered."""
        tools = server.list_tools()
        tool_names = [t.name for t in tools]
        assert "incremental_parse" in tool_names
