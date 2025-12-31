"""Elixir Parser using tree-sitter."""

from pathlib import Path
import tree_sitter_elixir as ts_elixir
from tree_sitter import Language, Parser, Node

from yata_core.domain.entities import (
    Entity, EntityType, FunctionEntity, ClassEntity,
    ModuleEntity, Relationship, RelationshipType,
)
from yata_core.domain.value_objects import EntityId, Location
from yata_core.infrastructure.parsers.parse_result import ParseResult


class ElixirParser:
    """Parser for Elixir source code using tree-sitter."""
    
    def __init__(self) -> None:
        self._language = Language(ts_elixir.language())
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
    
    def _extract_from_node(self, node: Node, code: str, file_path: str, entities: list, relationships: list, imports: list, errors: list, parent_id: str | None = None) -> None:
        if node.type == "call":
            self._handle_call(node, code, file_path, entities, relationships, imports, parent_id)
        
        for child in node.children:
            self._extract_from_node(child, code, file_path, entities, relationships, imports, errors, parent_id)
    
    def _handle_call(self, node: Node, code: str, file_path: str, entities: list, relationships: list, imports: list, parent_id: str | None) -> None:
        target = node.child_by_field_name("target")
        if not target:
            return
        
        call_name = self._get_node_text(target, code)
        
        if call_name == "defmodule":
            self._extract_module(node, code, file_path, entities, relationships, parent_id)
        elif call_name == "def":
            self._extract_function(node, code, file_path, entities, relationships, parent_id, is_private=False)
        elif call_name == "defp":
            self._extract_function(node, code, file_path, entities, relationships, parent_id, is_private=True)
        elif call_name in ["import", "alias", "use", "require"]:
            self._extract_import(node, code, imports, call_name)
        elif call_name == "defprotocol":
            self._extract_protocol(node, code, file_path, entities, relationships, parent_id)
        elif call_name == "defstruct":
            self._extract_struct(node, code, file_path, entities, relationships, parent_id)
    
    def _extract_module(self, node: Node, code: str, file_path: str, entities: list, relationships: list, parent_id: str | None) -> None:
        args = node.child_by_field_name("arguments")
        if not args:
            return
        
        module_name = None
        for child in args.children:
            if child.type in ["alias", "atom"]:
                module_name = self._get_node_text(child, code)
                break
        
        if not module_name:
            return
        
        mod_id = self._generate_id("module")
        entity = ClassEntity(
            id=EntityId(value=mod_id),
            name=module_name,
            type=EntityType.MODULE,
            location=Location(file=file_path, line=node.start_point[0] + 1, column=node.start_point[1]),
            methods=[],
            bases=[],
        )
        entities.append(entity)
        
        if parent_id:
            relationships.append(Relationship(source_id=EntityId(value=parent_id), target_id=EntityId(value=mod_id), type=RelationshipType.CONTAINS))
    
    def _extract_function(self, node: Node, code: str, file_path: str, entities: list, relationships: list, parent_id: str | None, is_private: bool = False) -> None:
        args = node.child_by_field_name("arguments")
        if not args:
            return
        
        func_name = None
        for child in args.children:
            if child.type == "call":
                target = child.child_by_field_name("target")
                if target:
                    func_name = self._get_node_text(target, code)
                    break
            elif child.type == "identifier":
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
    
    def _extract_protocol(self, node: Node, code: str, file_path: str, entities: list, relationships: list, parent_id: str | None) -> None:
        args = node.child_by_field_name("arguments")
        if not args:
            return
        
        protocol_name = None
        for child in args.children:
            if child.type in ["alias", "atom"]:
                protocol_name = self._get_node_text(child, code)
                break
        
        if not protocol_name:
            return
        
        protocol_id = self._generate_id("protocol")
        entity = ClassEntity(
            id=EntityId(value=protocol_id),
            name=protocol_name,
            type=EntityType.INTERFACE,
            location=Location(file=file_path, line=node.start_point[0] + 1, column=node.start_point[1]),
            methods=[],
            bases=[],
        )
        entities.append(entity)
        
        if parent_id:
            relationships.append(Relationship(source_id=EntityId(value=parent_id), target_id=EntityId(value=protocol_id), type=RelationshipType.CONTAINS))
    
    def _extract_struct(self, node: Node, code: str, file_path: str, entities: list, relationships: list, parent_id: str | None) -> None:
        # Struct is defined within a module, extract its fields if needed
        pass
    
    def _extract_import(self, node: Node, code: str, imports: list, import_type: str) -> None:
        args = node.child_by_field_name("arguments")
        if not args:
            return
        
        for child in args.children:
            if child.type in ["alias", "atom"]:
                import_name = self._get_node_text(child, code)
                imports.append(import_name)
                break
