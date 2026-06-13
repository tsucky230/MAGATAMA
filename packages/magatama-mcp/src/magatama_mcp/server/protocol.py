"""MCP Protocol Handler using FastMCP.

This module provides the actual MCP protocol implementation
using the official MCP Python SDK (FastMCP).
"""

from pathlib import Path
from typing import Any

from mcp.server import FastMCP

from magatama_core.application.usecases.comp_usecase import LoadCompIndexUseCase
from magatama_core.application.usecases.framework_usecase import (
    APICompatibilityUseCase,
    CodeContextUseCase,
    CodeEvolutionUseCase,
    CodeNavigationUseCase,
    CodeQualityUseCase,
    CodeRecommendationUseCase,
    # REQ-007, REQ-008, REQ-009, REQ-010
    CodingGuidanceUseCase,
    DependencyImpactUseCase,
    # REQ-001, REQ-002, REQ-003
    DocumentationGenerationUseCase,
    FrameworkKnowledgeUseCase,
    FrameworkSemanticSearchUseCase,
    # REQ-004, REQ-005, REQ-006
    HybridSearchUseCase,
    PatternDetectionUseCase,
    SemanticSearchUseCase,
)
from magatama_core.application.usecases.parse_usecase import (
    ParseDirectoryUseCase,
    ParseFileUseCase,
)
from magatama_core.domain.entities import EntityType
from magatama_core.domain.value_objects import EntityId

# Import all 24 language parsers
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

# Default knowledge graphs directory
DEFAULT_KNOWLEDGE_GRAPHS_DIR = (
    Path(__file__).parent.parent.parent.parent.parent.parent.parent / "knowledge_graphs"
)

# Supported languages configuration (24 languages)
SUPPORTED_LANGUAGES: dict[str, dict[str, Any]] = {
    "python": {"extensions": [".py"], "name": "Python", "parser": "PythonParser"},
    "typescript": {
        "extensions": [".ts", ".tsx"],
        "name": "TypeScript",
        "parser": "TypeScriptParser",
    },
    "javascript": {
        "extensions": [".js", ".jsx"],
        "name": "JavaScript",
        "parser": "JavaScriptParser",
    },
    "rust": {"extensions": [".rs"], "name": "Rust", "parser": "RustParser"},
    "go": {"extensions": [".go"], "name": "Go", "parser": "GoParser"},
    "ruby": {"extensions": [".rb"], "name": "Ruby", "parser": "RubyParser"},
    "java": {"extensions": [".java"], "name": "Java", "parser": "JavaParser"},
    "csharp": {"extensions": [".cs"], "name": "C#", "parser": "CSharpParser"},
    "cpp": {
        "extensions": [".cpp", ".hpp", ".cc", ".hh", ".cxx"],
        "name": "C++",
        "parser": "CppParser",
    },
    "c": {"extensions": [".c", ".h"], "name": "C", "parser": "CParser"},
    "objc": {"extensions": [".m", ".mm"], "name": "Objective-C", "parser": "ObjectiveCParser"},
    "php": {"extensions": [".php"], "name": "PHP", "parser": "PhpParser"},
    "swift": {"extensions": [".swift"], "name": "Swift", "parser": "SwiftParser"},
    "kotlin": {"extensions": [".kt", ".kts"], "name": "Kotlin", "parser": "KotlinParser"},
    "scala": {"extensions": [".scala"], "name": "Scala", "parser": "ScalaParser"},
    "lua": {"extensions": [".lua"], "name": "Lua", "parser": "LuaParser"},
    "haskell": {"extensions": [".hs"], "name": "Haskell", "parser": "HaskellParser"},
    "elixir": {"extensions": [".ex", ".exs"], "name": "Elixir", "parser": "ElixirParser"},
    "julia": {"extensions": [".jl"], "name": "Julia", "parser": "JuliaParser"},
    "sql": {"extensions": [".sql"], "name": "SQL", "parser": "SqlParser"},
    "groovy": {"extensions": [".groovy"], "name": "Groovy", "parser": "GroovyParser"},
    "dart": {"extensions": [".dart"], "name": "Dart", "parser": "DartParser"},
    "zig": {"extensions": [".zig"], "name": "Zig", "parser": "ZigParser"},
    "yaml": {"extensions": [".yaml", ".yml"], "name": "YAML", "parser": "YAMLParser"},
}


