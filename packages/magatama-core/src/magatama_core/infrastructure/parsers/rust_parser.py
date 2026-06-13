"""Rust Parser using tree-sitter.

This module provides Rust parsing capabilities for
extracting entities from Rust source code.
"""

from pathlib import Path

import tree_sitter_rust as ts_rust
from tree_sitter import Language, Node, Parser

from magatama_core.domain.entities import (
    ClassEntity,
    Entity,
    EntityType,
    EnumEntity,
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


class RustParser:
    """Parser for Rust source code using tree-sitter.

    Extracts:
    - Functions (fn)
    - Structs
    - Enums
    - Traits (as interfaces)
    - Impl blocks and methods
    - Type aliases
    - Modules
    """

    def __init__(self) -> None:
        """Initialize the Rust parser."""
        self._language = Language(ts_rust.language())
        self._parser = Parser()
        self._parser.language = self._language
        self._entity_counter = 0

    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse a Rust file.

        Args:
            file_path: Path to the Rust file

        Returns:
            ParseResult with extracted entities
        """
        content = file_path.read_text(encoding="utf-8")
        return self.parse_string(content, str(file_path))

    def parse_string(self, code: str, file_path: str = "<string>") -> ParseResult:
        """Parse Rust code from a string.

        Args:
            code: Rust source code
            file_path: Path for location information

        Returns:
            ParseResult with extracted entities
        """
        tree = self._parser.parse(code.encode("utf-8"))

        entities: list[Entity] = []
        relationships: list[Relationship] = []
        imports: list[str] = []
        errors: list[str] = []

        # Create module entity
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

        # Extract use/import relationships
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
        """Recursively extract entities from AST nodes.

        Args:
            node: Current AST node
            file_path: Source file path
            entities: List to append entities to
            relationships: List to append relationships to
            imports: List to append imports to
            errors: List to append errors to
            parent_id: ID of parent entity
        """
        # Handle different node types
        if node.type == "function_item":
            self._extract_function(node, file_path, entities, relationships, parent_id)
        elif node.type == "struct_item":
            self._extract_struct(node, file_path, entities, relationships, parent_id)
        elif node.type == "enum_item":
            self._extract_enum(node, file_path, entities, relationships, parent_id)
        elif node.type == "trait_item":
            self._extract_trait(node, file_path, entities, relationships, parent_id)
        elif node.type == "impl_item":
            self._extract_impl(node, file_path, entities, relationships, parent_id)
        elif node.type == "type_item":
            self._extract_type_alias(node, file_path, entities, relationships, parent_id)
        elif node.type == "mod_item":
            self._extract_mod(node, file_path, entities, relationships, imports, errors, parent_id)
        elif node.type == "use_declaration":
            self._extract_use(node, imports)
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
        """Extract a function definition."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        name = name_node.text.decode("utf-8")
        func_id = self._generate_id("func")

        # Check visibility
        is_public = self._is_public(node)

        # Get parameters
        params_node = node.child_by_field_name("parameters")
        parameters = self._extract_parameters(params_node) if params_node else []

        # Get return type
        return_type = self._extract_return_type(node)

        # Check if async (async is inside function_modifiers node)
        is_async = self._is_async(node)

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
            is_async=is_async,
            scope="public" if is_public else "private",
        )
        entities.append(entity)

        # Add CONTAINS relationship
        if parent_id:
            relationships.append(
                Relationship(
                    source_id=EntityId(value=parent_id),
                    target_id=entity.id,
                    type=RelationshipType.CONTAINS,
                )
            )

    def _extract_struct(
        self,
        node: Node,
        file_path: str,
        entities: list[Entity],
        relationships: list[Relationship],
        parent_id: str | None,
    ) -> None:
        """Extract a struct definition (treated as class)."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        name = name_node.text.decode("utf-8")
        struct_id = self._generate_id("struct")

        is_public = self._is_public(node)

        # Get generic parameters
        generics = self._extract_generics(node)

        entity = ClassEntity(
            id=EntityId(value=struct_id),
            name=name,
            type=EntityType.CLASS,
            location=Location(
                file=file_path,
                line=node.start_point[0] + 1,
                column=node.start_point[1],
            ),
            scope="public" if is_public else "private",
            bases=[],  # Rust doesn't have class inheritance
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

    def _extract_enum(
        self,
        node: Node,
        file_path: str,
        entities: list[Entity],
        relationships: list[Relationship],
        parent_id: str | None,
    ) -> None:
        """Extract an enum definition."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        name = name_node.text.decode("utf-8")
        enum_id = self._generate_id("enum")

        is_public = self._is_public(node)

        # Get enum variants
        variants: list[str] = []
        body_node = node.child_by_field_name("body")
        if body_node:
            for child in body_node.children:
                if child.type == "enum_variant":
                    variant_name = child.child_by_field_name("name")
                    if variant_name:
                        variants.append(variant_name.text.decode("utf-8"))

        entity = EnumEntity(
            id=EntityId(value=enum_id),
            name=name,
            type=EntityType.ENUM,
            location=Location(
                file=file_path,
                line=node.start_point[0] + 1,
                column=node.start_point[1],
            ),
            scope="public" if is_public else "private",
            variants=variants,
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

    def _extract_trait(
        self,
        node: Node,
        file_path: str,
        entities: list[Entity],
        relationships: list[Relationship],
        parent_id: str | None,
    ) -> None:
        """Extract a trait definition (as interface)."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        name = name_node.text.decode("utf-8")
        trait_id = self._generate_id("trait")

        is_public = self._is_public(node)

        # Get trait method signatures
        method_signatures: list[str] = []
        body_node = node.child_by_field_name("body")
        if body_node:
            for child in body_node.children:
                if child.type == "function_signature_item":
                    method_name = child.child_by_field_name("name")
                    if method_name:
                        method_signatures.append(method_name.text.decode("utf-8"))

        entity = InterfaceEntity(
            id=EntityId(value=trait_id),
            name=name,
            type=EntityType.INTERFACE,
            location=Location(
                file=file_path,
                line=node.start_point[0] + 1,
                column=node.start_point[1],
            ),
            scope="public" if is_public else "private",
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

    def _extract_impl(
        self,
        node: Node,
        file_path: str,
        entities: list[Entity],
        relationships: list[Relationship],
        parent_id: str | None,
    ) -> None:
        """Extract methods from impl block."""
        # Get the type being implemented for
        type_node = node.child_by_field_name("type")
        if not type_node:
            return

        impl_type_name = type_node.text.decode("utf-8")

        # Find the class entity to get its ID
        class_id: EntityId | None = None
        for entity in entities:
            if entity.type == EntityType.CLASS and entity.name == impl_type_name:
                class_id = entity.id
                break

        # If we couldn't find the class, create a placeholder ID
        if class_id is None:
            class_id = EntityId(value=f"class_{impl_type_name}")

        # Find methods in the impl body
        body_node = node.child_by_field_name("body")
        if not body_node:
            return

        for child in body_node.children:
            if child.type == "function_item":
                self._extract_method(child, file_path, entities, relationships, parent_id, class_id)

    def _extract_method(
        self,
        node: Node,
        file_path: str,
        entities: list[Entity],
        relationships: list[Relationship],
        parent_id: str | None,
        class_id: EntityId,
    ) -> None:
        """Extract a method from impl block."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        name = name_node.text.decode("utf-8")
        method_id = self._generate_id("method")

        is_public = self._is_public(node)

        # Get parameters
        params_node = node.child_by_field_name("parameters")
        parameters = self._extract_parameters(params_node) if params_node else []

        # Check if static (no self parameter) - parameters are now tuples
        is_static = not any(p[0] == "self" for p in parameters)

        # Get return type
        return_type = self._extract_return_type(node)

        is_async = self._is_async(node)

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
            is_static=is_static,
            is_async=is_async,
            scope="public" if is_public else "private",
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
        node: Node,
        file_path: str,
        entities: list[Entity],
        relationships: list[Relationship],
        parent_id: str | None,
    ) -> None:
        """Extract a type alias."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        name = name_node.text.decode("utf-8")
        type_id = self._generate_id("type")

        is_public = self._is_public(node)

        # Get the aliased type
        type_node = node.child_by_field_name("type")
        definition = type_node.text.decode("utf-8") if type_node else None

        entity = TypeEntity(
            id=EntityId(value=type_id),
            name=name,
            type=EntityType.TYPE,
            location=Location(
                file=file_path,
                line=node.start_point[0] + 1,
                column=node.start_point[1],
            ),
            scope="public" if is_public else "private",
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

    def _extract_mod(
        self,
        node: Node,
        file_path: str,
        entities: list[Entity],
        relationships: list[Relationship],
        imports: list[str],
        errors: list[str],
        parent_id: str | None,
    ) -> None:
        """Extract a mod declaration."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return

        name = name_node.text.decode("utf-8")

        # Check if this is an inline mod (has body) or external mod
        body_node = node.child_by_field_name("body")
        if body_node:
            # Inline module - extract contents
            mod_id = self._generate_id("mod")
            is_public = self._is_public(node)

            entity = ModuleEntity(
                id=EntityId(value=mod_id),
                name=name,
                type=EntityType.MODULE,
                location=Location(
                    file=file_path,
                    line=node.start_point[0] + 1,
                    column=node.start_point[1],
                ),
                file_path=file_path,
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

            # Extract entities from mod body
            for child in body_node.children:
                self._extract_from_node(
                    child, file_path, entities, relationships, imports, errors, mod_id
                )

    def _extract_use(self, node: Node, imports: list[str]) -> None:
        """Extract use declarations as imports."""
        # Get the use path
        for child in node.children:
            if (
                child.type == "use_clause"
                or child.type == "scoped_use_list"
                or child.type == "identifier"
                or child.type == "scoped_identifier"
            ):
                path = child.text.decode("utf-8")
                imports.append(path)

    def _is_public(self, node: Node) -> bool:
        """Check if an item has pub visibility."""
        for child in node.children:
            if child.type == "visibility_modifier":
                return "pub" in child.text.decode("utf-8")
        return False

    def _is_async(self, node: Node) -> bool:
        """Check if a function has async modifier."""
        for child in node.children:
            if child.type == "function_modifiers":
                for mod_child in child.children:
                    if mod_child.type == "async":
                        return True
        return False

    def _extract_parameters(self, params_node: Node) -> list[tuple[str, str | None]]:
        """Extract function parameters as (name, type) tuples."""
        parameters: list[tuple[str, str | None]] = []
        for child in params_node.children:
            if child.type == "parameter":
                pattern = child.child_by_field_name("pattern")
                type_node = child.child_by_field_name("type")
                if pattern:
                    param_name = pattern.text.decode("utf-8")
                    param_type = type_node.text.decode("utf-8") if type_node else None
                    parameters.append((param_name, param_type))
            elif child.type == "self_parameter":
                parameters.append(("self", None))
        return parameters

    def _extract_return_type(self, node: Node) -> str | None:
        """Extract return type from function signature."""
        return_type_node = node.child_by_field_name("return_type")
        if return_type_node:
            # Skip the -> token
            for child in return_type_node.children:
                if child.type != "->":
                    return child.text.decode("utf-8")
        return None

    def _extract_generics(self, node: Node) -> list[str]:
        """Extract generic type parameters."""
        generics: list[str] = []
        for child in node.children:
            if child.type == "type_parameters":
                for param in child.children:
                    if param.type == "type_identifier":
                        generics.append(param.text.decode("utf-8"))
        return generics

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
                # Handle simple function name
                simple_name = func_name.split("::")[-1].split(".")[0]

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
            if current.type in ("function_item",):
                return current
            current = current.parent
        return None

    def _extract_imports_relationships(
        self,
        node: Node,
        relationships: list[Relationship],
        module_id: EntityId,
    ) -> None:
        """Extract IMPORTS relationships from use declarations."""
        self._find_use_in_node(node, relationships, module_id)

    def _find_use_in_node(
        self,
        node: Node,
        relationships: list[Relationship],
        module_id: EntityId,
    ) -> None:
        """Recursively find use statements."""
        if node.type == "use_declaration":
            # Add IMPORTS relationship
            for child in node.children:
                if child.type in ("scoped_identifier", "identifier", "use_clause"):
                    import_path = child.text.decode("utf-8")
                    # Create external entity ID for the import
                    ext_id = EntityId(value=f"ext_{import_path.replace('::', '_')}")
                    relationships.append(
                        Relationship(
                            source_id=module_id,
                            target_id=ext_id,
                            type=RelationshipType.IMPORTS,
                            metadata={"import_path": import_path},
                        )
                    )
                    break

        for child in node.children:
            self._find_use_in_node(child, relationships, module_id)
