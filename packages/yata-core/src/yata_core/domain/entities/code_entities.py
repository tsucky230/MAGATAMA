"""
Code Entity Classes

REQ-KGC-001: Specific entity types for different code elements.
REQ-LANG-001 to REQ-LANG-005: Language-specific entities.
"""

from __future__ import annotations

from pydantic import Field

from yata_core.domain.entities.base import Entity, EntityType
from yata_core.domain.value_objects.ids import EntityId
from yata_core.domain.value_objects.location import Location


class FunctionEntity(Entity):
    """
    Function entity.

    Represents a standalone function (not a method).

    Attributes:
        parameters: List of (name, type) tuples
        return_type: Return type annotation
        decorators: List of decorator names
        is_async: Whether the function is async
    """

    type: EntityType = Field(default=EntityType.FUNCTION, frozen=True)
    parameters: list[tuple[str, str | None]] = Field(
        default_factory=list, description="Function parameters"
    )
    return_type: str | None = Field(default=None, description="Return type")
    decorators: list[str] = Field(default_factory=list, description="Decorators")
    is_async: bool = Field(default=False, description="Is async function")

    @property
    def signature(self) -> str:
        """Generate function signature string."""
        params = ", ".join(
            f"{name}: {typ}" if typ else name for name, typ in self.parameters
        )
        ret = f" -> {self.return_type}" if self.return_type else ""
        return f"{self.name}({params}){ret}"


class ClassEntity(Entity):
    """
    Class entity.

    Represents a class definition.

    Attributes:
        bases: List of base class names
        method_ids: List of method entity IDs
        decorators: List of decorator names
        is_abstract: Whether the class is abstract
    """

    type: EntityType = Field(default=EntityType.CLASS, frozen=True)
    bases: list[str] = Field(default_factory=list, description="Base classes")
    method_ids: list[EntityId] = Field(
        default_factory=list, description="Method entity IDs"
    )
    decorators: list[str] = Field(default_factory=list, description="Decorators")
    is_abstract: bool = Field(default=False, description="Is abstract class")


class MethodEntity(Entity):
    """
    Method entity.

    Represents a method within a class.

    Attributes:
        class_id: ID of the containing class
        parameters: List of (name, type) tuples
        return_type: Return type annotation
        decorators: List of decorator names
        is_static: Whether it's a static method
        is_classmethod: Whether it's a class method
        is_async: Whether the method is async
    """

    type: EntityType = Field(default=EntityType.METHOD, frozen=True)
    class_id: EntityId = Field(..., description="Containing class ID")
    parameters: list[tuple[str, str | None]] = Field(
        default_factory=list, description="Method parameters"
    )
    return_type: str | None = Field(default=None, description="Return type")
    decorators: list[str] = Field(default_factory=list, description="Decorators")
    is_static: bool = Field(default=False, description="Is static method")
    is_classmethod: bool = Field(default=False, description="Is class method")
    is_async: bool = Field(default=False, description="Is async method")

    @property
    def signature(self) -> str:
        """Generate method signature string."""
        params = ", ".join(
            f"{name}: {typ}" if typ else name for name, typ in self.parameters
        )
        ret = f" -> {self.return_type}" if self.return_type else ""
        return f"{self.name}({params}){ret}"


class ModuleEntity(Entity):
    """
    Module entity.

    Represents a Python module or package.

    Attributes:
        exports: List of exported names
        is_package: Whether it's a package (__init__.py)
    """

    type: EntityType = Field(default=EntityType.MODULE, frozen=True)
    exports: list[str] = Field(default_factory=list, description="Exported names")
    is_package: bool = Field(default=False, description="Is package")


class TypeEntity(Entity):
    """
    Type entity.

    Represents a type alias or type definition.

    Attributes:
        definition: Type definition string
        type_params: Generic type parameters
    """

    type: EntityType = Field(default=EntityType.TYPE, frozen=True)
    definition: str | None = Field(default=None, description="Type definition")
    type_params: list[str] = Field(
        default_factory=list, description="Generic type parameters"
    )


class InterfaceEntity(Entity):
    """
    Interface entity (TypeScript, Go).

    Represents an interface definition.

    Attributes:
        method_signatures: List of method signatures
        extends: List of extended interface names
    """

    type: EntityType = Field(default=EntityType.INTERFACE, frozen=True)
    method_signatures: list[str] = Field(
        default_factory=list, description="Method signatures"
    )
    extends: list[str] = Field(
        default_factory=list, description="Extended interfaces"
    )


class StructEntity(Entity):
    """
    Struct entity (Rust, Go).

    Represents a struct definition.

    Attributes:
        fields: List of (name, type) tuples
        type_params: Generic type parameters
    """

    type: EntityType = Field(default=EntityType.STRUCT, frozen=True)
    fields: list[tuple[str, str]] = Field(
        default_factory=list, description="Struct fields"
    )
    type_params: list[str] = Field(
        default_factory=list, description="Generic type parameters"
    )


class TraitEntity(Entity):
    """
    Trait entity (Rust).

    Represents a trait definition.

    Attributes:
        method_signatures: List of method signatures
        super_traits: List of super trait names
    """

    type: EntityType = Field(default=EntityType.TRAIT, frozen=True)
    method_signatures: list[str] = Field(
        default_factory=list, description="Method signatures"
    )
    super_traits: list[str] = Field(default_factory=list, description="Super traits")


class EnumEntity(Entity):
    """
    Enum entity.

    Represents an enumeration definition.

    Attributes:
        variants: List of enum variants
    """

    type: EntityType = Field(default=EntityType.ENUM, frozen=True)
    variants: list[str] = Field(default_factory=list, description="Enum variants")
