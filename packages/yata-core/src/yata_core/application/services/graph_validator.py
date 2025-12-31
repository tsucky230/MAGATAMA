"""Graph validation and integrity checking.

This module provides tools to validate the integrity of the knowledge graph:
- Orphaned node detection
- Invalid relationship detection  
- Graph consistency checks
- Automatic repair (optional)

REQ-NFR-005: Data integrity requirements.
"""

from dataclasses import dataclass, field
from typing import Sequence

from yata_core.domain.entities import Entity, Relationship
from yata_core.domain.repositories import KnowledgeGraphRepository
from yata_core.domain.value_objects import EntityId


@dataclass
class ValidationIssue:
    """Represents a validation issue found in the graph."""
    
    issue_type: str
    severity: str  # "error", "warning", "info"
    description: str
    entity_id: str | None = None
    relationship: tuple[str, str, str] | None = None  # (source, target, type)


@dataclass
class ValidationResult:
    """Result of a graph validation."""
    
    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    entities_checked: int = 0
    relationships_checked: int = 0
    
    @property
    def error_count(self) -> int:
        """Count of error-level issues."""
        return sum(1 for i in self.issues if i.severity == "error")
    
    @property
    def warning_count(self) -> int:
        """Count of warning-level issues."""
        return sum(1 for i in self.issues if i.severity == "warning")


@dataclass  
class RepairResult:
    """Result of a graph repair operation."""
    
    success: bool
    orphaned_nodes_removed: int = 0
    invalid_relationships_removed: int = 0
    errors: list[str] = field(default_factory=list)


class GraphValidator:
    """Validates knowledge graph integrity.
    
    Checks for:
    - Orphaned entities (no relationships)
    - Relationships pointing to non-existent entities
    - Duplicate entities
    - Circular dependencies (optional)
    """
    
    def __init__(self, knowledge_graph: KnowledgeGraphRepository) -> None:
        """Initialize the validator.
        
        Args:
            knowledge_graph: The knowledge graph to validate
        """
        self._graph = knowledge_graph
    
    def validate(
        self,
        check_orphans: bool = True,
        check_invalid_refs: bool = True,
        check_duplicates: bool = True,
    ) -> ValidationResult:
        """Validate the knowledge graph.
        
        Args:
            check_orphans: Check for orphaned entities
            check_invalid_refs: Check for relationships with invalid references
            check_duplicates: Check for duplicate entity names
            
        Returns:
            ValidationResult with any issues found
        """
        issues: list[ValidationIssue] = []
        entities = list(self._graph.entities.all())
        relationships = list(self._graph.relationships.all())
        
        entity_ids = {e.id.value for e in entities}
        
        # Check for invalid relationship references
        if check_invalid_refs:
            for rel in relationships:
                if rel.source_id.value not in entity_ids:
                    issues.append(ValidationIssue(
                        issue_type="invalid_source_reference",
                        severity="error",
                        description=f"Relationship source '{rel.source_id.value}' does not exist",
                        relationship=(rel.source_id.value, rel.target_id.value, rel.type.value),
                    ))
                if rel.target_id.value not in entity_ids:
                    issues.append(ValidationIssue(
                        issue_type="invalid_target_reference",
                        severity="error",
                        description=f"Relationship target '{rel.target_id.value}' does not exist",
                        relationship=(rel.source_id.value, rel.target_id.value, rel.type.value),
                    ))
        
        # Check for orphaned entities (no relationships)
        if check_orphans:
            entities_with_relationships: set[str] = set()
            for rel in relationships:
                entities_with_relationships.add(rel.source_id.value)
                entities_with_relationships.add(rel.target_id.value)
            
            for entity in entities:
                if entity.id.value not in entities_with_relationships:
                    # Modules without relationships are OK
                    if entity.type.value != "module":
                        issues.append(ValidationIssue(
                            issue_type="orphaned_entity",
                            severity="warning",
                            description=f"Entity '{entity.name}' has no relationships",
                            entity_id=entity.id.value,
                        ))
        
        # Check for duplicate entity names within same file
        if check_duplicates:
            seen: dict[tuple[str, str], str] = {}  # (file, name) -> id
            for entity in entities:
                key = (entity.location.file, entity.name)
                if key in seen and seen[key] != entity.id.value:
                    issues.append(ValidationIssue(
                        issue_type="duplicate_entity",
                        severity="warning",
                        description=f"Duplicate entity name '{entity.name}' in file '{entity.location.file}'",
                        entity_id=entity.id.value,
                    ))
                seen[key] = entity.id.value
        
        is_valid = all(i.severity != "error" for i in issues)
        
        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            entities_checked=len(entities),
            relationships_checked=len(relationships),
        )
    
    def repair(
        self,
        remove_orphans: bool = False,
        remove_invalid_refs: bool = True,
    ) -> RepairResult:
        """Repair graph integrity issues.
        
        Args:
            remove_orphans: Remove orphaned entities (use with caution)
            remove_invalid_refs: Remove relationships with invalid references
            
        Returns:
            RepairResult with counts of items repaired
        """
        errors: list[str] = []
        orphaned_removed = 0
        invalid_removed = 0
        
        entities = list(self._graph.entities.all())
        relationships = list(self._graph.relationships.all())
        entity_ids = {e.id.value for e in entities}
        
        # Remove relationships with invalid references
        if remove_invalid_refs:
            for rel in relationships:
                if rel.source_id.value not in entity_ids or rel.target_id.value not in entity_ids:
                    try:
                        deleted = self._graph.relationships.delete(
                            source_id=rel.source_id,
                            target_id=rel.target_id,
                            rel_type=rel.type,
                        )
                        invalid_removed += deleted
                    except Exception as e:
                        errors.append(f"Failed to remove relationship: {e}")
        
        # Remove orphaned entities (optional)
        if remove_orphans:
            # Re-fetch relationships after potential removals
            relationships = list(self._graph.relationships.all())
            entities_with_relationships: set[str] = set()
            for rel in relationships:
                entities_with_relationships.add(rel.source_id.value)
                entities_with_relationships.add(rel.target_id.value)
            
            for entity in entities:
                if (entity.id.value not in entities_with_relationships and 
                    entity.type.value != "module"):
                    try:
                        if self._graph.entities.delete(entity.id):
                            orphaned_removed += 1
                    except Exception as e:
                        errors.append(f"Failed to remove entity {entity.id.value}: {e}")
        
        return RepairResult(
            success=len(errors) == 0,
            orphaned_nodes_removed=orphaned_removed,
            invalid_relationships_removed=invalid_removed,
            errors=errors,
        )
    
    def get_statistics(self) -> dict[str, int]:
        """Get graph statistics.
        
        Returns:
            Dictionary with entity and relationship counts by type
        """
        entities = list(self._graph.entities.all())
        relationships = list(self._graph.relationships.all())
        
        entity_counts: dict[str, int] = {}
        for entity in entities:
            type_name = entity.type.value
            entity_counts[type_name] = entity_counts.get(type_name, 0) + 1
        
        relationship_counts: dict[str, int] = {}
        for rel in relationships:
            type_name = rel.type.value
            relationship_counts[type_name] = relationship_counts.get(type_name, 0) + 1
        
        return {
            "total_entities": len(entities),
            "total_relationships": len(relationships),
            **{f"entity_{k}": v for k, v in entity_counts.items()},
            **{f"relationship_{k}": v for k, v in relationship_counts.items()},
        }
