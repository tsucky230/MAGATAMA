"""
Python Parser using Tree-sitter

REQ-KGC-001: Entity extraction from Python code.
Uses Tree-sitter for robust AST parsing.
"""

from __future__ import annotations

from pathlib import Path

import tree_sitter_python as tspython
from tree_sitter import Language, Node, Parser

from magatama_core.domain.entities.base import Entity
from magatama_core.domain.entities.code_entities import (
    ClassEntity,
    FunctionEntity,
    MethodEntity,
    ModuleEntity,
)
from magatama_core.domain.entities.relationships import Relationship, RelationshipType
from magatama_core.domain.value_objects.ids import EntityId
from magatama_core.domain.value_objects.location import Location
from magatama_core.infrastructure.parsers.parse_result import ParseResult


class PythonParser:
    """
    Parser for Python source code using Tree-sitter.

    Extracts functions, classes, methods and their metadata
    from Python source files.
    """

    def __init__(self) -> None:
        """Initialize the Python parser."""
        self._language = Language(tspython.language())
        self._parser = Parser(self._language)

    @property
    def language(self) -> str:
        """Return the language this parser handles."""
        return "python"

    def parse_string(self, code: str, file_path: str = "<string>") -> ParseResult:
        """
        Parse Python code from a string.

        Args:
            code: Python source code
            file_path: Virtual file path for location tracking

        Returns:
            ParseResult containing extracted entities
        """
        tree = self._parser.parse(code.encode("utf-8"))
        return self._extract_entities(tree.root_node, code, Path(file_path))

    def parse_file(self, path: Path) -> ParseResult:
        """
        Parse Python code from a file.

        Args:
            path: Path to the Python file

        Returns:
            ParseResult containing extracted entities
        """
        code = path.read_text(encoding="utf-8")
        tree = self._parser.parse(code.encode("utf-8"))
        return self._extract_entities(tree.root_node, code, path)

    def _extract_entities(self, root: Node, code: str, file_path: Path) -> ParseResult:
        """Extract all entities from AST."""
        result = ParseResult(file_path=file_path)

        # Track function name -> EntityId for CALLS relationships
        function_name_to_id: dict[str, EntityId] = {}

        # Extract module entity
        module_name = file_path.stem
        module_docstring = self._extract_module_docstring(root, code)
        module_entity = ModuleEntity(
            id=EntityId.generate(),
            name=module_name,
            location=Location(file=str(file_path), line=1),
            docstring=module_docstring,
            exports=[],
        )
        result.entities.append(module_entity)

        # Extract imports and IMPORTS relationships
        result.imports = self._extract_imports(root, code)
        self._extract_imports_relationships(root, code, result, module_entity.id)

        # Extract functions and classes (first pass - collect entities)
        self._visit_node(
            root,
            code,
            file_path,
            result,
            parent_class_id=None,
            function_name_to_id=function_name_to_id,
        )

        # Extract CALLS relationships (second pass)
        self._extract_calls_relationships(root, code, result, function_name_to_id)

        return result

    def _visit_node(
        self,
        node: Node,
        code: str,
        file_path: Path,
        result: ParseResult,
        parent_class_id: EntityId | None,
        function_name_to_id: dict[str, EntityId],
    ) -> None:
        """Recursively visit AST nodes."""
        if node.type == "function_definition":
            entity = self._extract_function(node, code, file_path, parent_class_id)
            result.entities.append(entity)
            # Track function/method name for CALLS detection
            if parent_class_id is not None:
                # For methods, use class.method format
                class_name = self._get_class_name_by_id(result.entities, parent_class_id)
                function_name_to_id[f"{class_name}.{entity.name}"] = entity.id
                # Add CONTAINS relationship: class contains method
                result.relationships.append(
                    Relationship(
                        source_id=parent_class_id,
                        target_id=entity.id,
                        type=RelationshipType.CONTAINS,
                    )
                )
            function_name_to_id[entity.name] = entity.id
        elif node.type == "class_definition":
            class_entity = self._extract_class(node, code, file_path)
            result.entities.append(class_entity)
            # Visit class body for methods
            body = self._find_child(node, "block")
            if body:
                for child in body.children:
                    self._visit_node(
                        child, code, file_path, result, class_entity.id, function_name_to_id
                    )
        else:
            # Continue traversing
            for child in node.children:
                self._visit_node(
                    child, code, file_path, result, parent_class_id, function_name_to_id
                )

    def _extract_function(
        self,
        node: Node,
        code: str,
        file_path: Path,
        parent_class_id: EntityId | None,
    ) -> FunctionEntity | MethodEntity:
        """Extract function or method from AST node."""
        name = self._get_node_text(self._find_child(node, "identifier"), code)

        # Check if async
        is_async = any(c.type == "async" for c in node.children)

        # Extract parameters
        params_node = self._find_child(node, "parameters")
        parameters = self._extract_parameters(params_node, code) if params_node else []

        # Extract return type
        return_type = None
        return_node = self._find_child(node, "type")
        if return_node:
            return_type = self._get_node_text(return_node, code)

        # Extract docstring
        docstring = self._extract_docstring(node, code)

        # Extract decorators
        decorators = self._extract_decorators(node, code)

        location = Location(
            file=str(file_path),
            line=node.start_point[0] + 1,
            column=node.start_point[1],
        )

        if parent_class_id is not None:
            return MethodEntity(
                id=EntityId.generate(),
                name=name,
                location=location,
                class_id=parent_class_id,
                parameters=parameters,
                return_type=return_type,
                docstring=docstring,
                decorators=decorators,
                is_async=is_async,
            )
        else:
            return FunctionEntity(
                id=EntityId.generate(),
                name=name,
                location=location,
                parameters=parameters,
                return_type=return_type,
                docstring=docstring,
                decorators=decorators,
                is_async=is_async,
            )

    def _extract_class(
        self,
        node: Node,
        code: str,
        file_path: Path,
    ) -> ClassEntity:
        """Extract class from AST node."""
        name = self._get_node_text(self._find_child(node, "identifier"), code)

        # Extract base classes
        bases: list[str] = []
        arg_list = self._find_child(node, "argument_list")
        if arg_list:
            for child in arg_list.children:
                if child.type == "identifier" or child.type == "attribute":
                    bases.append(self._get_node_text(child, code))

        # Extract docstring
        docstring = self._extract_docstring(node, code)

        # Extract decorators
        decorators = self._extract_decorators(node, code)

        location = Location(
            file=str(file_path),
            line=node.start_point[0] + 1,
            column=node.start_point[1],
        )

        return ClassEntity(
            id=EntityId.generate(),
            name=name,
            location=location,
            bases=bases,
            docstring=docstring,
            decorators=decorators,
        )

    def _extract_parameters(self, node: Node, code: str) -> list[tuple[str, str | None]]:
        """Extract function parameters."""
        params: list[tuple[str, str | None]] = []

        for child in node.children:
            if child.type == "identifier":
                params.append((self._get_node_text(child, code), None))
            elif child.type == "typed_parameter" or child.type == "typed_default_parameter":
                name_node = self._find_child(child, "identifier")
                type_node = self._find_child(child, "type")
                name = self._get_node_text(name_node, code) if name_node else "?"
                type_hint = self._get_node_text(type_node, code) if type_node else None
                params.append((name, type_hint))
            elif child.type == "default_parameter":
                name_node = self._find_child(child, "identifier")
                name = self._get_node_text(name_node, code) if name_node else "?"
                params.append((name, None))

        return params

    def _extract_docstring(self, node: Node, code: str) -> str | None:
        """Extract docstring from function/class."""
        body = self._find_child(node, "block")
        if not body or not body.children:
            return None

        first_stmt = None
        for child in body.children:
            if child.type == "expression_statement":
                first_stmt = child
                break

        if first_stmt:
            string_node = self._find_child(first_stmt, "string")
            if string_node:
                raw = self._get_node_text(string_node, code)
                return self._clean_docstring(raw)

        return None

    def _extract_module_docstring(self, root: Node, code: str) -> str | None:
        """Extract module-level docstring."""
        for child in root.children:
            if child.type == "expression_statement":
                string_node = self._find_child(child, "string")
                if string_node:
                    raw = self._get_node_text(string_node, code)
                    return self._clean_docstring(raw)
            elif child.type not in ("comment",):
                # Stop at first non-comment, non-docstring
                break
        return None

    def _extract_decorators(self, node: Node, code: str) -> list[str]:
        """Extract decorator names."""
        decorators: list[str] = []

        # Decorators are siblings before the function/class definition
        parent = node.parent
        if parent:
            idx = parent.children.index(node)
            for i in range(idx - 1, -1, -1):
                sibling = parent.children[i]
                if sibling.type == "decorator":
                    # Get the decorator name (identifier or attribute)
                    for child in sibling.children:
                        if child.type == "identifier":
                            decorators.append(self._get_node_text(child, code))
                            break
                        elif child.type == "call":
                            func = self._find_child(child, "identifier")
                            if func:
                                decorators.append(self._get_node_text(func, code))
                            break
                        elif child.type == "attribute":
                            decorators.append(self._get_node_text(child, code))
                            break
                else:
                    break

        return list(reversed(decorators))

    def _get_class_name_by_id(self, entities: list[Entity], class_id: EntityId) -> str:
        """Get class name by its EntityId."""
        for entity in entities:
            if entity.id == class_id:
                return entity.name
        return ""

    def _extract_calls_relationships(
        self,
        root: Node,
        code: str,
        result: ParseResult,
        function_name_to_id: dict[str, EntityId],
    ) -> None:
        """
        Extract CALLS relationships from function bodies.

        Detects function calls within function definitions and creates
        CALLS relationships between the caller and callee.
        """

        # Build entity name -> id map for quick lookup
        entity_name_to_id: dict[str, EntityId] = {}
        for entity in result.entities:
            entity_name_to_id[entity.name] = entity.id

        # Merge with function_name_to_id
        entity_name_to_id.update(function_name_to_id)

        # Process each function/method entity
        self._find_calls_in_node(root, code, result, entity_name_to_id, current_function_id=None)

    def _find_calls_in_node(
        self,
        node: Node,
        code: str,
        result: ParseResult,
        entity_name_to_id: dict[str, EntityId],
        current_function_id: EntityId | None,
    ) -> None:
        """Recursively find call nodes and create CALLS relationships."""
        from magatama_core.domain.entities.relationships import Relationship, RelationshipType

        if node.type == "function_definition":
            # Get the function's entity id
            name_node = self._find_child(node, "identifier")
            func_name = self._get_node_text(name_node, code) if name_node else ""
            func_id = entity_name_to_id.get(func_name)

            # Process function body with this function as current
            body = self._find_child(node, "block")
            if body and func_id:
                for child in body.children:
                    self._find_calls_in_node(child, code, result, entity_name_to_id, func_id)
        elif node.type == "call":
            # Found a function call
            if current_function_id:
                callee_name = self._extract_call_name(node, code)
                callee_id = entity_name_to_id.get(callee_name)

                if callee_id and callee_id != current_function_id:
                    relationship = Relationship(
                        source_id=current_function_id,
                        target_id=callee_id,
                        type=RelationshipType.CALLS,
                        metadata={"call_name": callee_name},
                    )
                    # Avoid duplicates
                    if relationship not in result.relationships:
                        result.relationships.append(relationship)

            # Continue traversing call arguments
            for child in node.children:
                self._find_calls_in_node(
                    child, code, result, entity_name_to_id, current_function_id
                )
        elif node.type == "class_definition":
            # Process class methods
            body = self._find_child(node, "block")
            if body:
                for child in body.children:
                    self._find_calls_in_node(
                        child, code, result, entity_name_to_id, current_function_id
                    )
        else:
            # Continue traversing
            for child in node.children:
                self._find_calls_in_node(
                    child, code, result, entity_name_to_id, current_function_id
                )

    def _extract_call_name(self, call_node: Node, code: str) -> str:
        """
        Extract the function name from a call node.

        Handles:
        - Simple calls: foo()
        - Attribute calls: obj.method()
        - Chained calls: a.b.c()
        """
        for child in call_node.children:
            if child.type == "identifier":
                return self._get_node_text(child, code)
            elif child.type == "attribute":
                # Get the last identifier (method name)
                attr_text = self._get_node_text(child, code)
                # For self.method(), return method
                parts = attr_text.split(".")
                if len(parts) >= 2 and parts[0] == "self":
                    return parts[1]
                return parts[-1]
        return ""

    def _extract_imports(self, root: Node, code: str) -> list[str]:
        """Extract imported module names."""
        imports: list[str] = []

        for child in root.children:
            if child.type == "import_statement":
                # import x, y, z
                for name in child.children:
                    if name.type == "dotted_name":
                        imports.append(self._get_node_text(name, code).split(".")[0])
            elif child.type == "import_from_statement":
                # from x import y
                module_name = self._find_child(child, "dotted_name")
                if module_name:
                    imports.append(self._get_node_text(module_name, code).split(".")[0])

        return imports

    def _extract_imports_relationships(
        self,
        root: Node,
        code: str,
        result: ParseResult,
        module_id: EntityId,
    ) -> None:
        """
        Extract IMPORTS relationships from import statements.

        Creates relationships from the current module to imported modules/entities.
        For imports that can be resolved within the same parse (e.g., internal modules),
        the relationship points to the actual entity. For external modules, we create
        a placeholder target ID using the module name.
        """
        from magatama_core.domain.entities.relationships import Relationship, RelationshipType

        for child in root.children:
            if child.type == "import_statement":
                # import x, y, z
                for name in child.children:
                    if name.type == "dotted_name":
                        module_name = self._get_node_text(name, code)
                        # Create a target ID for the imported module
                        target_id = EntityId(value=f"external:{module_name}")
                        relationship = Relationship(
                            source_id=module_id,
                            target_id=target_id,
                            type=RelationshipType.IMPORTS,
                            metadata={
                                "import_type": "module",
                                "module_name": module_name,
                            },
                        )
                        if relationship not in result.relationships:
                            result.relationships.append(relationship)

            elif child.type == "import_from_statement":
                # from x import y, z
                # First dotted_name is the module, rest are imported names
                dotted_names = [c for c in child.children if c.type == "dotted_name"]

                if dotted_names:
                    module_node = dotted_names[0]
                    module_name = self._get_node_text(module_node, code)

                    # Get imported names from remaining dotted_names
                    imported_names: list[str] = []

                    # Check for import_list first (from x import y, z)
                    import_list = self._find_child(child, "import_list")
                    if import_list:
                        for item in import_list.children:
                            if item.type in ("dotted_name", "identifier"):
                                imported_names.append(self._get_node_text(item, code))
                            elif item.type == "aliased_import":
                                name_node = self._find_child(
                                    item, "identifier"
                                ) or self._find_child(item, "dotted_name")
                                if name_node:
                                    imported_names.append(self._get_node_text(name_node, code))
                    else:
                        # Single import case (from x import y)
                        # Get all dotted_names after the first one (module)
                        for dn in dotted_names[1:]:
                            imported_names.append(self._get_node_text(dn, code))

                        # Also check for identifiers (from x import y where y is simple identifier)
                        found_import_kw = False
                        for item in child.children:
                            if item.type == "import":
                                found_import_kw = True
                            elif found_import_kw and item.type == "identifier":
                                name = self._get_node_text(item, code)
                                if name and name not in imported_names:
                                    imported_names.append(name)

                    # Create relationship for the module
                    target_id = EntityId(value=f"external:{module_name}")
                    relationship = Relationship(
                        source_id=module_id,
                        target_id=target_id,
                        type=RelationshipType.IMPORTS,
                        metadata={
                            "import_type": "from",
                            "module_name": module_name,
                            "imported_names": imported_names,
                        },
                    )
                    if relationship not in result.relationships:
                        result.relationships.append(relationship)

    def _find_child(self, node: Node, type_name: str) -> Node | None:
        """Find first child of given type."""
        for child in node.children:
            if child.type == type_name:
                return child
        return None

    def _get_node_text(self, node: Node | None, code: str) -> str:
        """Get source text for a node."""
        if node is None:
            return ""
        return code[node.start_byte : node.end_byte]

    def _clean_docstring(self, raw: str) -> str:
        """Clean up docstring - remove quotes and extra whitespace."""
        # Remove triple quotes
        if (raw.startswith('"""') and raw.endswith('"""')) or (
            raw.startswith("'''") and raw.endswith("'''")
        ):
            raw = raw[3:-3]
        elif (raw.startswith('"') and raw.endswith('"')) or (
            raw.startswith("'") and raw.endswith("'")
        ):
            raw = raw[1:-1]

        return raw.strip()
