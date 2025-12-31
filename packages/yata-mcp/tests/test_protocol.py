"""Tests for MCP Protocol Handler using FastMCP."""

import pytest
from pathlib import Path

from yata_mcp.server.protocol import create_mcp_server


class TestMcpProtocolHandler:
    """Tests for MCP protocol handler."""

    def test_create_mcp_server(self) -> None:
        """Test creating MCP server returns FastMCP instance."""
        mcp = create_mcp_server()
        assert mcp is not None
        assert mcp.name == "yata"

    def test_server_has_tools_registered(self) -> None:
        """Test server has all expected tools."""
        mcp = create_mcp_server()
        
        # Get tool names from the server
        tool_names = list(mcp._tool_manager._tools.keys())
        
        assert "parse_file" in tool_names
        assert "parse_directory" in tool_names
        assert "search_entities" in tool_names
        assert "get_entity" in tool_names
        assert "get_related_entities" in tool_names
        assert "get_graph_stats" in tool_names

    def test_server_has_resources_registered(self) -> None:
        """Test server has expected resources."""
        mcp = create_mcp_server()
        
        resource_uris = list(mcp._resource_manager._resources.keys())
        
        assert any("stats" in uri for uri in resource_uris)

    def test_server_has_prompts_registered(self) -> None:
        """Test server has expected prompts."""
        mcp = create_mcp_server()
        
        prompt_names = list(mcp._prompt_manager._prompts.keys())
        
        assert "analyze_codebase" in prompt_names
        assert "explain_entity" in prompt_names
        assert "find_dependencies" in prompt_names

    @pytest.mark.asyncio
    async def test_parse_file_tool(self, tmp_path: Path) -> None:
        """Test parse_file tool via MCP."""
        mcp = create_mcp_server()
        
        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass")
        
        # Call tool
        result = await mcp.call_tool("parse_file", {"file_path": str(test_file)})
        
        # Result should be content blocks or dict
        assert result is not None

    @pytest.mark.asyncio
    async def test_search_entities_tool(self, tmp_path: Path) -> None:
        """Test search_entities tool via MCP."""
        mcp = create_mcp_server()
        
        # First parse a file
        test_file = tmp_path / "search.py"
        test_file.write_text("def my_search_function(): pass")
        await mcp.call_tool("parse_file", {"file_path": str(test_file)})
        
        # Then search
        result = await mcp.call_tool("search_entities", {"query": "search"})
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_graph_stats_tool(self, tmp_path: Path) -> None:
        """Test get_graph_stats tool via MCP."""
        mcp = create_mcp_server()
        
        # Parse some files first
        test_file = tmp_path / "stats.py"
        test_file.write_text("class MyClass: pass")
        await mcp.call_tool("parse_file", {"file_path": str(test_file)})
        
        # Get stats
        result = await mcp.call_tool("get_graph_stats", {})
        assert result is not None


class TestMcpPrompts:
    """Tests for MCP prompts."""

    @pytest.mark.asyncio
    async def test_analyze_codebase_prompt(self, tmp_path: Path) -> None:
        """Test analyze_codebase prompt generates analysis."""
        mcp = create_mcp_server()
        
        # Create test files
        (tmp_path / "main.py").write_text("def main(): pass")
        (tmp_path / "utils.py").write_text("def helper(): pass")
        
        # Call prompt
        result = await mcp.get_prompt("analyze_codebase", {"directory": str(tmp_path)})
        
        assert result is not None
        # Check messages are returned
        assert hasattr(result, "messages") or isinstance(result, list)

    @pytest.mark.asyncio
    async def test_explain_entity_prompt_not_found(self) -> None:
        """Test explain_entity prompt when entity not found."""
        mcp = create_mcp_server()
        
        # Call prompt for non-existent entity
        result = await mcp.get_prompt("explain_entity", {"entity_name": "NonExistent"})
        
        assert result is not None

    @pytest.mark.asyncio
    async def test_explain_entity_prompt_found(self, tmp_path: Path) -> None:
        """Test explain_entity prompt when entity is found."""
        mcp = create_mcp_server()
        
        # Create and parse file
        test_file = tmp_path / "entity.py"
        test_file.write_text('def my_function():\n    """A test function."""\n    pass')
        await mcp.call_tool("parse_file", {"file_path": str(test_file)})
        
        # Call prompt
        result = await mcp.get_prompt("explain_entity", {"entity_name": "my_function"})
        
        assert result is not None

    @pytest.mark.asyncio
    async def test_find_dependencies_prompt(self, tmp_path: Path) -> None:
        """Test find_dependencies prompt."""
        mcp = create_mcp_server()
        
        # Create and parse file
        test_file = tmp_path / "deps.py"
        test_file.write_text("""
class Parent:
    pass

class Child(Parent):
    def method(self):
        pass
""")
        await mcp.call_tool("parse_file", {"file_path": str(test_file)})
        
        # Call prompt
        result = await mcp.get_prompt("find_dependencies", {"entity_name": "Child"})
        
        assert result is not None

    @pytest.mark.asyncio
    async def test_find_dependencies_not_found(self) -> None:
        """Test find_dependencies prompt when entity not found."""
        mcp = create_mcp_server()
        
        result = await mcp.get_prompt("find_dependencies", {"entity_name": "Unknown"})
        
        assert result is not None
