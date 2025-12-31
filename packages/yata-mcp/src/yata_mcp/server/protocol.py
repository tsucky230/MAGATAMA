"""MCP Protocol Handler using FastMCP.

This module provides the actual MCP protocol implementation
using the official MCP Python SDK (FastMCP).
"""

from pathlib import Path
from typing import Any

from mcp.server import FastMCP

from yata_core.domain.entities import EntityType
from yata_core.domain.value_objects import EntityId
from yata_core.infrastructure.parsers import PythonParser, RustParser, GoParser
from yata_core.infrastructure.parsers.typescript_parser import TypeScriptParser
from yata_core.infrastructure.parsers.javascript_parser import JavaScriptParser
from yata_core.infrastructure.storage import NetworkXKnowledgeGraph
from yata_core.application.usecases.parse_usecase import (
    ParseFileUseCase,
    ParseDirectoryUseCase,
)


def create_mcp_server(name: str = "yata") -> FastMCP:
    """Create and configure the MCP server.
    
    This function creates a FastMCP server with all YATA tools
    and resources registered.
    
    Args:
        name: Server name for identification
        
    Returns:
        Configured FastMCP server instance
    """
    mcp = FastMCP(name=name)
    
    # Initialize knowledge graph
    knowledge_graph = NetworkXKnowledgeGraph()
    
    # Initialize parsers
    python_parser = PythonParser()
    ts_parser = TypeScriptParser()
    js_parser = JavaScriptParser()
    rust_parser = RustParser()
    go_parser = GoParser()
    
    parsers: dict[str, Any] = {
        ".py": python_parser,
        ".ts": ts_parser,
        ".tsx": ts_parser,
        ".js": js_parser,
        ".jsx": js_parser,
        ".rs": rust_parser,
        ".go": go_parser,
    }
    
    # Initialize use cases
    parse_file_usecase = ParseFileUseCase(
        parsers=parsers,
        knowledge_graph=knowledge_graph,
    )
    parse_directory_usecase = ParseDirectoryUseCase(
        parse_file_usecase=parse_file_usecase,
    )
    
    # Register tools
    
    @mcp.tool()
    def parse_file(file_path: str) -> dict[str, Any]:
        """Parse a source file and extract entities into the knowledge graph.
        
        Args:
            file_path: Path to the source file to parse
            
        Returns:
            Result with success status and entity counts
        """
        result = parse_file_usecase.execute(Path(file_path))
        return {
            "success": result.success,
            "entities_count": result.entities_count,
            "relationships_count": result.relationships_count,
            "errors": result.errors,
        }
    
    @mcp.tool()
    def parse_directory(
        directory: str,
        patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> dict[str, Any]:
        """Parse all matching files in a directory.
        
        Args:
            directory: Path to the directory to parse
            patterns: Glob patterns for files to include (default: ['**/*.py'])
            exclude_patterns: Glob patterns for files to exclude
            
        Returns:
            Result with file counts and entity totals
        """
        result = parse_directory_usecase.execute(
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
    
    @mcp.tool()
    def search_entities(
        query: str,
        entity_type: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Search for entities by name or type.
        
        Args:
            query: Search query (matches entity names, case-insensitive)
            entity_type: Filter by entity type (function, class, method, etc.)
            limit: Maximum number of results
            
        Returns:
            List of matching entities
        """
        all_entities = knowledge_graph.entities.all()
        
        # Filter by query
        query_lower = query.lower()
        filtered = [
            e for e in all_entities
            if query_lower in e.name.lower()
        ]
        
        # Filter by type
        if entity_type:
            try:
                target_type = EntityType(entity_type)
                filtered = [e for e in filtered if e.type == target_type]
            except ValueError:
                pass
        
        # Apply limit
        filtered = filtered[:limit]
        
        return {
            "entities": [
                {
                    "id": e.id.value,
                    "name": e.name,
                    "type": e.type.value,
                    "file": e.location.file,
                    "line": e.location.line,
                    "docstring": e.docstring,
                }
                for e in filtered
            ],
            "total_count": len(filtered),
        }
    
    @mcp.tool()
    def get_entity(entity_id: str) -> dict[str, Any]:
        """Get detailed information about a specific entity.
        
        Args:
            entity_id: The entity ID to retrieve
            
        Returns:
            Entity details or error
        """
        try:
            entity = knowledge_graph.entities.get(EntityId(value=entity_id))
            if entity:
                return {
                    "entity": {
                        "id": entity.id.value,
                        "name": entity.name,
                        "type": entity.type.value,
                        "file": entity.location.file,
                        "line": entity.location.line,
                        "docstring": entity.docstring,
                        "scope": entity.scope,
                    }
                }
            return {"entity": None, "error": "Entity not found"}
        except Exception as e:
            return {"entity": None, "error": str(e)}
    
    @mcp.tool()
    def get_related_entities(
        entity_id: str,
        depth: int = 1,
    ) -> dict[str, Any]:
        """Get entities related to a given entity.
        
        Args:
            entity_id: The entity ID to find related entities for
            depth: How many hops to traverse (default: 1)
            
        Returns:
            List of related entities
        """
        try:
            eid = EntityId(value=entity_id)
            neighbors = knowledge_graph.get_neighbors(eid, depth=depth)
            return {
                "related_entities": [
                    {
                        "id": e.id.value,
                        "name": e.name,
                        "type": e.type.value,
                        "file": e.location.file,
                        "line": e.location.line,
                    }
                    for e in neighbors
                ],
                "count": len(neighbors),
            }
        except Exception as e:
            return {"related_entities": [], "error": str(e)}
    
    @mcp.tool()
    def get_graph_stats() -> dict[str, Any]:
        """Get knowledge graph statistics.
        
        Returns:
            Statistics about the knowledge graph
        """
        entities = knowledge_graph.entities.all()
        
        type_counts: dict[str, int] = {}
        for entity in entities:
            type_name = entity.type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        
        return {
            "entity_count": len(entities),
            "relationship_count": len(list(knowledge_graph.relationships.all())),
            "entities_by_type": type_counts,
        }
    
    @mcp.tool()
    def save_graph(file_path: str) -> dict[str, Any]:
        """Save the knowledge graph to a JSON file.
        
        Args:
            file_path: Path to save the JSON file
            
        Returns:
            Result with success status and counts
        """
        try:
            path = Path(file_path)
            knowledge_graph.save(path)
            return {
                "success": True,
                "file_path": str(path.absolute()),
                "entities_count": knowledge_graph.entities.count(),
                "relationships_count": len(list(knowledge_graph.relationships.all())),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @mcp.tool()
    def load_graph(file_path: str) -> dict[str, Any]:
        """Load a knowledge graph from a JSON file.
        
        Args:
            file_path: Path to the JSON file to load
            
        Returns:
            Result with success status and counts
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return {"success": False, "error": f"File not found: {file_path}"}
            knowledge_graph.load(path)
            return {
                "success": True,
                "file_path": str(path.absolute()),
                "entities_count": knowledge_graph.entities.count(),
                "relationships_count": len(list(knowledge_graph.relationships.all())),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # Register resources
    
    @mcp.resource("yata://graph/stats")
    def graph_stats_resource() -> str:
        """Knowledge graph statistics resource."""
        import json
        stats = get_graph_stats()
        return json.dumps(stats, indent=2)
    
    # Register prompts
    
    @mcp.prompt()
    def analyze_codebase(directory: str) -> str:
        """Analyze a codebase structure and provide insights.
        
        This prompt parses the directory and generates a comprehensive
        analysis of the code structure including entity counts,
        relationship patterns, and key insights.
        
        Args:
            directory: Path to the directory to analyze
        """
        result = parse_directory_usecase.execute(
            Path(directory),
            patterns=["**/*.py", "**/*.ts", "**/*.tsx"],
        )
        
        stats = get_graph_stats()
        
        # Build analysis prompt
        prompt_parts = [
            "# Codebase Analysis Request",
            "",
            f"I have parsed the codebase at `{directory}` and gathered the following information:",
            "",
            "## Summary",
            f"- Files processed: {result.files_processed}",
            f"- Total entities: {result.total_entities}",
            f"- Total relationships: {result.total_relationships}",
            "",
            "## Entity Distribution",
        ]
        
        for entity_type, count in stats.get("entities_by_type", {}).items():
            prompt_parts.append(f"- {entity_type}: {count}")
        
        if result.errors:
            prompt_parts.extend([
                "",
                "## Parse Errors",
                *[f"- {e}" for e in result.errors[:5]],
            ])
        
        prompt_parts.extend([
            "",
            "## Analysis Tasks",
            "Please analyze this codebase structure and provide:",
            "1. Overall architecture assessment",
            "2. Key modules and their responsibilities",
            "3. Potential areas for refactoring",
            "4. Code organization recommendations",
        ])
        
        return "\n".join(prompt_parts)
    
    @mcp.prompt()
    def explain_entity(entity_name: str) -> str:
        """Generate a prompt to explain a specific entity.
        
        This prompt searches for an entity and provides context
        for generating explanations.
        
        Args:
            entity_name: Name of the entity to explain
        """
        all_entities = knowledge_graph.entities.all()
        
        # Find matching entities
        query_lower = entity_name.lower()
        matches = [
            e for e in all_entities
            if query_lower in e.name.lower()
        ]
        
        if not matches:
            return f"No entity found matching '{entity_name}'. Please parse the codebase first using the parse_directory tool."
        
        # Get the best match
        entity = matches[0]
        for e in matches:
            if e.name.lower() == query_lower:
                entity = e
                break
        
        # Get related entities
        neighbors = knowledge_graph.get_neighbors(entity.id, depth=1)
        
        prompt_parts = [
            f"# Explain: {entity.name}",
            "",
            "## Entity Information",
            f"- Type: {entity.type.value}",
            f"- Location: {entity.location.file}:{entity.location.line}",
        ]
        
        if entity.docstring:
            prompt_parts.extend([
                "",
                "## Documentation",
                f"```",
                entity.docstring,
                "```",
            ])
        
        if neighbors:
            prompt_parts.extend([
                "",
                "## Related Entities",
                *[f"- {n.name} ({n.type.value})" for n in neighbors[:10]],
            ])
        
        prompt_parts.extend([
            "",
            "## Request",
            f"Please provide a detailed explanation of the `{entity.name}` {entity.type.value}.",
            "Include its purpose, how it works, and how it relates to other parts of the codebase.",
        ])
        
        return "\n".join(prompt_parts)
    
    @mcp.prompt()
    def find_dependencies(entity_name: str) -> str:
        """Generate a prompt to analyze dependencies of an entity.
        
        This prompt helps understand what an entity depends on
        and what depends on it.
        
        Args:
            entity_name: Name of the entity to analyze
        """
        all_entities = knowledge_graph.entities.all()
        all_relationships = list(knowledge_graph.relationships.all())
        
        # Find matching entities
        query_lower = entity_name.lower()
        matches = [
            e for e in all_entities
            if query_lower in e.name.lower()
        ]
        
        if not matches:
            return f"No entity found matching '{entity_name}'. Please parse the codebase first."
        
        entity = matches[0]
        for e in matches:
            if e.name.lower() == query_lower:
                entity = e
                break
        
        # Find outgoing and incoming relationships
        outgoing = [
            r for r in all_relationships
            if r.source_id == entity.id
        ]
        incoming = [
            r for r in all_relationships
            if r.target_id == entity.id
        ]
        
        prompt_parts = [
            f"# Dependency Analysis: {entity.name}",
            "",
            f"## Entity: {entity.name} ({entity.type.value})",
            f"Location: {entity.location.file}:{entity.location.line}",
            "",
            "## Outgoing Dependencies (what this entity uses)",
        ]
        
        if outgoing:
            for rel in outgoing[:15]:
                target = knowledge_graph.entities.get(rel.target_id)
                if target:
                    prompt_parts.append(f"- {rel.type.value} → {target.name} ({target.type.value})")
        else:
            prompt_parts.append("- None found")
        
        prompt_parts.extend([
            "",
            "## Incoming Dependencies (what uses this entity)",
        ])
        
        if incoming:
            for rel in incoming[:15]:
                source = knowledge_graph.entities.get(rel.source_id)
                if source:
                    prompt_parts.append(f"- {source.name} ({source.type.value}) → {rel.type.value}")
        else:
            prompt_parts.append("- None found")
        
        prompt_parts.extend([
            "",
            "## Analysis Request",
            "Based on the dependency information above, please analyze:",
            "1. What are the key dependencies of this entity?",
            "2. Is this entity tightly coupled or loosely coupled?",
            "3. Are there any circular dependency risks?",
            "4. Suggestions for improving the dependency structure",
        ])
        
        return "\n".join(prompt_parts)
    
    return mcp


def run_stdio_server() -> None:
    """Run the MCP server with stdio transport.
    
    This is the main entry point for running YATA as an MCP server
    that communicates via standard input/output.
    """
    mcp = create_mcp_server()
    mcp.run(transport="stdio")
