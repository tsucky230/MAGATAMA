"""Zig Parser using tree-sitter."""

from pathlib import Path
import tree_sitter_zig as ts_zig
from tree_sitter import Language, Parser, Node

from yata_core.domain.entities import (
    Entity, EntityType, ClassEntity, FunctionEntity,
    ModuleEntity, Relationship, RelationshipType,
)
from yata_core.domain.value_objects import EntityId, Location
from yata_core.infrastructure.parsers.parse_result import ParseResult


class ZigParser:
    """Parser for Zig source code using tree-sitter."""
    
    def __init__(self) -> None:
        self._language = Language(ts_zig.language())
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
        if node.type == "function_declaration":
            self._extract_function(node, code, file_path, entities, relationships, parent_id)
        elif node.type == "variable_declaration":
            self._extract_var_decl(node, code, file_path, entities, relationships, imports, parent_id)
        elif node.type == "container_declaration":
            self._extract_struct(node, code, file_path, entities, relationships, parent_id)
        elif node.type == "test_declaration":
            self._extract_test(node, code, file_path, entities, relationships, parent_id)
        
        for child in node.children:
            self._extract_from_node(child, code, file_path, entities, relationships, imports, errors, parent_id)
    
    def _extract_function(self, node: Node, code: str, file_path: str, entities: list, relationships: list, parent_id: str | None) -> None:
        func_name = None
        
        for child in node.children:
            if child.type == "identifier":
                func_name = self._get_node_text(child, code)
                break
        
        if not func_name:
            return
        
        func_id = self._generate_id("function")
        parameters = self._extract_parameters(node, code)
        
        func_entity = FunctionEntity(
            id=EntityId(value=func_id),
            name=func_name,
            type=EntityType.FUNCTION,
            location=Location(file=file_path, line=node.start_point[0] + 1, column=node.start_point[1]),
            parameters=parameters,
        )
        entities.append(func_entity)
        
        if parent_id:
            relationships.append(Relationship(source_id=EntityId(value=parent_id), target_id=EntityId(value=func_id), type=RelationshipType.CONTAINS))
    
    def _extract_parameters(self, node: Node, code: str) -> list[tuple[str, str | None]]:
        parameters: list[tuple[str, str | None]] = []
        
        for child in node.children:
            if child.type == "parameters":
                for param in child.children:
                    if param.type == "parameter":
                        param_name = None
                        param_type = None
                        for param_child in param.children:
                            if param_child.type == "identifier":
                                param_name = self._get_node_text(param_child, code)
                            elif param_child.type == "builtin_type":
                                param_type = self._get_node_text(param_child, code)
                        if param_name:
                            parameters.append((param_name, param_type))
        
        return parameters
    
    def _extract_struct(self, node: Node, code: str, file_path: str, entities: list, relationships: list, parent_id: str | None) -> None:
        struct_name = None
        
        parent = node.parent
        if parent and parent.type == "variable_declaration":
            for child in parent.children:
                if child.type == "identifier":
                    struct_name = self._get_node_text(child, code)
                    break
        
        if not struct_name:
            return
        
        struct_id = self._generate_id("struct")
        
        struct_entity = ClassEntity(
            id=EntityId(value=struct_id),
            name=struct_name,
            type=EntityType.CLASS,
            location=Location(file=file_path, line=node.start_point[0] + 1, column=node.start_point[1]),
            bases=[],
        )
        entities.append(struct_entity)
        
        if parent_id:
            relationships.append(Relationship(source_id=EntityId(value=parent_id), target_id=EntityId(value=struct_id), type=RelationshipType.CONTAINS))
    
    def _extract_var_decl(self, node: Node, code: str, file_path: str, entities: list, relationships: list, imports: list, parent_id: str | None) -> None:
        is_import = False
        var_name = None
        
        for child in node.children:
            if child.type == "identifier":
                var_name = self._get_node_text(child, code)
            elif child.type == "builtin_call_expression":
                builtin_text = self._get_node_text(child, code)
                if "@import" in builtin_text:
                    is_import = True
                    import_match = builtin_text
                    if '"' in import_match:
                        start = import_match.find('"') + 1
                        end = import_match.rfind('"')
                        if start < end:
                            imports.append(import_match[start:end])
        
        if is_import and var_name:
            return
    
    def _extract_test(self, node: Node, code: str, file_path: str, entities: list, relationships: list, parent_id: str | None) -> None:
        test_name = None
        
        for child in node.children:
            if child.type == "string_literal":
                test_name = self._get_node_text(child, code).strip('"')
                break
        
        if not test_name:
            test_name = "anonymous_test"
        
        test_id = self._generate_id("test")
        
        test_entity = FunctionEntity(
            id=EntityId(value=test_id),
            name=f"test_{test_name}",
            type=EntityType.FUNCTION,
            location=Location(file=file_path, line=node.start_point[0] + 1, column=node.start_point[1]),
            parameters=[],
        )
        entities.append(test_entity)
        
        if parent_id:
            relationships.append(Relationship(source_id=EntityId(value=parent_id), target_id=EntityId(value=test_id), type=RelationshipType.CONTAINS))
