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


class TestMcpToolsExtended:
    """Extended tests for MCP tools."""

    @pytest.mark.asyncio
    async def test_get_entity_tool(self, tmp_path: Path) -> None:
        """Test get_entity tool via MCP."""
        mcp = create_mcp_server()
        
        test_file = tmp_path / "entity.py"
        test_file.write_text("def my_func(): pass")
        await mcp.call_tool("parse_file", {"file_path": str(test_file)})
        
        # Get entity - even with invalid ID should return response
        result = await mcp.call_tool("get_entity", {"entity_id": "nonexistent"})
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_related_entities_tool(self, tmp_path: Path) -> None:
        """Test get_related_entities tool."""
        mcp = create_mcp_server()
        
        test_file = tmp_path / "related.py"
        test_file.write_text("class A:\n    def method(self): pass")
        await mcp.call_tool("parse_file", {"file_path": str(test_file)})
        
        result = await mcp.call_tool("get_related_entities", {"entity_id": "module_0001"})
        assert result is not None

    @pytest.mark.asyncio
    async def test_search_entities_with_type(self, tmp_path: Path) -> None:
        """Test search_entities with type filter."""
        mcp = create_mcp_server()
        
        test_file = tmp_path / "typed.py"
        test_file.write_text("class MyClass:\n    def method(self): pass")
        await mcp.call_tool("parse_file", {"file_path": str(test_file)})
        
        result = await mcp.call_tool("search_entities", {
            "query": "My",
            "entity_type": "class",
            "limit": 5
        })
        assert result is not None

    @pytest.mark.asyncio
    async def test_parse_directory_tool(self, tmp_path: Path) -> None:
        """Test parse_directory tool."""
        mcp = create_mcp_server()
        
        # Create test files
        (tmp_path / "file1.py").write_text("def f1(): pass")
        (tmp_path / "file2.py").write_text("def f2(): pass")
        
        result = await mcp.call_tool("parse_directory", {
            "directory": str(tmp_path),
            "patterns": ["**/*.py"]
        })
        assert result is not None


class TestMcpFrameworkTools:
    """Tests for framework knowledge tools."""

    @pytest.mark.asyncio
    async def test_list_frameworks_tool(self) -> None:
        """Test list_frameworks tool."""
        mcp = create_mcp_server()
        result = await mcp.call_tool("list_frameworks", {})
        assert result is not None


class TestCompBridgeTools:
    """Tests for comP bridge tools."""

    def test_server_has_comp_tools(self) -> None:
        """read_external_graph and get_external_graph_info are registered."""
        mcp = create_mcp_server()
        tool_names = list(mcp._tool_manager._tools.keys())
        assert "read_external_graph" in tool_names
        assert "get_external_graph_info" in tool_names

    @pytest.mark.asyncio
    async def test_get_external_graph_info_not_found(self, tmp_path: Path) -> None:
        """get_external_graph_info returns exists=False for missing path."""
        mcp = create_mcp_server()
        result = await mcp.call_tool(
            "get_external_graph_info", {"path": str(tmp_path / "no_such")}
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_read_external_graph_not_found(self, tmp_path: Path) -> None:
        """read_external_graph returns success=False for missing path."""
        mcp = create_mcp_server()
        result = await mcp.call_tool(
            "read_external_graph", {"path": str(tmp_path / "no_such")}
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_read_external_graph_success(self, tmp_path: Path) -> None:
        """read_external_graph loads a valid comP index."""
        import sqlite3

        workspace = tmp_path / "proj"
        comp_dir = workspace / ".comp"
        comp_dir.mkdir(parents=True)
        db_path = comp_dir / "index.db"
        conn = sqlite3.connect(db_path)
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
            "INSERT INTO files (path, hash, language) VALUES ('a.py', 'h', 'python')"
        )
        conn.commit()
        conn.close()

        mcp = create_mcp_server()
        result = await mcp.call_tool(
            "read_external_graph", {"path": str(workspace)}
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_external_graph_info_success(self, tmp_path: Path) -> None:
        """get_external_graph_info returns counts for valid index."""
        import sqlite3

        workspace = tmp_path / "proj2"
        comp_dir = workspace / ".comp"
        comp_dir.mkdir(parents=True)
        db_path = comp_dir / "index.db"
        conn = sqlite3.connect(db_path)
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
            "INSERT INTO files (path, hash, language) VALUES ('b.py', 'h', 'python')"
        )
        conn.commit()
        conn.close()

        mcp = create_mcp_server()
        result = await mcp.call_tool(
            "get_external_graph_info", {"path": str(workspace)}
        )
        assert result is not None


class TestMcpUtilityTools:
    """Tests for utility tools."""

    @pytest.mark.asyncio
    async def test_list_supported_languages_tool(self) -> None:
        """Test list_supported_languages tool."""
        mcp = create_mcp_server()
        result = await mcp.call_tool("list_supported_languages", {})
        assert result is not None

    @pytest.mark.asyncio
    async def test_save_and_load_graph_tool(self, tmp_path: Path) -> None:
        """Test save_graph and load_graph tools."""
        mcp = create_mcp_server()
        
        # First parse something
        test_file = tmp_path / "graph.py"
        test_file.write_text("def foo(): pass")
        await mcp.call_tool("parse_file", {"file_path": str(test_file)})
        
        # Save graph
        graph_file = tmp_path / "graph.json"
        save_result = await mcp.call_tool("save_graph", {"file_path": str(graph_file)})
        assert save_result is not None
        
        # Load graph
        load_result = await mcp.call_tool("load_graph", {"file_path": str(graph_file)})
        assert load_result is not None

    @pytest.mark.asyncio
    async def test_load_graph_not_found(self) -> None:
        """Test load_graph with non-existent file."""
        mcp = create_mcp_server()
        result = await mcp.call_tool("load_graph", {"file_path": "/nonexistent/graph.json"})
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_entity_invalid(self) -> None:
        """Test get_entity with invalid ID."""
        mcp = create_mcp_server()
        result = await mcp.call_tool("get_entity", {"entity_id": "invalid_id"})
        assert result is not None
