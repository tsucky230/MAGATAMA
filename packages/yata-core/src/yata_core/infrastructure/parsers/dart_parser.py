"""Dart Parser using regex-based parsing.

This module provides Dart parsing capabilities for
extracting entities from Dart source code.
Since tree-sitter-dart is not available on PyPI,
this uses regex-based parsing.
"""

import re
from pathlib import Path
from typing import Any

from yata_core.domain.entities import (
    Entity,
    EntityType,
    ClassEntity,
    FunctionEntity,
    MethodEntity,
    InterfaceEntity,
    ModuleEntity,
    Relationship,
    RelationshipType,
)
from yata_core.domain.value_objects import EntityId, Location
from yata_core.infrastructure.parsers.parse_result import ParseResult


class DartParser:
    """Parser for Dart source code using regex-based parsing.
    
    Extracts:
    - Classes
    - Mixins
    - Extensions
    - Functions
    - Methods
    - Enums
    - Typedefs
    """
    
    def __init__(self) -> None:
        """Initialize the Dart parser."""
        self._entity_counter = 0
        
        # Regex patterns for Dart constructs
        self._class_pattern = re.compile(
            r'(?:abstract\s+)?class\s+(\w+)(?:<[^>]+>)?(?:\s+extends\s+(\w+))?(?:\s+with\s+([^{]+))?(?:\s+implements\s+([^{]+))?\s*\{',
            re.MULTILINE
        )
        self._mixin_pattern = re.compile(
            r'mixin\s+(\w+)(?:<[^>]+>)?(?:\s+on\s+([^{]+))?\s*\{',
            re.MULTILINE
        )
        self._extension_pattern = re.compile(
            r'extension\s+(\w+)?\s+on\s+(\w+(?:<[^>]+>)?)\s*\{',
            re.MULTILINE
        )
        self._function_pattern = re.compile(
            r'^(?:Future<[^>]+>|Stream<[^>]+>|[\w<>,\s]+)\s+(\w+)\s*\(([^)]*)\)\s*(?:async\s*)?\{',
            re.MULTILINE
        )
        self._method_pattern = re.compile(
            r'^\s+(?:static\s+)?(?:Future<[^>]+>|Stream<[^>]+>|[\w<>,?\s]+)\s+(\w+)\s*\(([^)]*)\)\s*(?:async\s*)?[{;]',
            re.MULTILINE
        )
        self._enum_pattern = re.compile(
            r'enum\s+(\w+)\s*\{',
            re.MULTILINE
        )
        self._typedef_pattern = re.compile(
            r'typedef\s+(\w+)(?:<[^>]+>)?\s*=',
            re.MULTILINE
        )
        self._import_pattern = re.compile(
            r"import\s+['\"]([^'\"]+)['\"]",
            re.MULTILINE
        )
    
    def parse_file(self, file_path: Path) -> ParseResult:
        """Parse a Dart file.
        
        Args:
            file_path: Path to the Dart file
            
        Returns:
            ParseResult with extracted entities
        """
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        return self.parse_string(content, str(file_path))
    
    def parse_string(self, code: str, file_path: str = "<string>") -> ParseResult:
        """Parse Dart code from a string.
        
        Args:
            code: Dart source code
            file_path: Path for location information
            
        Returns:
            ParseResult with extracted entities
        """
        entities: list[Entity] = []
        relationships: list[Relationship] = []
        imports: list[str] = []
        errors: list[str] = []
        
        # Reset counter for each file
        self._entity_counter = 0
        
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
        
        # Extract imports
        for match in self._import_pattern.finditer(code):
            imports.append(match.group(1))
            relationships.append(
                Relationship(
                    source_id=EntityId(value=module_id),
                    target_id=EntityId(value=f"external:{match.group(1)}"),
                    type=RelationshipType.IMPORTS,
                )
            )
        
        # Extract classes
        for match in self._class_pattern.finditer(code):
            class_name = match.group(1)
            base_class = match.group(2)
            mixins = match.group(3)
            interfaces = match.group(4)
            
            line_num = code[:match.start()].count('\n') + 1
            class_id = self._generate_id("class")
            
            bases = []
            if base_class:
                bases.append(base_class.strip())
            if mixins:
                bases.extend([m.strip() for m in mixins.split(',')])
            if interfaces:
                bases.extend([i.strip() for i in interfaces.split(',')])
            
            class_entity = ClassEntity(
                id=EntityId(value=class_id),
                name=class_name,
                type=EntityType.CLASS,
                location=Location(file=file_path, line=line_num, column=0),
                bases=bases,
            )
            entities.append(class_entity)
            
            # Add CONTAINS relationship
            relationships.append(
                Relationship(
                    source_id=EntityId(value=module_id),
                    target_id=EntityId(value=class_id),
                    type=RelationshipType.CONTAINS,
                )
            )
            
            # Extract methods within class
            class_start = match.end()
            class_end = self._find_matching_brace(code, class_start - 1)
            if class_end > class_start:
                class_body = code[class_start:class_end]
                self._extract_methods(
                    class_body, file_path, line_num, class_id,
                    entities, relationships
                )
        
        # Extract mixins
        for match in self._mixin_pattern.finditer(code):
            mixin_name = match.group(1)
            line_num = code[:match.start()].count('\n') + 1
            mixin_id = self._generate_id("mixin")
            
            mixin_entity = ClassEntity(
                id=EntityId(value=mixin_id),
                name=mixin_name,
                type=EntityType.CLASS,
                location=Location(file=file_path, line=line_num, column=0),
                bases=[],
                docstring="mixin",
            )
            entities.append(mixin_entity)
            
            relationships.append(
                Relationship(
                    source_id=EntityId(value=module_id),
                    target_id=EntityId(value=mixin_id),
                    type=RelationshipType.CONTAINS,
                )
            )
        
        # Extract extensions
        for match in self._extension_pattern.finditer(code):
            ext_name = match.group(1) or "Anonymous"
            on_type = match.group(2)
            line_num = code[:match.start()].count('\n') + 1
            ext_id = self._generate_id("extension")
            
            ext_entity = ClassEntity(
                id=EntityId(value=ext_id),
                name=ext_name,
                type=EntityType.CLASS,
                location=Location(file=file_path, line=line_num, column=0),
                bases=[on_type] if on_type else [],
                docstring="extension",
            )
            entities.append(ext_entity)
            
            relationships.append(
                Relationship(
                    source_id=EntityId(value=module_id),
                    target_id=EntityId(value=ext_id),
                    type=RelationshipType.CONTAINS,
                )
            )
        
        # Extract enums
        for match in self._enum_pattern.finditer(code):
            enum_name = match.group(1)
            line_num = code[:match.start()].count('\n') + 1
            enum_id = self._generate_id("enum")
            
            enum_entity = ClassEntity(
                id=EntityId(value=enum_id),
                name=enum_name,
                type=EntityType.CLASS,
                location=Location(file=file_path, line=line_num, column=0),
                bases=[],
                docstring="enum",
            )
            entities.append(enum_entity)
            
            relationships.append(
                Relationship(
                    source_id=EntityId(value=module_id),
                    target_id=EntityId(value=enum_id),
                    type=RelationshipType.CONTAINS,
                )
            )
        
        # Extract top-level functions
        for match in self._function_pattern.finditer(code):
            func_name = match.group(1)
            params_str = match.group(2)
            
            # Skip if inside a class (indented)
            line_start = code.rfind('\n', 0, match.start()) + 1
            if code[line_start:match.start()].strip():
                continue
            
            line_num = code[:match.start()].count('\n') + 1
            func_id = self._generate_id("function")
            
            parameters = self._parse_parameters(params_str)
            
            func_entity = FunctionEntity(
                id=EntityId(value=func_id),
                name=func_name,
                type=EntityType.FUNCTION,
                location=Location(file=file_path, line=line_num, column=0),
                parameters=parameters,
            )
            entities.append(func_entity)
            
            relationships.append(
                Relationship(
                    source_id=EntityId(value=module_id),
                    target_id=EntityId(value=func_id),
                    type=RelationshipType.CONTAINS,
                )
            )
        
        # Extract typedefs
        for match in self._typedef_pattern.finditer(code):
            typedef_name = match.group(1)
            line_num = code[:match.start()].count('\n') + 1
            typedef_id = self._generate_id("typedef")
            
            typedef_entity = ClassEntity(
                id=EntityId(value=typedef_id),
                name=typedef_name,
                type=EntityType.CLASS,
                location=Location(file=file_path, line=line_num, column=0),
                bases=[],
                docstring="typedef",
            )
            entities.append(typedef_entity)
        
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
    
    def _find_matching_brace(self, code: str, start: int) -> int:
        """Find the position of the matching closing brace."""
        depth = 0
        i = start
        while i < len(code):
            if code[i] == '{':
                depth += 1
            elif code[i] == '}':
                depth -= 1
                if depth == 0:
                    return i
            i += 1
        return len(code)
    
    def _extract_methods(
        self,
        class_body: str,
        file_path: str,
        class_line: int,
        class_id: str,
        entities: list[Entity],
        relationships: list[Relationship],
    ) -> None:
        """Extract methods from a class body."""
        # Method pattern for class body
        method_pattern = re.compile(
            r'^\s+(?:@\w+\s*)*(?:static\s+)?(?:Future<[^>]+>|Stream<[^>]+>|void|[\w<>,?\s]+)\s+(?:get\s+)?(\w+)\s*(?:\(([^)]*)\))?\s*(?:async\s*)?[{;=>]',
            re.MULTILINE
        )
        
        for match in method_pattern.finditer(class_body):
            method_name = match.group(1)
            params_str = match.group(2) or ""
            
            # Skip constructors and private internals
            if method_name.startswith('_') and method_name.endswith('_'):
                continue
            
            line_num = class_line + class_body[:match.start()].count('\n')
            method_id = self._generate_id("method")
            
            parameters = self._parse_parameters(params_str)
            
            method_entity = MethodEntity(
                id=EntityId(value=method_id),
                name=method_name,
                type=EntityType.METHOD,
                location=Location(file=file_path, line=line_num, column=0),
                class_id=EntityId(value=class_id),
                parameters=parameters,
            )
            entities.append(method_entity)
            
            relationships.append(
                Relationship(
                    source_id=EntityId(value=class_id),
                    target_id=EntityId(value=method_id),
                    type=RelationshipType.CONTAINS,
                )
            )
    
    def _parse_parameters(self, params_str: str) -> list[tuple[str, str | None]]:
        """Parse parameter string into list of (name, type) tuples."""
        if not params_str.strip():
            return []
        
        params: list[tuple[str, str | None]] = []
        # Split by comma, handling nested generics
        depth = 0
        current = ""
        for char in params_str:
            if char in '<{[(':
                depth += 1
                current += char
            elif char in '>}])':
                depth -= 1
                current += char
            elif char == ',' and depth == 0:
                param = current.strip()
                if param:
                    name, param_type = self._parse_single_param(param)
                    if name:
                        params.append((name, param_type))
                current = ""
            else:
                current += char
        
        # Handle last parameter
        param = current.strip()
        if param:
            name, param_type = self._parse_single_param(param)
            if name:
                params.append((name, param_type))
        
        return params
    
    def _parse_single_param(self, param: str) -> tuple[str | None, str | None]:
        """Parse a single parameter into (name, type)."""
        param = param.strip()
        if not param or param.startswith('{') or param.startswith('['):
            return None, None
        
        # Handle "Type name" or "Type? name" format
        parts = param.split()
        if len(parts) >= 2:
            param_type = parts[0].strip('?')
            name = parts[-1].strip('?')
            return name, param_type
        elif len(parts) == 1:
            return parts[0].strip('?'), None
        return None, None
