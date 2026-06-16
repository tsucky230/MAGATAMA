"""Julia Parser using tree-sitter."""

from pathlib import Path

import tree_sitter_julia as ts_julia
from tree_sitter import Language, Node, Parser

from magatama_core.domain.entities import (
    ClassEntity,
    Entity,
    EntityType,
    FunctionEntity,
    ModuleEntity,
    Relationship,
    RelationshipType,
)
from magatama_core.domain.value_objects import EntityId, Location
from magatama_core.infrastructure.parsers.parse_result import ParseResult


class JuliaParser:
    """Parser for Julia source code using tree-sitter."""

    def __init__(self) -> None:
        self._language = Language(ts_julia.language())
        self._parser = Parser()
        self._parser.language = self._language
        self._entity_counter = 0

    def parse_file(self, file_path: Path) -> ParseResult:
        content = file_path.read_text(encoding="utf-8")
        return self.parse_string(content, str(file_path))

    def parse_string(self, code: str, file_path: str = "<string>") -> ParseResult:
        code = code.encode("utf-8")
        tree = self._parser.parse(code)

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

        self._extract_from_node(
            tree.root_node, code, file_path, entities, relationships, imports, errors, module_id
        )

        return ParseResult(
            file_path=file_path,
            entities=entities,
            relationships=relationships,
            imports=imports,
            errors=errors,
        )

    def _generate_id(self, prefix: str) -> str:
        self._entity_counter += 1
        return f"{prefix}_{self._entity_counter:04d}"

    def _get_node_text(self, node: Node, code: bytes) -> str:
        return code[node.start_byte : node.end_byte].decode("utf-8")

    def _extract_from_node(
        self,
        node: Node,
        code: bytes,
        file_path: str,
        entities: list,
        relationships: list,
        imports: list,
        errors: list,
        parent_id: str | None = None,
    ) -> None:
        if node.type == "function_definition":
            self._extract_function(node, code, file_path, entities, relationships, parent_id)
        elif node.type == "short_function_definition":
            self._extract_short_function(node, code, file_path, entities, relationships, parent_id)
        elif node.type == "struct_definition":
            self._extract_struct(node, code, file_path, entities, relationships, parent_id)
        elif node.type == "abstract_definition":
            self._extract_abstract_type(node, code, file_path, entities, relationships, parent_id)
        elif node.type == "module_definition":
            self._extract_module(node, code, file_path, entities, relationships, parent_id)
        elif node.type in ["import_statement", "using_statement"]:
            self._extract_import(node, code, imports)
        elif node.type == "macro_definition":
            self._extract_macro(node, code, file_path, entities, relationships, parent_id)

        for child in node.children:
            self._extract_from_node(
                child, code, file_path, entities, relationships, imports, errors, parent_id
            )

    def _extract_function(
        self,
        node: Node,
        code: bytes,
        file_path: str,
        entities: list,
        relationships: list,
        parent_id: str | None,
    ) -> None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            # Try to find identifier in children
            for child in node.children:
                if child.type == "identifier":
                    name_node = child
                    break
                elif child.type == "call_expression":
                    # function foo(x) ... style
                    for subchild in child.children:
                        if subchild.type == "identifier":
                            name_node = subchild
                            break
                    break

        if not name_node:
            return

        func_name = self._get_node_text(name_node, code)
        func_id = self._generate_id("function")

        entity = FunctionEntity(
            id=EntityId(value=func_id),
            name=func_name,
            type=EntityType.FUNCTION,
            location=Location(
                file=file_path, line=node.start_point[0] + 1, column=node.start_point[1]
            ),
            parameters=[],
        )
        entities.append(entity)

        if parent_id:
            relationships.append(
                Relationship(
                    source_id=EntityId(value=parent_id),
                    target_id=EntityId(value=func_id),
                    type=RelationshipType.CONTAINS,
                )
            )

    def _extract_short_function(
        self,
        node: Node,
        code: bytes,
        file_path: str,
        entities: list,
        relationships: list,
        parent_id: str | None,
    ) -> None:
        # Short function: f(x) = x^2
        self._extract_function(node, code, file_path, entities, relationships, parent_id)

    def _extract_struct(
        self,
        node: Node,
        code: bytes,
        file_path: str,
        entities: list,
        relationships: list,
        parent_id: str | None,
    ) -> None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            for child in node.children:
                if child.type == "identifier":
                    name_node = child
                    break

        if not name_node:
            return

        struct_name = self._get_node_text(name_node, code)
        struct_id = self._generate_id("struct")

        entity = ClassEntity(
            id=EntityId(value=struct_id),
            name=struct_name,
            type=EntityType.CLASS,
            location=Location(
                file=file_path, line=node.start_point[0] + 1, column=node.start_point[1]
            ),
            methods=[],
            bases=[],
        )
        entities.append(entity)

        if parent_id:
            relationships.append(
                Relationship(
                    source_id=EntityId(value=parent_id),
                    target_id=EntityId(value=struct_id),
                    type=RelationshipType.CONTAINS,
                )
            )

    def _extract_abstract_type(
        self,
        node: Node,
        code: bytes,
        file_path: str,
        entities: list,
        relationships: list,
        parent_id: str | None,
    ) -> None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            for child in node.children:
                if child.type == "identifier":
                    name_node = child
                    break

        if not name_node:
            return

        type_name = self._get_node_text(name_node, code)
        type_id = self._generate_id("type")

        entity = ClassEntity(
            id=EntityId(value=type_id),
            name=type_name,
            type=EntityType.INTERFACE,
            location=Location(
                file=file_path, line=node.start_point[0] + 1, column=node.start_point[1]
            ),
            methods=[],
            bases=[],
        )
        entities.append(entity)

        if parent_id:
            relationships.append(
                Relationship(
                    source_id=EntityId(value=parent_id),
                    target_id=EntityId(value=type_id),
                    type=RelationshipType.CONTAINS,
                )
            )

    def _extract_module(
        self,
        node: Node,
        code: bytes,
        file_path: str,
        entities: list,
        relationships: list,
        parent_id: str | None,
    ) -> None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            for child in node.children:
                if child.type == "identifier":
                    name_node = child
                    break

        if not name_node:
            return

        mod_name = self._get_node_text(name_node, code)
        mod_id = self._generate_id("module")

        entity = ModuleEntity(
            id=EntityId(value=mod_id),
            name=mod_name,
            type=EntityType.MODULE,
            location=Location(
                file=file_path, line=node.start_point[0] + 1, column=node.start_point[1]
            ),
            file_path=file_path,
        )
        entities.append(entity)

        if parent_id:
            relationships.append(
                Relationship(
                    source_id=EntityId(value=parent_id),
                    target_id=EntityId(value=mod_id),
                    type=RelationshipType.CONTAINS,
                )
            )

    def _extract_macro(
        self,
        node: Node,
        code: bytes,
        file_path: str,
        entities: list,
        relationships: list,
        parent_id: str | None,
    ) -> None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            for child in node.children:
                if child.type == "identifier":
                    name_node = child
                    break

        if not name_node:
            return

        macro_name = self._get_node_text(name_node, code)
        macro_id = self._generate_id("macro")

        entity = FunctionEntity(
            id=EntityId(value=macro_id),
            name=f"@{macro_name}",
            type=EntityType.FUNCTION,
            location=Location(
                file=file_path, line=node.start_point[0] + 1, column=node.start_point[1]
            ),
            parameters=[],
        )
        entities.append(entity)

        if parent_id:
            relationships.append(
                Relationship(
                    source_id=EntityId(value=parent_id),
                    target_id=EntityId(value=macro_id),
                    type=RelationshipType.CONTAINS,
                )
            )

    def _extract_import(self, node: Node, code: bytes, imports: list) -> None:
        for child in node.children:
            if child.type in ["identifier", "scoped_identifier"]:
                import_name = self._get_node_text(child, code)
                imports.append(import_name)
