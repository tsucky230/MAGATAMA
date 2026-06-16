"""Lua Parser using tree-sitter."""

from pathlib import Path

import tree_sitter_lua as ts_lua
from tree_sitter import Language, Node, Parser

from magatama_core.domain.entities import (
    Entity,
    EntityType,
    FunctionEntity,
    ModuleEntity,
    Relationship,
    RelationshipType,
)
from magatama_core.domain.value_objects import EntityId, Location
from magatama_core.infrastructure.parsers.parse_result import ParseResult


class LuaParser:
    """Parser for Lua source code using tree-sitter."""

    def __init__(self) -> None:
        self._language = Language(ts_lua.language())
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
        if node.type == "function_declaration":
            self._extract_function(node, code, file_path, entities, relationships, parent_id)
        elif node.type == "local_function":
            self._extract_local_function(node, code, file_path, entities, relationships, parent_id)
        elif node.type == "function_call":
            self._extract_require(node, code, imports)

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

    def _extract_local_function(
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

    def _extract_require(self, node: Node, code: bytes, imports: list) -> None:
        # Check if this is a require call
        func_name = None
        for child in node.children:
            if child.type == "identifier":
                func_name = self._get_node_text(child, code)
                break

        if func_name == "require":
            for child in node.children:
                if child.type == "arguments":
                    for arg in child.children:
                        if arg.type == "string":
                            import_name = self._get_node_text(arg, code).strip("'\"")
                            imports.append(import_name)
