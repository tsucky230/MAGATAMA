"""MAGATAMA MCP Server implementation.

This module provides the main MCP server that exposes knowledge graph
functionality to AI coding assistants via the Model Context Protocol.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from magatama_core.application.usecases.comp_usecase import (
    EntityHistoryUseCase,
    LoadCompIndexUseCase,
    LoadCompSessionsUseCase,
)
from magatama_core.application.usecases.handoff_usecase import GenerateHandoffUseCase
from magatama_core.application.usecases.parse_usecase import (
    IncrementalParseUseCase,
    ParseDirectoryUseCase,
    ParseFileUseCase,
)
from magatama_core.domain.entities import Entity, EntityType
from magatama_core.infrastructure.parsers import (
    CParser,
    CppParser,
    CSharpParser,
    DartParser,
    ElixirParser,
    GoParser,
    GroovyParser,
    HaskellParser,
    JavaParser,
    JavaScriptParser,
    JuliaParser,
    KotlinParser,
    LuaParser,
    ObjectiveCParser,
    PhpParser,
    PythonParser,
    RubyParser,
    RustParser,
    ScalaParser,
    SqlParser,
    SwiftParser,
    TypeScriptParser,
    YAMLParser,
    ZigParser,
)
from magatama_core.infrastructure.storage import NetworkXKnowledgeGraph


@dataclass
class Tool:
    """MCP Tool definition."""

    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass
class Resource:
    """MCP Resource definition."""

    uri: str
    name: str
    description: str
    mime_type: str = "application/json"


class MagatamaMcpServer:
    """MAGATAMA MCP Server.

    Provides knowledge graph functionality via MCP protocol:
    - Tools for parsing files and querying entities
    - Resources for accessing graph statistics

    This server implements Article II (MCP-First) by exposing
    all functionality through the MCP protocol.
    """

    def __init__(self, name: str = "magatama") -> None:
        """Initialize the MCP server.

        Args:
            name: Server name for identification
        """
        self.name = name

        # Initialize knowledge graph (Article I: Library-First)
        self._knowledge_graph = NetworkXKnowledgeGraph()

        # Initialize parsers (24 languages, matching server/protocol.py)
        python_parser = PythonParser()
        ts_parser = TypeScriptParser()
        js_parser = JavaScriptParser()
        rust_parser = RustParser()
        go_parser = GoParser()
        ruby_parser = RubyParser()
        java_parser = JavaParser()
        csharp_parser = CSharpParser()
        cpp_parser = CppParser()
        c_parser = CParser()
        objc_parser = ObjectiveCParser()
        php_parser = PhpParser()
        swift_parser = SwiftParser()
        kotlin_parser = KotlinParser()
        scala_parser = ScalaParser()
        lua_parser = LuaParser()
        haskell_parser = HaskellParser()
        elixir_parser = ElixirParser()
        julia_parser = JuliaParser()
        sql_parser = SqlParser()
        groovy_parser = GroovyParser()
        dart_parser = DartParser()
        zig_parser = ZigParser()
        yaml_parser = YAMLParser()

        self._parsers: dict[str, Any] = {
            ".py": python_parser,
            ".ts": ts_parser,
            ".tsx": ts_parser,
            ".js": js_parser,
            ".jsx": js_parser,
            ".rs": rust_parser,
            ".go": go_parser,
            ".rb": ruby_parser,
            ".java": java_parser,
            ".cs": csharp_parser,
            ".cpp": cpp_parser,
            ".hpp": cpp_parser,
            ".cc": cpp_parser,
            ".hh": cpp_parser,
            ".cxx": cpp_parser,
            ".c": c_parser,
            ".h": c_parser,
            ".m": objc_parser,
            ".mm": objc_parser,
            ".php": php_parser,
            ".swift": swift_parser,
            ".kt": kotlin_parser,
            ".kts": kotlin_parser,
            ".scala": scala_parser,
            ".lua": lua_parser,
            ".hs": haskell_parser,
            ".ex": elixir_parser,
            ".exs": elixir_parser,
            ".jl": julia_parser,
            ".sql": sql_parser,
            ".groovy": groovy_parser,
            ".dart": dart_parser,
            ".zig": zig_parser,
            ".yaml": yaml_parser,
            ".yml": yaml_parser,
        }

        # Initialize use cases
        self._parse_file_usecase = ParseFileUseCase(
            parsers=self._parsers,
            knowledge_graph=self._knowledge_graph,
        )
        self._parse_directory_usecase = ParseDirectoryUseCase(
            parse_file_usecase=self._parse_file_usecase,
        )
        self._incremental_parse_usecase = IncrementalParseUseCase(
            parsers=self._parsers,
            knowledge_graph=self._knowledge_graph,
        )
        self._load_comp_index_usecase = LoadCompIndexUseCase(
            knowledge_graph=self._knowledge_graph,
        )
        self._load_comp_sessions_usecase = LoadCompSessionsUseCase(
            knowledge_graph=self._knowledge_graph,
        )
        self._entity_history_usecase = EntityHistoryUseCase(
            knowledge_graph=self._knowledge_graph,
        )
        self._generate_handoff_usecase = GenerateHandoffUseCase()

        # Register tool handlers
        self._tool_handlers: dict[str, Callable[..., Awaitable[dict[str, Any]]]] = {
            "parse_file": self._handle_parse_file,
            "parse_directory": self._handle_parse_directory,
            "incremental_parse": self._handle_incremental_parse,
            "search_entities": self._handle_search_entities,
            "get_entity": self._handle_get_entity,
            "get_related_entities": self._handle_get_related_entities,
            "save_graph": self._handle_save_graph,
            "load_graph": self._handle_load_graph,
            "read_external_graph": self._handle_read_external_graph,
            "read_external_sessions": self._handle_read_external_sessions,
            "get_entity_history": self._handle_get_entity_history,
            "generate_handoff": self._handle_generate_handoff,
            "get_external_graph_info": self._handle_get_external_graph_info,
        }

        # Define tools
        self._tools: list[Tool] = [
            Tool(
                name="parse_file",
                description="Parse a source file and extract entities into the knowledge graph",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the source file to parse",
                        },
                    },
                    "required": ["file_path"],
                },
            ),
            Tool(
                name="parse_directory",
                description="Parse all matching files in a directory",
                input_schema={
                    "type": "object",
                    "properties": {
                        "directory": {
                            "type": "string",
                            "description": "Path to the directory to parse",
                        },
                        "patterns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Glob patterns for files to include (default: ['**/*.py'])",
                        },
                        "exclude_patterns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Glob patterns for files to exclude",
                        },
                    },
                    "required": ["directory"],
                },
            ),
            Tool(
                name="incremental_parse",
                description="Incrementally parse a directory, only re-parsing changed files. Efficiently updates the knowledge graph by detecting file changes via content hashes.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "directory": {
                            "type": "string",
                            "description": "Path to the directory to parse",
                        },
                        "patterns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Glob patterns for files to include (default: ['**/*.py'])",
                        },
                        "exclude_patterns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Glob patterns for files to exclude",
                        },
                    },
                    "required": ["directory"],
                },
            ),
            Tool(
                name="search_entities",
                description="Search for entities by name or type",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (matches entity names)",
                        },
                        "entity_type": {
                            "type": "string",
                            "enum": [t.value for t in EntityType],
                            "description": "Filter by entity type",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (default: 20)",
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="get_entity",
                description="Get detailed information about a specific entity",
                input_schema={
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "string",
                            "description": "The entity ID to retrieve",
                        },
                    },
                    "required": ["entity_id"],
                },
            ),
            Tool(
                name="get_related_entities",
                description="Get entities related to a given entity (neighbors in the graph)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "string",
                            "description": "The entity ID to find related entities for",
                        },
                        "depth": {
                            "type": "integer",
                            "description": "How many hops to traverse (default: 1)",
                        },
                    },
                    "required": ["entity_id"],
                },
            ),
            Tool(
                name="save_graph",
                description="Save the knowledge graph to a JSON file",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to save the JSON file",
                        },
                    },
                    "required": ["file_path"],
                },
            ),
            Tool(
                name="load_graph",
                description="Load a knowledge graph from a JSON file",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the JSON file to load",
                        },
                    },
                    "required": ["file_path"],
                },
            ),
            Tool(
                name="read_external_graph",
                description=(
                    "Load an external comP index (.comp/index.db) into the knowledge graph"
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": (
                                "Workspace root containing .comp/index.db, the .comp "
                                "directory, or a direct path to the .db file"
                            ),
                        },
                        "mode": {
                            "type": "string",
                            "description": (
                                "'replace' (default) removes previously loaded entities "
                                "from the same workspace before loading; 'merge' adds on top"
                            ),
                        },
                    },
                    "required": ["path"],
                },
            ),
            Tool(
                name="read_external_sessions",
                description=(
                    "Load comP session history (.comp/session-memory.json and "
                    ".comp/history/*.jsonl) into the knowledge graph as SESSION "
                    "entities linked to code entities via DISCUSSED relationships"
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": (
                                "Workspace root containing .comp/, or the .comp directory"
                            ),
                        },
                        "mode": {
                            "type": "string",
                            "description": (
                                "'replace' (default) removes previously loaded session "
                                "entities from the same workspace first; 'merge' adds on top"
                            ),
                        },
                    },
                    "required": ["path"],
                },
            ),
            Tool(
                name="get_entity_history",
                description=(
                    "Get past comP session records that discussed a file or symbol "
                    "(via DISCUSSED links), plus current impact analysis. Load data "
                    "first with read_external_graph/read_external_sessions, or pass "
                    "path to load automatically"
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "File path (relative or absolute) or exact symbol name",
                        },
                        "path": {
                            "type": "string",
                            "description": (
                                "Optional comP workspace root; when given, index and "
                                "sessions are (re)loaded from it before the query"
                            ),
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Max history records to return (default 10)",
                        },
                        "analyze": {
                            "type": "boolean",
                            "description": "Also run impact analysis (default true)",
                        },
                    },
                    "required": ["name"],
                },
            ),
            Tool(
                name="generate_handoff",
                description=(
                    "Generate a handoff Markdown for the next session from recent comP "
                    "session records and git state, and append it to .comp/history "
                    "(full text saved under .magatama/handoffs/)"
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": (
                                "Workspace root containing .comp/, or the .comp directory"
                            ),
                        },
                        "token_budget": {
                            "type": "integer",
                            "description": (
                                "Approximate token size of the output "
                                "(rough estimate at 2 chars/token; default 2000)"
                            ),
                        },
                        "recent": {
                            "type": "integer",
                            "description": "Max recent session records to include (default 10)",
                        },
                    },
                    "required": ["path"],
                },
            ),
            Tool(
                name="get_external_graph_info",
                description="Inspect a comP index (.comp/index.db) without loading it",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": (
                                "Workspace root containing .comp/index.db, the .comp "
                                "directory, or a direct path to the .db file"
                            ),
                        },
                    },
                    "required": ["path"],
                },
            ),
        ]

        # Define resources
        self._resources: list[Resource] = [
            Resource(
                uri="magatama://graph/stats",
                name="Knowledge Graph Statistics",
                description="Get statistics about the knowledge graph",
            ),
        ]

    def list_tools(self) -> list[Tool]:
        """List available tools."""
        return self._tools

    def list_resources(self) -> list[Resource]:
        """List available resources."""
        return self._resources

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool by name.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool result

        Raises:
            ValueError: If tool is unknown
        """
        handler = self._tool_handlers.get(name)
        if handler is None:
            raise ValueError(f"Unknown tool: {name}")
        return await handler(**arguments)

    async def read_resource(self, uri: str) -> dict[str, Any]:
        """Read a resource by URI.

        Args:
            uri: Resource URI

        Returns:
            Resource content

        Raises:
            ValueError: If resource is unknown
        """
        if uri == "magatama://graph/stats":
            return self._get_graph_stats()
        raise ValueError(f"Unknown resource: {uri}")

    def read_resource_sync(self, uri: str) -> dict[str, Any]:
        """Synchronous version of read_resource for CLI usage.

        Args:
            uri: Resource URI

        Returns:
            Resource content

        Raises:
            ValueError: If resource is unknown
        """
        if uri == "magatama://graph/stats":
            return self._get_graph_stats()
        raise ValueError(f"Unknown resource: {uri}")

    # Tool handlers

    async def _handle_parse_file(self, file_path: str) -> dict[str, Any]:
        """Handle parse_file tool."""
        result = self._parse_file_usecase.execute(Path(file_path))
        return {
            "success": result.success,
            "entities_count": result.entities_count,
            "relationships_count": result.relationships_count,
            "errors": result.errors,
        }

    async def _handle_parse_directory(
        self,
        directory: str,
        patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> dict[str, Any]:
        """Handle parse_directory tool."""
        result = self._parse_directory_usecase.execute(
            Path(directory),
            patterns=patterns,
            exclude_patterns=exclude_patterns,
        )
        return {
            "success": result.success,
            "files_processed": result.files_processed,
            "total_entities": result.total_entities,
            "total_relationships": result.total_relationships,
            "errors": result.errors,
        }

    async def _handle_incremental_parse(
        self,
        directory: str,
        patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> dict[str, Any]:
        """Handle incremental_parse tool.

        Incrementally parses a directory, only re-parsing files that have
        changed since the last parse. This is more efficient for large
        codebases where only a few files change at a time.
        """
        result = self._incremental_parse_usecase.execute(
            Path(directory),
            patterns=patterns,
            exclude_patterns=exclude_patterns,
        )
        return {
            "success": result.success,
            "files_processed": result.files_processed,
            "files_skipped": result.files_skipped,
            "files_removed": result.files_removed,
            "total_entities": result.total_entities,
            "total_relationships": result.total_relationships,
            "entities_removed": result.entities_removed,
            "errors": result.errors,
        }

    async def _handle_search_entities(
        self,
        query: str,
        entity_type: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Handle search_entities tool."""
        all_entities = self._knowledge_graph.entities.all()

        # Filter by query (case-insensitive name match)
        query_lower = query.lower()
        filtered = [e for e in all_entities if query_lower in e.name.lower()]

        # Filter by type if specified
        if entity_type:
            try:
                target_type = EntityType(entity_type)
                filtered = [e for e in filtered if e.type == target_type]
            except ValueError:
                pass  # Invalid type, ignore filter

        # Apply limit
        filtered = filtered[:limit]

        return {
            "entities": [self._entity_to_dict(e) for e in filtered],
            "total_count": len(filtered),
        }

    async def _handle_get_entity(self, entity_id: str) -> dict[str, Any]:
        """Handle get_entity tool."""
        from magatama_core.domain.value_objects import EntityId

        try:
            entity = self._knowledge_graph.entities.get(EntityId(value=entity_id))
            if entity:
                return {"entity": self._entity_to_dict(entity)}
            return {"entity": None, "error": "Entity not found"}
        except Exception as e:
            return {"entity": None, "error": str(e)}

    async def _handle_get_related_entities(
        self,
        entity_id: str,
        depth: int = 1,
    ) -> dict[str, Any]:
        """Handle get_related_entities tool."""
        from magatama_core.domain.value_objects import EntityId

        try:
            eid = EntityId(value=entity_id)
            neighbors = self._knowledge_graph.get_neighbors(eid, depth=depth)
            return {
                "related_entities": [self._entity_to_dict(e) for e in neighbors],
                "count": len(neighbors),
            }
        except Exception as e:
            return {"related_entities": [], "error": str(e)}

    async def _handle_save_graph(self, file_path: str) -> dict[str, Any]:
        """Handle save_graph tool."""
        try:
            path = Path(file_path)
            self._knowledge_graph.save(path)
            entities_count = self._knowledge_graph.entities.count()
            relationships_count = len(list(self._knowledge_graph.relationships.all()))
            return {
                "success": True,
                "file_path": str(path.absolute()),
                "entities_count": entities_count,
                "relationships_count": relationships_count,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _handle_load_graph(self, file_path: str) -> dict[str, Any]:
        """Handle load_graph tool."""
        try:
            path = Path(file_path)
            if not path.exists():
                return {"success": False, "error": f"File not found: {file_path}"}
            self._knowledge_graph.load(path)
            entities_count = self._knowledge_graph.entities.count()
            relationships_count = len(list(self._knowledge_graph.relationships.all()))
            return {
                "success": True,
                "file_path": str(path.absolute()),
                "entities_count": entities_count,
                "relationships_count": relationships_count,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _handle_read_external_graph(
        self,
        path: str,
        mode: str = "replace",
    ) -> dict[str, Any]:
        """Handle read_external_graph tool (comP bridge)."""
        result = self._load_comp_index_usecase.execute(path, mode=mode)
        return {
            "success": result.success,
            "alias": result.alias,
            "db_path": result.db_path,
            "entities_loaded": result.entities_loaded,
            "relationships_loaded": result.relationships_loaded,
            "entities_removed": result.entities_removed,
            "skipped_edges": result.skipped_edges,
            "comp_metadata": result.comp_metadata,
            "errors": result.errors,
        }

    async def _handle_read_external_sessions(
        self,
        path: str,
        mode: str = "replace",
    ) -> dict[str, Any]:
        """Handle read_external_sessions tool (comP bridge)."""
        result = self._load_comp_sessions_usecase.execute(path, mode=mode)
        return {
            "success": result.success,
            "alias": result.alias,
            "comp_dir": result.comp_dir,
            "sessions_loaded": result.sessions_loaded,
            "entities_removed": result.entities_removed,
            "discussed_links": result.discussed_links,
            "unmatched_files": result.unmatched_files,
            "unmatched_symbols": result.unmatched_symbols,
            "sources": result.sources,
            "skipped_records": result.skipped_records,
            "errors": result.errors,
        }

    async def _handle_get_entity_history(
        self,
        name: str,
        path: str = "",
        limit: int = 10,
        analyze: bool = True,
    ) -> dict[str, Any]:
        """Handle get_entity_history tool (comP bridge)."""
        load_errors: list[str] = []
        if path:
            index_result = self._load_comp_index_usecase.execute(path, mode="replace")
            load_errors.extend(index_result.errors)
            sessions_result = self._load_comp_sessions_usecase.execute(path, mode="replace")
            load_errors.extend(sessions_result.errors)
        result = self._entity_history_usecase.execute(name, limit=limit, analyze=analyze)
        return {
            "success": result.success,
            "query": result.query,
            "matched_entities": result.matched_entities,
            "history": result.history,
            "impact": result.impact,
            "errors": load_errors + result.errors,
        }

    async def _handle_generate_handoff(
        self,
        path: str,
        token_budget: int = 2000,
        recent: int = 10,
    ) -> dict[str, Any]:
        """Handle generate_handoff tool (comP bridge)."""
        result = self._generate_handoff_usecase.execute(
            path, token_budget=token_budget, recent=recent
        )
        return {
            "success": result.success,
            "markdown": result.markdown,
            "estimated_tokens": result.estimated_tokens,
            "sessions_included": result.sessions_included,
            "history_file": result.history_file,
            "handoff_file": result.handoff_file,
            "errors": result.errors,
        }

    async def _handle_get_external_graph_info(self, path: str) -> dict[str, Any]:
        """Handle get_external_graph_info tool (comP bridge)."""
        import sqlite3
        import urllib.parse

        from magatama_core.infrastructure.storage.comp_index_reader import (
            CompIndexNotFoundError,
            resolve_db_path,
        )

        try:
            db_path = resolve_db_path(path)
        except CompIndexNotFoundError as e:
            return {"exists": False, "error": str(e)}
        uri = f"file:{urllib.parse.quote(db_path.as_posix())}?mode=ro"
        try:
            conn = sqlite3.connect(uri, uri=True)
            try:
                conn.execute("PRAGMA busy_timeout=5000")
                files = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
                nodes = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
                edges = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
                meta = dict(conn.execute("SELECT key, value FROM metadata").fetchall())
                last_indexed = conn.execute("SELECT MAX(last_indexed) FROM files").fetchone()[0]
            finally:
                conn.close()
        except sqlite3.Error as e:
            return {"exists": True, "db_path": str(db_path), "error": str(e)}
        return {
            "exists": True,
            "db_path": str(db_path),
            "files": files,
            "nodes": nodes,
            "edges": edges,
            "last_indexed": last_indexed,
            "metadata": meta,
        }

    # Resource handlers

    def _get_graph_stats(self) -> dict[str, Any]:
        """Get knowledge graph statistics."""
        entities = self._knowledge_graph.entities.all()

        # Count by type
        type_counts: dict[str, int] = {}
        for entity in entities:
            type_name = entity.type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        return {
            "entity_count": len(entities),
            "relationship_count": len(list(self._knowledge_graph.relationships.all())),
            "entities_by_type": type_counts,
        }

    # Helpers

    def _entity_to_dict(self, entity: Entity) -> dict[str, Any]:
        """Convert entity to dictionary for JSON serialization."""
        return {
            "id": entity.id.value,
            "name": entity.name,
            "type": entity.type.value,
            "location": {
                "file": entity.location.file,
                "line": entity.location.line,
                "column": entity.location.column,
            },
            "docstring": entity.docstring,
            "scope": entity.scope,
        }