def create_mcp_server(name: str = "magatama") -> FastMCP:
    """Create and configure the MCP server.

    This function creates a FastMCP server with all MAGATAMA tools
    and resources registered.

    Args:
        name: Server name for identification

    Returns:
        Configured FastMCP server instance
    """
    mcp = FastMCP(name=name)

    # Initialize knowledge graph
    knowledge_graph = NetworkXKnowledgeGraph()

    # Initialize all 24 language parsers
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

    # Map file extensions to parsers (24 languages, 40+ extensions)
    parsers: dict[str, Any] = {
        # Python
        ".py": python_parser,
        # TypeScript
        ".ts": ts_parser,
        ".tsx": ts_parser,
        # JavaScript
        ".js": js_parser,
        ".jsx": js_parser,
        # Rust
        ".rs": rust_parser,
        # Go
        ".go": go_parser,
        # Ruby
        ".rb": ruby_parser,
        # Java
        ".java": java_parser,
        # C#
        ".cs": csharp_parser,
        # C++
        ".cpp": cpp_parser,
        ".hpp": cpp_parser,
        ".cc": cpp_parser,
        ".hh": cpp_parser,
        ".cxx": cpp_parser,
        # C
        ".c": c_parser,
        ".h": c_parser,
        # Objective-C
        ".m": objc_parser,
        ".mm": objc_parser,
        # PHP
        ".php": php_parser,
        # Swift
        ".swift": swift_parser,
        # Kotlin
        ".kt": kotlin_parser,
        ".kts": kotlin_parser,
        # Scala
        ".scala": scala_parser,
        # Lua
        ".lua": lua_parser,
        # Haskell
        ".hs": haskell_parser,
        # Elixir
        ".ex": elixir_parser,
        ".exs": elixir_parser,
        # Julia
        ".jl": julia_parser,
        # SQL
        ".sql": sql_parser,
        # Groovy
        ".groovy": groovy_parser,
        # Dart
        ".dart": dart_parser,
        # Zig
        ".zig": zig_parser,
        # YAML
        ".yaml": yaml_parser,
        ".yml": yaml_parser,
    }

    # Initialize use cases
    parse_file_usecase = ParseFileUseCase(
        parsers=parsers,
        knowledge_graph=knowledge_graph,
    )
    parse_directory_usecase = ParseDirectoryUseCase(
        parse_file_usecase=parse_file_usecase,
    )

    # Initialize new use cases for enhanced features
    framework_usecase = FrameworkKnowledgeUseCase(DEFAULT_KNOWLEDGE_GRAPHS_DIR)
    code_context_usecase = CodeContextUseCase(knowledge_graph)
    semantic_search_usecase = SemanticSearchUseCase(knowledge_graph)
    framework_semantic_search = FrameworkSemanticSearchUseCase(DEFAULT_KNOWLEDGE_GRAPHS_DIR)

    # Phase 1 (Sprint 13) use cases
    doc_generation_usecase = DocumentationGenerationUseCase(knowledge_graph)
    code_recommendation_usecase = CodeRecommendationUseCase(
        local_graph=knowledge_graph,
        frameworks_dir=DEFAULT_KNOWLEDGE_GRAPHS_DIR,
    )
    impact_analysis_usecase = DependencyImpactUseCase(knowledge_graph)

    # Phase 2 (Sprint 14) use cases
    hybrid_search_usecase = HybridSearchUseCase(
        local_graph=knowledge_graph,
        frameworks_dir=DEFAULT_KNOWLEDGE_GRAPHS_DIR,
    )
    quality_analysis_usecase = CodeQualityUseCase(knowledge_graph)
    evolution_tracking_usecase = CodeEvolutionUseCase(knowledge_graph)

    # Phase 3 (Sprint 15) use cases
    coding_guidance_usecase = CodingGuidanceUseCase(knowledge_graph)
    pattern_detection_usecase = PatternDetectionUseCase(knowledge_graph)
    api_compatibility_usecase = APICompatibilityUseCase(
        knowledge_graph=knowledge_graph,
        frameworks_dir=DEFAULT_KNOWLEDGE_GRAPHS_DIR,
    )
    navigation_usecase = CodeNavigationUseCase(knowledge_graph)

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
        filtered = [e for e in all_entities if query_lower in e.name.lower()]

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

    @mcp.tool()
    def list_supported_languages() -> dict[str, Any]:
        """List all supported programming languages for code parsing.

        Returns information about all 24 supported languages including
        file extensions and parser availability.

        Returns:
            List of supported languages with their extensions
        """
        languages = []
        for lang_id, info in SUPPORTED_LANGUAGES.items():
            languages.append(
                {
                    "id": lang_id,
                    "name": info["name"],
                    "extensions": info["extensions"],
                    "parser": info["parser"],
                }
            )

        # Count total extensions
        total_extensions = sum(len(info["extensions"]) for info in SUPPORTED_LANGUAGES.values())

        return {
            "languages": languages,
            "total_languages": len(languages),
            "total_extensions": total_extensions,
        }

    @mcp.tool()
    def get_language_for_file(file_path: str) -> dict[str, Any]:
        """Get the programming language for a specific file based on its extension.

        Args:
            file_path: Path to the file

        Returns:
            Language information or error if unsupported
        """
        path = Path(file_path)
        ext = path.suffix.lower()

        for lang_id, info in SUPPORTED_LANGUAGES.items():
            if ext in info["extensions"]:
                return {
                    "supported": True,
                    "language": {
                        "id": lang_id,
                        "name": info["name"],
                        "extension": ext,
                        "parser": info["parser"],
                    },
                }

        return {
            "supported": False,
            "extension": ext,
            "error": f"Unsupported file extension: {ext}",
            "supported_extensions": [
                ext for info in SUPPORTED_LANGUAGES.values() for ext in info["extensions"]
            ],
        }

    # Register resources

    @mcp.resource("magatama://graph/stats")
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
            prompt_parts.extend(
                [
                    "",
                    "## Parse Errors",
                    *[f"- {e}" for e in result.errors[:5]],
                ]
            )

        prompt_parts.extend(
            [
                "",
                "## Analysis Tasks",
                "Please analyze this codebase structure and provide:",
                "1. Overall architecture assessment",
                "2. Key modules and their responsibilities",
                "3. Potential areas for refactoring",
                "4. Code organization recommendations",
            ]
        )

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
        matches = [e for e in all_entities if query_lower in e.name.lower()]

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
            prompt_parts.extend(
                [
                    "",
                    "## Documentation",
                    "```",
                    entity.docstring,
                    "```",
                ]
            )

        if neighbors:
            prompt_parts.extend(
                [
                    "",
                    "## Related Entities",
                    *[f"- {n.name} ({n.type.value})" for n in neighbors[:10]],
                ]
            )

        prompt_parts.extend(
            [
                "",
                "## Request",
                f"Please provide a detailed explanation of the `{entity.name}` {entity.type.value}.",
                "Include its purpose, how it works, and how it relates to other parts of the codebase.",
            ]
        )

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
        matches = [e for e in all_entities if query_lower in e.name.lower()]

        if not matches:
            return f"No entity found matching '{entity_name}'. Please parse the codebase first."

        entity = matches[0]
        for e in matches:
            if e.name.lower() == query_lower:
                entity = e
                break

        # Find outgoing and incoming relationships
        outgoing = [r for r in all_relationships if r.source_id == entity.id]
        incoming = [r for r in all_relationships if r.target_id == entity.id]

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

        prompt_parts.extend(
            [
                "",
                "## Incoming Dependencies (what uses this entity)",
            ]
        )

        if incoming:
            for rel in incoming[:15]:
                source = knowledge_graph.entities.get(rel.source_id)
                if source:
                    prompt_parts.append(f"- {source.name} ({source.type.value}) → {rel.type.value}")
        else:
            prompt_parts.append("- None found")

        prompt_parts.extend(
            [
                "",
                "## Analysis Request",
                "Based on the dependency information above, please analyze:",
                "1. What are the key dependencies of this entity?",
                "2. Is this entity tightly coupled or loosely coupled?",
                "3. Are there any circular dependency risks?",
                "4. Suggestions for improving the dependency structure",
            ]
        )

        return "\n".join(prompt_parts)

    # ============================================================
    # NEW TOOLS: Framework Knowledge, Semantic Search, Code Context
    # ============================================================

    @mcp.tool()
    def list_frameworks() -> dict[str, Any]:
        """List all available framework knowledge graphs.

        Returns information about pre-analyzed frameworks including
        React, Angular, Vue, Django, Flask, Rails, and more.

        Returns:
            List of available frameworks with entity counts
        """
        frameworks = framework_usecase.list_frameworks()
        return {
            "frameworks": [
                {
                    "name": fw.name,
                    "entities_count": fw.entities_count,
                    "relationships_count": fw.relationships_count,
                    "entity_types": fw.entity_types,
                }
                for fw in frameworks
            ],
            "total_count": len(frameworks),
        }

    @mcp.tool()
    def search_framework_docs(
        framework: str,
        query: str,
        entity_type: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Search for code patterns and entities in a framework's knowledge graph.

        Use this to find how specific patterns are implemented in frameworks.
        For example, search for "Router" in "react" to find routing implementations.

        Args:
            framework: Framework name (e.g., "react", "django", "rails")
            query: Search query (matches entity names)
            entity_type: Filter by type (function, class, method, etc.)
            limit: Maximum results

        Returns:
            Matching entities from the framework
        """
        type_filter = None
        if entity_type:
            try:
                type_filter = EntityType(entity_type)
            except ValueError:
                pass

        result = framework_usecase.search_framework(framework, query, type_filter, limit)
        return {
            "framework": result.framework,
            "query": result.query,
            "entities": result.entities,
            "total_count": result.total_count,
        }

    @mcp.tool()
    def search_all_frameworks(
        query: str,
        entity_type: str | None = None,
        limit_per_framework: int = 5,
    ) -> dict[str, Any]:
        """Search for patterns across ALL framework knowledge graphs.

        Useful for comparing how different frameworks implement similar patterns.
        For example, search for "middleware" to see implementations across
        Express, Django, Rails, etc.

        Args:
            query: Search query
            entity_type: Filter by type
            limit_per_framework: Max results per framework

        Returns:
            Results grouped by framework
        """
        type_filter = None
        if entity_type:
            try:
                type_filter = EntityType(entity_type)
            except ValueError:
                pass

        results = framework_usecase.search_all_frameworks(query, type_filter, limit_per_framework)

        return {
            "query": query,
            "frameworks_matched": len(results),
            "results": {
                fw: {
                    "entities": r.entities,
                    "total_count": r.total_count,
                }
                for fw, r in results.items()
            },
        }

    @mcp.tool()
    def find_code_patterns(
        pattern: str,
        entity_type: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Find similar code patterns across all frameworks.

        Identifies common patterns like Controller, Service, Repository,
        Middleware, Router, Handler, etc. across different frameworks.

        Args:
            pattern: Pattern to search for (e.g., "Controller", "Service")
            entity_type: Filter by type
            limit: Maximum results

        Returns:
            Examples of the pattern from various frameworks
        """
        type_filter = None
        if entity_type:
            try:
                type_filter = EntityType(entity_type)
            except ValueError:
                pass

        result = framework_usecase.find_similar_patterns(pattern, type_filter, limit)

        return {
            "pattern": result.pattern_name,
            "examples": result.examples,
            "frameworks": result.frameworks,
            "total_count": result.total_count,
        }

    @mcp.tool()
    def get_framework_entity_context(
        framework: str,
        entity_id: str,
        depth: int = 2,
    ) -> dict[str, Any]:
        """Get detailed context for an entity in a framework.

        Retrieves the entity along with its relationships and related entities,
        providing full context for understanding how it works.

        Args:
            framework: Framework name
            entity_id: Entity ID to get context for
            depth: How many relationship hops to include

        Returns:
            Entity with full context including relationships
        """
        return framework_usecase.get_entity_context(framework, entity_id, depth)

    @mcp.tool()
    def semantic_search(
        query: str,
        entity_types: list[str] | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Perform semantic search across the local knowledge graph.

        Searches entity names, docstrings, and file paths with relevance scoring.
        More intelligent than simple string matching.

        Args:
            query: Search query (natural language)
            entity_types: Filter by types (e.g., ["function", "class"])
            limit: Maximum results

        Returns:
            Matching entities with relevance scores
        """
        type_filters = None
        if entity_types:
            type_filters = []
            for t in entity_types:
                try:
                    type_filters.append(EntityType(t))
                except ValueError:
                    pass

        results = semantic_search_usecase.search(query, type_filters, limit)
        return {
            "query": query,
            "results": results,
            "total_count": len(results),
        }

    @mcp.tool()
    def find_by_pattern(
        pattern: str,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Find entities matching a naming pattern in local codebase.

        Supports wildcard patterns:
        - "*Controller" finds UserController, AuthController, etc.
        - "get*" finds getUser, getData, etc.
        - "*Service" finds AuthService, UserService, etc.

        Args:
            pattern: Pattern with * wildcard
            limit: Maximum results

        Returns:
            Matching entities
        """
        results = semantic_search_usecase.find_by_pattern(pattern, limit)
        return {
            "pattern": pattern,
            "results": results,
            "total_count": len(results),
        }

    @mcp.tool()
    def get_code_context(
        entity_id: str,
        include_source: bool = False,
        max_related: int = 10,
    ) -> dict[str, Any]:
        """Get comprehensive code context for an entity.

        Provides detailed context including what the entity calls,
        what calls it, imports, and containment relationships.
        Essential for understanding how code fits together.

        Args:
            entity_id: Entity ID to get context for
            include_source: Include source code snippet
            max_related: Maximum related entities per category

        Returns:
            Entity with categorized relationships and context
        """
        return code_context_usecase.generate_context(entity_id, include_source, max_related)

    @mcp.tool()
    def find_usage_examples(
        entity_name: str,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Find usage examples of an entity in the codebase.

        Shows where and how an entity is used, helping understand
        correct usage patterns.

        Args:
            entity_name: Name of entity to find usages for
            limit: Maximum examples

        Returns:
            List of usage examples with caller information
        """
        examples = code_context_usecase.find_usage_examples(entity_name, limit)
        return {
            "entity_name": entity_name,
            "examples": examples,
            "total_count": len(examples),
        }

    @mcp.tool()
    def framework_semantic_search_tool(
        query: str,
        frameworks: list[str] | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Perform semantic search across framework knowledge graphs.

        Searches entity names, docstrings, and file paths with relevance scoring
        across all 25+ pre-built framework knowledge graphs.

        Args:
            query: Search query (natural language)
            frameworks: Limit to specific frameworks (None = all)
            limit: Maximum results

        Returns:
            Matching entities with relevance scores, sorted by relevance
        """
        results = framework_semantic_search.search(query, frameworks, limit)
        return {
            "query": query,
            "results": results.results,
            "total_count": results.total_count,
            "relevance_distribution": results.relevance_distribution,
        }

    @mcp.tool()
    def framework_find_by_pattern(
        pattern: str,
        frameworks: list[str] | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Find entities matching a naming pattern across frameworks.

        Supports wildcard patterns:
        - "*Controller" finds UserController, AuthController, etc.
        - "get*" finds getUser, getData, etc.
        - "*Service" finds AuthService, UserService, etc.

        Args:
            pattern: Pattern with * wildcard
            frameworks: Limit to specific frameworks (None = all)
            limit: Maximum results

        Returns:
            Matching entities across frameworks
        """
        results = framework_semantic_search.find_by_pattern(pattern, frameworks, limit)
        return {
            "pattern": results.pattern,
            "matches": results.matches,
            "total_count": results.total_count,
        }

    # =========================================================================
    # Phase 1 (Sprint 13) Tools - REQ-001, REQ-002, REQ-003
    # =========================================================================

    @mcp.tool()
    def generate_documentation(
        entity_name: str,
        format: str = "markdown",
        include_examples: bool = True,
        include_related: bool = True,
    ) -> dict[str, Any]:
        """Generate intelligent documentation for a code entity.

        Analyzes entity structure, relationships, and usage patterns to
        generate comprehensive documentation in multiple formats.

        Supported formats: markdown, jsdoc, google, numpy, sphinx

        Args:
            entity_name: Name of the entity to document
            format: Output format (default: markdown)
            include_examples: Include usage examples (default: True)
            include_related: Include related entities (default: True)

        Returns:
            Generated documentation with metadata
        """
        result = doc_generation_usecase.generate_documentation(
            entity_name=entity_name,
            format=format,
            include_examples=include_examples,
            include_related=include_related,
        )
        return {
            "entity_name": result.entity_name,
            "entity_type": result.entity_type,
            "documentation": result.documentation,
            "format": result.format,
            "related_entities": result.related_entities,
            "source_file": result.source_file,
            "generated_at": result.generated_at,
        }

    @mcp.tool()
    def recommend_code(
        query: str,
        include_frameworks: bool = True,
        include_local: bool = True,
        limit: int = 10,
        min_relevance: float = 0.3,
    ) -> dict[str, Any]:
        """Recommend code snippets based on a query.

        Combines local codebase and framework knowledge to provide
        contextually relevant code recommendations with relevance scoring.

        Relevance formula: name_match*0.4 + docstring*0.3 + context*0.2 + usage*0.1

        Args:
            query: Natural language or technical query
            include_frameworks: Include framework knowledge (default: True)
            include_local: Include local codebase (default: True)
            limit: Maximum results (max 50)
            min_relevance: Minimum relevance score 0.0-1.0 (default: 0.3)

        Returns:
            Recommended code snippets with relevance scores
        """
        result = code_recommendation_usecase.recommend_code(
            query=query,
            include_frameworks=include_frameworks,
            include_local=include_local,
            limit=limit,
            min_relevance=min_relevance,
        )
        return {
            "query": result.query,
            "snippets": result.snippets,
            "total_count": result.total_count,
            "source_breakdown": result.source_breakdown,
        }

    @mcp.tool()
    def analyze_impact(
        entity_name: str,
        depth: int = 3,
    ) -> dict[str, Any]:
        """Analyze the impact of changes to an entity.

        Identifies all entities that depend on the target entity,
        both directly and indirectly, to assess change risk.

        Impact formula: direct*1.0 + sum(indirect[d] * 0.5^d)

        Risk levels:
        - high: impact >= 10 or affected >= 20
        - medium: impact >= 5 or affected >= 10
        - low: otherwise

        Args:
            entity_name: Name of the entity to analyze
            depth: Analysis depth 1-10 (default: 3)

        Returns:
            Impact analysis with dependents and risk assessment
        """
        result = impact_analysis_usecase.analyze_impact(
            entity_name=entity_name,
            depth=depth,
        )
        return {
            "entity_name": result.entity_name,
            "direct_dependents": result.direct_dependents,
            "indirect_dependents": result.indirect_dependents,
            "impact_score": result.impact_score,
            "total_affected": result.total_affected,
            "depth_analyzed": result.depth_analyzed,
            "risk_level": result.risk_level,
        }

    @mcp.tool()
    def find_critical_paths(
        entity_name: str,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Find critical dependency paths from an entity.

        Identifies the most important dependency chains that could be
        affected by changes to the target entity.

        Args:
            entity_name: Starting entity name
            limit: Maximum paths to return (default: 10)

        Returns:
            List of dependency paths
        """
        paths = impact_analysis_usecase.find_critical_paths(
            entity_name=entity_name,
            limit=limit,
        )
        return {
            "entity_name": entity_name,
            "critical_paths": paths,
            "path_count": len(paths),
        }

    # ========================================
    # Phase 2 (Sprint 14) MCP Tools
    # REQ-004, REQ-005, REQ-006
    # ========================================

    @mcp.tool()
    def hybrid_search(
        query: str,
        local_weight: float = 0.5,
        frameworks: list[str] | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Perform hybrid search combining local codebase and framework knowledge.

        Merges results from local knowledge graph and framework graphs
        using configurable weighting. Useful for finding code patterns
        across both project-specific and library implementations.

        Weighting formula:
        - final_score = local_score * local_weight + framework_score * (1 - local_weight)

        Args:
            query: Search query (natural language or technical terms)
            local_weight: Weight for local results 0.0-1.0 (default: 0.5)
            frameworks: Specific frameworks to search (None = all available)
            limit: Maximum results to return (default: 20, max: 100)

        Returns:
            Merged search results with source attribution and scores
        """
        results = hybrid_search_usecase.hybrid_search(
            query=query,
            local_weight=local_weight,
            frameworks=frameworks or [],
            limit=limit,
        )
        return {
            "query": results.query,
            "results": [
                {
                    "entity_name": r.get("entity_name") or r.get("name"),
                    "entity_type": r.get("entity_type") or r.get("type"),
                    "source": r.get("source"),
                    "score": r.get("score", r.get("weighted_score", r.get("relevance_score"))),
                    "file_path": r.get("file_path") or r.get("file"),
                    "docstring": r.get("docstring"),
                }
                for r in results.results
            ],
            "total_count": results.total_count,
            "local_count": results.source_breakdown.get("local", 0),
            "framework_count": results.source_breakdown.get("framework", 0),
            "frameworks_searched": results.detected_frameworks,
        }

    @mcp.tool()
    def analyze_quality(
        entity_name: str,
    ) -> dict[str, Any]:
        """Analyze code quality metrics for an entity.

        Computes various quality metrics including:
        - Cyclomatic complexity: Number of independent paths
        - Coupling: Number of external dependencies
        - Cohesion: Internal relatedness of methods/attributes
        - Method lines: Average lines per method
        - Parameter count: Average parameters per method

        Provides recommendations based on industry best practices.

        Args:
            entity_name: Name of the class, function, or module to analyze

        Returns:
            Quality metrics with scores and improvement recommendations
        """
        result = quality_analysis_usecase.analyze_quality(entity_name)
        return {
            "entity_name": result.entity_name,
            "entity_type": result.entity_type,
            "metrics": [
                {
                    "name": m.name,
                    "value": m.value,
                    "threshold_good": m.threshold_good,
                    "threshold_warning": m.threshold_warning,
                    "status": m.status,
                    "description": m.description,
                }
                for m in result.metrics
            ],
            "overall_score": result.overall_score,
            "overall_status": result.overall_status,
            "recommendations": result.recommendations,
        }

    @mcp.tool()
    def track_evolution(
        entity_name: str,
        since: str | None = None,
        until: str | None = None,
        include_blame: bool = False,
    ) -> dict[str, Any]:
        """Track the evolution history of an entity from Git.

        Analyzes Git history to show how an entity has changed over time,
        including commits, authors, and change frequency.

        Requires GitPython and must be run in a Git repository.

        Args:
            entity_name: Name of the entity to track
            since: Start date (ISO format, e.g., "2024-01-01")
            until: End date (ISO format, e.g., "2024-12-31")
            include_blame: Include line-by-line author attribution

        Returns:
            Evolution history with commits, authors, and change frequency
        """
        result = evolution_tracking_usecase.track_evolution(
            entity_name=entity_name,
            since=since,
            until=until,
            include_blame=include_blame,
        )
        return {
            "entity_name": result.entity_name,
            "file_path": result.entity_file,
            "events": [
                {
                    "commit_hash": e.commit_hash,
                    "author": e.author,
                    "date": e.date,
                    "message": e.message,
                    "lines_changed": e.lines_changed,
                }
                for e in result.events
            ],
            "total_commits": result.total_changes,
            "unique_authors": result.unique_authors,
            "hotspot_score": result.hotspot_score,
            "is_hotspot": result.is_hotspot,
            "timeline": result.timeline_data,
        }

    @mcp.tool()
    def find_hotspots(
        limit: int = 10,
    ) -> dict[str, Any]:
        """Find code hotspots based on change frequency and complexity.

        Identifies files and entities that are changed frequently,
        which often indicates areas that need refactoring or have high bug risk.

        Hotspot score formula:
        - hotspot_score = change_frequency * complexity_factor

        Args:
            limit: Maximum hotspots to return (default: 10)

        Returns:
            List of hotspots with change frequency and complexity scores
        """
        hotspots = evolution_tracking_usecase.find_hotspots(limit=limit)
        return {
            "hotspots": hotspots,
            "count": len(hotspots),
        }

    # ========================================
    # Phase 3 (Sprint 15) MCP Tools
    # REQ-007, REQ-008, REQ-009, REQ-010
    # ========================================

    @mcp.tool()
    def get_coding_guidance(
        task: str,
        entity_type: str = "class",
        similar_to: str | None = None,
    ) -> dict[str, Any]:
        """Get AI-powered coding guidance for a development task.

        Analyzes project patterns to provide guidance including:
        - Naming conventions (snake_case, camelCase, PascalCase)
        - Code templates based on similar entities
        - Directory placement suggestions
        - Import suggestions

        Args:
            task: Description of what to create (e.g., "user authentication service")
            entity_type: Type of entity to create (class, function, method, module)
            similar_to: Reference entity name to base patterns on (optional)

        Returns:
            Coding guidance with patterns, templates, and suggestions
        """
        result = coding_guidance_usecase.get_guidance(
            task=task,
            entity_type=entity_type,
            similar_to=similar_to,
        )
        return {
            "task": result.task,
            "entity_type": result.entity_type,
            "naming_convention": result.naming_convention,
            "suggested_name": result.suggested_name,
            "template": result.template,
            "similar_entities": result.similar_entities,
            "import_suggestions": result.import_suggestions,
            "directory_suggestion": result.directory_suggestion,
            "confidence": result.confidence,
        }

    @mcp.tool()
    def detect_patterns(
        limit: int = 20,
        min_confidence: float = 0.5,
    ) -> dict[str, Any]:
        """Detect design patterns in the codebase.

        Identifies 10 common design patterns:
        - Creational: Singleton, Factory Method, Builder
        - Structural: Adapter, Decorator, Facade
        - Behavioral: Observer, Strategy, Command, Template Method

        Args:
            limit: Maximum patterns to return (default: 20)
            min_confidence: Minimum confidence threshold 0.0-1.0 (default: 0.5)

        Returns:
            Detected patterns with locations and confidence scores
        """
        result = pattern_detection_usecase.detect_patterns(
            limit=limit,
            min_confidence=min_confidence,
        )
        return {
            "patterns": [
                {
                    "pattern_name": p.pattern_name,
                    "category": p.category,
                    "entities": p.entities,
                    "confidence": p.confidence,
                    "description": p.description,
                    "suggestions": p.suggestions,
                }
                for p in result.patterns
            ],
            "total_patterns": result.total_patterns,
            "coverage": result.coverage,
        }

    @mcp.tool()
    def check_api_compatibility(
        framework: str,
        target_version: str,
    ) -> dict[str, Any]:
        """Check API compatibility against a framework version.

        Scans local code for usage of deprecated, removed, or changed APIs
        when upgrading to a new framework version.

        Supported frameworks: django, fastapi, react, flask

        Args:
            framework: Framework name (django, fastapi, react, flask)
            target_version: Target version to check against (e.g., "4.2")

        Returns:
            Compatibility issues with migration hints
        """
        result = api_compatibility_usecase.check_compatibility(
            framework=framework,
            target_version=target_version,
        )
        return {
            "framework": result.framework,
            "target_version": result.target_version,
            "current_usage_count": result.current_usage_count,
            "issues": [
                {
                    "entity_name": i.entity_name,
                    "file": i.file,
                    "line": i.line,
                    "api_used": i.api_used,
                    "issue_type": i.issue_type,
                    "message": i.message,
                    "migration_hint": i.migration_hint,
                }
                for i in result.issues
            ],
            "compatible": result.compatible,
            "compatibility_score": result.compatibility_score,
        }

    @mcp.tool()
    def navigate_code(
        entity_name: str,
        direction: str = "both",
        depth: int = 2,
    ) -> dict[str, Any]:
        """Navigate code relationships interactively.

        Explores code dependencies from a starting entity:
        - callers: Find what calls this entity
        - callees: Find what this entity calls
        - both: Explore in both directions

        Args:
            entity_name: Starting entity name
            direction: Navigation direction (callers, callees, both)
            depth: Maximum depth to explore (default: 2)

        Returns:
            Navigation graph with nodes and edges
        """
        result = navigation_usecase.navigate_from(
            entity_name=entity_name,
            direction=direction,
            depth=depth,
        )
        return {
            "root_entity": result.root_entity,
            "direction": result.direction,
            "nodes": [
                {
                    "name": n.name,
                    "type": n.type,
                    "file": n.file,
                    "line": n.line,
                    "depth": n.depth,
                    "relationship": n.relationship,
                }
                for n in result.nodes
            ],
            "edges": result.edges,
            "max_depth": result.max_depth,
            "total_nodes": result.total_nodes,
        }

    @mcp.tool()
    def get_call_graph(
        entity_name: str,
        depth: int = 3,
    ) -> dict[str, Any]:
        """Get call graph data for visualization.

        Returns graph data in D3-compatible format for visual rendering
        of code dependencies and call relationships.

        Args:
            entity_name: Center entity name
            depth: Depth to explore (default: 3)

        Returns:
            Graph data with nodes and links for visualization
        """
        return navigation_usecase.get_call_graph(
            entity_name=entity_name,
            depth=depth,
        )

    # ===== External Index Tools (comP Bridge) =====

    load_comp_index_usecase = LoadCompIndexUseCase(knowledge_graph=knowledge_graph)

    @mcp.tool()
    def read_external_graph(path: str, mode: str = "replace") -> dict[str, Any]:
        """Load an external comP index (.comp/index.db) into MAGATAMA's knowledge graph.

        comP (https://github.com/tsucky230/comP) is a VSCode-based code indexer.
        This tool imports its SQLite index so that all MAGATAMA tools
        (search_entities, get_related_entities, analyze_impact, etc.)
        can answer questions about the indexed project without re-parsing.

        Args:
            path: Workspace root containing .comp/index.db, the .comp directory,
                  or a direct path to the .db file.
            mode: "replace" (default) removes previously loaded entities from the
                  same workspace before loading; "merge" adds on top.

        Returns:
            Load statistics: entities_loaded, relationships_loaded, alias, etc.
        """
        result = load_comp_index_usecase.execute(path, mode=mode)
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

    @mcp.tool()
    def get_external_graph_info(path: str) -> dict[str, Any]:
        """Inspect a comP index (.comp/index.db) without loading it.

        Returns file/node/edge counts and comP metadata. Use this to check
        whether an index exists and how fresh it is before calling
        read_external_graph.
        """
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

    return mcp


def run_stdio_server() -> None:
    """Run the MCP server with stdio transport.

    This is the main entry point for running MAGATAMA as an MCP server
    that communicates via standard input/output.
    """
    mcp = create_mcp_server()
    mcp.run(transport="stdio")
