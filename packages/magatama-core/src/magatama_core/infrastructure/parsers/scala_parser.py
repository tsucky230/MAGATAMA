"""Scala Parser using tree-sitter."""

from pathlib import Path

import tree_sitter_scala as ts_scala
from tree_sitter import Language, Node, Parser

from magatama_core.domain.entities import (
    ClassEntity,
    Entity,
    EntityType,
    FunctionEntity,
    InterfaceEntity,
    MethodEntity,
    ModuleEntity,
    Relationship,
    RelationshipType,
)
from magatama_core.domain.value_objects import EntityId, Location
from magatama_core.infrastructure.parsers.parse_result import ParseResult


class ScalaParser:
    """Parser for Scala source code using tree-sitter."""

    def __init__(self) -> None:
        self._language = Language(ts_scala.language())
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
        current_class_id: str | None = None,
    ) -> None:
        if node.type == "class_definition":
            self._extract_class(node, code, file_path, entities, relationships, parent_id)
            return
        elif node.type == "object_definition":
            self._extract_object(node, code, file_path, entities, relationships, parent_id)
            return
        elif node.type == "trait_definition":
            self._extract_trait(node, code, file_path, entities, relationships, parent_id)
            return
        elif node.type == "function_definition":
            self._extract_function(
                node, code, file_path, entities, relationships, parent_id, current_class_id
            )
        elif node.type == "import_declaration":
            self._extract_import(node, code, imports)
        elif node.type == "package_clause":
            self._extract_package(node, code, file_path, entities, relationships, parent_id)

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
        code: bytes,
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

    def _extract_object(
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

        object_name = self._get_node_text(name_node, code)
        object_id = self._generate_id("class")

        object_entity = ClassEntity(
            id=EntityId(value=object_id),
            name=object_name,
            type=EntityType.CLASS,
            location=Location(
                file=file_path, line=node.start_point[0] + 1, column=node.start_point[1]
            ),
            bases=[],
        )
        entities.append(object_entity)

        if parent_id:
            relationships.append(
                Relationship(
                    source_id=EntityId(value=parent_id),
                    target_id=EntityId(value=object_id),
                    type=RelationshipType.CONTAINS,
                )
            )

        body_node = node.child_by_field_name("body")
        if body_node:
            for child in body_node.children:
                self._extract_from_node(
                    child, code, file_path, entities, relationships, [], [], object_id, object_id
                )

    def _extract_trait(
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

        trait_name = self._get_node_text(name_node, code)
        trait_id = self._generate_id("interface")

        trait_entity = InterfaceEntity(
            id=EntityId(value=trait_id),
            name=trait_name,
            type=EntityType.INTERFACE,
            location=Location(
                file=file_path, line=node.start_point[0] + 1, column=node.start_point[1]
            ),
            bases=[],
        )
        entities.append(trait_entity)

        if parent_id:
            relationships.append(
                Relationship(
                    source_id=EntityId(value=parent_id),
                    target_id=EntityId(value=trait_id),
                    type=RelationshipType.CONTAINS,
                )
            )

    def _extract_function(
        self,
        node: Node,
        code: bytes,
        file_path: str,
        entities: list,
        relationships: list,
        parent_id: str | None,
        current_class_id: str | None,
    ) -> None:
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        func_name = self._get_node_text(name_node, code)
        func_id = self._generate_id("function" if not current_class_id else "method")

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

    def _extract_import(self, node: Node, code: bytes, imports: list) -> None:
        for child in node.children:
            if child.type == "stable_identifier":
                imports.append(self._get_node_text(child, code))

    def _extract_package(
        self,
        node: Node,
        code: bytes,
        file_path: str,
        entities: list,
        relationships: list,
        parent_id: str | None,
    ) -> None:
        for child in node.children:
            if child.type == "package_identifier":
                package_name = self._get_node_text(child, code)
                package_id = self._generate_id("module")

                package_entity = ModuleEntity(
                    id=EntityId(value=package_id),
                    name=package_name,
                    type=EntityType.MODULE,
                    location=Location(
                        file=file_path, line=node.start_point[0] + 1, column=node.start_point[1]
                    ),
                    file_path=file_path,
                )
                entities.append(package_entity)

                if parent_id:
                    relationships.append(
                        Relationship(
                            source_id=EntityId(value=parent_id),
                            target_id=EntityId(value=package_id),
                            type=RelationshipType.CONTAINS,
                        )
                    )
                break
