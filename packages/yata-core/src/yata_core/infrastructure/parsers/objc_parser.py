"""Objective-C Parser using tree-sitter."""

from pathlib import Path
import tree_sitter_objc as ts_objc
from tree_sitter import Language, Parser, Node

from yata_core.domain.entities import (
    Entity, EntityType, ClassEntity, FunctionEntity, MethodEntity,
    ModuleEntity, InterfaceEntity, Relationship, RelationshipType,
)
from yata_core.domain.value_objects import EntityId, Location
from yata_core.infrastructure.parsers.parse_result import ParseResult


class ObjectiveCParser:
    """Parser for Objective-C source code using tree-sitter."""
    
    def __init__(self) -> None:
        self._language = Language(ts_objc.language())
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
        module_id = self._generate_id("module")
        module_entity = ModuleEntity(
            id=EntityId(value=module_id),
            name=module_name,
            type=EntityType.MODULE,
            location=Location(file=file_path, line=1, column=0),
            file_path=file_path,
        )
        entities.append(module_entity)
        
        self._extract_from_node(tree.root_node, code, file_path, entities, relationships, imports, errors, module_id)
        
        return ParseResult(file_path=file_path, entities=entities, relationships=relationships, imports=imports, errors=errors)
    
    def _generate_id(self, prefix: str) -> str:
        self._entity_counter += 1
        return f"{prefix}_{self._entity_counter:04d}"
    
    def _get_node_text(self, node: Node, code: str) -> str:
        return code[node.start_byte:node.end_byte]
    
    def _extract_from_node(self, node: Node, code: str, file_path: str, entities: list, relationships: list, imports: list, errors: list, parent_id: str | None = None, current_class_id: str | None = None) -> None:
        if node.type == "class_interface":
            self._extract_class_interface(node, code, file_path, entities, relationships, parent_id)
        elif node.type == "class_implementation":
            self._extract_class_implementation(node, code, file_path, entities, relationships, parent_id)
        elif node.type == "protocol_declaration":
            self._extract_protocol(node, code, file_path, entities, relationships, parent_id)
        elif node.type == "method_definition":
            self._extract_method(node, code, file_path, entities, relationships, parent_id, current_class_id)
        elif node.type == "function_definition":
            self._extract_function(node, code, file_path, entities, relationships, parent_id)
        elif node.type == "preproc_import":
            self._extract_import(node, code, imports)
        
        for child in node.children:
            self._extract_from_node(child, code, file_path, entities, relationships, imports, errors, parent_id, current_class_id)
    
    def _extract_class_interface(self, node: Node, code: str, file_path: str, entities: list, relationships: list, parent_id: str | None) -> None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        
        class_name = self._get_node_text(name_node, code)
        class_id = self._generate_id("class")
        
        bases = []
        superclass_node = node.child_by_field_name("superclass")
        if superclass_node:
            bases.append(self._get_node_text(superclass_node, code))
        
        class_entity = ClassEntity(
            id=EntityId(value=class_id),
            name=class_name,
            type=EntityType.CLASS,
            location=Location(file=file_path, line=node.start_point[0] + 1, column=node.start_point[1]),
            bases=bases,
        )
        entities.append(class_entity)
        
        if parent_id:
            relationships.append(Relationship(source_id=EntityId(value=parent_id), target_id=EntityId(value=class_id), type=RelationshipType.CONTAINS))
    
    def _extract_class_implementation(self, node: Node, code: str, file_path: str, entities: list, relationships: list, parent_id: str | None) -> None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        
        class_name = self._get_node_text(name_node, code)
        class_id = self._generate_id("class")
        
        class_entity = ClassEntity(
            id=EntityId(value=class_id),
            name=class_name,
            type=EntityType.CLASS,
            location=Location(file=file_path, line=node.start_point[0] + 1, column=node.start_point[1]),
            bases=[],
        )
        entities.append(class_entity)
        
        if parent_id:
            relationships.append(Relationship(source_id=EntityId(value=parent_id), target_id=EntityId(value=class_id), type=RelationshipType.CONTAINS))
        
        for child in node.children:
            if child.type == "method_definition":
                self._extract_method(child, code, file_path, entities, relationships, class_id, class_id)
    
    def _extract_protocol(self, node: Node, code: str, file_path: str, entities: list, relationships: list, parent_id: str | None) -> None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        
        protocol_name = self._get_node_text(name_node, code)
        protocol_id = self._generate_id("interface")
        
        protocol_entity = InterfaceEntity(
            id=EntityId(value=protocol_id),
            name=protocol_name,
            type=EntityType.INTERFACE,
            location=Location(file=file_path, line=node.start_point[0] + 1, column=node.start_point[1]),
            bases=[],
        )
        entities.append(protocol_entity)
        
        if parent_id:
            relationships.append(Relationship(source_id=EntityId(value=parent_id), target_id=EntityId(value=protocol_id), type=RelationshipType.CONTAINS))
    
    def _extract_method(self, node: Node, code: str, file_path: str, entities: list, relationships: list, parent_id: str | None, current_class_id: str | None) -> None:
        selector_node = node.child_by_field_name("selector")
        if not selector_node:
            return
        
        method_name = self._get_node_text(selector_node, code).split(":")[0]
        method_id = self._generate_id("method")
        
        entity = MethodEntity(
            id=EntityId(value=method_id),
            name=method_name,
            type=EntityType.METHOD,
            location=Location(file=file_path, line=node.start_point[0] + 1, column=node.start_point[1]),
            class_id=EntityId(value=current_class_id) if current_class_id else None,
            parameters=[],
        )
        entities.append(entity)
        
        if parent_id:
            relationships.append(Relationship(source_id=EntityId(value=parent_id), target_id=EntityId(value=method_id), type=RelationshipType.CONTAINS))
    
    def _extract_function(self, node: Node, code: str, file_path: str, entities: list, relationships: list, parent_id: str | None) -> None:
        declarator = node.child_by_field_name("declarator")
        if not declarator:
            return
        
        func_name = None
        for child in declarator.children:
            if child.type == "identifier":
                func_name = self._get_node_text(child, code)
                break
        
        if not func_name:
            return
        
        func_id = self._generate_id("function")
        entity = FunctionEntity(
            id=EntityId(value=func_id),
            name=func_name,
            type=EntityType.FUNCTION,
            location=Location(file=file_path, line=node.start_point[0] + 1, column=node.start_point[1]),
            parameters=[],
        )
        entities.append(entity)
        
        if parent_id:
            relationships.append(Relationship(source_id=EntityId(value=parent_id), target_id=EntityId(value=func_id), type=RelationshipType.CONTAINS))
    
    def _extract_import(self, node: Node, code: str, imports: list) -> None:
        for child in node.children:
            if child.type in ("string_literal", "system_lib_string"):
                import_path = self._get_node_text(child, code).strip('<>"')
                imports.append(import_path)
