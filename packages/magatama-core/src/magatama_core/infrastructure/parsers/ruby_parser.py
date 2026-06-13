"""Ruby Parser using tree-sitter.

This module provides Ruby parsing capabilities for
extracting entities from Ruby source code.
"""

from pathlib import Path

import tree_sitter_ruby as ts_ruby
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


class RubyParser:
    """Parser for Ruby source code using tree-sitter.

    Extracts:
    - Classes
    - Modules
    - Methods (def)
    - Singleton methods (def self.xxx)
    - Require/require_relative statements
    """

    def __init__(self) -> None:
        """Initialize the Ruby parser."""
        self._language = Language(ts_ruby.language())
        self._parser = Parser()
        self._parser.language = self._language
        self._entity_counter = 0

    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse a Ruby file.

        Args:
            file_path: Path to the Ruby file

        Returns:
            ParseResult with extracted entities
        """
        content = file_path.read_text(encoding="utf-8")
        return self.parse_string(content, str(file_path))

    def parse_string(self, code: str, file_path: str = "<string>") -> ParseResult:
        """Parse Ruby code from a string.

        Args:
            code: Ruby source code
            file_path: Path for location information

        Returns:
            ParseResult with extracted entities
        """
        tree = self._parser.parse(code.encode("utf-8"))

        entities: list[Entity] = []
        relationships: list[Relationship] = []
        imports: list[str] = []
        errors: list[str] = []

        # Create module entity for the file
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

        # Extract entities from AST
        self._extract_from_node(
            tree.root_node,
            code,
            file_path,
            entities,
            relationships,
            imports,
            errors,
            parent_id=module_id,
        )

        # Build method name -> EntityId map
        method_name_to_id: dict[str, EntityId] = {}
        for entity in entities:
            if entity.type in (EntityType.FUNCTION, EntityType.METHOD):
                method_name_to_id[entity.name] = entity.id

        # Extract CALLS relationships
        self._extract_calls_relationships(
            tree.root_node,
            code,
            relationships,
            method_name_to_id,
        )

        # Extract require/import relationships
        self._extract_imports_relationships(
            tree.root_node,
            code,
            relationships,
            EntityId(value=module_id),
        )

        return ParseResult(
            file_path=file_path,
            entities=entities,
            relationships=relationships,
            imports=imports,
            errors=errors,
        )

    def _generate_id(self, prefix: str) -> str:
        """Generate a unique entity ID."""
        self._entity_counter += 1
        return f"{prefix}_{self._entity_counter:04d}"

    def _get_node_text(self, node: Node, code: str) -> str:
        """Get the text content of a node."""
        return code[node.start_byte : node.end_byte]

    def _extract_from_node(
        self,
        node: Node,
        code: str,
        file_path: str,
        entities: list[Entity],
        relationships: list[Relationship],
        imports: list[str],
        errors: list[str],
        parent_id: str | None = None,
        current_class_id: str | None = None,
    ) -> None:
        """Recursively extract entities from AST nodes."""

        if node.type == "class":
            self._extract_class(
                node,
                code,
                file_path,
                entities,
                relationships,
                imports,
                errors,
                parent_id,
            )
            return  # Don't recurse, _extract_class handles children

        elif node.type == "module":
            self._extract_module(
                node,
                code,
                file_path,
                entities,
                relationships,
                imports,
                errors,
                parent_id,
            )
            return  # Don't recurse, _extract_module handles children

        elif node.type == "method":
            self._extract_method(
                node,
                code,
                file_path,
                entities,
                relationships,
                parent_id,
                current_class_id,
                is_singleton=False,
            )
            return

        elif node.type == "singleton_method":
            self._extract_method(
                node,
                code,
                file_path,
                entities,
                relationships,
                parent_id,
                current_class_id,
                is_singleton=True,
            )
            return

        # Recurse into children
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
        entities: list[Entity],
        relationships: list[Relationship],
        imports: list[str],
        errors: list[str],
        parent_id: str | None,
    ) -> None:
        """Extract a Ruby class."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        class_name = self._get_node_text(name_node, code)
        class_id = self._generate_id("class")

        # Extract superclass if present
        superclass = None
        superclass_node = node.child_by_field_name("superclass")
        if superclass_node:
            superclass = self._get_node_text(superclass_node, code)

        # Extract docstring (comment before class)
        docstring = self._get_preceding_comment(node, code)

        class_entity = ClassEntity(
            id=EntityId(value=class_id),
            name=class_name,
            type=EntityType.CLASS,
            location=Location(
                file=file_path,
                line=node.start_point[0] + 1,
                column=node.start_point[1],
            ),
            docstring=docstring,
            bases=[superclass] if superclass else [],
        )
        entities.append(class_entity)

        # Add CONTAINS relationship from parent
        if parent_id:
            relationships.append(
                Relationship(
                    source_id=EntityId(value=parent_id),
                    target_id=EntityId(value=class_id),
                    type=RelationshipType.CONTAINS,
                )
            )

        # Add INHERITS relationship if superclass exists
        if superclass:
            relationships.append(
                Relationship(
                    source_id=EntityId(value=class_id),
                    target_id=EntityId(value=f"external:{superclass}"),
                    type=RelationshipType.INHERITS,
                )
            )

        # Extract class body
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
                    parent_id=class_id,
                    current_class_id=class_id,
                )

    def _extract_module(
        self,
        node: Node,
        code: str,
        file_path: str,
        entities: list[Entity],
        relationships: list[Relationship],
        imports: list[str],
        errors: list[str],
        parent_id: str | None,
    ) -> None:
        """Extract a Ruby module."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        module_name = self._get_node_text(name_node, code)
        module_id = self._generate_id("module")

        docstring = self._get_preceding_comment(node, code)

        module_entity = ModuleEntity(
            id=EntityId(value=module_id),
            name=module_name,
            type=EntityType.MODULE,
            location=Location(
                file=file_path,
                line=node.start_point[0] + 1,
                column=node.start_point[1],
            ),
            file_path=file_path,
            docstring=docstring,
        )
        entities.append(module_entity)

        # Add CONTAINS relationship from parent
        if parent_id:
            relationships.append(
                Relationship(
                    source_id=EntityId(value=parent_id),
                    target_id=EntityId(value=module_id),
                    type=RelationshipType.CONTAINS,
                )
            )

        # Extract module body
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
                    parent_id=module_id,
                    current_class_id=None,
                )

    def _extract_method(
        self,
        node: Node,
        code: str,
        file_path: str,
        entities: list[Entity],
        relationships: list[Relationship],
        parent_id: str | None,
        current_class_id: str | None,
        is_singleton: bool,
    ) -> None:
        """Extract a Ruby method."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        method_name = self._get_node_text(name_node, code)

        # Extract parameters
        parameters: list[tuple[str, str | None]] = []
        params_node = node.child_by_field_name("parameters")
        if params_node:
            for param in params_node.children:
                if param.type in (
                    "identifier",
                    "optional_parameter",
                    "splat_parameter",
                    "hash_splat_parameter",
                    "block_parameter",
                    "keyword_parameter",
                ):
                    param_name = self._get_node_text(param, code)
                    # Remove leading *, **, &
                    param_name = param_name.lstrip("*&")
                    if "=" in param_name:
                        param_name = param_name.split("=")[0].strip()
                    if ":" in param_name:
                        param_name = param_name.split(":")[0].strip()
                    if param_name:
                        parameters.append((param_name, None))

        # Get docstring
        docstring = self._get_preceding_comment(node, code)

        # Determine if this is a method (in class) or function (standalone)
        if current_class_id:
            method_id = self._generate_id("method")
            entity = MethodEntity(
                id=EntityId(value=method_id),
                name=method_name,
                type=EntityType.METHOD,
                location=Location(
                    file=file_path,
                    line=node.start_point[0] + 1,
                    column=node.start_point[1],
                ),
                class_id=EntityId(value=current_class_id),
                parameters=parameters,
                docstring=docstring,
                is_static=is_singleton,
            )
        else:
            method_id = self._generate_id("function")
            entity = FunctionEntity(
                id=EntityId(value=method_id),
                name=method_name,
                type=EntityType.FUNCTION,
                location=Location(
                    file=file_path,
                    line=node.start_point[0] + 1,
                    column=node.start_point[1],
                ),
                parameters=parameters,
                docstring=docstring,
            )

        entities.append(entity)

        # Add CONTAINS relationship from parent
        if parent_id:
            relationships.append(
                Relationship(
                    source_id=EntityId(value=parent_id),
                    target_id=EntityId(value=method_id),
                    type=RelationshipType.CONTAINS,
                )
            )

    def _get_preceding_comment(self, node: Node, code: str) -> str | None:
        """Get comment immediately preceding a node."""
        # Look for comment in previous sibling
        prev = node.prev_sibling
        if prev and prev.type == "comment":
            comment = self._get_node_text(prev, code)
            # Remove # prefix
            return comment.lstrip("#").strip()
        return None

    def _extract_calls_relationships(
        self,
        node: Node,
        code: str,
        relationships: list[Relationship],
        method_name_to_id: dict[str, EntityId],
    ) -> None:
        """Extract method call relationships."""
        if node.type == "call":
            method_node = node.child_by_field_name("method")
            if method_node:
                method_name = self._get_node_text(method_node, code)

                # Find caller (enclosing method/function)
                caller_id = self._find_enclosing_method(node, code, method_name_to_id)

                if caller_id and method_name in method_name_to_id:
                    relationships.append(
                        Relationship(
                            source_id=caller_id,
                            target_id=method_name_to_id[method_name],
                            type=RelationshipType.CALLS,
                        )
                    )

        # Recurse into children
        for child in node.children:
            self._extract_calls_relationships(
                child,
                code,
                relationships,
                method_name_to_id,
            )

    def _find_enclosing_method(
        self,
        node: Node,
        code: str,
        method_name_to_id: dict[str, EntityId],
    ) -> EntityId | None:
        """Find the enclosing method of a node."""
        current = node.parent
        while current:
            if current.type in ("method", "singleton_method"):
                name_node = current.child_by_field_name("name")
                if name_node:
                    name = self._get_node_text(name_node, code)
                    if name in method_name_to_id:
                        return method_name_to_id[name]
            current = current.parent
        return None

    def _extract_imports_relationships(
        self,
        node: Node,
        code: str,
        relationships: list[Relationship],
        module_id: EntityId,
    ) -> None:
        """Extract require/require_relative relationships."""
        if node.type == "call":
            method_node = node.child_by_field_name("method")
            if method_node:
                method_name = self._get_node_text(method_node, code)
                if method_name in ("require", "require_relative"):
                    args_node = node.child_by_field_name("arguments")
                    if args_node:
                        for arg in args_node.children:
                            if arg.type == "string":
                                # Get string content without quotes
                                import_path = self._get_node_text(arg, code)
                                import_path = import_path.strip("'\"")
                                relationships.append(
                                    Relationship(
                                        source_id=module_id,
                                        target_id=EntityId(value=f"external:{import_path}"),
                                        type=RelationshipType.IMPORTS,
                                    )
                                )

        # Recurse into children
        for child in node.children:
            self._extract_imports_relationships(
                child,
                code,
                relationships,
                module_id,
            )
