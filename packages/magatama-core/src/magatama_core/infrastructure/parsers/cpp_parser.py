"""C++ Parser using tree-sitter."""

from pathlib import Path

import tree_sitter_cpp as ts_cpp
from tree_sitter import Language, Node, Parser

from magatama_core.domain.entities import (
    ClassEntity,
    Entity,
    EntityType,
    FunctionEntity,
    MethodEntity,
    ModuleEntity,
    Relationship,
    RelationshipType,
)
from magatama_core.domain.value_objects import EntityId, Location
from magatama_core.infrastructure.parsers.parse_result import ParseResult


class CppParser:
    """Parser for C++ source code using tree-sitter."""

    def __init__(self) -> None:
        self._language = Language(ts_cpp.language())
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

    def _get_node_text(self, node: Node, code: str) -> str:
        return code[node.start_byte : node.end_byte]

    def _extract_from_node(
        self,
        node: Node,
        code: str,
        file_path: str,
        entities: list,
        relationships: list,
        imports: list,
        errors: list,
        parent_id: str | None = None,
        current_class_id: str | None = None,
    ) -> None:
        if node.type == "class_specifier":
            self._extract_class(node, code, file_path, entities, relationships, parent_id)
        elif node.type == "struct_specifier":
            self._extract_struct(node, code, file_path, entities, relationships, parent_id)
        elif node.type == "function_definition":
            self._extract_function(
                node, code, file_path, entities, relationships, parent_id, current_class_id
            )
        elif node.type == "preproc_include":
            self._extract_include(node, code, imports)
        elif node.type == "namespace_definition":
            self._extract_namespace(
                node, code, file_path, entities, relationships, imports, errors, parent_id
            )
            return

        for child in node.children:
            self._extract_from_node(
                child,
                code,
                file_path,
                entities,
                relationships,
                imports,
                errors,
                parent_id,
                current_class_id,
            )

    def _extract_class(
        self,
        node: Node,
        code: str,
        file_path: str,
        entities: list,
        relationships: list,
        parent_id: str | None,
    ) -> None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        class_name = self._get_node_text(name_node, code)
        class_id = self._generate_id("class")

        class_entity = ClassEntity(
            id=EntityId(value=class_id),
            name=class_name,
            type=EntityType.CLASS,
            location=Location(
                file=file_path, line=node.start_point[0] + 1, column=node.start_point[1]
            ),
            bases=[],
        )
        entities.append(class_entity)

        if parent_id:
            relationships.append(
                Relationship(
                    source_id=EntityId(value=parent_id),
                    target_id=EntityId(value=class_id),
                    type=RelationshipType.CONTAINS,
                )
            )

        body_node = node.child_by_field_name("body")
        if body_node:
            for child in body_node.children:
                self._extract_from_node(
                    child, code, file_path, entities, relationships, [], [], class_id, class_id
                )

    def _extract_struct(
        self,
        node: Node,
        code: str,
        file_path: str,
        entities: list,
        relationships: list,
        parent_id: str | None,
    ) -> None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        struct_name = self._get_node_text(name_node, code)
        struct_id = self._generate_id("class")

        struct_entity = ClassEntity(
            id=EntityId(value=struct_id),
            name=struct_name,
            type=EntityType.CLASS,
            location=Location(
                file=file_path, line=node.start_point[0] + 1, column=node.start_point[1]
            ),
            bases=[],
        )
        entities.append(struct_entity)

        if parent_id:
            relationships.append(
                Relationship(
                    source_id=EntityId(value=parent_id),
                    target_id=EntityId(value=struct_id),
                    type=RelationshipType.CONTAINS,
                )
            )

    def _extract_function(
        self,
        node: Node,
        code: str,
        file_path: str,
        entities: list,
        relationships: list,
        parent_id: str | None,
        current_class_id: str | None,
    ) -> None:
        declarator = node.child_by_field_name("declarator")
        if not declarator:
            return

        func_name = None
        for child in declarator.children:
            if child.type in ("identifier", "field_identifier"):
                func_name = self._get_node_text(child, code)
                break
            elif child.type == "function_declarator":
                for subchild in child.children:
                    if subchild.type in ("identifier", "field_identifier"):
                        func_name = self._get_node_text(subchild, code)
                        break

        if not func_name:
            return

        func_id = self._generate_id("function")

        if current_class_id:
            entity = MethodEntity(
                id=EntityId(value=func_id),
                name=func_name,
                type=EntityType.METHOD,
                location=Location(
                    file=file_path, line=node.start_point[0] + 1, column=node.start_point[1]
                ),
                class_id=EntityId(value=current_class_id),
                parameters=[],
            )
        else:
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

    def _extract_include(self, node: Node, code: str, imports: list) -> None:
        for child in node.children:
            if child.type in ("string_literal", "system_lib_string"):
                import_path = self._get_node_text(child, code).strip('<>"')
                imports.append(import_path)

    def _extract_namespace(
        self,
        node: Node,
        code: str,
        file_path: str,
        entities: list,
        relationships: list,
        imports: list,
        errors: list,
        parent_id: str | None,
    ) -> None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        namespace_name = self._get_node_text(name_node, code)
        namespace_id = self._generate_id("module")

        namespace_entity = ModuleEntity(
            id=EntityId(value=namespace_id),
            name=namespace_name,
            type=EntityType.MODULE,
            location=Location(
                file=file_path, line=node.start_point[0] + 1, column=node.start_point[1]
            ),
            file_path=file_path,
        )
        entities.append(namespace_entity)

        if parent_id:
            relationships.append(
                Relationship(
                    source_id=EntityId(value=parent_id),
                    target_id=EntityId(value=namespace_id),
                    type=RelationshipType.CONTAINS,
                )
            )

        body_node = node.child_by_field_name("body")
        if body_node:
            for child in body_node.children:
                self._extract_from_node(
                    child,
                    code,
                    file_path,
                    entities,
                    relationships,
                    imports,
                    errors,
                    namespace_id,
                    None,
                )
