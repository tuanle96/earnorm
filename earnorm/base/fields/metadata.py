"""Field metadata implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type


@dataclass
class FieldMetadata:
    """Field metadata.

    This class stores metadata about a field including:
    - Basic info (name, type, required, unique)
    - Validation rules
    - Index configuration
    - Default value
    - Custom options

    Attributes:
        name: Field name
        field_type: Python type of the field
        required: Whether field is required
        unique: Whether field value must be unique
        index: Whether to create an index for this field
        default: Default value when None
        description: Field description
        validators: List of validation functions
        options: Additional field options
    """

    name: str
    field_type: Type[Any]
    required: bool = False
    unique: bool = False
    index: bool = False
    default: Any = None
    description: Optional[str] = None
    validators: List[Callable[[Any], None]] = field(default_factory=list)
    options: Dict[str, Any] = field(default_factory=dict)

    def to_index(self) -> Dict[str, Any]:
        """Convert field metadata to MongoDB index definition.

        Returns:
            Dict containing index configuration including:
            - keys: List of (field_name, direction) tuples
            - unique: Whether index enforces uniqueness
            - sparse: Whether index should be sparse
            - expireAfterSeconds: TTL for the index
        """
        index: Dict[str, Any] = {"keys": [(self.name, 1)], "unique": self.unique}

        # Add sparse option
        if self.options.get("sparse"):
            index["sparse"] = True

        # Add TTL option
        if self.options.get("expire_after_seconds"):
            index["expireAfterSeconds"] = self.options["expire_after_seconds"]

        return index

    def validate(self, value: Any) -> None:
        """Validate field value.

        Performs validation including:
        - Required field check
        - Type check
        - Custom validators

        Args:
            value: Value to validate

        Raises:
            ValueError: If value is required but None
            TypeError: If value type doesn't match field_type
            ValidationError: If custom validation fails
        """
        # Check required
        if self.required and value is None:
            raise ValueError(f"Field {self.name} is required")

        # Check type
        if value is not None and not isinstance(value, self.field_type):
            raise TypeError(
                f"Field {self.name} must be of type {self.field_type.__name__}"
            )

        # Run validators
        for validator in self.validators:
            validator(value)

    def __str__(self) -> str:
        """Get string representation.

        Returns:
            String containing core field metadata
        """
        return (
            f"FieldMetadata(name={self.name}, "
            f"type={self.field_type.__name__}, "
            f"required={self.required}, "
            f"unique={self.unique})"
        )
