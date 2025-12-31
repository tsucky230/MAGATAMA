"""JavaScript Parser using tree-sitter.

This module provides JavaScript/JSX parsing capabilities for
extracting entities from JavaScript source code.

It reuses the TypeScript parser logic since JavaScript is a subset
of TypeScript (for parsing purposes).
"""

from pathlib import Path
from typing import Any

import tree_sitter_javascript as ts_javascript
from tree_sitter import Language, Parser, Node

from yata_core.domain.entities import (
    Entity,
    EntityType,
    ClassEntity,
    FunctionEntity,
    MethodEntity,
    ModuleEntity,
    Relationship,
    RelationshipType,
)
from yata_core.domain.value_objects import EntityId, Location
from yata_core.infrastructure.parsers.parse_result import ParseResult


class JavaScriptParser:
    """Parser for JavaScript/JSX source code using tree-sitter.
    
    Extracts:
    - Functions (including arrow functions)
    - Classes and methods
    - Exports
    
    Note: JavaScript doesn't have interfaces, type aliases, or enums
    like TypeScript, so those are not extracted.
    """
    
    def __init__(self) -> None:
        """Initialize the JavaScript parser."""
        self._js_language = Language(ts_javascript.language())
        self._parser = Parser()
        self._parser.language = self._js_language
        self._entity_counter = 0
    
    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse a JavaScript file.
        
        Args:
            file_path: Path to the JavaScript file
            
        Returns:
            ParseResult with extracted entities
        """
        content = file_path.read_text(encoding="utf-8")
        return self.parse_string(content, str(file_path))
    
    def parse_string(self, code: str, file_path: str = "<string>") -> ParseResult:
        """Parse JavaScript code from a string.
        
        Args:
            code: JavaScript source code
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
        
        # Extract IMPORTS relationships
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
        """Recursively extract entities from AST nodes."""
        
        # Function declarations
        if node.type == "function_declaration":
            entity = self._extract_function(node, file_path)
            if entity:
                entities.append(entity)
                if parent_id:
                    relationships.append(Relationship(
                        source_id=EntityId(value=parent_id),
                        target_id=entity.id,
                        type=RelationshipType.CONTAINS,
                    ))
        
        # Arrow functions assigned to variables
        elif node.type == "lexical_declaration":
            for child in node.children:
                if child.type == "variable_declarator":
                    name_node = child.child_by_field_name("name")
                    value_node = child.child_by_field_name("value")
                    if name_node and value_node and value_node.type == "arrow_function":
                        entity = self._extract_arrow_function(
                            name_node, value_node, node, file_path
                        )
                        if entity:
                            entities.append(entity)
                            if parent_id:
                                relationships.append(Relationship(
                                    source_id=EntityId(value=parent_id),
                                    target_id=entity.id,
                                    type=RelationshipType.CONTAINS,
                                ))
        
        # Class declarations
        elif node.type == "class_declaration":
            entity, methods = self._extract_class(node, file_path)
            if entity:
                entities.append(entity)
                entities.extend(methods)
                if parent_id:
                    relationships.append(Relationship(
                        source_id=EntityId(value=parent_id),
                        target_id=entity.id,
                        type=RelationshipType.CONTAINS,
                    ))
                for method in methods:
                    relationships.append(Relationship(
                        source_id=entity.id,
                        target_id=method.id,
                        type=RelationshipType.CONTAINS,
                    ))
        
        # Import statements
        elif node.type == "import_statement":
            import_text = node.text.decode("utf-8") if node.text else ""
            imports.append(import_text)
        
        # Export statements - recurse into exported items
        elif node.type in ("export_statement", "export_declaration"):
            for child in node.children:
                self._extract_from_node(
                    child, file_path, entities, relationships,
                    imports, errors, parent_id
                )
            return  # Don't recurse again below
        
        # Recurse into children
        for child in node.children:
            self._extract_from_node(
                child, file_path, entities, relationships,
                imports, errors, parent_id
            )
    
    def _extract_function(self, node: Node, file_path: str) -> FunctionEntity | None:
        """Extract a function entity from an AST node."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None
        
        name = name_node.text.decode("utf-8") if name_node.text else ""
        if not name:
            return None
        
        # Get parameters as list of (name, type) tuples
        # JavaScript doesn't have type annotations, so type is always None
        params_node = node.child_by_field_name("parameters")
        parameters: list[tuple[str, str | None]] = []
        if params_node:
            for param in params_node.children:
                if param.type == "identifier":
                    param_name = param.text.decode("utf-8") if param.text else ""
                    if param_name:
                        parameters.append((param_name, None))
                elif param.type == "assignment_pattern":
                    # Default parameter: name = value
                    left = param.child_by_field_name("left")
                    if left and left.text:
                        parameters.append((left.text.decode("utf-8"), None))
                elif param.type == "rest_pattern":
                    # Rest parameter: ...args
                    for child in param.children:
                        if child.type == "identifier" and child.text:
                            parameters.append((f"...{child.text.decode('utf-8')}", None))
                            break
        
        # Check for async
        is_async = any(
            child.type == "async" for child in node.children
        )
        
        return FunctionEntity(
            id=EntityId(value=self._generate_id("func")),
            name=name,
            type=EntityType.FUNCTION,
            location=Location(
                file=file_path,
                line=node.start_point[0] + 1,
                column=node.start_point[1],
            ),
            parameters=parameters,
            return_type=None,  # JavaScript doesn't have return type annotations
            is_async=is_async,
        )
    
    def _extract_arrow_function(
        self,
        name_node: Node,
        arrow_node: Node,
        decl_node: Node,
        file_path: str,
    ) -> FunctionEntity | None:
        """Extract an arrow function assigned to a variable."""
        name = name_node.text.decode("utf-8") if name_node.text else ""
        if not name:
            return None
        
        # Get parameters
        params_node = arrow_node.child_by_field_name("parameters")
        parameters: list[tuple[str, str | None]] = []
        if params_node:
            for param in params_node.children:
                if param.type == "identifier":
                    param_name = param.text.decode("utf-8") if param.text else ""
                    if param_name:
                        parameters.append((param_name, None))
        
        # Check for async
        is_async = any(
            child.type == "async" for child in arrow_node.children
        )
        
        return FunctionEntity(
            id=EntityId(value=self._generate_id("func")),
            name=name,
            type=EntityType.FUNCTION,
            location=Location(
                file=file_path,
                line=decl_node.start_point[0] + 1,
                column=decl_node.start_point[1],
            ),
            parameters=parameters,
            return_type=None,
            is_async=is_async,
        )
    
    def _extract_class(
        self, node: Node, file_path: str
    ) -> tuple[ClassEntity | None, list[MethodEntity]]:
        """Extract a class entity and its methods."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None, []
        
        name = name_node.text.decode("utf-8") if name_node.text else ""
        if not name:
            return None, []
        
        # Get base class (extends) - JavaScript uses class_heritage
        bases: list[str] = []
        for child in node.children:
            if child.type == "class_heritage":
                # Look for the identifier after "extends"
                for heritage_child in child.children:
                    if heritage_child.type == "identifier" and heritage_child.text:
                        bases.append(heritage_child.text.decode("utf-8"))
        
        class_id = self._generate_id("class")
        class_entity = ClassEntity(
            id=EntityId(value=class_id),
            name=name,
            type=EntityType.CLASS,
            location=Location(
                file=file_path,
                line=node.start_point[0] + 1,
                column=node.start_point[1],
            ),
            bases=bases,
        )
        
        # Extract methods
        methods: list[MethodEntity] = []
        body = node.child_by_field_name("body")
        if body:
            for child in body.children:
                if child.type == "method_definition":
                    method = self._extract_method(child, file_path, class_id)
                    if method:
                        methods.append(method)
        
        return class_entity, methods
    
    def _extract_method(
        self, node: Node, file_path: str, class_id: str
    ) -> MethodEntity | None:
        """Extract a method entity."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None
        
        name = name_node.text.decode("utf-8") if name_node.text else ""
        if not name:
            return None
        
        # Get parameters
        params_node = node.child_by_field_name("parameters")
        parameters: list[tuple[str, str | None]] = []
        if params_node:
            for param in params_node.children:
                if param.type == "identifier":
                    param_name = param.text.decode("utf-8") if param.text else ""
                    if param_name:
                        parameters.append((param_name, None))
        
        # Check for async
        is_async = any(child.type == "async" for child in node.children)
        
        # Check for static
        is_static = any(child.type == "static" for child in node.children)
        
        return MethodEntity(
            id=EntityId(value=self._generate_id("method")),
            name=name,
            type=EntityType.METHOD,
            location=Location(
                file=file_path,
                line=node.start_point[0] + 1,
                column=node.start_point[1],
            ),
            class_id=EntityId(value=class_id),
            parameters=parameters,
            is_async=is_async,
            is_static=is_static,
        )

    def _extract_calls_relationships(
        self,
        root: Node,
        code: str,
        relationships: list[Relationship],
        function_name_to_id: dict[str, EntityId],
    ) -> None:
        """
        Extract CALLS relationships from function bodies.
        
        Detects function calls within function definitions and creates
        CALLS relationships between the caller and callee.
        """
        self._find_calls_in_node(root, code, relationships, function_name_to_id, current_function_id=None)

    def _find_calls_in_node(
        self,
        node: Node,
        code: str,
        relationships: list[Relationship],
        function_name_to_id: dict[str, EntityId],
        current_function_id: EntityId | None,
    ) -> None:
        """Recursively find call nodes and create CALLS relationships."""
        
        # Function/method definition nodes
        if node.type in ("function_declaration", "method_definition", "arrow_function"):
            # Get the function's name
            name_node = node.child_by_field_name("name")
            func_name = ""
            if name_node and name_node.text:
                func_name = name_node.text.decode("utf-8")
            
            func_id = function_name_to_id.get(func_name)
            
            # Process function body with this function as current
            body = node.child_by_field_name("body")
            if body and func_id:
                for child in body.children:
                    self._find_calls_in_node(child, code, relationships, function_name_to_id, func_id)
            elif body:
                # Still traverse body even without func_id
                for child in body.children:
                    self._find_calls_in_node(child, code, relationships, function_name_to_id, current_function_id)
        
        elif node.type == "call_expression":
            # Found a function call
            if current_function_id:
                callee_name = self._extract_call_name(node)
                callee_id = function_name_to_id.get(callee_name)
                
                if callee_id and callee_id != current_function_id:
                    relationship = Relationship(
                        source_id=current_function_id,
                        target_id=callee_id,
                        type=RelationshipType.CALLS,
                        metadata={"call_name": callee_name}
                    )
                    # Avoid duplicates
                    if relationship not in relationships:
                        relationships.append(relationship)
            
            # Continue traversing call arguments
            for child in node.children:
                self._find_calls_in_node(child, code, relationships, function_name_to_id, current_function_id)
        
        elif node.type == "class_declaration":
            # Process class methods
            body = node.child_by_field_name("body")
            if body:
                for child in body.children:
                    self._find_calls_in_node(child, code, relationships, function_name_to_id, current_function_id)
        
        else:
            # Continue traversing
            for child in node.children:
                self._find_calls_in_node(child, code, relationships, function_name_to_id, current_function_id)

    def _extract_call_name(self, call_node: Node) -> str:
        """
        Extract the function name from a call node.
        
        Handles:
        - Simple calls: foo()
        - Attribute calls: obj.method()
        - this.method() calls
        """
        func_node = call_node.child_by_field_name("function")
        if not func_node:
            return ""
        
        if func_node.type == "identifier" and func_node.text:
            return func_node.text.decode("utf-8")
        elif func_node.type == "member_expression":
            # Get the last property (method name)
            property_node = func_node.child_by_field_name("property")
            if property_node and property_node.text:
                return property_node.text.decode("utf-8")
        
        return ""

    def _extract_imports_relationships(
        self,
        root: Node,
        relationships: list[Relationship],
        module_id: EntityId,
    ) -> None:
        """
        Extract IMPORTS relationships from import statements.
        
        Creates relationships from the current module to imported modules.
        """
        for child in root.children:
            if child.type == "import_statement":
                # import x from "module"
                source_node = child.child_by_field_name("source")
                if source_node and source_node.text:
                    module_name = source_node.text.decode("utf-8").strip("'\"")
                    
                    # Get imported names
                    imported_names: list[str] = []
                    
                    # Check for import clause
                    for import_child in child.children:
                        if import_child.type == "import_clause":
                            for clause_child in import_child.children:
                                if clause_child.type == "identifier" and clause_child.text:
                                    # Default import
                                    imported_names.append(clause_child.text.decode("utf-8"))
                                elif clause_child.type == "named_imports":
                                    for spec in clause_child.children:
                                        if spec.type == "import_specifier":
                                            name_node = spec.child_by_field_name("name")
                                            if name_node and name_node.text:
                                                imported_names.append(name_node.text.decode("utf-8"))
                                elif clause_child.type == "namespace_import":
                                    # import * as x
                                    name_node = clause_child.child_by_field_name("name")
                                    if name_node and name_node.text:
                                        imported_names.append(f"* as {name_node.text.decode('utf-8')}")
                    
                    target_id = EntityId(value=f"external:{module_name}")
                    relationship = Relationship(
                        source_id=module_id,
                        target_id=target_id,
                        type=RelationshipType.IMPORTS,
                        metadata={
                            "import_type": "import",
                            "module_name": module_name,
                            "imported_names": imported_names,
                        }
                    )
                    if relationship not in relationships:
                        relationships.append(relationship)
