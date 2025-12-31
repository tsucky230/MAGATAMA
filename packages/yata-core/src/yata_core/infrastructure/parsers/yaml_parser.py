"""YAML Parser using tree-sitter."""

from pathlib import Path
import tree_sitter_yaml as ts_yaml
from tree_sitter import Language, Parser, Node

from yata_core.domain.entities import (
    Entity, EntityType,
    ModuleEntity, Relationship, RelationshipType,
)
from yata_core.domain.value_objects import EntityId, Location
from yata_core.infrastructure.parsers.parse_result import ParseResult


class YAMLParser:
    """Parser for YAML files using tree-sitter."""
    
    def __init__(self) -> None:
        self._language = Language(ts_yaml.language())
        self._parser = Parser()
        self._parser.language = self._language
        self._entity_counter = 0
    
    def parse_file(self, file_path: Path) -> ParseResult:
        content = file_path.read_text(encoding="utf-8")
        return self.parse_string(content, str(file_path))
    
    def parse_string(self, code: str, file_path: str = "<string>") -> ParseResult:
        tree = self._parser.parse(code.encode("utf-8"))
        
        entities: list[Entity] = []
        relationships: list[Relationship] = []
        imports: list[str] = []
        errors: list[str] = []
        
        module_name = Path(file_path).stem
        module_id = self._generate_id("document")
        module_entity = ModuleEntity(
            id=EntityId(value=module_id),
            name=module_name,
            type=EntityType.MODULE,
            location=Location(file=file_path, line=1, column=0),
            file_path=file_path,
        )
        entities.append(module_entity)
        
        self._extract_from_node(tree.root_node, code, file_path, entities, relationships, module_id, "")
        
        return ParseResult(file_path=file_path, entities=entities, relationships=relationships, imports=imports, errors=errors)
    
    def _generate_id(self, prefix: str) -> str:
        self._entity_counter += 1
        return f"{prefix}_{self._entity_counter:04d}"
    
    def _get_node_text(self, node: Node, code: str) -> str:
        return code[node.start_byte:node.end_byte]
    
    def _extract_from_node(self, node: Node, code: str, file_path: str, entities: list, relationships: list, parent_id: str, path_prefix: str) -> None:
        if node.type == "block_mapping_pair":
            self._extract_mapping_pair(node, code, file_path, entities, relationships, parent_id, path_prefix)
        elif node.type == "block_sequence_item":
            self._extract_sequence_item(node, code, file_path, entities, relationships, parent_id, path_prefix)
        else:
            for child in node.children:
                self._extract_from_node(child, code, file_path, entities, relationships, parent_id, path_prefix)
    
    def _extract_mapping_pair(self, node: Node, code: str, file_path: str, entities: list, relationships: list, parent_id: str, path_prefix: str) -> None:
        key_node = None
        value_node = None
        
        for child in node.children:
            if child.type == "flow_node" and key_node is None:
                key_node = child
            elif child.type in ["block_node", "flow_node"] and key_node is not None:
                value_node = child
        
        if key_node is None:
            for child in node.children:
                if child.type not in [":", "block_node", "flow_node"]:
                    key_text = self._get_node_text(child, code).strip()
                    if key_text:
                        key_node = child
                        break
        
        if key_node:
            key_name = self._get_node_text(key_node, code).strip()
            current_path = f"{path_prefix}.{key_name}" if path_prefix else key_name
            
            key_id = self._generate_id("key")
            key_entity = ModuleEntity(
                id=EntityId(value=key_id),
                name=current_path,
                type=EntityType.MODULE,
                location=Location(file=file_path, line=key_node.start_point[0] + 1, column=key_node.start_point[1]),
                file_path=file_path,
            )
            entities.append(key_entity)
            
            relationships.append(Relationship(
                source_id=EntityId(value=parent_id),
                target_id=EntityId(value=key_id),
                type=RelationshipType.CONTAINS,
            ))
            
            if value_node:
                for child in value_node.children:
                    self._extract_from_node(child, code, file_path, entities, relationships, key_id, current_path)
    
    def _extract_sequence_item(self, node: Node, code: str, file_path: str, entities: list, relationships: list, parent_id: str, path_prefix: str) -> None:
        index = 0
        parent_node = node.parent
        if parent_node:
            for i, sibling in enumerate(parent_node.children):
                if sibling == node:
                    index = i
                    break
        
        current_path = f"{path_prefix}[{index}]" if path_prefix else f"[{index}]"
        
        item_id = self._generate_id("item")
        item_entity = ModuleEntity(
            id=EntityId(value=item_id),
            name=current_path,
            type=EntityType.MODULE,
            location=Location(file=file_path, line=node.start_point[0] + 1, column=node.start_point[1]),
            file_path=file_path,
        )
        entities.append(item_entity)
        
        relationships.append(Relationship(
            source_id=EntityId(value=parent_id),
            target_id=EntityId(value=item_id),
            type=RelationshipType.CONTAINS,
        ))
        
        for child in node.children:
            if child.type not in ["-"]:
                self._extract_from_node(child, code, file_path, entities, relationships, item_id, current_path)
