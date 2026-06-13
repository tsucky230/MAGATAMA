"""Java Parser using tree-sitter.

This module provides Java parsing capabilities for
extracting entities from Java source code.
"""

from pathlib import Path

import tree_sitter_java as ts_java
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


class JavaParser:
    """Parser for Java source code using tree-sitter.

    Extracts:
    - Classes
    - Interfaces
    - Methods
    - Constructors
    - Fields
    - Import statements
    - Package declarations
    """

    def __init__(self) -> None:
        """Initialize the Java parser."""
        self._language = Language(ts_java.language())
        self._parser = Parser()
        self._parser.language = self._language
        self._entity_counter = 0

    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse a Java file.

        Args:
            file_path: Path to the Java file

        Returns:
            ParseResult with extracted entities
        """
        content = file_path.read_text(encoding="utf-8")
        return self.parse_string(content, str(file_path))

    def parse_string(self, code: str, file_path: str = "<string>") -> ParseResult:
        """Parse Java code from a string.

        Args:
            code: Java source code
            file_path: Path for location information

        Returns:
            ParseResult with extracted entities
        """
        tree = self._parser.parse(code.encode("utf-8"))

        entities: list[Entity] = []
        relationships: list[Relationship] = []
        imports: list[str] = []
        errors: list[str] = []

        # Extract package name
        package_name = self._extract_package(tree.root_node, code)

        # Create module entity for the file
        module_name = package_name if package_name else Path(file_path).stem
        module_id = self._generate_id("module")
        module_entity = ModuleEntity(
            id=EntityId(value=module_id),
            name=module_name,
            type=EntityType.MODULE,
            location=Location(file=file_path, line=1, column=0),
            file_path=file_path,
        )
        entities.append(module_entity)

        # Extract imports first
        self._extract_imports(tree.root_node, code, imports)

        # Add IMPORTS relationships
        for imp in imports:
            relationships.append(
                Relationship(
                    source_id=EntityId(value=module_id),
                    target_id=EntityId(value=f"external:{imp}"),
                    type=RelationshipType.IMPORTS,
                )
            )

        # Extract entities from AST
        self._extract_from_node(
            tree.root_node,
            code,
            file_path,
            entities,
            relationships,
            errors,
            parent_id=module_id,
        )

        # Build method name -> EntityId map for CALLS relationships
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

    def _extract_package(self, node: Node, code: str) -> str | None:
        """Extract package declaration."""
        for child in node.children:
            if child.type == "package_declaration":
                for subchild in child.children:
                    if subchild.type == "scoped_identifier" or subchild.type == "identifier":
                        return self._get_node_text(subchild, code)
        return None

    def _extract_imports(self, node: Node, code: str, imports: list[str]) -> None:
        """Extract import statements."""
        for child in node.children:
            if child.type == "import_declaration":
                for subchild in child.children:
                    if subchild.type in ("scoped_identifier", "identifier"):
                        import_name = self._get_node_text(subchild, code)
                        imports.append(import_name)
                        break

    def _extract_from_node(
        self,
        node: Node,
        code: str,
        file_path: str,
        entities: list[Entity],
        relationships: list[Relationship],
        errors: list[str],
        parent_id: str | None = None,
        current_class_id: str | None = None,
    ) -> None:
        """Recursively extract entities from AST nodes."""

        if node.type == "class_declaration":
            self._extract_class(
                node,
                code,
                file_path,
                entities,
                relationships,
                errors,
                parent_id,
            )
            return

        elif node.type == "interface_declaration":
            self._extract_interface(
                node,
                code,
                file_path,
                entities,
                relationships,
                errors,
                parent_id,
            )
            return

        elif node.type == "enum_declaration":
            self._extract_enum(
                node,
                code,
                file_path,
                entities,
                relationships,
                errors,
                parent_id,
            )
            return

        elif node.type == "method_declaration":
            self._extract_method(
                node,
                code,
                file_path,
                entities,
                relationships,
                parent_id,
                current_class_id,
            )
            return

        elif node.type == "constructor_declaration":
            self._extract_constructor(
                node,
                code,
                file_path,
                entities,
                relationships,
                parent_id,
                current_class_id,
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
        errors: list[str],
        parent_id: str | None,
    ) -> None:
        """Extract a Java class."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        class_name = self._get_node_text(name_node, code)
        class_id = self._generate_id("class")

        # Extract modifiers
        modifiers: list[str] = []
        for child in node.children:
            if child.type == "modifiers":
                for mod in child.children:
                    modifiers.append(self._get_node_text(mod, code))

        # Extract superclass
        bases: list[str] = []
        superclass_node = node.child_by_field_name("superclass")
        if superclass_node:
            # superclass is type_identifier
            for child in superclass_node.children:
                if child.type in ("type_identifier", "scoped_type_identifier"):
                    bases.append(self._get_node_text(child, code))

        # Extract implemented interfaces
        interfaces_node = node.child_by_field_name("interfaces")
        if interfaces_node:
            for child in interfaces_node.children:
                if child.type in ("type_identifier", "scoped_type_identifier"):
                    bases.append(self._get_node_text(child, code))

        # Extract Javadoc
        docstring = self._get_javadoc(node, code)

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
            bases=bases,
            is_abstract="abstract" in modifiers,
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

        # Add INHERITS/IMPLEMENTS relationships
        for base in bases:
            relationships.append(
                Relationship(
                    source_id=EntityId(value=class_id),
                    target_id=EntityId(value=f"external:{base}"),
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
                    errors,
                    parent_id=class_id,
                    current_class_id=class_id,
                )

    def _extract_interface(
        self,
        node: Node,
        code: str,
        file_path: str,
        entities: list[Entity],
        relationships: list[Relationship],
        errors: list[str],
        parent_id: str | None,
    ) -> None:
        """Extract a Java interface."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        interface_name = self._get_node_text(name_node, code)
        interface_id = self._generate_id("interface")

        # Extract Javadoc
        docstring = self._get_javadoc(node, code)

        # Extract extended interfaces
        bases: list[str] = []
        extends_node = node.child_by_field_name("type_parameters")
        for child in node.children:
            if child.type == "extends_interfaces":
                for subchild in child.children:
                    if subchild.type in ("type_identifier", "scoped_type_identifier"):
                        bases.append(self._get_node_text(subchild, code))

        interface_entity = InterfaceEntity(
            id=EntityId(value=interface_id),
            name=interface_name,
            type=EntityType.INTERFACE,
            location=Location(
                file=file_path,
                line=node.start_point[0] + 1,
                column=node.start_point[1],
            ),
            docstring=docstring,
            bases=bases,
        )
        entities.append(interface_entity)

        # Add CONTAINS relationship from parent
        if parent_id:
            relationships.append(
                Relationship(
                    source_id=EntityId(value=parent_id),
                    target_id=EntityId(value=interface_id),
                    type=RelationshipType.CONTAINS,
                )
            )

        # Extract interface body
        body_node = node.child_by_field_name("body")
        if body_node:
            for child in body_node.children:
                self._extract_from_node(
                    child,
                    code,
                    file_path,
                    entities,
                    relationships,
                    errors,
                    parent_id=interface_id,
                    current_class_id=interface_id,
                )

    def _extract_enum(
        self,
        node: Node,
        code: str,
        file_path: str,
        entities: list[Entity],
        relationships: list[Relationship],
        errors: list[str],
        parent_id: str | None,
    ) -> None:
        """Extract a Java enum."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        enum_name = self._get_node_text(name_node, code)
        enum_id = self._generate_id("class")

        docstring = self._get_javadoc(node, code)

        # Treat enum as a class
        enum_entity = ClassEntity(
            id=EntityId(value=enum_id),
            name=enum_name,
            type=EntityType.CLASS,
            location=Location(
                file=file_path,
                line=node.start_point[0] + 1,
                column=node.start_point[1],
            ),
            docstring=docstring,
            bases=["Enum"],
        )
        entities.append(enum_entity)

        # Add CONTAINS relationship from parent
        if parent_id:
            relationships.append(
                Relationship(
                    source_id=EntityId(value=parent_id),
                    target_id=EntityId(value=enum_id),
                    type=RelationshipType.CONTAINS,
                )
            )

        # Extract enum body
        body_node = node.child_by_field_name("body")
        if body_node:
            for child in body_node.children:
                self._extract_from_node(
                    child,
                    code,
                    file_path,
                    entities,
                    relationships,
                    errors,
                    parent_id=enum_id,
                    current_class_id=enum_id,
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
    ) -> None:
        """Extract a Java method."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        method_name = self._get_node_text(name_node, code)

        # Extract modifiers
        modifiers: list[str] = []
        for child in node.children:
            if child.type == "modifiers":
                for mod in child.children:
                    mod_text = self._get_node_text(mod, code)
                    if mod_text not in ("@Override", "@Deprecated"):
                        modifiers.append(mod_text)

        # Extract return type
        return_type = None
        type_node = node.child_by_field_name("type")
        if type_node:
            return_type = self._get_node_text(type_node, code)

        # Extract parameters
        parameters: list[tuple[str, str | None]] = []
        params_node = node.child_by_field_name("parameters")
        if params_node:
            for param in params_node.children:
                if param.type == "formal_parameter":
                    param_name_node = param.child_by_field_name("name")
                    param_type_node = param.child_by_field_name("type")
                    if param_name_node:
                        param_name = self._get_node_text(param_name_node, code)
                        param_type = None
                        if param_type_node:
                            param_type = self._get_node_text(param_type_node, code)
                        parameters.append((param_name, param_type))

        # Get Javadoc
        docstring = self._get_javadoc(node, code)

        method_id = self._generate_id("method")

        if current_class_id:
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
                return_type=return_type,
                docstring=docstring,
                is_static="static" in modifiers,
                is_abstract="abstract" in modifiers,
            )
        else:
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
                return_type=return_type,
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

    def _extract_constructor(
        self,
        node: Node,
        code: str,
        file_path: str,
        entities: list[Entity],
        relationships: list[Relationship],
        parent_id: str | None,
        current_class_id: str | None,
    ) -> None:
        """Extract a Java constructor."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        constructor_name = self._get_node_text(name_node, code)

        # Extract parameters
        parameters: list[tuple[str, str | None]] = []
        params_node = node.child_by_field_name("parameters")
        if params_node:
            for param in params_node.children:
                if param.type == "formal_parameter":
                    param_name_node = param.child_by_field_name("name")
                    param_type_node = param.child_by_field_name("type")
                    if param_name_node:
                        param_name = self._get_node_text(param_name_node, code)
                        param_type = None
                        if param_type_node:
                            param_type = self._get_node_text(param_type_node, code)
                        parameters.append((param_name, param_type))

        docstring = self._get_javadoc(node, code)

        method_id = self._generate_id("method")

        entity = MethodEntity(
            id=EntityId(value=method_id),
            name=constructor_name,
            type=EntityType.METHOD,
            location=Location(
                file=file_path,
                line=node.start_point[0] + 1,
                column=node.start_point[1],
            ),
            class_id=EntityId(value=current_class_id) if current_class_id else None,
            parameters=parameters,
            return_type=None,
            docstring=docstring,
            is_constructor=True,
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

    def _get_javadoc(self, node: Node, code: str) -> str | None:
        """Get Javadoc comment preceding a node."""
        prev = node.prev_sibling
        while prev:
            if prev.type == "block_comment":
                comment = self._get_node_text(prev, code)
                if comment.startswith("/**"):
                    # Clean up Javadoc
                    lines = comment.split("\n")
                    cleaned_lines = []
                    for line in lines:
                        line = line.strip()
                        if line.startswith("/**"):
                            line = line[3:].strip()
                        elif line.startswith("*/"):
                            continue
                        elif line.startswith("*"):
                            line = line[1:].strip()
                        if line:
                            cleaned_lines.append(line)
                    return "\n".join(cleaned_lines) if cleaned_lines else None
                break
            elif prev.type == "line_comment":
                comment = self._get_node_text(prev, code)
                return comment.lstrip("/").strip()
            elif prev.type not in ("modifiers",):
                break
            prev = prev.prev_sibling
        return None

    def _extract_calls_relationships(
        self,
        node: Node,
        code: str,
        relationships: list[Relationship],
        method_name_to_id: dict[str, EntityId],
    ) -> None:
        """Extract method call relationships."""
        if node.type == "method_invocation":
            name_node = node.child_by_field_name("name")
            if name_node:
                method_name = self._get_node_text(name_node, code)

                # Find caller
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
            if current.type in ("method_declaration", "constructor_declaration"):
                name_node = current.child_by_field_name("name")
                if name_node:
                    name = self._get_node_text(name_node, code)
                    if name in method_name_to_id:
                        return method_name_to_id[name]
            current = current.parent
        return None
