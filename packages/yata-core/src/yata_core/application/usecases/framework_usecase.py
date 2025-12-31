"""Framework Knowledge Graph Use Cases.

This module provides use cases for querying framework knowledge graphs,
enabling AI coding assistants to provide framework-specific guidance.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json

from yata_core.domain.entities import Entity, EntityType
from yata_core.domain.value_objects import EntityId
from yata_core.infrastructure.storage import NetworkXKnowledgeGraph


@dataclass
class FrameworkInfo:
    """Information about a framework."""
    
    name: str
    entities_count: int
    relationships_count: int
    entity_types: dict[str, int]
    graph_path: Path | None = None


@dataclass
class FrameworkSearchResult:
    """Result from framework documentation search."""
    
    framework: str
    entities: list[dict[str, Any]]
    total_count: int
    query: str


@dataclass
class CodePatternResult:
    """Result from code pattern search."""
    
    pattern_name: str
    examples: list[dict[str, Any]]
    frameworks: list[str]
    total_count: int


class FrameworkKnowledgeUseCase:
    """Use case for querying framework knowledge graphs.
    
    This use case enables:
    - Loading and querying pre-built framework knowledge graphs
    - Searching for patterns across frameworks
    - Getting framework-specific code examples and structures
    """
    
    def __init__(self, knowledge_graphs_dir: Path) -> None:
        """Initialize the use case.
        
        Args:
            knowledge_graphs_dir: Directory containing framework JSON files
        """
        self._graphs_dir = knowledge_graphs_dir
        self._loaded_graphs: dict[str, NetworkXKnowledgeGraph] = {}
        self._framework_info: dict[str, FrameworkInfo] = {}
        self._load_summary()
    
    def _load_summary(self) -> None:
        """Load summary information about available frameworks."""
        summary_path = self._graphs_dir / "summary.json"
        if summary_path.exists():
            with open(summary_path, "r") as f:
                data = json.load(f)
                frameworks_data = data.get("frameworks", [])
                
                # Handle both list and dict formats
                if isinstance(frameworks_data, list):
                    # List format from analyze_frameworks.py
                    for fw_data in frameworks_data:
                        fw_name = fw_data.get("name", "").lower().replace(" ", "-")
                        self._framework_info[fw_name] = FrameworkInfo(
                            name=fw_name,
                            entities_count=fw_data.get("entities", 0),
                            relationships_count=fw_data.get("relationships", 0),
                            entity_types=fw_data.get("entity_types", {}),
                            graph_path=Path(fw_data.get("graph_file", "")) if fw_data.get("graph_file") else None,
                        )
                elif isinstance(frameworks_data, dict):
                    # Dict format
                    for fw_name, fw_data in frameworks_data.items():
                        self._framework_info[fw_name] = FrameworkInfo(
                            name=fw_name,
                            entities_count=fw_data.get("entities", 0),
                            relationships_count=fw_data.get("relationships", 0),
                            entity_types=fw_data.get("entity_types", {}),
                            graph_path=self._graphs_dir / f"{fw_name}.json",
                        )
    
    def _load_graph(self, framework: str) -> NetworkXKnowledgeGraph | None:
        """Load a framework's knowledge graph.
        
        Args:
            framework: Framework name
            
        Returns:
            Loaded knowledge graph or None if not found
        """
        if framework in self._loaded_graphs:
            return self._loaded_graphs[framework]
        
        graph_path = self._graphs_dir / f"{framework}.json"
        if not graph_path.exists():
            return None
        
        graph = NetworkXKnowledgeGraph()
        graph.load(graph_path)
        self._loaded_graphs[framework] = graph
        return graph
    
    def list_frameworks(self) -> list[FrameworkInfo]:
        """List all available frameworks.
        
        Returns:
            List of framework information
        """
        # Also scan for JSON files not in summary
        for json_file in self._graphs_dir.glob("*.json"):
            if json_file.name == "summary.json":
                continue
            fw_name = json_file.stem
            if fw_name not in self._framework_info:
                # Load basic info
                graph = self._load_graph(fw_name)
                if graph:
                    entities = list(graph.entities.all())
                    relationships = list(graph.relationships.all())
                    type_counts: dict[str, int] = {}
                    for e in entities:
                        type_counts[e.type.value] = type_counts.get(e.type.value, 0) + 1
                    self._framework_info[fw_name] = FrameworkInfo(
                        name=fw_name,
                        entities_count=len(entities),
                        relationships_count=len(relationships),
                        entity_types=type_counts,
                        graph_path=json_file,
                    )
        
        return list(self._framework_info.values())
    
    def get_framework_info(self, framework: str) -> FrameworkInfo | None:
        """Get information about a specific framework.
        
        Args:
            framework: Framework name
            
        Returns:
            Framework information or None if not found
        """
        return self._framework_info.get(framework)
    
    def search_framework(
        self,
        framework: str,
        query: str,
        entity_type: EntityType | None = None,
        limit: int = 20,
    ) -> FrameworkSearchResult:
        """Search for entities in a framework's knowledge graph.
        
        Args:
            framework: Framework name
            query: Search query (matches entity names)
            entity_type: Filter by entity type
            limit: Maximum results
            
        Returns:
            Search results
        """
        graph = self._load_graph(framework)
        if not graph:
            return FrameworkSearchResult(
                framework=framework,
                entities=[],
                total_count=0,
                query=query,
            )
        
        all_entities = list(graph.entities.all())
        query_lower = query.lower()
        
        # Filter by query
        filtered = [
            e for e in all_entities
            if query_lower in e.name.lower()
        ]
        
        # Filter by type
        if entity_type:
            filtered = [e for e in filtered if e.type == entity_type]
        
        # Sort by relevance (exact match first, then by name length)
        def sort_key(e: Entity) -> tuple[int, int]:
            exact = 0 if e.name.lower() == query_lower else 1
            return (exact, len(e.name))
        
        filtered.sort(key=sort_key)
        total = len(filtered)
        filtered = filtered[:limit]
        
        return FrameworkSearchResult(
            framework=framework,
            entities=[
                {
                    "id": e.id.value,
                    "name": e.name,
                    "type": e.type.value,
                    "file": e.location.file,
                    "line": e.location.line,
                    "docstring": e.docstring[:200] if e.docstring else None,
                }
                for e in filtered
            ],
            total_count=total,
            query=query,
        )
    
    def search_all_frameworks(
        self,
        query: str,
        entity_type: EntityType | None = None,
        limit_per_framework: int = 5,
    ) -> dict[str, FrameworkSearchResult]:
        """Search for entities across all frameworks.
        
        Args:
            query: Search query
            entity_type: Filter by entity type
            limit_per_framework: Max results per framework
            
        Returns:
            Dict of framework name to search results
        """
        results: dict[str, FrameworkSearchResult] = {}
        
        for fw_name in self._framework_info:
            result = self.search_framework(
                fw_name, query, entity_type, limit_per_framework
            )
            if result.entities:
                results[fw_name] = result
        
        return results
    
    def find_similar_patterns(
        self,
        pattern_name: str,
        entity_type: EntityType | None = None,
        limit: int = 20,
    ) -> CodePatternResult:
        """Find similar code patterns across frameworks.
        
        This helps identify common patterns like:
        - Component, Controller, Service, Repository patterns
        - Middleware, Router, Handler patterns
        - Model, Schema, Entity patterns
        
        Args:
            pattern_name: Pattern to search for (e.g., "Controller", "Service")
            entity_type: Filter by entity type
            limit: Maximum total results
            
        Returns:
            Matching patterns across frameworks
        """
        examples: list[dict[str, Any]] = []
        frameworks_found: set[str] = set()
        
        for fw_name in self._framework_info:
            graph = self._load_graph(fw_name)
            if not graph:
                continue
            
            pattern_lower = pattern_name.lower()
            for entity in graph.entities.all():
                if pattern_lower in entity.name.lower():
                    if entity_type and entity.type != entity_type:
                        continue
                    
                    examples.append({
                        "framework": fw_name,
                        "name": entity.name,
                        "type": entity.type.value,
                        "file": entity.location.file,
                        "docstring": entity.docstring[:200] if entity.docstring else None,
                    })
                    frameworks_found.add(fw_name)
                    
                    if len(examples) >= limit:
                        break
            
            if len(examples) >= limit:
                break
        
        return CodePatternResult(
            pattern_name=pattern_name,
            examples=examples,
            frameworks=list(frameworks_found),
            total_count=len(examples),
        )
    
    def get_entity_context(
        self,
        framework: str,
        entity_id: str,
        depth: int = 2,
    ) -> dict[str, Any]:
        """Get context around an entity including related entities.
        
        Args:
            framework: Framework name
            entity_id: Entity ID
            depth: How many hops to traverse
            
        Returns:
            Entity with related context
        """
        graph = self._load_graph(framework)
        if not graph:
            return {"error": f"Framework '{framework}' not found"}
        
        try:
            eid = EntityId(value=entity_id)
            entity = graph.entities.get(eid)
            if not entity:
                return {"error": f"Entity '{entity_id}' not found"}
            
            neighbors = graph.get_neighbors(eid, depth=depth)
            
            # Get relationships
            all_rels = list(graph.relationships.all())
            outgoing = [r for r in all_rels if r.source_id == eid]
            incoming = [r for r in all_rels if r.target_id == eid]
            
            return {
                "entity": {
                    "id": entity.id.value,
                    "name": entity.name,
                    "type": entity.type.value,
                    "file": entity.location.file,
                    "line": entity.location.line,
                    "docstring": entity.docstring,
                },
                "related_entities": [
                    {
                        "id": e.id.value,
                        "name": e.name,
                        "type": e.type.value,
                    }
                    for e in neighbors[:20]
                ],
                "outgoing_relationships": [
                    {
                        "type": r.type.value,
                        "target": r.target_id.value,
                    }
                    for r in outgoing[:10]
                ],
                "incoming_relationships": [
                    {
                        "type": r.type.value,
                        "source": r.source_id.value,
                    }
                    for r in incoming[:10]
                ],
            }
        except Exception as e:
            return {"error": str(e)}


class CodeContextUseCase:
    """Use case for generating code context for AI assistants.
    
    This helps AI understand the surrounding code structure
    when working with specific entities.
    """
    
    def __init__(self, knowledge_graph: NetworkXKnowledgeGraph) -> None:
        """Initialize the use case.
        
        Args:
            knowledge_graph: Knowledge graph to query
        """
        self._graph = knowledge_graph
    
    def generate_context(
        self,
        entity_id: str,
        include_source: bool = False,
        max_related: int = 10,
    ) -> dict[str, Any]:
        """Generate context for an entity.
        
        Args:
            entity_id: Entity ID
            include_source: Whether to include source file content
            max_related: Maximum related entities
            
        Returns:
            Context information for the entity
        """
        try:
            eid = EntityId(value=entity_id)
            entity = self._graph.entities.get(eid)
            if not entity:
                return {"error": f"Entity '{entity_id}' not found"}
            
            # Get neighbors
            neighbors = self._graph.get_neighbors(eid, depth=1)
            
            # Get all relationships
            all_rels = list(self._graph.relationships.all())
            
            # Categorize relationships
            calls = [r for r in all_rels if r.source_id == eid and r.type.value == "calls"]
            called_by = [r for r in all_rels if r.target_id == eid and r.type.value == "calls"]
            imports = [r for r in all_rels if r.source_id == eid and r.type.value == "imports"]
            contains = [r for r in all_rels if r.source_id == eid and r.type.value == "contains"]
            contained_in = [r for r in all_rels if r.target_id == eid and r.type.value == "contains"]
            
            context: dict[str, Any] = {
                "entity": {
                    "id": entity.id.value,
                    "name": entity.name,
                    "type": entity.type.value,
                    "file": entity.location.file,
                    "line": entity.location.line,
                    "docstring": entity.docstring,
                    "scope": entity.scope,
                },
                "calls": [
                    self._get_entity_brief(r.target_id)
                    for r in calls[:max_related]
                ],
                "called_by": [
                    self._get_entity_brief(r.source_id)
                    for r in called_by[:max_related]
                ],
                "imports": [
                    self._get_entity_brief(r.target_id)
                    for r in imports[:max_related]
                ],
                "contains": [
                    self._get_entity_brief(r.target_id)
                    for r in contains[:max_related]
                ],
                "contained_in": [
                    self._get_entity_brief(r.source_id)
                    for r in contained_in[:max_related]
                ],
            }
            
            # Optionally include source
            if include_source:
                source = self._read_source(entity)
                if source:
                    context["source_snippet"] = source
            
            return context
        except Exception as e:
            return {"error": str(e)}
    
    def _get_entity_brief(self, entity_id: EntityId) -> dict[str, Any] | None:
        """Get brief entity info."""
        entity = self._graph.entities.get(entity_id)
        if entity:
            return {
                "id": entity.id.value,
                "name": entity.name,
                "type": entity.type.value,
            }
        return None
    
    def _read_source(self, entity: Entity, context_lines: int = 10) -> str | None:
        """Read source code around an entity."""
        try:
            file_path = Path(entity.location.file)
            if not file_path.exists():
                return None
            
            with open(file_path, "r") as f:
                lines = f.readlines()
            
            start = max(0, entity.location.line - 1)
            end = min(len(lines), start + context_lines + 20)
            
            return "".join(lines[start:end])
        except Exception:
            return None
    
    def find_usage_examples(
        self,
        entity_name: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Find usage examples of an entity.
        
        Args:
            entity_name: Name to search for
            limit: Maximum examples
            
        Returns:
            List of usage examples
        """
        examples: list[dict[str, Any]] = []
        name_lower = entity_name.lower()
        
        # Find the entity
        target_entity: Entity | None = None
        for entity in self._graph.entities.all():
            if entity.name.lower() == name_lower:
                target_entity = entity
                break
        
        if not target_entity:
            return []
        
        # Find who calls/uses this entity
        all_rels = list(self._graph.relationships.all())
        callers = [r for r in all_rels if r.target_id == target_entity.id]
        
        for rel in callers[:limit]:
            caller = self._graph.entities.get(rel.source_id)
            if caller:
                examples.append({
                    "caller": {
                        "name": caller.name,
                        "type": caller.type.value,
                        "file": caller.location.file,
                        "line": caller.location.line,
                    },
                    "relationship": rel.type.value,
                })
        
        return examples


