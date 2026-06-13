"""Go Parser using tree-sitter.

This module provides Go parsing capabilities for
extracting entities from Go source code.
"""

from pathlib import Path

import tree_sitter_go as ts_go
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
    TypeEntity,
)
from magatama_core.domain.value_objects import EntityId, Location
from magatama_core.infrastructure.parsers.parse_result import ParseResult


class GoParser:
    """Parser for Go source code using tree-sitter.

    Extracts:
    - Functions
    - Structs (as classes)
    - Interfaces
    - Methods (functions with receivers)
    - Type aliases
    - Package declarations
    """

    def __init__(self) -> None:
        """Initialize the Go parser."""
        self._language = Language(ts_go.language())
        self._parser = Parser()
        self._parser.language = self._language
        self._entity_counter = 0

    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse a Go file.

        Args:
            file_path: Path to the Go file

        Returns:
            ParseResult with extracted entities
        """
        content = file_path.read_text(encoding="utf-8")
        return self.parse_string(content, str(file_path))

    def parse_string(self, code: str, file_path: str = "<string>") -> ParseResult:
        """Parse Go code from a string.

        Args:
            code: Go source code
            file_path: Path for location information

        Returns:
            ParseResult with extracted entities
        """
        tree = self._parser.parse(code.encode("utf-8"))

        entities: list[Entity] = []
        relationships: list[Relationship] = []
        imports: list[str] = []
        errors: list[str] = []

        # Get package name
        package_name = self._extract_package_name(tree.root_node)
        if not package_name:
            package_name = Path(file_path).stem

        # Create module entity
        module_id = self._generate_id("module")
        module_entity = ModuleEntity(
            id=EntityId(value=module_id),
            name=package_name,
            type=EntityType.MODULE,
            location=Location(file=file_path, line=1, column=0),
            file_path=file_path,
        )
        entities.append(module_entity)

        # Extract entities from AST
        self._extract_from_node(
            tree.root_node,
            file_path,
            entities,
            relationships,
            imports,
            errors,
            parent_id=module_id,
        )

        # Build function name -> EntityId map
        function_name_to_id: dict[str, EntityId] = {}
        for entity in entities:
            if entity.type in (EntityType.FUNCTION, EntityType.METHOD):
                function_name_to_id[entity.name] = entity.id

        # Extract CALLS relationships
        self._extract_calls_relationships(
            tree.root_node,
            code,
            relationships,
            function_name_to_id,
        )

        # Extract import relationships
        self._extract_imports_relationships(
            tree.root_node,
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

    def _extract_package_name(self, root: Node) -> str | None:
        """Extract package name from package clause."""
        for child in root.children:
            if child.type == "package_clause":
                for pkg_child in child.children:
                    if pkg_child.type == "package_identifier":
                        return pkg_child.text.decode("utf-8")
        return None

    def _extract_from_node(
        self,
        node: Node,
        file_path: str,
        entities: list[Entity],
        relationships: list[Relationship],
        imports: list[str],
        errors: list[str],
        parent_id: str | None = None,
    ) -> None:
        """Recursively extract entities from AST nodes."""
        if node.type == "function_declaration":
            self._extract_function(node, file_path, entities, relationships, parent_id)
        elif node.type == "method_declaration":
            self._extract_method(node, file_path, entities, relationships, parent_id)
        elif node.type == "type_declaration":
            self._extract_type_declaration(node, file_path, entities, relationships, parent_id)
        elif node.type == "import_declaration":
            self._extract_imports(node, imports)
        else:
            # Recurse into children
            for child in node.children:
                self._extract_from_node(
                    child, file_path, entities, relationships, imports, errors, parent_id
                )

    def _extract_function(
        self,
        node: Node,
        file_path: str,
        entities: list[Entity],
        relationships: list[Relationship],
        parent_id: str | None,
    ) -> None:
        """Extract a function declaration."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        name = name_node.text.decode("utf-8")
        func_id = self._generate_id("func")

        # In Go, exported = starts with uppercase
        is_exported = name[0].isupper() if name else False

        # Get parameters
        params_node = node.child_by_field_name("parameters")
        parameters = self._extract_parameters(params_node) if params_node else []

        # Get return type
        return_type = self._extract_return_type(node)

        entity = FunctionEntity(
            id=EntityId(value=func_id),
            name=name,
            type=EntityType.FUNCTION,
            location=Location(
                file=file_path,
                line=node.start_point[0] + 1,
                column=node.start_point[1],
            ),
            parameters=parameters,
            return_type=return_type,
            is_async=False,  # Go doesn't have async/await
            scope="public" if is_exported else "private",
        )
        entities.append(entity)

        if parent_id:
            relationships.append(
                Relationship(
                    source_id=EntityId(value=parent_id),
                    target_id=entity.id,
                    type=RelationshipType.CONTAINS,
                )
            )

    def _extract_method(
        self,
        node: Node,
        file_path: str,
        entities: list[Entity],
        relationships: list[Relationship],
        parent_id: str | None,
    ) -> None:
        """Extract a method declaration (function with receiver)."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        name = name_node.text.decode("utf-8")
        method_id = self._generate_id("method")

        is_exported = name[0].isupper() if name else False

        # Get receiver type
        receiver_node = node.child_by_field_name("receiver")
        receiver_type_name = self._extract_receiver_type(receiver_node) if receiver_node else ""

        # Create a class_id for the receiver type
        class_id = EntityId(value=f"class_{receiver_type_name}")

        # Get parameters
        params_node = node.child_by_field_name("parameters")
        parameters = self._extract_parameters(params_node) if params_node else []

        # Get return type
        return_type = self._extract_return_type(node)

        entity = MethodEntity(
            id=EntityId(value=method_id),
            name=name,
            type=EntityType.METHOD,
            location=Location(
                file=file_path,
                line=node.start_point[0] + 1,
                column=node.start_point[1],
            ),
            class_id=class_id,
            parameters=parameters,
            return_type=return_type,
            is_static=False,  # Go methods always have receiver
            is_async=False,
            scope="public" if is_exported else "private",
        )
        entities.append(entity)

        if parent_id:
            relationships.append(
                Relationship(
                    source_id=EntityId(value=parent_id),
                    target_id=entity.id,
                    type=RelationshipType.CONTAINS,
                )
            )

    def _extract_type_declaration(
        self,
        node: Node,
        file_path: str,
        entities: list[Entity],
        relationships: list[Relationship],
        parent_id: str | None,
    ) -> None:
        """Extract type declarations (struct, interface, type alias)."""
        for child in node.children:
            if child.type == "type_spec":
                self._extract_type_spec(child, file_path, entities, relationships, parent_id)

    def _extract_type_spec(
        self,
        node: Node,
        file_path: str,
        entities: list[Entity],
        relationships: list[Relationship],
        parent_id: str | None,
    ) -> None:
        """Extract a type specification."""
        name_node = node.child_by_field_name("name")
        type_node = node.child_by_field_name("type")

        if not name_node:
            return

        name = name_node.text.decode("utf-8")
        is_exported = name[0].isupper() if name else False

        if type_node:
            if type_node.type == "struct_type":
                self._extract_struct(
                    name, type_node, file_path, entities, relationships, parent_id, is_exported
                )
            elif type_node.type == "interface_type":
                self._extract_interface(
                    name, type_node, file_path, entities, relationships, parent_id, is_exported
                )
            else:
                # Type alias
                self._extract_type_alias(
                    name, type_node, file_path, entities, relationships, parent_id, is_exported
                )

    def _extract_struct(
        self,
        name: str,
        node: Node,
        file_path: str,
        entities: list[Entity],
        relationships: list[Relationship],
        parent_id: str | None,
        is_exported: bool,
    ) -> None:
        """Extract a struct type (as class)."""
        struct_id = self._generate_id("struct")

        entity = ClassEntity(
            id=EntityId(value=struct_id),
            name=name,
            type=EntityType.CLASS,
            location=Location(
                file=file_path,
                line=node.start_point[0] + 1,
                column=node.start_point[1],
            ),
            scope="public" if is_exported else "private",
            bases=[],  # Go uses embedding, not inheritance
        )
        entities.append(entity)

        if parent_id:
            relationships.append(
                Relationship(
                    source_id=EntityId(value=parent_id),
                    target_id=entity.id,
                    type=RelationshipType.CONTAINS,
                )
            )

    def _extract_interface(
        self,
        name: str,
        node: Node,
        file_path: str,
        entities: list[Entity],
        relationships: list[Relationship],
        parent_id: str | None,
        is_exported: bool,
    ) -> None:
        """Extract an interface type."""
        interface_id = self._generate_id("interface")

        # Get interface method signatures
        method_signatures: list[str] = []
        for child in node.children:
            # Go uses method_elem or method_spec for interface methods
            if child.type in ("method_elem", "method_spec"):
                # Method name is in field_identifier
                for subchild in child.children:
                    if subchild.type == "field_identifier":
                        method_signatures.append(subchild.text.decode("utf-8"))
                        break

        entity = InterfaceEntity(
            id=EntityId(value=interface_id),
            name=name,
            type=EntityType.INTERFACE,
            location=Location(
                file=file_path,
                line=node.start_point[0] + 1,
                column=node.start_point[1],
            ),
            scope="public" if is_exported else "private",
            method_signatures=method_signatures,
        )
        entities.append(entity)

        if parent_id:
            relationships.append(
                Relationship(
                    source_id=EntityId(value=parent_id),
                    target_id=entity.id,
                    type=RelationshipType.CONTAINS,
                )
            )

    def _extract_type_alias(
        self,
        name: str,
        node: Node,
        file_path: str,
        entities: list[Entity],
        relationships: list[Relationship],
        parent_id: str | None,
        is_exported: bool,
    ) -> None:
        """Extract a type alias."""
        type_id = self._generate_id("type")

        definition = node.text.decode("utf-8")

        entity = TypeEntity(
            id=EntityId(value=type_id),
            name=name,
            type=EntityType.TYPE,
            location=Location(
                file=file_path,
                line=node.start_point[0] + 1,
                column=node.start_point[1],
            ),
            scope="public" if is_exported else "private",
            definition=definition,
        )
        entities.append(entity)

        if parent_id:
            relationships.append(
                Relationship(
                    source_id=EntityId(value=parent_id),
                    target_id=entity.id,
                    type=RelationshipType.CONTAINS,
                )
            )

    def _extract_imports(self, node: Node, imports: list[str]) -> None:
        """Extract import declarations."""
        for child in node.children:
            if child.type == "import_spec":
                path_node = child.child_by_field_name("path")
                if path_node:
                    # Remove quotes from import path
                    import_path = path_node.text.decode("utf-8").strip('"')
                    imports.append(import_path)
            elif child.type == "import_spec_list":
                for spec in child.children:
                    if spec.type == "import_spec":
                        path_node = spec.child_by_field_name("path")
                        if path_node:
                            import_path = path_node.text.decode("utf-8").strip('"')
                            imports.append(import_path)

    def _extract_receiver_type(self, receiver_node: Node) -> str:
        """Extract the receiver type name from a method."""
        for child in receiver_node.children:
            if child.type == "parameter_declaration":
                type_node = child.child_by_field_name("type")
                if type_node:
                    type_text = type_node.text.decode("utf-8")
                    # Remove pointer indicator
                    return type_text.lstrip("*")
        return ""

    def _extract_parameters(self, params_node: Node) -> list[tuple[str, str | None]]:
        """Extract function/method parameters as (name, type) tuples."""
        parameters: list[tuple[str, str | None]] = []
        for child in params_node.children:
            if child.type == "parameter_declaration":
                type_node = child.child_by_field_name("type")
                param_type = type_node.text.decode("utf-8") if type_node else None
                # Get parameter name(s)
                for param_child in child.children:
                    if param_child.type == "identifier":
                        parameters.append((param_child.text.decode("utf-8"), param_type))
        return parameters

    def _extract_return_type(self, node: Node) -> str | None:
        """Extract return type from function/method."""
        result_node = node.child_by_field_name("result")
        if result_node:
            return result_node.text.decode("utf-8")
        return None

    def _extract_calls_relationships(
        self,
        node: Node,
        code: str,
        relationships: list[Relationship],
        function_name_to_id: dict[str, EntityId],
    ) -> None:
        """Extract function call relationships."""
        self._find_calls_in_node(node, code, relationships, function_name_to_id, set())

    def _find_calls_in_node(
        self,
        node: Node,
        code: str,
        relationships: list[Relationship],
        function_name_to_id: dict[str, EntityId],
        processed_calls: set[tuple[str, str]],
    ) -> None:
        """Recursively find function calls."""
        if node.type == "call_expression":
            func_node = node.child_by_field_name("function")
            if func_node:
                func_name = func_node.text.decode("utf-8")
                # Handle method calls like obj.Method()
                simple_name = func_name.split(".")[-1]

                if simple_name in function_name_to_id:
                    # Find containing function
                    container = self._find_containing_function(node)
                    if container:
                        container_name_node = container.child_by_field_name("name")
                        if container_name_node:
                            caller_name = container_name_node.text.decode("utf-8")
                            if caller_name in function_name_to_id:
                                caller_id = function_name_to_id[caller_name]
                                callee_id = function_name_to_id[simple_name]

                                call_key = (caller_id.value, callee_id.value)
                                if call_key not in processed_calls and caller_id != callee_id:
                                    processed_calls.add(call_key)
                                    relationships.append(
                                        Relationship(
                                            source_id=caller_id,
                                            target_id=callee_id,
                                            type=RelationshipType.CALLS,
                                        )
                                    )

        for child in node.children:
            self._find_calls_in_node(
                child, code, relationships, function_name_to_id, processed_calls
            )

    def _find_containing_function(self, node: Node) -> Node | None:
        """Find the function/method containing this node."""
        current = node.parent
        while current:
            if current.type in ("function_declaration", "method_declaration"):
                return current
            current = current.parent
        return None

    def _extract_imports_relationships(
        self,
        node: Node,
        relationships: list[Relationship],
        module_id: EntityId,
    ) -> None:
        """Extract IMPORTS relationships from import declarations."""
        self._find_imports_in_node(node, relationships, module_id)

    def _find_imports_in_node(
        self,
        node: Node,
        relationships: list[Relationship],
        module_id: EntityId,
    ) -> None:
        """Recursively find import declarations."""
        if node.type == "import_declaration":
            for child in node.children:
                if child.type == "import_spec":
                    path_node = child.child_by_field_name("path")
                    if path_node:
                        import_path = path_node.text.decode("utf-8").strip('"')
                        ext_id = EntityId(value=f"ext_{import_path.replace('/', '_')}")
                        relationships.append(
                            Relationship(
                                source_id=module_id,
                                target_id=ext_id,
                                type=RelationshipType.IMPORTS,
                                metadata={"import_path": import_path},
                            )
                        )
                elif child.type == "import_spec_list":
                    for spec in child.children:
                        if spec.type == "import_spec":
                            path_node = spec.child_by_field_name("path")
                            if path_node:
                                import_path = path_node.text.decode("utf-8").strip('"')
                                ext_id = EntityId(value=f"ext_{import_path.replace('/', '_')}")
                                relationships.append(
                                    Relationship(
                                        source_id=module_id,
                                        target_id=ext_id,
                                        type=RelationshipType.IMPORTS,
                                        metadata={"import_path": import_path},
                                    )
                                )

        for child in node.children:
            self._find_imports_in_node(child, relationships, module_id)
