"""SQL Parser using tree-sitter."""

from pathlib import Path

import tree_sitter_sql as ts_sql
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


class SqlParser:
    """Parser for SQL source code using tree-sitter."""

    def __init__(self) -> None:
        self._language = Language(ts_sql.language())
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
        module_id = self._generate_id("schema")
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
    ) -> None:
        if node.type == "create_table_statement":
            self._extract_table(node, code, file_path, entities, relationships, parent_id)
        elif node.type == "create_view_statement":
            self._extract_view(node, code, file_path, entities, relationships, parent_id)
        elif node.type in ["create_function_statement", "create_procedure_statement"]:
            self._extract_function(node, code, file_path, entities, relationships, parent_id)
        elif node.type == "create_index_statement":
            self._extract_index(node, code, file_path, entities, relationships, parent_id)
        elif node.type == "create_trigger_statement":
            self._extract_trigger(node, code, file_path, entities, relationships, parent_id)

        for child in node.children:
            self._extract_from_node(
                child, code, file_path, entities, relationships, imports, errors, parent_id
            )

    def _extract_table(
        self,
        node: Node,
        code: str,
        file_path: str,
        entities: list,
        relationships: list,
        parent_id: str | None,
    ) -> None:
        table_name = None
        for child in node.children:
            if child.type in ["identifier", "table_name", "object_reference"]:
                table_name = self._get_node_text(child, code)
                break

        if not table_name:
            return

        table_id = self._generate_id("table")
        entity = ClassEntity(
            id=EntityId(value=table_id),
            name=table_name,
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
                    target_id=EntityId(value=table_id),
                    type=RelationshipType.CONTAINS,
                )
            )

        # Extract columns
        self._extract_columns(node, code, file_path, entities, relationships, table_id)

    def _extract_columns(
        self,
        node: Node,
        code: str,
        file_path: str,
        entities: list,
        relationships: list,
        table_id: str,
    ) -> None:
        for child in node.children:
            if child.type in ["column_definition", "column_def"]:
                self._extract_column(child, code, file_path, entities, relationships, table_id)
            else:
                for subchild in child.children:
                    if subchild.type in ["column_definition", "column_def"]:
                        self._extract_column(
                            subchild, code, file_path, entities, relationships, table_id
                        )

    def _extract_column(
        self,
        node: Node,
        code: str,
        file_path: str,
        entities: list,
        relationships: list,
        table_id: str,
    ) -> None:
        col_name = None
        for child in node.children:
            if child.type in ["identifier", "column_name"]:
                col_name = self._get_node_text(child, code)
                break

        if not col_name:
            return

        col_id = self._generate_id("column")
        entity = FunctionEntity(
            id=EntityId(value=col_id),
            name=col_name,
            type=EntityType.FIELD,
            location=Location(
                file=file_path, line=node.start_point[0] + 1, column=node.start_point[1]
            ),
            parameters=[],
        )
        entities.append(entity)
        relationships.append(
            Relationship(
                source_id=EntityId(value=table_id),
                target_id=EntityId(value=col_id),
                type=RelationshipType.CONTAINS,
            )
        )

    def _extract_view(
        self,
        node: Node,
        code: str,
        file_path: str,
        entities: list,
        relationships: list,
        parent_id: str | None,
    ) -> None:
        view_name = None
        for child in node.children:
            if child.type in ["identifier", "view_name", "object_reference"]:
                view_name = self._get_node_text(child, code)
                break

        if not view_name:
            return

        view_id = self._generate_id("view")
        entity = ClassEntity(
            id=EntityId(value=view_id),
            name=view_name,
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
                    target_id=EntityId(value=view_id),
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
    ) -> None:
        func_name = None
        for child in node.children:
            if child.type in ["identifier", "function_name", "object_reference"]:
                func_name = self._get_node_text(child, code)
                break

        if not func_name:
            return

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

    def _extract_index(
        self,
        node: Node,
        code: str,
        file_path: str,
        entities: list,
        relationships: list,
        parent_id: str | None,
    ) -> None:
        index_name = None
        for child in node.children:
            if child.type in ["identifier", "index_name"]:
                index_name = self._get_node_text(child, code)
                break

        if not index_name:
            return

        idx_id = self._generate_id("index")
        entity = FunctionEntity(
            id=EntityId(value=idx_id),
            name=index_name,
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
                    target_id=EntityId(value=idx_id),
                    type=RelationshipType.CONTAINS,
                )
            )

    def _extract_trigger(
        self,
        node: Node,
        code: str,
        file_path: str,
        entities: list,
        relationships: list,
        parent_id: str | None,
    ) -> None:
        trigger_name = None
        for child in node.children:
            if child.type in ["identifier", "trigger_name"]:
                trigger_name = self._get_node_text(child, code)
                break

        if not trigger_name:
            return

        trigger_id = self._generate_id("trigger")
        entity = FunctionEntity(
            id=EntityId(value=trigger_id),
            name=trigger_name,
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
                    target_id=EntityId(value=trigger_id),
                    type=RelationshipType.CONTAINS,
                )
            )