class SemanticSearchUseCase:
    """Use case for semantic code search on local codebase.
    
    Provides intelligent search capabilities beyond simple string matching.
    Operates on the local project's knowledge graph.
    """
    
    def __init__(self, knowledge_graph: NetworkXKnowledgeGraph) -> None:
        """Initialize the use case.
        
        Args:
            knowledge_graph: Knowledge graph to search
        """
        self._graph = knowledge_graph
    
    def search(
        self,
        query: str,
        entity_types: list[EntityType] | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Perform semantic search on local knowledge graph.
        
        Args:
            query: Search query
            entity_types: Filter by entity types
            limit: Maximum results
            
        Returns:
            Matching entities with relevance scores
        """
        results: list[tuple[float, Entity]] = []
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        for entity in self._graph.entities.all():
            if entity_types and entity.type not in entity_types:
                continue
            
            score = self._calculate_relevance(entity, query_lower, query_words)
            if score > 0:
                results.append((score, entity))
        
        results.sort(key=lambda x: x[0], reverse=True)
        results = results[:limit]
        
        return [
            {
                "id": e.id.value,
                "name": e.name,
                "type": e.type.value,
                "file": e.location.file,
                "line": e.location.line,
                "docstring": e.docstring[:200] if e.docstring else None,
                "relevance_score": round(score, 3),
            }
            for score, e in results
        ]
    
    def _calculate_relevance(
        self,
        entity: Entity,
        query_lower: str,
        query_words: set[str],
    ) -> float:
        """Calculate relevance score for an entity."""
        score = 0.0
        name_lower = entity.name.lower()
        
        if name_lower == query_lower:
            score += 10.0
        elif query_lower in name_lower:
            score += 5.0
        elif name_lower in query_lower:
            score += 3.0
        
        name_words = set(self._split_identifier(name_lower))
        word_overlap = len(query_words & name_words)
        score += word_overlap * 2.0
        
        if entity.docstring:
            doc_lower = entity.docstring.lower()
            if query_lower in doc_lower:
                score += 2.0
            doc_word_overlap = len(query_words & set(doc_lower.split()))
            score += doc_word_overlap * 0.5
        
        if query_lower in entity.location.file.lower():
            score += 1.0
        
        return score
    
    def _split_identifier(self, name: str) -> list[str]:
        """Split an identifier into words."""
        import re
        parts = name.split("_")
        words = []
        for part in parts:
            words.extend(re.findall(r'[a-z]+|[A-Z][a-z]*', part))
        return [w.lower() for w in words if w]
    
    def find_by_pattern(
        self,
        pattern: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Find entities matching a naming pattern.
        
        Args:
            pattern: Pattern with * wildcard
            limit: Maximum results
            
        Returns:
            Matching entities
        """
        import re
        
        regex_pattern = pattern.replace("*", ".*")
        regex = re.compile(f"^{regex_pattern}$", re.IGNORECASE)
        
        results: list[Entity] = []
        for entity in self._graph.entities.all():
            if regex.match(entity.name):
                results.append(entity)
                if len(results) >= limit:
                    break
        
        return [
            {
                "id": e.id.value,
                "name": e.name,
                "type": e.type.value,
                "file": e.location.file,
                "line": e.location.line,
            }
            for e in results
        ]


@dataclass
class _FrameworkGraphInfo:
    """Internal info for framework graph paths."""
    name: str
    file_path: Path
    entities_count: int = 0
    relationships_count: int = 0


class FrameworkSemanticSearchUseCase:
    """Use case for semantic search across framework knowledge graphs.
    
    Provides intelligent search capabilities across all pre-built
    framework knowledge graphs.
    """
    
    def __init__(self, graphs_dir: Path) -> None:
        """Initialize the use case.
        
        Args:
            graphs_dir: Directory containing framework knowledge graphs
        """
        self._graphs_dir = graphs_dir
        self._frameworks: dict[str, _FrameworkGraphInfo] = {}
        self._load_summary()
    
    def _load_summary(self) -> None:
        """Load summary information about available frameworks."""
        summary_path = self._graphs_dir / "summary.json"
        if summary_path.exists():
            with open(summary_path, "r") as f:
                data = json.load(f)
                frameworks_data = data.get("frameworks", [])
                
                # Handle both list and dict formats
                if isinstance(frameworks_data, list):
                    for fw_data in frameworks_data:
                        fw_name = fw_data.get("name", "").lower().replace(" ", "-")
                        if fw_name:
                            # Files are directly in graphs_dir, not in subdirectories
                            self._frameworks[fw_name] = _FrameworkGraphInfo(
                                name=fw_data.get("name", fw_name),
                                entities_count=fw_data.get("entity_count", 0),
                                relationships_count=fw_data.get("relationship_count", 0),
                                file_path=self._graphs_dir / f"{fw_name}.json",
                            )
                else:
                    for fw_name, fw_data in frameworks_data.items():
                        self._frameworks[fw_name] = _FrameworkGraphInfo(
                            name=fw_data.get("name", fw_name),
                            entities_count=fw_data.get("entities_count", 0),
                            relationships_count=fw_data.get("relationships_count", 0),
                            file_path=self._graphs_dir / f"{fw_name}.json",
                        )
    
    def search(
        self,
        query: str,
        frameworks: list[str] | None = None,
        limit: int = 50,
    ) -> "FrameworkSearchResults":
        """Perform semantic search across framework knowledge graphs.
        
        Args:
            query: Search query
            frameworks: Limit to specific frameworks (None = all)
            limit: Maximum results
            
        Returns:
            Search results with relevance scores
        """
        results: list[dict[str, Any]] = []
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        relevance_distribution = {"high": 0, "medium": 0, "low": 0}
        
        for fw_name, fw_info in self._frameworks.items():
            if frameworks and fw_name not in [f.lower() for f in frameworks]:
                continue
            
            if not fw_info.file_path.exists():
                continue
            
            try:
                with open(fw_info.file_path, "r") as f:
                    data = json.load(f)
                    
                for entity_data in data.get("entities", []):
                    entity_name = entity_data.get("name", "")
                    entity_type = entity_data.get("type", "")
                    docstring = entity_data.get("docstring", "")
                    file_path = entity_data.get("location", {}).get("file", "")
                    
                    score = self._calculate_relevance(
                        entity_name, entity_type, docstring, file_path,
                        query_lower, query_words
                    )
                    
                    if score > 0:
                        if score >= 7.0:
                            relevance_distribution["high"] += 1
                        elif score >= 3.0:
                            relevance_distribution["medium"] += 1
                        else:
                            relevance_distribution["low"] += 1
                            
                        results.append({
                            "framework": fw_name,
                            "name": entity_name,
                            "type": entity_type,
                            "file": file_path,
                            "line": entity_data.get("location", {}).get("line", 0),
                            "docstring": (docstring[:200] + "...") if docstring and len(docstring) > 200 else docstring,
                            "relevance_score": round(score, 3),
                        })
            except (json.JSONDecodeError, OSError):
                continue
        
        # Sort by score descending
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        results = results[:limit]
        
        return FrameworkSearchResults(
            results=results,
            total_count=len(results),
            relevance_distribution=relevance_distribution,
        )
    
    def _calculate_relevance(
        self,
        name: str,
        entity_type: str,
        docstring: str | None,
        file_path: str,
        query_lower: str,
        query_words: set[str],
    ) -> float:
        """Calculate relevance score for an entity."""
        score = 0.0
        name_lower = name.lower()
        
        # Exact name match
        if name_lower == query_lower:
            score += 10.0
        # Name contains query
        elif query_lower in name_lower:
            score += 5.0
        # Query contains name
        elif name_lower in query_lower:
            score += 3.0
        
        # Word matches in name
        name_words = set(self._split_identifier(name_lower))
        word_overlap = len(query_words & name_words)
        score += word_overlap * 2.0
        
        # Docstring matches
        if docstring:
            doc_lower = docstring.lower()
            if query_lower in doc_lower:
                score += 2.0
            doc_word_overlap = len(query_words & set(doc_lower.split()))
            score += doc_word_overlap * 0.5
        
        # File path matches
        if query_lower in file_path.lower():
            score += 1.0
        
        return score
    
    def _split_identifier(self, name: str) -> list[str]:
        """Split an identifier into words."""
        import re
        parts = name.split("_")
        words = []
        for part in parts:
            words.extend(re.findall(r'[a-z]+|[A-Z][a-z]*', part))
        return [w.lower() for w in words if w]
    
    def find_by_pattern(
        self,
        pattern: str,
        frameworks: list[str] | None = None,
        limit: int = 50,
    ) -> "FrameworkPatternResults":
        """Find entities matching a naming pattern across frameworks.
        
        Common patterns:
        - "*Controller" - finds UserController, AuthController, etc.
        - "get*" - finds getUser, getData, etc.
        - "*Service" - finds AuthService, UserService, etc.
        
        Args:
            pattern: Pattern with * wildcard
            frameworks: Limit to specific frameworks (None = all)
            limit: Maximum results
            
        Returns:
            Matching entities across frameworks
        """
        import re
        
        # Convert pattern to regex
        regex_pattern = pattern.replace("*", ".*")
        regex = re.compile(f"^{regex_pattern}$", re.IGNORECASE)
        
        matches: list[dict[str, Any]] = []
        
        for fw_name, fw_info in self._frameworks.items():
            if frameworks and fw_name not in [f.lower() for f in frameworks]:
                continue
            
            if not fw_info.file_path.exists():
                continue
            
            try:
                with open(fw_info.file_path, "r") as f:
                    data = json.load(f)
                    
                for entity_data in data.get("entities", []):
                    entity_name = entity_data.get("name", "")
                    
                    if regex.match(entity_name):
                        matches.append({
                            "framework": fw_name,
                            "name": entity_name,
                            "type": entity_data.get("type", ""),
                            "file": entity_data.get("location", {}).get("file", ""),
                            "line": entity_data.get("location", {}).get("line", 0),
                        })
                        
                        if len(matches) >= limit:
                            break
            except (json.JSONDecodeError, OSError):
                continue
                
            if len(matches) >= limit:
                break
        
        return FrameworkPatternResults(
            matches=matches,
            total_count=len(matches),
            pattern=pattern,
        )


@dataclass
class FrameworkSearchResults:
    """Results from semantic search across frameworks."""
    results: list[dict[str, Any]]
    total_count: int
    relevance_distribution: dict[str, int]


@dataclass
class FrameworkPatternResults:
    """Results from pattern matching across frameworks."""
    matches: list[dict[str, Any]]
    total_count: int
    pattern: str


# =============================================================================
# REQ-001: Intelligent Documentation Generation
# =============================================================================

@dataclass
class DocumentationResult:
    """Result from documentation generation."""
    entity_name: str
    entity_type: str
    documentation: str
    format: str
    related_entities: list[dict[str, Any]]
    source_file: str | None
    generated_at: str


class DocumentationGenerationUseCase:
    """Use case for intelligent documentation generation.
    
    Generates documentation for entities by analyzing:
    - Entity structure (parameters, return types, attributes)
    - Related entities (calls, imports, contains)
    - Docstrings and comments
    - Usage patterns in the codebase
    
    Supports multiple output formats: markdown, jsdoc, google, numpy, sphinx
    """
    
    SUPPORTED_FORMATS = {"markdown", "jsdoc", "google", "numpy", "sphinx"}
    
    def __init__(self, knowledge_graph: NetworkXKnowledgeGraph) -> None:
        """Initialize the use case.
        
        Args:
            knowledge_graph: Knowledge graph to query
        """
        self._graph = knowledge_graph
    
    def generate_documentation(
        self,
        entity_name: str,
        format: str = "markdown",
        include_examples: bool = True,
        include_related: bool = True,
    ) -> DocumentationResult:
        """Generate documentation for an entity.
        
        Args:
            entity_name: Name of the entity to document
            format: Output format (markdown, jsdoc, google, numpy, sphinx)
            include_examples: Include usage examples
            include_related: Include related entities
            
        Returns:
            Generated documentation result
        """
        from datetime import datetime
        
        if format not in self.SUPPORTED_FORMATS:
            format = "markdown"
        
        # Find the entity
        entity = self._find_entity_by_name(entity_name)
        if not entity:
            return DocumentationResult(
                entity_name=entity_name,
                entity_type="unknown",
                documentation=f"# Error\n\nEntity '{entity_name}' not found in knowledge graph.",
                format=format,
                related_entities=[],
                source_file=None,
                generated_at=datetime.now().isoformat(),
            )
        
        # Get relationships
        all_rels = list(self._graph.relationships.all())
        outgoing = [r for r in all_rels if r.source_id == entity.id]
        incoming = [r for r in all_rels if r.target_id == entity.id]
        
        # Get related entities
        related: list[dict[str, Any]] = []
        if include_related:
            neighbors = self._graph.get_neighbors(entity.id, depth=1)
            related = [
                {
                    "name": n.name,
                    "type": n.type.value,
                    "relationship": self._get_relationship_type(entity.id, n.id, all_rels),
                }
                for n in neighbors[:20]
            ]
        
        # Get usage examples
        examples: list[dict[str, Any]] = []
        if include_examples:
            callers = [r for r in incoming if r.type.value == "calls"]
            for rel in callers[:5]:
                caller = self._graph.entities.get(rel.source_id)
                if caller:
                    examples.append({
                        "name": caller.name,
                        "type": caller.type.value,
                        "file": caller.location.file,
                        "line": caller.location.line,
                    })
        
        # Generate documentation
        doc = self._format_documentation(entity, outgoing, incoming, examples, format)
        
        return DocumentationResult(
            entity_name=entity.name,
            entity_type=entity.type.value,
            documentation=doc,
            format=format,
            related_entities=related,
            source_file=entity.location.file,
            generated_at=datetime.now().isoformat(),
        )
    
    def _find_entity_by_name(self, name: str) -> Entity | None:
        """Find entity by name (case-insensitive)."""
        name_lower = name.lower()
        for entity in self._graph.entities.all():
            if entity.name.lower() == name_lower:
                return entity
        # Fallback to partial match
        for entity in self._graph.entities.all():
            if name_lower in entity.name.lower():
                return entity
        return None
    
    def _get_relationship_type(
        self,
        source_id: EntityId,
        target_id: EntityId,
        all_rels: list[Any],
    ) -> str:
        """Get relationship type between two entities."""
        for rel in all_rels:
            if rel.source_id == source_id and rel.target_id == target_id:
                return rel.type.value
            if rel.source_id == target_id and rel.target_id == source_id:
                return f"inverse_{rel.type.value}"
        return "related"
    
    def _format_documentation(
        self,
        entity: Entity,
        outgoing: list[Any],
        incoming: list[Any],
        examples: list[dict[str, Any]],
        format: str,
    ) -> str:
        """Format documentation based on format type."""
        if format == "markdown":
            return self._format_markdown(entity, outgoing, incoming, examples)
        elif format == "jsdoc":
            return self._format_jsdoc(entity, outgoing, incoming)
        elif format == "google":
            return self._format_google(entity, outgoing, incoming)
        elif format == "numpy":
            return self._format_numpy(entity, outgoing, incoming)
        elif format == "sphinx":
            return self._format_sphinx(entity, outgoing, incoming)
        return self._format_markdown(entity, outgoing, incoming, examples)
    
    def _format_markdown(
        self,
        entity: Entity,
        outgoing: list[Any],
        incoming: list[Any],
        examples: list[dict[str, Any]],
    ) -> str:
        """Format as Markdown documentation."""
        lines = [
            f"# {entity.name}",
            "",
            f"**Type**: `{entity.type.value}`  ",
            f"**File**: `{entity.location.file}`  ",
            f"**Line**: {entity.location.line}",
            "",
        ]
        
        if entity.docstring:
            lines.extend([
                "## Description",
                "",
                entity.docstring,
                "",
            ])
        
        # Dependencies
        calls = [r for r in outgoing if r.type.value == "calls"]
        imports = [r for r in outgoing if r.type.value == "imports"]
        
        if calls or imports:
            lines.extend(["## Dependencies", ""])
            if imports:
                lines.append("### Imports")
                for rel in imports[:10]:
                    target = self._graph.entities.get(rel.target_id)
                    if target:
                        lines.append(f"- `{target.name}`")
                lines.append("")
            if calls:
                lines.append("### Calls")
                for rel in calls[:10]:
                    target = self._graph.entities.get(rel.target_id)
                    if target:
                        lines.append(f"- `{target.name}` ({target.type.value})")
                lines.append("")
        
        # Usage
        callers = [r for r in incoming if r.type.value == "calls"]
        if callers:
            lines.extend(["## Used By", ""])
            for rel in callers[:10]:
                source = self._graph.entities.get(rel.source_id)
                if source:
                    lines.append(f"- `{source.name}` ({source.type.value})")
            lines.append("")
        
        # Examples
        if examples:
            lines.extend(["## Usage Examples", ""])
            for ex in examples:
                lines.append(f"- `{ex['name']}` in `{ex['file']}:{ex['line']}`")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_jsdoc(
        self,
        entity: Entity,
        outgoing: list[Any],
        incoming: list[Any],
    ) -> str:
        """Format as JSDoc documentation."""
        lines = ["/**"]
        
        if entity.docstring:
            for line in entity.docstring.split("\n"):
                lines.append(f" * {line}")
        else:
            lines.append(f" * {entity.name}")
        
        lines.append(" *")
        lines.append(f" * @type {{{entity.type.value}}}")
        lines.append(f" * @file {entity.location.file}")
        
        # Add dependencies as @see
        calls = [r for r in outgoing if r.type.value == "calls"]
        for rel in calls[:5]:
            target = self._graph.entities.get(rel.target_id)
            if target:
                lines.append(f" * @see {target.name}")
        
        lines.append(" */")
        return "\n".join(lines)
    
    def _format_google(
        self,
        entity: Entity,
        outgoing: list[Any],
        incoming: list[Any],
    ) -> str:
        """Format as Google-style docstring."""
        lines = ['"""']
        
        if entity.docstring:
            lines.append(entity.docstring)
        else:
            lines.append(f"{entity.name}")
        
        lines.append("")
        
        # Add attributes/dependencies
        calls = [r for r in outgoing if r.type.value == "calls"]
        if calls:
            lines.append("Attributes:")
            for rel in calls[:5]:
                target = self._graph.entities.get(rel.target_id)
                if target:
                    lines.append(f"    {target.name}: {target.type.value}")
        
        lines.append('"""')
        return "\n".join(lines)
    
    def _format_numpy(
        self,
        entity: Entity,
        outgoing: list[Any],
        incoming: list[Any],
    ) -> str:
        """Format as NumPy-style docstring."""
        lines = ['"""']
        
        if entity.docstring:
            lines.append(entity.docstring)
        else:
            lines.append(f"{entity.name}")
        
        lines.append("")
        
        calls = [r for r in outgoing if r.type.value == "calls"]
        if calls:
            lines.extend(["See Also", "--------"])
            for rel in calls[:5]:
                target = self._graph.entities.get(rel.target_id)
                if target:
                    lines.append(f"{target.name} : {target.type.value}")
        
        lines.append('"""')
        return "\n".join(lines)
    
    def _format_sphinx(
        self,
        entity: Entity,
        outgoing: list[Any],
        incoming: list[Any],
    ) -> str:
        """Format as Sphinx-style docstring."""
        lines = ['"""']
        
        if entity.docstring:
            lines.append(entity.docstring)
        else:
            lines.append(f"{entity.name}")
        
        lines.append("")
        
        lines.append(f":type: {entity.type.value}")
        lines.append(f":file: {entity.location.file}")
        
        calls = [r for r in outgoing if r.type.value == "calls"]
        for rel in calls[:5]:
            target = self._graph.entities.get(rel.target_id)
            if target:
                lines.append(f":seealso: :class:`{target.name}`")
        
        lines.append('"""')
        return "\n".join(lines)


# =============================================================================
# REQ-002: Code Snippet Recommendation
# =============================================================================

@dataclass
class CodeSnippetResult:
    """Result from code snippet recommendation."""
    query: str
    snippets: list[dict[str, Any]]
    total_count: int
    source_breakdown: dict[str, int]  # local vs framework counts


class CodeRecommendationUseCase:
    """Use case for intelligent code snippet recommendation.
    
    Combines local codebase and framework knowledge to provide
    contextually relevant code recommendations.
    
    Relevance score formula:
    relevance = name_match * 0.4 + docstring_match * 0.3 + context_match * 0.2 + usage_frequency * 0.1
    """
    
    def __init__(
        self,
        local_graph: NetworkXKnowledgeGraph | None = None,
        frameworks_dir: Path | None = None,
    ) -> None:
        """Initialize the use case.
        
        Args:
            local_graph: Local project's knowledge graph
            frameworks_dir: Directory containing framework knowledge graphs
        """
        self._local_graph = local_graph
        self._frameworks_dir = frameworks_dir
        self._usage_cache: dict[str, int] = {}
    
    def recommend_code(
        self,
        query: str,
        include_frameworks: bool = True,
        include_local: bool = True,
        limit: int = 10,
        min_relevance: float = 0.3,
    ) -> CodeSnippetResult:
        """Recommend code snippets based on query.
        
        Args:
            query: Natural language or technical query
            include_frameworks: Include framework knowledge
            include_local: Include local codebase
            limit: Maximum results (max 50)
            min_relevance: Minimum relevance score (0.0-1.0)
            
        Returns:
            Recommended code snippets with relevance scores
        """
        limit = min(limit, 50)
        results: list[tuple[float, dict[str, Any]]] = []
        source_breakdown: dict[str, int] = {"local": 0, "framework": 0}
        
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        # Search local codebase
        if include_local and self._local_graph:
            local_results = self._search_local(query_lower, query_words)
            for score, snippet in local_results:
                if score >= min_relevance:
                    snippet["source"] = "local"
                    results.append((score, snippet))
                    source_breakdown["local"] += 1
        
        # Search framework knowledge
        if include_frameworks and self._frameworks_dir:
            fw_results = self._search_frameworks(query_lower, query_words)
            for score, snippet in fw_results:
                if score >= min_relevance:
                    snippet["source"] = "framework"
                    results.append((score, snippet))
                    source_breakdown["framework"] += 1
        
        # Sort by relevance
        results.sort(key=lambda x: x[0], reverse=True)
        results = results[:limit]
        
        # Handle empty results - suggest similar queries
        snippets = [s for _, s in results]
        if not snippets and query_words:
            # Return helpful message
            return CodeSnippetResult(
                query=query,
                snippets=[{
                    "suggestion": "No results found. Try searching for:",
                    "alternatives": list(query_words)[:3],
                }],
                total_count=0,
                source_breakdown=source_breakdown,
            )
        
        return CodeSnippetResult(
            query=query,
            snippets=snippets,
            total_count=len(snippets),
            source_breakdown=source_breakdown,
        )
    
    def _search_local(
        self,
        query_lower: str,
        query_words: set[str],
    ) -> list[tuple[float, dict[str, Any]]]:
        """Search local knowledge graph."""
        if not self._local_graph:
            return []
        
        results: list[tuple[float, dict[str, Any]]] = []
        
        # Build usage frequency cache
        if not self._usage_cache:
            all_rels = list(self._local_graph.relationships.all())
            for rel in all_rels:
                if rel.type.value == "calls":
                    target_name = rel.target_id.value
                    self._usage_cache[target_name] = self._usage_cache.get(target_name, 0) + 1
        
        for entity in self._local_graph.entities.all():
            score = self._calculate_relevance(entity, query_lower, query_words)
            if score > 0:
                # Read context (±5 lines)
                context = self._read_context(entity, context_lines=5)
                
                results.append((score, {
                    "id": entity.id.value,
                    "name": entity.name,
                    "type": entity.type.value,
                    "file": entity.location.file,
                    "line": entity.location.line,
                    "docstring": entity.docstring[:200] if entity.docstring else None,
                    "relevance_score": round(score, 3),
                    "context": context,
                }))
        
        return results
    
    def _search_frameworks(
        self,
        query_lower: str,
        query_words: set[str],
    ) -> list[tuple[float, dict[str, Any]]]:
        """Search framework knowledge graphs."""
        if not self._frameworks_dir:
            return []
        
        results: list[tuple[float, dict[str, Any]]] = []
        
        for json_file in self._frameworks_dir.glob("*.json"):
            if json_file.name == "summary.json":
                continue
            
            fw_name = json_file.stem
            try:
                with open(json_file, "r") as f:
                    data = json.load(f)
                
                for entity_data in data.get("entities", []):
                    name = entity_data.get("name", "")
                    docstring = entity_data.get("docstring", "")
                    entity_type = entity_data.get("type", "")
                    file_path = entity_data.get("location", {}).get("file", "")
                    line = entity_data.get("location", {}).get("line", 0)
                    
                    score = self._calculate_entity_relevance(
                        name, docstring, file_path, query_lower, query_words
                    )
                    
                    if score > 0:
                        results.append((score, {
                            "name": name,
                            "type": entity_type,
                            "file": file_path,
                            "line": line,
                            "docstring": (docstring[:200] + "...") if docstring and len(docstring) > 200 else docstring,
                            "relevance_score": round(score, 3),
                            "framework": fw_name,
                        }))
            except (json.JSONDecodeError, OSError):
                continue
        
        return results
    
    def _calculate_relevance(
        self,
        entity: Entity,
        query_lower: str,
        query_words: set[str],
    ) -> float:
        """Calculate relevance score using the formula."""
        name_lower = entity.name.lower()
        
        # Name match (0.4 weight)
        name_score = 0.0
        if name_lower == query_lower:
            name_score = 1.0
        elif query_lower in name_lower:
            name_score = 0.7
        elif name_lower in query_lower:
            name_score = 0.5
        else:
            name_words = set(self._split_identifier(name_lower))
            overlap = len(query_words & name_words)
            if overlap > 0:
                name_score = min(overlap * 0.3, 0.9)
        
        # Docstring match (0.3 weight)
        docstring_score = 0.0
        if entity.docstring:
            doc_lower = entity.docstring.lower()
            if query_lower in doc_lower:
                docstring_score = 0.8
            else:
                doc_words = set(doc_lower.split())
                overlap = len(query_words & doc_words)
                if overlap > 0:
                    docstring_score = min(overlap * 0.2, 0.7)
        
        # Context match (0.2 weight)
        context_score = 0.0
        if query_lower in entity.location.file.lower():
            context_score = 0.5
        
        # Usage frequency (0.1 weight)
        usage_score = 0.0
        usage_count = self._usage_cache.get(entity.id.value, 0)
        if usage_count > 10:
            usage_score = 1.0
        elif usage_count > 5:
            usage_score = 0.7
        elif usage_count > 0:
            usage_score = 0.4
        
        # Apply weights
        return (
            name_score * 0.4 +
            docstring_score * 0.3 +
            context_score * 0.2 +
            usage_score * 0.1
        )
    
    def _calculate_entity_relevance(
        self,
        name: str,
        docstring: str | None,
        file_path: str,
        query_lower: str,
        query_words: set[str],
    ) -> float:
        """Calculate relevance for framework entity."""
        name_lower = name.lower()
        
        # Name match
        name_score = 0.0
        if name_lower == query_lower:
            name_score = 1.0
        elif query_lower in name_lower:
            name_score = 0.7
        elif name_lower in query_lower:
            name_score = 0.5
        else:
            name_words = set(self._split_identifier(name_lower))
            overlap = len(query_words & name_words)
            if overlap > 0:
                name_score = min(overlap * 0.3, 0.9)
        
        # Docstring match
        docstring_score = 0.0
        if docstring:
            doc_lower = docstring.lower()
            if query_lower in doc_lower:
                docstring_score = 0.8
            else:
                doc_words = set(doc_lower.split())
                overlap = len(query_words & doc_words)
                if overlap > 0:
                    docstring_score = min(overlap * 0.2, 0.7)
        
        # Context match
        context_score = 0.0
        if query_lower in file_path.lower():
            context_score = 0.5
        
        # Framework entities don't have usage tracking
        return (
            name_score * 0.4 +
            docstring_score * 0.3 +
            context_score * 0.2
        )
    
    def _split_identifier(self, name: str) -> list[str]:
        """Split identifier into words."""
        import re
        parts = name.split("_")
        words = []
        for part in parts:
            words.extend(re.findall(r'[a-z]+|[A-Z][a-z]*', part))
        return [w.lower() for w in words if w]
    
    def _read_context(self, entity: Entity, context_lines: int = 5) -> str | None:
        """Read source code context around entity."""
        try:
            file_path = Path(entity.location.file)
            if not file_path.exists():
                return None
            
            with open(file_path, "r") as f:
                lines = f.readlines()
            
            start = max(0, entity.location.line - 1 - context_lines)
            end = min(len(lines), entity.location.line + context_lines)
            
            return "".join(lines[start:end])
        except Exception:
            return None


# =============================================================================
# REQ-003: Dependency Impact Analysis
# =============================================================================

@dataclass
class ImpactAnalysisResult:
    """Result from dependency impact analysis."""
    entity_name: str
    direct_dependents: list[dict[str, Any]]
    indirect_dependents: list[dict[str, Any]]
    impact_score: float
    total_affected: int
    depth_analyzed: int
    risk_level: str  # high, medium, low


class DependencyImpactUseCase:
    """Use case for analyzing dependency impact.
    
    Analyzes how changes to an entity would impact the codebase.
    
    Impact score formula:
    impact = direct_count * 1.0 + sum(indirect_count[d] * (0.5 ^ d)) for d in 1..depth
    """
    
    def __init__(self, knowledge_graph: NetworkXKnowledgeGraph) -> None:
        """Initialize the use case.
        
        Args:
            knowledge_graph: Knowledge graph to analyze
        """
        self._graph = knowledge_graph
    
    def analyze_impact(
        self,
        entity_name: str,
        depth: int = 3,
    ) -> ImpactAnalysisResult:
        """Analyze impact of changes to an entity.
        
        Args:
            entity_name: Name of the entity to analyze
            depth: Analysis depth (1-10, default 3)
            
        Returns:
            Impact analysis result
        """
        depth = max(1, min(depth, 10))
        
        # Find the entity
        entity = self._find_entity_by_name(entity_name)
        if not entity:
            return ImpactAnalysisResult(
                entity_name=entity_name,
                direct_dependents=[],
                indirect_dependents=[],
                impact_score=0.0,
                total_affected=0,
                depth_analyzed=depth,
                risk_level="low",
            )
        
        # Get all relationships
        all_rels = list(self._graph.relationships.all())
        
        # Find direct dependents (who calls/uses this entity)
        direct = self._find_direct_dependents(entity.id, all_rels)
        
        # Find indirect dependents (recursive)
        indirect: list[dict[str, Any]] = []
        visited: set[str] = {entity.id.value}
        visited.update(d["id"] for d in direct)
        
        current_level = [EntityId(value=d["id"]) for d in direct]
        
        for level in range(2, depth + 1):
            next_level: list[EntityId] = []
            for dep_id in current_level:
                level_deps = self._find_direct_dependents(dep_id, all_rels)
                for dep in level_deps:
                    if dep["id"] not in visited:
                        visited.add(dep["id"])
                        dep["depth"] = level
                        indirect.append(dep)
                        next_level.append(EntityId(value=dep["id"]))
            current_level = next_level
            if not current_level:
                break
        
        # Calculate impact score
        impact_score = len(direct) * 1.0
        for dep in indirect:
            dep_depth = dep.get("depth", 2)
            impact_score += 0.5 ** (dep_depth - 1)
        
        # Determine risk level
        total_affected = len(direct) + len(indirect)
        if impact_score >= 10 or total_affected >= 20:
            risk_level = "high"
        elif impact_score >= 5 or total_affected >= 10:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        return ImpactAnalysisResult(
            entity_name=entity_name,
            direct_dependents=direct,
            indirect_dependents=indirect,
            impact_score=round(impact_score, 2),
            total_affected=total_affected,
            depth_analyzed=depth,
            risk_level=risk_level,
        )
    
    def _find_entity_by_name(self, name: str) -> Entity | None:
        """Find entity by name."""
        name_lower = name.lower()
        for entity in self._graph.entities.all():
            if entity.name.lower() == name_lower:
                return entity
        return None
    
    def _find_direct_dependents(
        self,
        entity_id: EntityId,
        all_rels: list[Any],
    ) -> list[dict[str, Any]]:
        """Find entities that directly depend on this entity."""
        dependents: list[dict[str, Any]] = []
        
        # Find incoming relationships (who calls/imports/uses this)
        incoming = [r for r in all_rels if r.target_id == entity_id]
        
        for rel in incoming:
            source = self._graph.entities.get(rel.source_id)
            if source:
                dependents.append({
                    "id": source.id.value,
                    "name": source.name,
                    "type": source.type.value,
                    "relationship": rel.type.value,
                    "file": source.location.file,
                    "line": source.location.line,
                    "depth": 1,
                })
        
        return dependents
    
    def find_critical_paths(
        self,
        entity_name: str,
        limit: int = 10,
    ) -> list[list[dict[str, Any]]]:
        """Find critical dependency paths from an entity.
        
        Args:
            entity_name: Starting entity
            limit: Maximum paths to return
            
        Returns:
            List of dependency paths (each path is a list of entities)
        """
        entity = self._find_entity_by_name(entity_name)
        if not entity:
            return []
        
        paths: list[list[dict[str, Any]]] = []
        all_rels = list(self._graph.relationships.all())
        
        # DFS to find paths
        def dfs(
            current_id: EntityId,
            path: list[dict[str, Any]],
            visited: set[str],
        ) -> None:
            if len(paths) >= limit:
                return
            
            # Find next level
            incoming = [r for r in all_rels if r.target_id == current_id]
            
            if not incoming:
                # End of path
                if len(path) > 1:
                    paths.append(path.copy())
                return
            
            for rel in incoming[:5]:  # Limit branching
                if rel.source_id.value in visited:
                    continue
                
                source = self._graph.entities.get(rel.source_id)
                if source:
                    new_visited = visited | {rel.source_id.value}
                    path.append({
                        "name": source.name,
                        "type": source.type.value,
                        "relationship": rel.type.value,
                    })
                    dfs(rel.source_id, path, new_visited)
                    path.pop()
        
        initial_path = [{
            "name": entity.name,
            "type": entity.type.value,
            "relationship": "root",
        }]
        dfs(entity.id, initial_path, {entity.id.value})
        
        return paths


# =============================================================================
# REQ-004: Hybrid Search (Local + Framework)
# =============================================================================

@dataclass
class HybridSearchResult:
    """Result from hybrid search."""
    query: str
    results: list[dict[str, Any]]
    total_count: int
    source_breakdown: dict[str, int]
    detected_frameworks: list[str]


class HybridSearchUseCase:
    """Use case for hybrid search combining local and framework knowledge.
    
    Searches both local codebase and framework knowledge graphs,
    merging results with configurable weighting.
    
    Score formula: hybrid_score = local_score * local_weight + framework_score * (1 - local_weight)
    """
    
    def __init__(
        self,
        local_graph: NetworkXKnowledgeGraph | None = None,
        frameworks_dir: Path | None = None,
    ) -> None:
        """Initialize the use case.
        
        Args:
            local_graph: Local project's knowledge graph
            frameworks_dir: Directory containing framework knowledge graphs
        """
        self._local_graph = local_graph
        self._frameworks_dir = frameworks_dir
    
    def hybrid_search(
        self,
        query: str,
        local_weight: float = 0.5,
        frameworks: list[str] | None = None,
        limit: int = 20,
    ) -> HybridSearchResult:
        """Perform hybrid search across local and framework knowledge.
        
        Args:
            query: Search query
            local_weight: Weight for local results (0.0-1.0)
            frameworks: Specific frameworks to search (None = auto-detect)
            limit: Maximum results
            
        Returns:
            Combined search results
        """
        local_weight = max(0.0, min(1.0, local_weight))
        
        results: list[tuple[float, dict[str, Any]]] = []
        source_breakdown: dict[str, int] = {"local": 0, "framework": 0}
        detected_frameworks: list[str] = []
        
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        # Auto-detect frameworks if not specified
        if frameworks is None:
            detected_frameworks = self._detect_project_frameworks()
        else:
            detected_frameworks = frameworks
        
        # Search local codebase
        if self._local_graph:
            local_results = self._search_local(query_lower, query_words)
            for score, result in local_results:
                # Apply local weight
                weighted_score = score * local_weight
                result["source"] = "local"
                result["weighted_score"] = round(weighted_score, 3)
                results.append((weighted_score, result))
                source_breakdown["local"] += 1
        
        # Search framework knowledge
        if self._frameworks_dir:
            fw_results = self._search_frameworks(
                query_lower, query_words, detected_frameworks
            )
            for score, result in fw_results:
                # Apply framework weight
                weighted_score = score * (1 - local_weight)
                result["source"] = "framework"
                result["weighted_score"] = round(weighted_score, 3)
                results.append((weighted_score, result))
                source_breakdown["framework"] += 1
        
        # Sort by weighted score
        results.sort(key=lambda x: x[0], reverse=True)
        
        # Group similar results
        grouped_results = self._group_similar_results([r for _, r in results])
        grouped_results = grouped_results[:limit]
        
        return HybridSearchResult(
            query=query,
            results=grouped_results,
            total_count=len(grouped_results),
            source_breakdown=source_breakdown,
            detected_frameworks=detected_frameworks,
        )
    
    def _detect_project_frameworks(self) -> list[str]:
        """Auto-detect frameworks used in the project."""
        detected: list[str] = []
        
        if not self._local_graph:
            return detected
        
        # Check for common framework patterns in entity names
        framework_indicators = {
            "fastapi": ["fastapi", "APIRouter", "FastAPI"],
            "django": ["django", "models.Model", "View"],
            "flask": ["flask", "Blueprint", "Flask"],
            "react": ["React", "useState", "useEffect"],
            "express": ["express", "Router", "middleware"],
            "spring": ["@Controller", "@Service", "@Repository"],
        }
        
        all_entities = list(self._local_graph.entities.all())
        entity_names = {e.name for e in all_entities}
        
        for fw_name, indicators in framework_indicators.items():
            for indicator in indicators:
                if any(indicator.lower() in name.lower() for name in entity_names):
                    detected.append(fw_name)
                    break
        
        return detected
    
    def _search_local(
        self,
        query_lower: str,
        query_words: set[str],
    ) -> list[tuple[float, dict[str, Any]]]:
        """Search local knowledge graph."""
        if not self._local_graph:
            return []
        
        results: list[tuple[float, dict[str, Any]]] = []
        
        for entity in self._local_graph.entities.all():
            score = self._calculate_relevance(entity, query_lower, query_words)
            if score > 0:
                results.append((score, {
                    "name": entity.name,
                    "type": entity.type.value,
                    "file": entity.location.file,
                    "line": entity.location.line,
                    "docstring": entity.docstring[:200] if entity.docstring else None,
                    "relevance_score": round(score, 3),
                }))
        
        return results
    
    def _search_frameworks(
        self,
        query_lower: str,
        query_words: set[str],
        frameworks: list[str],
    ) -> list[tuple[float, dict[str, Any]]]:
        """Search framework knowledge graphs."""
        if not self._frameworks_dir:
            return []
        
        results: list[tuple[float, dict[str, Any]]] = []
        
        for json_file in self._frameworks_dir.glob("*.json"):
            if json_file.name == "summary.json":
                continue
            
            fw_name = json_file.stem
            # If frameworks specified, only search those
            if frameworks and fw_name not in [f.lower() for f in frameworks]:
                continue
            
            try:
                with open(json_file, "r") as f:
                    data = json.load(f)
                
                for entity_data in data.get("entities", []):
                    name = entity_data.get("name", "")
                    docstring = entity_data.get("docstring", "")
                    
                    score = self._calculate_entity_relevance(
                        name, docstring, query_lower, query_words
                    )
                    
                    if score > 0:
                        results.append((score, {
                            "name": name,
                            "type": entity_data.get("type", ""),
                            "file": entity_data.get("location", {}).get("file", ""),
                            "line": entity_data.get("location", {}).get("line", 0),
                            "docstring": (docstring[:200] + "...") if docstring and len(docstring) > 200 else docstring,
                            "relevance_score": round(score, 3),
                            "framework": fw_name,
                        }))
            except (json.JSONDecodeError, OSError):
                continue
        
        return results
    
    def _calculate_relevance(
        self,
        entity: Entity,
        query_lower: str,
        query_words: set[str],
    ) -> float:
        """Calculate relevance score for entity."""
        score = 0.0
        name_lower = entity.name.lower()
        
        if name_lower == query_lower:
            score += 10.0
        elif query_lower in name_lower:
            score += 5.0
        elif name_lower in query_lower:
            score += 3.0
        
        name_words = set(self._split_identifier(name_lower))
        word_overlap = len(query_words & name_words)
        score += word_overlap * 2.0
        
        if entity.docstring:
            doc_lower = entity.docstring.lower()
            if query_lower in doc_lower:
                score += 2.0
        
        return score
    
    def _calculate_entity_relevance(
        self,
        name: str,
        docstring: str | None,
        query_lower: str,
        query_words: set[str],
    ) -> float:
        """Calculate relevance for framework entity."""
        score = 0.0
        name_lower = name.lower()
        
        if name_lower == query_lower:
            score += 10.0
        elif query_lower in name_lower:
            score += 5.0
        elif name_lower in query_lower:
            score += 3.0
        
        name_words = set(self._split_identifier(name_lower))
        word_overlap = len(query_words & name_words)
        score += word_overlap * 2.0
        
        if docstring:
            doc_lower = docstring.lower()
            if query_lower in doc_lower:
                score += 2.0
        
        return score
    
    def _split_identifier(self, name: str) -> list[str]:
        """Split identifier into words."""
        import re
        parts = name.split("_")
        words = []
        for part in parts:
            words.extend(re.findall(r'[a-z]+|[A-Z][a-z]*', part))
        return [w.lower() for w in words if w]
    
    def _group_similar_results(
        self,
        results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Group similar results together."""
        # Simple grouping by name similarity
        grouped: list[dict[str, Any]] = []
        seen_names: set[str] = set()
        
        for result in results:
            name_lower = result.get("name", "").lower()
            # Skip if we've seen a very similar name
            if any(name_lower == seen or name_lower in seen or seen in name_lower 
                   for seen in seen_names):
                continue
            
            seen_names.add(name_lower)
            grouped.append(result)
        
        return grouped


# =============================================================================
# REQ-005: Code Quality Analysis
# =============================================================================

@dataclass
class QualityMetric:
    """A single quality metric."""
    name: str
    value: float
    threshold_good: float
    threshold_warning: float
    status: str  # good, warning, danger
    description: str


@dataclass
class QualityAnalysisResult:
    """Result from code quality analysis."""
    entity_name: str
    entity_type: str
    metrics: list[QualityMetric]
    overall_score: float  # 0-100
    overall_status: str  # good, warning, danger
    recommendations: list[str]


class CodeQualityUseCase:
    """Use case for code quality analysis.
    
    Analyzes code quality metrics including:
    - Cyclomatic complexity
    - Coupling (Afferent/Efferent)
    - Cohesion (LCOM)
    - Method length
    - Parameter count
    """
    
    # Thresholds from requirements
    THRESHOLDS = {
        "cyclomatic_complexity": {"good": 10, "warning": 20},
        "afferent_coupling": {"good": 10, "warning": 20},
        "efferent_coupling": {"good": 10, "warning": 15},
        "lcom": {"good": 0.3, "warning": 0.7},
        "method_lines": {"good": 30, "warning": 50},
        "parameter_count": {"good": 4, "warning": 7},
    }
    
    def __init__(self, knowledge_graph: NetworkXKnowledgeGraph) -> None:
        """Initialize the use case.
        
        Args:
            knowledge_graph: Knowledge graph to analyze
        """
        self._graph = knowledge_graph
    
    def analyze_quality(
        self,
        entity_name: str,
    ) -> QualityAnalysisResult:
        """Analyze code quality for an entity.
        
        Args:
            entity_name: Name of the entity to analyze
            
        Returns:
            Quality analysis result with metrics and recommendations
        """
        entity = self._find_entity_by_name(entity_name)
        if not entity:
            return QualityAnalysisResult(
                entity_name=entity_name,
                entity_type="unknown",
                metrics=[],
                overall_score=0.0,
                overall_status="unknown",
                recommendations=["Entity not found in knowledge graph."],
            )
        
        metrics: list[QualityMetric] = []
        recommendations: list[str] = []
        
        # Calculate metrics based on entity type
        if entity.type in [EntityType.CLASS, EntityType.MODULE]:
            metrics.extend(self._analyze_class_metrics(entity))
        elif entity.type in [EntityType.FUNCTION, EntityType.METHOD]:
            metrics.extend(self._analyze_function_metrics(entity))
        
        # Calculate coupling metrics (applicable to all)
        metrics.extend(self._analyze_coupling_metrics(entity))
        
        # Generate recommendations
        for metric in metrics:
            if metric.status == "danger":
                recommendations.append(
                    f"CRITICAL: {metric.name} ({metric.value}) exceeds danger threshold. "
                    f"Consider refactoring to reduce {metric.name.lower()}."
                )
            elif metric.status == "warning":
                recommendations.append(
                    f"WARNING: {metric.name} ({metric.value}) is above optimal. "
                    f"Consider reviewing and optimizing."
                )
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(metrics)
        overall_status = self._determine_status(overall_score, 70, 50)
        
        return QualityAnalysisResult(
            entity_name=entity.name,
            entity_type=entity.type.value,
            metrics=metrics,
            overall_score=round(overall_score, 1),
            overall_status=overall_status,
            recommendations=recommendations if recommendations else ["No quality issues detected."],
        )
    
    def _find_entity_by_name(self, name: str) -> Entity | None:
        """Find entity by name."""
        name_lower = name.lower()
        for entity in self._graph.entities.all():
            if entity.name.lower() == name_lower:
                return entity
        return None
    
    def _analyze_class_metrics(self, entity: Entity) -> list[QualityMetric]:
        """Analyze metrics for class entities."""
        metrics: list[QualityMetric] = []
        
        # Get contained methods
        all_rels = list(self._graph.relationships.all())
        contains = [r for r in all_rels if r.source_id == entity.id and r.type.value == "contains"]
        
        method_count = 0
        total_complexity = 0
        
        for rel in contains:
            child = self._graph.entities.get(rel.target_id)
            if child and child.type == EntityType.METHOD:
                method_count += 1
                # Estimate complexity from method structure
                total_complexity += self._estimate_complexity(child)
        
        # Average complexity
        avg_complexity = total_complexity / max(method_count, 1)
        metrics.append(QualityMetric(
            name="Average Cyclomatic Complexity",
            value=round(avg_complexity, 1),
            threshold_good=self.THRESHOLDS["cyclomatic_complexity"]["good"],
            threshold_warning=self.THRESHOLDS["cyclomatic_complexity"]["warning"],
            status=self._determine_status(
                avg_complexity,
                self.THRESHOLDS["cyclomatic_complexity"]["good"],
                self.THRESHOLDS["cyclomatic_complexity"]["warning"],
                lower_is_better=True,
            ),
            description="Average branching complexity of methods",
        ))
        
        # LCOM (Lack of Cohesion of Methods)
        lcom = self._calculate_lcom(entity, contains)
        metrics.append(QualityMetric(
            name="LCOM (Cohesion)",
            value=round(lcom, 2),
            threshold_good=self.THRESHOLDS["lcom"]["good"],
            threshold_warning=self.THRESHOLDS["lcom"]["warning"],
            status=self._determine_status(
                lcom,
                self.THRESHOLDS["lcom"]["good"],
                self.THRESHOLDS["lcom"]["warning"],
                lower_is_better=True,
            ),
            description="Lack of Cohesion of Methods (lower is better)",
        ))
        
        return metrics
    
    def _analyze_function_metrics(self, entity: Entity) -> list[QualityMetric]:
        """Analyze metrics for function/method entities."""
        metrics: list[QualityMetric] = []
        
        # Cyclomatic complexity
        complexity = self._estimate_complexity(entity)
        metrics.append(QualityMetric(
            name="Cyclomatic Complexity",
            value=complexity,
            threshold_good=self.THRESHOLDS["cyclomatic_complexity"]["good"],
            threshold_warning=self.THRESHOLDS["cyclomatic_complexity"]["warning"],
            status=self._determine_status(
                complexity,
                self.THRESHOLDS["cyclomatic_complexity"]["good"],
                self.THRESHOLDS["cyclomatic_complexity"]["warning"],
                lower_is_better=True,
            ),
            description="Number of independent paths through the code",
        ))
        
        # Estimate method lines (rough estimate from location)
        lines = self._estimate_method_lines(entity)
        metrics.append(QualityMetric(
            name="Method Lines",
            value=lines,
            threshold_good=self.THRESHOLDS["method_lines"]["good"],
            threshold_warning=self.THRESHOLDS["method_lines"]["warning"],
            status=self._determine_status(
                lines,
                self.THRESHOLDS["method_lines"]["good"],
                self.THRESHOLDS["method_lines"]["warning"],
                lower_is_better=True,
            ),
            description="Estimated number of lines in the method",
        ))
        
        # Parameter count (from signature if available)
        params = self._count_parameters(entity)
        metrics.append(QualityMetric(
            name="Parameter Count",
            value=params,
            threshold_good=self.THRESHOLDS["parameter_count"]["good"],
            threshold_warning=self.THRESHOLDS["parameter_count"]["warning"],
            status=self._determine_status(
                params,
                self.THRESHOLDS["parameter_count"]["good"],
                self.THRESHOLDS["parameter_count"]["warning"],
                lower_is_better=True,
            ),
            description="Number of function parameters",
        ))
        
        return metrics
    
    def _analyze_coupling_metrics(self, entity: Entity) -> list[QualityMetric]:
        """Analyze coupling metrics."""
        metrics: list[QualityMetric] = []
        all_rels = list(self._graph.relationships.all())
        
        # Afferent coupling (who depends on this)
        afferent = len([r for r in all_rels if r.target_id == entity.id])
        metrics.append(QualityMetric(
            name="Afferent Coupling",
            value=afferent,
            threshold_good=self.THRESHOLDS["afferent_coupling"]["good"],
            threshold_warning=self.THRESHOLDS["afferent_coupling"]["warning"],
            status=self._determine_status(
                afferent,
                self.THRESHOLDS["afferent_coupling"]["good"],
                self.THRESHOLDS["afferent_coupling"]["warning"],
                lower_is_better=True,
            ),
            description="Number of entities depending on this",
        ))
        
        # Efferent coupling (what this depends on)
        efferent = len([r for r in all_rels if r.source_id == entity.id])
        metrics.append(QualityMetric(
            name="Efferent Coupling",
            value=efferent,
            threshold_good=self.THRESHOLDS["efferent_coupling"]["good"],
            threshold_warning=self.THRESHOLDS["efferent_coupling"]["warning"],
            status=self._determine_status(
                efferent,
                self.THRESHOLDS["efferent_coupling"]["good"],
                self.THRESHOLDS["efferent_coupling"]["warning"],
                lower_is_better=True,
            ),
            description="Number of entities this depends on",
        ))
        
        return metrics
    
    def _estimate_complexity(self, entity: Entity) -> int:
        """Estimate cyclomatic complexity from entity."""
        # Base complexity
        complexity = 1
        
        # Add based on outgoing calls (more calls = more complexity)
        all_rels = list(self._graph.relationships.all())
        calls = [r for r in all_rels if r.source_id == entity.id and r.type.value == "calls"]
        complexity += len(calls) // 3
        
        # Check docstring for complexity indicators
        if entity.docstring:
            doc_lower = entity.docstring.lower()
            indicators = ["if", "else", "elif", "for", "while", "try", "except", "case", "switch"]
            for indicator in indicators:
                complexity += doc_lower.count(indicator)
        
        return min(complexity, 50)  # Cap at 50
    
    def _estimate_method_lines(self, entity: Entity) -> int:
        """Estimate method line count."""
        # Default estimate based on entity type
        if entity.type == EntityType.METHOD:
            return 15
        elif entity.type == EntityType.FUNCTION:
            return 20
        return 10
    
    def _count_parameters(self, entity: Entity) -> int:
        """Count parameters from entity signature."""
        # Extract from docstring or name patterns
        if entity.docstring and "Args:" in entity.docstring:
            # Count Args lines
            args_section = entity.docstring.split("Args:")[1].split("\n\n")[0]
            return len([l for l in args_section.split("\n") if l.strip() and ":" in l])
        return 2  # Default estimate
    
    def _calculate_lcom(self, entity: Entity, contains: list[Any]) -> float:
        """Calculate Lack of Cohesion of Methods."""
        if len(contains) <= 1:
            return 0.0
        
        # Simplified LCOM: methods that don't share any relationships
        method_ids = [r.target_id for r in contains]
        all_rels = list(self._graph.relationships.all())
        
        # Count methods that interact with each other
        interactions = 0
        total_pairs = len(method_ids) * (len(method_ids) - 1) // 2
        
        for i, m1 in enumerate(method_ids):
            for m2 in method_ids[i+1:]:
                # Check if they share any target
                m1_targets = {r.target_id for r in all_rels if r.source_id == m1}
                m2_targets = {r.target_id for r in all_rels if r.source_id == m2}
                if m1_targets & m2_targets:
                    interactions += 1
        
        if total_pairs == 0:
            return 0.0
        
        # LCOM = 1 - (interactions / total_pairs)
        return 1.0 - (interactions / total_pairs)
    
    def _determine_status(
        self,
        value: float,
        good_threshold: float,
        warning_threshold: float,
        lower_is_better: bool = True,
    ) -> str:
        """Determine status based on thresholds."""
        if lower_is_better:
            if value <= good_threshold:
                return "good"
            elif value <= warning_threshold:
                return "warning"
            return "danger"
        else:
            if value >= good_threshold:
                return "good"
            elif value >= warning_threshold:
                return "warning"
            return "danger"
    
    def _calculate_overall_score(self, metrics: list[QualityMetric]) -> float:
        """Calculate overall quality score (0-100)."""
        if not metrics:
            return 100.0
        
        scores = []
        for metric in metrics:
            if metric.status == "good":
                scores.append(100)
            elif metric.status == "warning":
                scores.append(60)
            else:
                scores.append(20)
        
        return sum(scores) / len(scores)


# =============================================================================
# REQ-006: Code Evolution Tracking
# =============================================================================

@dataclass
class EvolutionEvent:
    """A single evolution event."""
    date: str
    author: str
    commit_hash: str
    message: str
    lines_changed: int


@dataclass
class EvolutionResult:
    """Result from code evolution tracking."""
    entity_name: str
    entity_file: str
    events: list[EvolutionEvent]
    total_changes: int
    unique_authors: int
    hotspot_score: float
    is_hotspot: bool
    timeline_data: list[dict[str, Any]]


class CodeEvolutionUseCase:
    """Use case for tracking code evolution via Git history.
    
    Analyzes Git history to track changes to specific entities.
    
    Hotspot score formula:
    hotspot_score = change_frequency * 0.5 + unique_authors * 0.3 + lines_changed * 0.2
    """
    
    def __init__(
        self,
        knowledge_graph: NetworkXKnowledgeGraph,
        repo_path: Path | None = None,
    ) -> None:
        """Initialize the use case.
        
        Args:
            knowledge_graph: Knowledge graph to query
            repo_path: Path to Git repository (auto-detected if None)
        """
        self._graph = knowledge_graph
        self._repo_path = repo_path
        self._git_available = self._check_git()
    
    def _check_git(self) -> bool:
        """Check if GitPython is available."""
        try:
            import git
            return True
        except ImportError:
            return False
    
    def track_evolution(
        self,
        entity_name: str,
        since: str | None = None,
        until: str | None = None,
        include_blame: bool = False,
    ) -> EvolutionResult:
        """Track evolution of an entity.
        
        Args:
            entity_name: Name of the entity to track
            since: Start date (default: 6 months ago)
            until: End date (default: now)
            include_blame: Include git blame info
            
        Returns:
            Evolution tracking result
        """
        entity = self._find_entity_by_name(entity_name)
        if not entity:
            return EvolutionResult(
                entity_name=entity_name,
                entity_file="",
                events=[],
                total_changes=0,
                unique_authors=0,
                hotspot_score=0.0,
                is_hotspot=False,
                timeline_data=[],
            )
        
        file_path = entity.location.file
        
        if not self._git_available:
            # Return empty result with explanation
            return EvolutionResult(
                entity_name=entity.name,
                entity_file=file_path,
                events=[],
                total_changes=0,
                unique_authors=0,
                hotspot_score=0.0,
                is_hotspot=False,
                timeline_data=[{"error": "GitPython not available. Install with: pip install gitpython"}],
            )
        
        try:
            import git
            from datetime import datetime, timedelta
            
            # Find repo
            repo = self._find_repo(file_path)
            if not repo:
                return EvolutionResult(
                    entity_name=entity.name,
                    entity_file=file_path,
                    events=[],
                    total_changes=0,
                    unique_authors=0,
                    hotspot_score=0.0,
                    is_hotspot=False,
                    timeline_data=[{"error": "Not a Git repository"}],
                )
            
            # Parse dates
            if since:
                since_date = datetime.fromisoformat(since)
            else:
                since_date = datetime.now() - timedelta(days=180)
            
            if until:
                until_date = datetime.fromisoformat(until)
            else:
                until_date = datetime.now()
            
            # Get commits for this file
            events: list[EvolutionEvent] = []
            authors: set[str] = set()
            total_lines = 0
            timeline: list[dict[str, Any]] = []
            
            try:
                # Make file path relative to repo
                relative_path = Path(file_path)
                if relative_path.is_absolute():
                    relative_path = relative_path.relative_to(repo.working_dir)
                
                commits = list(repo.iter_commits(
                    paths=str(relative_path),
                    since=since_date,
                    until=until_date,
                ))
                
                for commit in commits[:50]:  # Limit to 50 commits
                    author = commit.author.name if commit.author else "Unknown"
                    authors.add(author)
                    
                    # Calculate lines changed
                    try:
                        stats = commit.stats.files.get(str(relative_path), {})
                        lines = stats.get("insertions", 0) + stats.get("deletions", 0)
                    except Exception:
                        lines = 0
                    
                    total_lines += lines
                    
                    events.append(EvolutionEvent(
                        date=commit.committed_datetime.isoformat(),
                        author=author,
                        commit_hash=commit.hexsha[:8],
                        message=commit.message.split("\n")[0][:80],
                        lines_changed=lines,
                    ))
                    
                    timeline.append({
                        "date": commit.committed_datetime.strftime("%Y-%m-%d"),
                        "changes": lines,
                        "author": author,
                    })
                
            except Exception as e:
                timeline.append({"error": str(e)})
            
            # Calculate hotspot score
            change_freq = len(events) / 30  # Normalize to ~30 expected changes
            author_factor = len(authors) / 5  # Normalize to ~5 expected authors
            lines_factor = total_lines / 500  # Normalize to ~500 expected lines
            
            hotspot_score = (
                min(change_freq, 1.0) * 0.5 +
                min(author_factor, 1.0) * 0.3 +
                min(lines_factor, 1.0) * 0.2
            )
            
            return EvolutionResult(
                entity_name=entity.name,
                entity_file=file_path,
                events=events,
                total_changes=len(events),
                unique_authors=len(authors),
                hotspot_score=round(hotspot_score, 3),
                is_hotspot=hotspot_score >= 0.7,  # Top 30% threshold
                timeline_data=timeline,
            )
            
        except Exception as e:
            return EvolutionResult(
                entity_name=entity.name,
                entity_file=file_path,
                events=[],
                total_changes=0,
                unique_authors=0,
                hotspot_score=0.0,
                is_hotspot=False,
                timeline_data=[{"error": str(e)}],
            )
    
    def _find_entity_by_name(self, name: str) -> Entity | None:
        """Find entity by name."""
        name_lower = name.lower()
        for entity in self._graph.entities.all():
            if entity.name.lower() == name_lower:
                return entity
        return None
    
    def _find_repo(self, file_path: str) -> Any:
        """Find Git repository for file."""
        try:
            import git
            
            if self._repo_path:
                return git.Repo(self._repo_path)
            
            # Search up from file path
            path = Path(file_path).resolve()
            for parent in [path] + list(path.parents):
                git_dir = parent / ".git"
                if git_dir.exists():
                    return git.Repo(parent)
            
            return None
        except Exception:
            return None
    
    def find_hotspots(
        self,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Find hotspot entities across the codebase.
        
        Args:
            limit: Maximum hotspots to return
            
        Returns:
            List of hotspot entities with scores
        """
        hotspots: list[dict[str, Any]] = []
        
        # Track unique files
        files_analyzed: set[str] = set()
        
        for entity in self._graph.entities.all():
            if entity.location.file in files_analyzed:
                continue
            
            files_analyzed.add(entity.location.file)
            result = self.track_evolution(entity.name)
            
            if result.hotspot_score > 0:
                hotspots.append({
                    "name": entity.name,
                    "file": entity.location.file,
                    "hotspot_score": result.hotspot_score,
                    "total_changes": result.total_changes,
                    "unique_authors": result.unique_authors,
                    "is_hotspot": result.is_hotspot,
                })
        
        # Sort by hotspot score
        hotspots.sort(key=lambda x: x["hotspot_score"], reverse=True)
        return hotspots[:limit]


# =============================================================================
# REQ-007: AI Code Generation Guidance
# =============================================================================

@dataclass
class CodingGuidanceResult:
    """Result from coding guidance analysis."""
    task: str
    entity_type: str
    naming_convention: str
    suggested_name: str
    template: str
    similar_entities: list[dict[str, Any]]
    import_suggestions: list[str]
    directory_suggestion: str
    confidence: float


class CodingGuidanceUseCase:
    """Use case for AI-powered coding guidance.
    
    Analyzes project patterns to provide coding guidance including:
    - Naming conventions (snake_case, camelCase, PascalCase)
    - Structure patterns from similar entities
    - Directory placement suggestions
    - Import suggestions
    """
    
    def __init__(self, knowledge_graph: NetworkXKnowledgeGraph) -> None:
        """Initialize the use case.
        
        Args:
            knowledge_graph: Knowledge graph to analyze
        """
        self._graph = knowledge_graph
    
    def get_guidance(
        self,
        task: str,
        entity_type: str = "class",
        similar_to: str | None = None,
    ) -> CodingGuidanceResult:
        """Get coding guidance for a task.
        
        Args:
            task: Description of what to create
            entity_type: Type of entity (class, function, module)
            similar_to: Reference entity name (optional)
            
        Returns:
            Coding guidance with patterns and suggestions
        """
        # Find similar entities
        similar = self._find_similar_entities(task, entity_type, similar_to)
        
        # Detect naming convention
        naming_convention = self._detect_naming_convention(entity_type)
        
        # Generate suggested name
        suggested_name = self._generate_name(task, naming_convention, entity_type)
        
        # Generate template
        template = self._generate_template(entity_type, similar)
        
        # Suggest imports
        imports = self._suggest_imports(similar)
        
        # Suggest directory
        directory = self._suggest_directory(entity_type, similar)
        
        # Calculate confidence
        confidence = min(len(similar) / 3, 1.0)  # Need 3+ similar for full confidence
        
        return CodingGuidanceResult(
            task=task,
            entity_type=entity_type,
            naming_convention=naming_convention,
            suggested_name=suggested_name,
            template=template,
            similar_entities=[
                {
                    "name": e.name,
                    "type": e.type.value,
                    "file": e.location.file,
                    "docstring": e.docstring[:100] if e.docstring else None,
                }
                for e in similar[:5]
            ],
            import_suggestions=imports,
            directory_suggestion=directory,
            confidence=round(confidence, 2),
        )
    
    def _find_similar_entities(
        self,
        task: str,
        entity_type: str,
        similar_to: str | None,
    ) -> list[Entity]:
        """Find entities similar to the task."""
        similar: list[Entity] = []
        task_words = set(task.lower().split())
        
        # Map string type to EntityType
        type_map = {
            "class": EntityType.CLASS,
            "function": EntityType.FUNCTION,
            "method": EntityType.METHOD,
            "module": EntityType.MODULE,
        }
        target_type = type_map.get(entity_type.lower())
        
        for entity in self._graph.entities.all():
            # Filter by type if specified
            if target_type and entity.type != target_type:
                continue
            
            # If similar_to specified, find exact match first
            if similar_to and entity.name.lower() == similar_to.lower():
                similar.insert(0, entity)
                continue
            
            # Score by name/docstring similarity
            score = 0
            name_lower = entity.name.lower()
            
            for word in task_words:
                if word in name_lower:
                    score += 2
                if entity.docstring and word in entity.docstring.lower():
                    score += 1
            
            if score > 0:
                similar.append(entity)
        
        return similar[:10]
    
    def _detect_naming_convention(self, entity_type: str) -> str:
        """Detect the naming convention used in the project."""
        conventions = {"snake_case": 0, "camelCase": 0, "PascalCase": 0}
        
        type_map = {
            "class": EntityType.CLASS,
            "function": EntityType.FUNCTION,
            "method": EntityType.METHOD,
        }
        target_type = type_map.get(entity_type.lower())
        
        for entity in self._graph.entities.all():
            if target_type and entity.type != target_type:
                continue
            
            name = entity.name
            if "_" in name and name.islower():
                conventions["snake_case"] += 1
            elif name[0].isupper() and not "_" in name:
                conventions["PascalCase"] += 1
            elif name[0].islower() and not "_" in name and any(c.isupper() for c in name):
                conventions["camelCase"] += 1
        
        if not any(conventions.values()):
            return "PascalCase" if entity_type == "class" else "snake_case"
        
        return max(conventions, key=conventions.get)
    
    def _generate_name(self, task: str, convention: str, entity_type: str) -> str:
        """Generate a name based on task and convention."""
        # Extract key words from task
        stop_words = {"a", "an", "the", "to", "for", "of", "in", "on", "with", "new", "create"}
        words = [w for w in task.split() if w.lower() not in stop_words]
        
        if not words:
            words = ["New", entity_type.capitalize()]
        
        if convention == "snake_case":
            return "_".join(w.lower() for w in words[:3])
        elif convention == "camelCase":
            return words[0].lower() + "".join(w.capitalize() for w in words[1:3])
        else:  # PascalCase
            return "".join(w.capitalize() for w in words[:3])
    
    def _generate_template(self, entity_type: str, similar: list[Entity]) -> str:
        """Generate a code template."""
        if entity_type == "class":
            return '''class {name}:
    """Description of the class."""
    
    def __init__(self):
        """Initialize the instance."""
        pass
    
    def execute(self):
        """Main method."""
        pass'''
        elif entity_type == "function":
            return '''def {name}():
    """Description of the function.
    
    Returns:
        Result description.
    """
    pass'''
        elif entity_type == "method":
            return '''def {name}(self):
    """Description of the method.
    
    Returns:
        Result description.
    """
    pass'''
        else:
            return '''"""Module description."""

# Module code here'''
    
    def _suggest_imports(self, similar: list[Entity]) -> list[str]:
        """Suggest imports based on similar entities."""
        imports: set[str] = set()
        all_rels = list(self._graph.relationships.all())
        
        for entity in similar[:5]:
            # Find what this entity imports
            for rel in all_rels:
                if rel.source_id == entity.id and rel.type.value == "imports":
                    target = self._graph.entities.get(rel.target_id)
                    if target:
                        imports.add(f"from {target.location.file.replace('/', '.').replace('.py', '')} import {target.name}")
        
        return list(imports)[:5]
    
    def _suggest_directory(self, entity_type: str, similar: list[Entity]) -> str:
        """Suggest directory based on similar entities."""
        directories: dict[str, int] = {}
        
        for entity in similar:
            dir_path = "/".join(entity.location.file.split("/")[:-1])
            if dir_path:
                directories[dir_path] = directories.get(dir_path, 0) + 1
        
        if directories:
            return max(directories, key=directories.get)
        
        # Default suggestions
        defaults = {
            "class": "src/services/",
            "function": "src/utils/",
            "method": "src/",
            "module": "src/",
        }
        return defaults.get(entity_type, "src/")


# =============================================================================
# REQ-008: Design Pattern Detection
# =============================================================================

@dataclass
class PatternMatch:
    """A detected design pattern."""
    pattern_name: str
    category: str  # creational, structural, behavioral
    entities: list[dict[str, Any]]
    confidence: float
    description: str
    suggestions: list[str]


@dataclass
class PatternDetectionResult:
    """Result from pattern detection."""
    patterns: list[PatternMatch]
    total_patterns: int
    coverage: float  # % of codebase with patterns


class PatternDetectionUseCase:
    """Use case for detecting design patterns in code.
    
    Detects 10 common design patterns:
    - Creational: Singleton, Factory Method, Builder
    - Structural: Adapter, Decorator, Facade
    - Behavioral: Observer, Strategy, Command, Template Method
    """
    
    # Pattern definitions with detection heuristics
    PATTERNS = {
        "Singleton": {
            "category": "creational",
            "indicators": ["_instance", "get_instance", "getInstance", "__new__"],
            "description": "Ensures a class has only one instance",
        },
        "Factory Method": {
            "category": "creational",
            "indicators": ["create_", "make_", "build_", "Factory"],
            "description": "Defines interface for creating objects",
        },
        "Builder": {
            "category": "creational",
            "indicators": ["with_", "set_", "build", "Builder"],
            "description": "Separates construction of complex objects",
        },
        "Adapter": {
            "category": "structural",
            "indicators": ["Adapter", "Wrapper", "adapt"],
            "description": "Converts interface of a class to another",
        },
        "Decorator": {
            "category": "structural",
            "indicators": ["Decorator", "Wrapper", "@"],
            "description": "Attaches additional responsibilities dynamically",
        },
        "Facade": {
            "category": "structural",
            "indicators": ["Facade", "Manager", "Service"],
            "description": "Provides unified interface to subsystems",
        },
        "Observer": {
            "category": "behavioral",
            "indicators": ["subscribe", "notify", "Observer", "Listener", "on_"],
            "description": "Defines one-to-many dependency between objects",
        },
        "Strategy": {
            "category": "behavioral",
            "indicators": ["Strategy", "execute", "algorithm", "Policy"],
            "description": "Defines family of interchangeable algorithms",
        },
        "Command": {
            "category": "behavioral",
            "indicators": ["Command", "execute", "undo", "Handler"],
            "description": "Encapsulates request as an object",
        },
        "Template Method": {
            "category": "behavioral",
            "indicators": ["_do_", "hook_", "Template", "abstract"],
            "description": "Defines skeleton algorithm with customizable steps",
        },
    }
    
    def __init__(self, knowledge_graph: NetworkXKnowledgeGraph) -> None:
        """Initialize the use case.
        
        Args:
            knowledge_graph: Knowledge graph to analyze
        """
        self._graph = knowledge_graph
    
    def detect_patterns(
        self,
        limit: int = 20,
        min_confidence: float = 0.5,
    ) -> PatternDetectionResult:
        """Detect design patterns in the codebase.
        
        Args:
            limit: Maximum patterns to return
            min_confidence: Minimum confidence threshold
            
        Returns:
            Detection results with matched patterns
        """
        detected: list[PatternMatch] = []
        entities_with_patterns: set[str] = set()
        
        all_entities = list(self._graph.entities.all())
        
        for pattern_name, pattern_info in self.PATTERNS.items():
            matches = self._detect_pattern(
                pattern_name,
                pattern_info,
                all_entities,
            )
            
            for match in matches:
                if match.confidence >= min_confidence:
                    detected.append(match)
                    for e in match.entities:
                        entities_with_patterns.add(e["name"])
        
        # Sort by confidence
        detected.sort(key=lambda x: x.confidence, reverse=True)
        detected = detected[:limit]
        
        # Calculate coverage
        total_entities = len(all_entities)
        coverage = len(entities_with_patterns) / max(total_entities, 1)
        
        return PatternDetectionResult(
            patterns=detected,
            total_patterns=len(detected),
            coverage=round(coverage, 3),
        )
    
    def _detect_pattern(
        self,
        pattern_name: str,
        pattern_info: dict[str, Any],
        entities: list[Entity],
    ) -> list[PatternMatch]:
        """Detect a specific pattern."""
        matches: list[PatternMatch] = []
        indicators = pattern_info["indicators"]
        
        for entity in entities:
            if entity.type not in [EntityType.CLASS, EntityType.FUNCTION, EntityType.METHOD]:
                continue
            
            score = 0
            matched_indicators: list[str] = []
            
            # Check name
            name_lower = entity.name.lower()
            for indicator in indicators:
                if indicator.lower() in name_lower:
                    score += 2
                    matched_indicators.append(indicator)
            
            # Check docstring
            if entity.docstring:
                doc_lower = entity.docstring.lower()
                for indicator in indicators:
                    if indicator.lower() in doc_lower:
                        score += 1
            
            # Check relationships (more complex patterns)
            if score > 0:
                rel_score = self._check_pattern_relationships(entity, pattern_name)
                score += rel_score
            
            if score >= 2:
                confidence = min(score / 5, 1.0)
                
                suggestions = self._get_pattern_suggestions(pattern_name, entity)
                
                matches.append(PatternMatch(
                    pattern_name=pattern_name,
                    category=pattern_info["category"],
                    entities=[{
                        "name": entity.name,
                        "type": entity.type.value,
                        "file": entity.location.file,
                        "line": entity.location.line,
                        "matched_indicators": matched_indicators,
                    }],
                    confidence=round(confidence, 2),
                    description=pattern_info["description"],
                    suggestions=suggestions,
                ))
        
        return matches
    
    def _check_pattern_relationships(self, entity: Entity, pattern_name: str) -> float:
        """Check relationships for pattern indicators."""
        score = 0.0
        all_rels = list(self._graph.relationships.all())
        
        if pattern_name == "Singleton":
            # Check for self-reference or limited instantiation
            for rel in all_rels:
                if rel.source_id == entity.id and rel.target_id == entity.id:
                    score += 1.0
        
        elif pattern_name == "Observer":
            # Check for multiple incoming "calls" relationships
            incoming = [r for r in all_rels if r.target_id == entity.id]
            if len(incoming) > 3:
                score += 0.5
        
        elif pattern_name == "Facade":
            # Check for many outgoing relationships
            outgoing = [r for r in all_rels if r.source_id == entity.id]
            if len(outgoing) > 5:
                score += 0.5
        
        return score
    
    def _get_pattern_suggestions(self, pattern_name: str, entity: Entity) -> list[str]:
        """Get improvement suggestions for a pattern."""
        suggestions = []
        
        if pattern_name == "Singleton":
            suggestions.append("Consider using dependency injection instead of Singleton for testability")
        elif pattern_name == "Factory Method":
            suggestions.append("Ensure factory method is properly abstracted for extensibility")
        elif pattern_name == "Observer":
            suggestions.append("Consider weak references to prevent memory leaks")
        elif pattern_name == "Strategy":
            suggestions.append("Ensure strategies are interchangeable at runtime")
        
        return suggestions


# =============================================================================
# REQ-009: API Compatibility Check
# =============================================================================

@dataclass
class CompatibilityIssue:
    """An API compatibility issue."""
    entity_name: str
    file: str
    line: int
    api_used: str
    issue_type: str  # deprecated, removed, changed
    message: str
    migration_hint: str | None


@dataclass
class CompatibilityResult:
    """Result from compatibility check."""
    framework: str
    target_version: str
    current_usage_count: int
    issues: list[CompatibilityIssue]
    compatible: bool
    compatibility_score: float  # 0-100


class APICompatibilityUseCase:
    """Use case for checking API compatibility.
    
    Checks local code against framework APIs to detect:
    - Deprecated APIs
    - Removed APIs
    - Changed APIs
    """
    
    # Known deprecations/changes (simplified database)
    KNOWN_ISSUES: dict[str, dict[str, list[dict[str, Any]]]] = {
        "django": {
            "4.0": [
                {"api": "url", "type": "removed", "hint": "Use path() instead of url()"},
                {"api": "ugettext", "type": "deprecated", "hint": "Use gettext instead"},
            ],
            "4.2": [
                {"api": "default_app_config", "type": "deprecated", "hint": "Remove default_app_config from __init__.py"},
            ],
        },
        "fastapi": {
            "0.100": [
                {"api": "on_event", "type": "deprecated", "hint": "Use lifespan context manager instead"},
            ],
        },
        "react": {
            "18.0": [
                {"api": "componentWillMount", "type": "removed", "hint": "Use useEffect hook instead"},
                {"api": "componentWillReceiveProps", "type": "removed", "hint": "Use getDerivedStateFromProps"},
            ],
        },
        "flask": {
            "2.0": [
                {"api": "before_first_request", "type": "deprecated", "hint": "Use app context or flask-caching"},
            ],
        },
    }
    
    def __init__(
        self,
        knowledge_graph: NetworkXKnowledgeGraph,
        frameworks_dir: Path | None = None,
    ) -> None:
        """Initialize the use case.
        
        Args:
            knowledge_graph: Knowledge graph to analyze
            frameworks_dir: Directory containing framework knowledge
        """
        self._graph = knowledge_graph
        self._frameworks_dir = frameworks_dir
    
    def check_compatibility(
        self,
        framework: str,
        target_version: str,
    ) -> CompatibilityResult:
        """Check API compatibility against a framework version.
        
        Args:
            framework: Framework name (django, fastapi, react, etc.)
            target_version: Target version to check against
            
        Returns:
            Compatibility check results
        """
        framework_lower = framework.lower()
        issues: list[CompatibilityIssue] = []
        usage_count = 0
        
        # Get known issues for this framework/version
        fw_issues = self.KNOWN_ISSUES.get(framework_lower, {})
        version_issues: list[dict[str, Any]] = []
        
        for version, version_issue_list in fw_issues.items():
            if self._version_compare(target_version, version) >= 0:
                version_issues.extend(version_issue_list)
        
        # Scan local code for issues
        for entity in self._graph.entities.all():
            usage_count += 1
            
            for known_issue in version_issues:
                api_name = known_issue["api"]
                
                # Check entity name
                if api_name.lower() in entity.name.lower():
                    issues.append(CompatibilityIssue(
                        entity_name=entity.name,
                        file=entity.location.file,
                        line=entity.location.line,
                        api_used=api_name,
                        issue_type=known_issue["type"],
                        message=f"{known_issue['type'].capitalize()} API: {api_name}",
                        migration_hint=known_issue.get("hint"),
                    ))
                
                # Check docstring/comments for API usage
                if entity.docstring and api_name.lower() in entity.docstring.lower():
                    issues.append(CompatibilityIssue(
                        entity_name=entity.name,
                        file=entity.location.file,
                        line=entity.location.line,
                        api_used=api_name,
                        issue_type=known_issue["type"],
                        message=f"Reference to {known_issue['type']} API: {api_name}",
                        migration_hint=known_issue.get("hint"),
                    ))
        
        # Check relationships for imported deprecated APIs
        all_rels = list(self._graph.relationships.all())
        for rel in all_rels:
            if rel.type.value == "imports":
                target = self._graph.entities.get(rel.target_id)
                if target:
                    for known_issue in version_issues:
                        if known_issue["api"].lower() in target.name.lower():
                            source = self._graph.entities.get(rel.source_id)
                            if source:
                                issues.append(CompatibilityIssue(
                                    entity_name=source.name,
                                    file=source.location.file,
                                    line=source.location.line,
                                    api_used=known_issue["api"],
                                    issue_type=known_issue["type"],
                                    message=f"Imports {known_issue['type']} API: {known_issue['api']}",
                                    migration_hint=known_issue.get("hint"),
                                ))
        
        # Calculate compatibility score
        if usage_count == 0:
            score = 100.0
        else:
            issue_penalty = len(issues) * 10
            score = max(0, 100 - issue_penalty)
        
        return CompatibilityResult(
            framework=framework,
            target_version=target_version,
            current_usage_count=usage_count,
            issues=issues,
            compatible=len(issues) == 0,
            compatibility_score=round(score, 1),
        )
    
    def _version_compare(self, v1: str, v2: str) -> int:
        """Compare two version strings. Returns -1, 0, or 1."""
        try:
            parts1 = [int(x) for x in v1.split(".")]
            parts2 = [int(x) for x in v2.split(".")]
            
            for i in range(max(len(parts1), len(parts2))):
                p1 = parts1[i] if i < len(parts1) else 0
                p2 = parts2[i] if i < len(parts2) else 0
                
                if p1 < p2:
                    return -1
                elif p1 > p2:
                    return 1
            
            return 0
        except ValueError:
            return 0


# =============================================================================
# REQ-010: Interactive Code Navigation
# =============================================================================

@dataclass
class NavigationNode:
    """A node in the navigation graph."""
    name: str
    type: str
    file: str
    line: int
    depth: int
    relationship: str | None


@dataclass
class NavigationResult:
    """Result from code navigation."""
    root_entity: str
    direction: str  # callers, callees, both
    nodes: list[NavigationNode]
    edges: list[dict[str, str]]
    max_depth: int
    total_nodes: int


class CodeNavigationUseCase:
    """Use case for interactive code navigation.
    
    Provides step-by-step exploration of code relationships:
    - Callers (who calls this)
    - Callees (what this calls)
    - Full graph navigation
    """
    
    def __init__(self, knowledge_graph: NetworkXKnowledgeGraph) -> None:
        """Initialize the use case.
        
        Args:
            knowledge_graph: Knowledge graph to navigate
        """
        self._graph = knowledge_graph
    
    def navigate_from(
        self,
        entity_name: str,
        direction: str = "both",
        depth: int = 2,
        relationship_types: list[str] | None = None,
    ) -> NavigationResult:
        """Navigate from an entity.
        
        Args:
            entity_name: Starting entity name
            direction: Navigation direction (callers, callees, both)
            depth: Maximum depth to explore
            relationship_types: Filter by relationship types
            
        Returns:
            Navigation result with graph structure
        """
        entity = self._find_entity_by_name(entity_name)
        if not entity:
            return NavigationResult(
                root_entity=entity_name,
                direction=direction,
                nodes=[],
                edges=[],
                max_depth=0,
                total_nodes=0,
            )
        
        nodes: list[NavigationNode] = []
        edges: list[dict[str, str]] = []
        visited: set[str] = set()
        
        # Add root node
        nodes.append(NavigationNode(
            name=entity.name,
            type=entity.type.value,
            file=entity.location.file,
            line=entity.location.line,
            depth=0,
            relationship=None,
        ))
        visited.add(entity.id.value)
        
        # Explore based on direction
        if direction in ["callers", "both"]:
            self._explore_direction(
                entity.id, "incoming", depth, nodes, edges, visited, relationship_types
            )
        
        if direction in ["callees", "both"]:
            self._explore_direction(
                entity.id, "outgoing", depth, nodes, edges, visited, relationship_types
            )
        
        return NavigationResult(
            root_entity=entity.name,
            direction=direction,
            nodes=nodes,
            edges=edges,
            max_depth=max(n.depth for n in nodes) if nodes else 0,
            total_nodes=len(nodes),
        )
    
    def get_call_graph(
        self,
        entity_name: str,
        depth: int = 3,
    ) -> dict[str, Any]:
        """Get call graph data for visualization.
        
        Args:
            entity_name: Center entity name
            depth: Depth to explore
            
        Returns:
            Graph data in D3-compatible format
        """
        result = self.navigate_from(entity_name, direction="both", depth=depth)
        
        # Convert to D3 format
        nodes_data = [
            {
                "id": n.name,
                "type": n.type,
                "depth": n.depth,
                "file": n.file,
            }
            for n in result.nodes
        ]
        
        links_data = [
            {
                "source": e["source"],
                "target": e["target"],
                "type": e["type"],
            }
            for e in result.edges
        ]
        
        return {
            "nodes": nodes_data,
            "links": links_data,
            "center": entity_name,
        }
    
    def _find_entity_by_name(self, name: str) -> Entity | None:
        """Find entity by name."""
        name_lower = name.lower()
        for entity in self._graph.entities.all():
            if entity.name.lower() == name_lower:
                return entity
        return None
    
    def _explore_direction(
        self,
        entity_id: EntityId,
        direction: str,
        max_depth: int,
        nodes: list[NavigationNode],
        edges: list[dict[str, str]],
        visited: set[str],
        relationship_types: list[str] | None,
        current_depth: int = 1,
    ) -> None:
        """Explore in a direction."""
        if current_depth > max_depth:
            return
        
        all_rels = list(self._graph.relationships.all())
        
        # Get relationships based on direction
        if direction == "incoming":
            rels = [r for r in all_rels if r.target_id == entity_id]
        else:
            rels = [r for r in all_rels if r.source_id == entity_id]
        
        # Filter by relationship types
        if relationship_types:
            rels = [r for r in rels if r.type.value in relationship_types]
        
        for rel in rels[:20]:  # Limit per level
            if direction == "incoming":
                other_id = rel.source_id
                source_name = self._graph.entities.get(rel.source_id)
                target_name = self._graph.entities.get(entity_id)
            else:
                other_id = rel.target_id
                source_name = self._graph.entities.get(entity_id)
                target_name = self._graph.entities.get(rel.target_id)
            
            if other_id.value in visited:
                continue
            
            other = self._graph.entities.get(other_id)
            if not other:
                continue
            
            visited.add(other_id.value)
            
            nodes.append(NavigationNode(
                name=other.name,
                type=other.type.value,
                file=other.location.file,
                line=other.location.line,
                depth=current_depth,
                relationship=rel.type.value,
            ))
            
            if source_name and target_name:
                edges.append({
                    "source": source_name.name,
                    "target": target_name.name,
                    "type": rel.type.value,
                })
            
            # Recurse
            self._explore_direction(
                other_id, direction, max_depth, nodes, edges, visited,
                relationship_types, current_depth + 1
            )
