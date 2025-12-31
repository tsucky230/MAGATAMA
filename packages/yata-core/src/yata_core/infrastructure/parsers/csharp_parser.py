"""C# Parser using tree-sitter.

This module provides C# parsing capabilities for
extracting entities from C# source code.
"""

from pathlib import Path
from typing import Any

import tree_sitter_c_sharp as ts_csharp
from tree_sitter import Language, Parser, Node

from yata_core.domain.entities import (
    Entity,
    EntityType,
    ClassEntity,
    FunctionEntity,
    MethodEntity,
    ModuleEntity,
    InterfaceEntity,
    Relationship,
    RelationshipType,
)
from yata_core.domain.value_objects import EntityId, Location
from yata_core.infrastructure.parsers.parse_result import ParseResult


class CSharpParser:
    """Parser for C# source code using tree-sitter.
    
    Extracts:
    - Classes
    - Interfaces
    - Structs
    - Methods
    - Properties
    - Constructors
    - Using statements
    - Namespaces
    """
    
    def __init__(self) -> None:
        """Initialize the C# parser."""
        self._language = Language(ts_csharp.language())
        self._parser = Parser()
        self._parser.language = self._language
        self._entity_counter = 0
    
    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse a C# file.
        
        Args:
            file_path: Path to the C# file
            
        Returns:
            ParseResult with extracted entities
        """
        content = file_path.read_text(encoding="utf-8")
        return self.parse_string(content, str(file_path))
    
    def parse_string(self, code: str, file_path: str = "<string>") -> ParseResult:
        """Parse C# code from a string.
        
        Args:
            code: C# source code
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
        
        # Extract using directives
        self._extract_usings(tree.root_node, code, imports)
        
        # Add IMPORTS relationships
        for imp in imports:
            relationships.append(Relationship(
                source_id=EntityId(value=module_id),
                target_id=EntityId(value=f"external:{imp}"),
                type=RelationshipType.IMPORTS,
            ))
        
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
        return code[node.start_byte:node.end_byte]
    
    def _extract_usings(self, node: Node, code: str, imports: list[str]) -> None:
        """Extract using directives."""
        for child in node.children:
            if child.type == "using_directive":
                for subchild in child.children:
                    if subchild.type in ("qualified_name", "identifier"):
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
        
        if node.type == "namespace_declaration":
            self._extract_namespace(
                node, code, file_path, entities, relationships,
                errors, parent_id,
            )
            return
        
        elif node.type == "file_scoped_namespace_declaration":
            self._extract_file_scoped_namespace(
                node, code, file_path, entities, relationships,
                errors, parent_id,
            )
            return
        
        elif node.type == "class_declaration":
            self._extract_class(
                node, code, file_path, entities, relationships,
                errors, parent_id,
            )
            return
        
        elif node.type == "interface_declaration":
            self._extract_interface(
                node, code, file_path, entities, relationships,
                errors, parent_id,
            )
            return
        
        elif node.type == "struct_declaration":
            self._extract_struct(
                node, code, file_path, entities, relationships,
                errors, parent_id,
            )
            return
        
        elif node.type == "enum_declaration":
            self._extract_enum(
                node, code, file_path, entities, relationships,
                errors, parent_id,
            )
            return
        
        elif node.type == "method_declaration":
            self._extract_method(
                node, code, file_path, entities, relationships,
                parent_id, current_class_id,
            )
            return
        
        elif node.type == "constructor_declaration":
            self._extract_constructor(
                node, code, file_path, entities, relationships,
                parent_id, current_class_id,
            )
            return
        
        elif node.type == "property_declaration":
            self._extract_property(
                node, code, file_path, entities, relationships,
                parent_id, current_class_id,
            )
            return
        
        # Recurse into children
        for child in node.children:
            self._extract_from_node(
                child, code, file_path, entities, relationships,
                errors, parent_id, current_class_id,
            )
    
    def _extract_namespace(
        self,
        node: Node,
        code: str,
        file_path: str,
        entities: list[Entity],
        relationships: list[Relationship],
        errors: list[str],
        parent_id: str | None,
    ) -> None:
        """Extract a C# namespace."""
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
                file=file_path,
                line=node.start_point[0] + 1,
                column=node.start_point[1],
            ),
            file_path=file_path,
        )
        entities.append(namespace_entity)
        
        # Add CONTAINS relationship from parent
        if parent_id:
            relationships.append(Relationship(
                source_id=EntityId(value=parent_id),
                target_id=EntityId(value=namespace_id),
                type=RelationshipType.CONTAINS,
            ))
        
        # Extract namespace body
        body_node = node.child_by_field_name("body")
        if body_node:
            for child in body_node.children:
                self._extract_from_node(
                    child, code, file_path, entities, relationships,
                    errors, parent_id=namespace_id, current_class_id=None,
                )
    
    def _extract_file_scoped_namespace(
        self,
        node: Node,
        code: str,
        file_path: str,
        entities: list[Entity],
        relationships: list[Relationship],
        errors: list[str],
        parent_id: str | None,
    ) -> None:
        """Extract a C# file-scoped namespace."""
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
                file=file_path,
                line=node.start_point[0] + 1,
                column=node.start_point[1],
            ),
            file_path=file_path,
        )
        entities.append(namespace_entity)
        
        # Add CONTAINS relationship from parent
        if parent_id:
            relationships.append(Relationship(
                source_id=EntityId(value=parent_id),
                target_id=EntityId(value=namespace_id),
                type=RelationshipType.CONTAINS,
            ))
        
        # Continue extracting from remaining children in tree
        for child in node.children:
            if child != name_node and child.type != ";":
                self._extract_from_node(
                    child, code, file_path, entities, relationships,
                    errors, parent_id=namespace_id, current_class_id=None,
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
        """Extract a C# class."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        
        class_name = self._get_node_text(name_node, code)
        class_id = self._generate_id("class")
        
        # Extract modifiers
        modifiers: list[str] = []
        for child in node.children:
            if child.type == "modifier":
                modifiers.append(self._get_node_text(child, code))
        
        # Extract base types (base class and interfaces)
        bases: list[str] = []
        base_list = node.child_by_field_name("bases")
        if base_list:
            for child in base_list.children:
                if child.type in ("identifier", "qualified_name", "generic_name"):
                    bases.append(self._get_node_text(child, code))
        
        # Extract XML documentation comment
        docstring = self._get_xml_doc(node, code)
        
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
            relationships.append(Relationship(
                source_id=EntityId(value=parent_id),
                target_id=EntityId(value=class_id),
                type=RelationshipType.CONTAINS,
            ))
        
        # Add INHERITS relationships
        for base in bases:
            relationships.append(Relationship(
                source_id=EntityId(value=class_id),
                target_id=EntityId(value=f"external:{base}"),
                type=RelationshipType.INHERITS,
            ))
        
        # Extract class body
        body_node = node.child_by_field_name("body")
        if body_node:
            for child in body_node.children:
                self._extract_from_node(
                    child, code, file_path, entities, relationships,
                    errors, parent_id=class_id, current_class_id=class_id,
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
        """Extract a C# interface."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        
        interface_name = self._get_node_text(name_node, code)
        interface_id = self._generate_id("interface")
        
        # Extract base interfaces
        bases: list[str] = []
        base_list = node.child_by_field_name("bases")
        if base_list:
            for child in base_list.children:
                if child.type in ("identifier", "qualified_name", "generic_name"):
                    bases.append(self._get_node_text(child, code))
        
        docstring = self._get_xml_doc(node, code)
        
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
            relationships.append(Relationship(
                source_id=EntityId(value=parent_id),
                target_id=EntityId(value=interface_id),
                type=RelationshipType.CONTAINS,
            ))
        
        # Extract interface body
        body_node = node.child_by_field_name("body")
        if body_node:
            for child in body_node.children:
                self._extract_from_node(
                    child, code, file_path, entities, relationships,
                    errors, parent_id=interface_id, current_class_id=interface_id,
                )
    
    def _extract_struct(
        self,
        node: Node,
        code: str,
        file_path: str,
        entities: list[Entity],
        relationships: list[Relationship],
        errors: list[str],
        parent_id: str | None,
    ) -> None:
        """Extract a C# struct."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        
        struct_name = self._get_node_text(name_node, code)
        struct_id = self._generate_id("class")
        
        # Extract interfaces
        bases: list[str] = []
        base_list = node.child_by_field_name("bases")
        if base_list:
            for child in base_list.children:
                if child.type in ("identifier", "qualified_name", "generic_name"):
                    bases.append(self._get_node_text(child, code))
        
        docstring = self._get_xml_doc(node, code)
        
        # Treat struct as a class
        struct_entity = ClassEntity(
            id=EntityId(value=struct_id),
            name=struct_name,
            type=EntityType.CLASS,
            location=Location(
                file=file_path,
                line=node.start_point[0] + 1,
                column=node.start_point[1],
            ),
            docstring=docstring,
            bases=bases,
        )
        entities.append(struct_entity)
        
        # Add CONTAINS relationship from parent
        if parent_id:
            relationships.append(Relationship(
                source_id=EntityId(value=parent_id),
                target_id=EntityId(value=struct_id),
                type=RelationshipType.CONTAINS,
            ))
        
        # Extract struct body
        body_node = node.child_by_field_name("body")
        if body_node:
            for child in body_node.children:
                self._extract_from_node(
                    child, code, file_path, entities, relationships,
                    errors, parent_id=struct_id, current_class_id=struct_id,
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
        """Extract a C# enum."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        
        enum_name = self._get_node_text(name_node, code)
        enum_id = self._generate_id("class")
        
        docstring = self._get_xml_doc(node, code)
        
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
            relationships.append(Relationship(
                source_id=EntityId(value=parent_id),
                target_id=EntityId(value=enum_id),
                type=RelationshipType.CONTAINS,
            ))
    
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
        """Extract a C# method."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        
        method_name = self._get_node_text(name_node, code)
        
        # Extract modifiers
        modifiers: list[str] = []
        for child in node.children:
            if child.type == "modifier":
                modifiers.append(self._get_node_text(child, code))
        
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
                if param.type == "parameter":
                    param_name_node = param.child_by_field_name("name")
                    param_type_node = param.child_by_field_name("type")
                    if param_name_node:
                        param_name = self._get_node_text(param_name_node, code)
                        param_type = None
                        if param_type_node:
                            param_type = self._get_node_text(param_type_node, code)
                        parameters.append((param_name, param_type))
        
        docstring = self._get_xml_doc(node, code)
        
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
            relationships.append(Relationship(
                source_id=EntityId(value=parent_id),
                target_id=EntityId(value=method_id),
                type=RelationshipType.CONTAINS,
            ))
    
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
        """Extract a C# constructor."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        
        constructor_name = self._get_node_text(name_node, code)
        
        # Extract parameters
        parameters: list[tuple[str, str | None]] = []
        params_node = node.child_by_field_name("parameters")
        if params_node:
            for param in params_node.children:
                if param.type == "parameter":
                    param_name_node = param.child_by_field_name("name")
                    param_type_node = param.child_by_field_name("type")
                    if param_name_node:
                        param_name = self._get_node_text(param_name_node, code)
                        param_type = None
                        if param_type_node:
                            param_type = self._get_node_text(param_type_node, code)
                        parameters.append((param_name, param_type))
        
        docstring = self._get_xml_doc(node, code)
        
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
            relationships.append(Relationship(
                source_id=EntityId(value=parent_id),
                target_id=EntityId(value=method_id),
                type=RelationshipType.CONTAINS,
            ))
    
    def _extract_property(
        self,
        node: Node,
        code: str,
        file_path: str,
        entities: list[Entity],
        relationships: list[Relationship],
        parent_id: str | None,
        current_class_id: str | None,
    ) -> None:
        """Extract a C# property."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return
        
        property_name = self._get_node_text(name_node, code)
        
        # Extract type
        property_type = None
        type_node = node.child_by_field_name("type")
        if type_node:
            property_type = self._get_node_text(type_node, code)
        
        # Extract modifiers
        modifiers: list[str] = []
        for child in node.children:
            if child.type == "modifier":
                modifiers.append(self._get_node_text(child, code))
        
        docstring = self._get_xml_doc(node, code)
        
        property_id = self._generate_id("method")
        
        # Treat property as a method
        entity = MethodEntity(
            id=EntityId(value=property_id),
            name=property_name,
            type=EntityType.METHOD,
            location=Location(
                file=file_path,
                line=node.start_point[0] + 1,
                column=node.start_point[1],
            ),
            class_id=EntityId(value=current_class_id) if current_class_id else None,
            parameters=[],
            return_type=property_type,
            docstring=docstring,
            is_static="static" in modifiers,
        )
        
        entities.append(entity)
        
        # Add CONTAINS relationship from parent
        if parent_id:
            relationships.append(Relationship(
                source_id=EntityId(value=parent_id),
                target_id=EntityId(value=property_id),
                type=RelationshipType.CONTAINS,
            ))
    
    def _get_xml_doc(self, node: Node, code: str) -> str | None:
        """Get XML documentation comment preceding a node."""
        prev = node.prev_sibling
        while prev:
            if prev.type == "comment":
                comment = self._get_node_text(prev, code)
                if comment.startswith("///"):
                    # Collect all consecutive /// comments
                    comments = [comment]
                    prev_comment = prev.prev_sibling
                    while prev_comment and prev_comment.type == "comment":
                        c = self._get_node_text(prev_comment, code)
                        if c.startswith("///"):
                            comments.insert(0, c)
                            prev_comment = prev_comment.prev_sibling
                        else:
                            break
                    
                    # Clean up and join
                    cleaned = []
                    for c in comments:
                        # Remove /// and trim
                        line = c.lstrip("/").strip()
                        # Skip XML tags, keep text content
                        if not line.startswith("<") and not line.startswith("</"):
                            cleaned.append(line)
                    return "\n".join(cleaned) if cleaned else None
                break
            elif prev.type not in ("modifier", "attribute_list"):
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
        if node.type == "invocation_expression":
            # Get the method name
            for child in node.children:
                if child.type == "identifier":
                    method_name = self._get_node_text(child, code)
                    
                    # Find caller
                    caller_id = self._find_enclosing_method(node, code, method_name_to_id)
                    
                    if caller_id and method_name in method_name_to_id:
                        relationships.append(Relationship(
                            source_id=caller_id,
                            target_id=method_name_to_id[method_name],
                            type=RelationshipType.CALLS,
                        ))
                    break
                elif child.type == "member_access_expression":
                    # Get the method name from member access
                    name_node = child.child_by_field_name("name")
                    if name_node:
                        method_name = self._get_node_text(name_node, code)
                        
                        caller_id = self._find_enclosing_method(node, code, method_name_to_id)
                        
                        if caller_id and method_name in method_name_to_id:
                            relationships.append(Relationship(
                                source_id=caller_id,
                                target_id=method_name_to_id[method_name],
                                type=RelationshipType.CALLS,
                            ))
                    break
        
        # Recurse into children
        for child in node.children:
            self._extract_calls_relationships(
                child, code, relationships, method_name_to_id,
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
