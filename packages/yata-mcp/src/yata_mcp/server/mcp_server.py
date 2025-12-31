"""YATA MCP Server implementation.

This module provides the main MCP server that exposes knowledge graph
functionality to AI coding assistants via the Model Context Protocol.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Awaitable

from yata_core.domain.entities import Entity, EntityType
from yata_core.infrastructure.parsers import PythonParser, RustParser, GoParser
from yata_core.infrastructure.parsers.typescript_parser import TypeScriptParser
from yata_core.infrastructure.parsers.javascript_parser import JavaScriptParser
from yata_core.infrastructure.storage import NetworkXKnowledgeGraph
from yata_core.application.usecases.parse_usecase import (
    ParseFileUseCase,
    ParseDirectoryUseCase,
    IncrementalParseUseCase,
)


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


class YataMcpServer:
    """YATA MCP Server.
    
    Provides knowledge graph functionality via MCP protocol:
    - Tools for parsing files and querying entities
    - Resources for accessing graph statistics
    
    This server implements Article II (MCP-First) by exposing
    all functionality through the MCP protocol.
    """
    
    def __init__(self, name: str = "yata") -> None:
        """Initialize the MCP server.
        
        Args:
            name: Server name for identification
        """
        self.name = name
        
        # Initialize knowledge graph (Article I: Library-First)
        self._knowledge_graph = NetworkXKnowledgeGraph()
        
        # Initialize parsers
        python_parser = PythonParser()
        ts_parser = TypeScriptParser()
        js_parser = JavaScriptParser()
        rust_parser = RustParser()
        go_parser = GoParser()
        
        self._parsers: dict[str, Any] = {
            ".py": python_parser,
            ".ts": ts_parser,
            ".tsx": ts_parser,
            ".js": js_parser,
            ".jsx": js_parser,
            ".rs": rust_parser,
            ".go": go_parser,
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
        ]
        
        # Define resources
        self._resources: list[Resource] = [
            Resource(
                uri="yata://graph/stats",
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
        if uri == "yata://graph/stats":
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
        if uri == "yata://graph/stats":
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
        filtered = [
            e for e in all_entities
            if query_lower in e.name.lower()
        ]
        
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
        from yata_core.domain.value_objects import EntityId
        
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
        from yata_core.domain.value_objects import EntityId
        
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
