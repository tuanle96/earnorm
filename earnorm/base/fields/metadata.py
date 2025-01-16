"""Field metadata."""

from typing import Any, Protocol


class FieldProtocol(Protocol):
    """Protocol for field classes."""

    name: str
    required: bool
    unique: bool
    default: Any

    def validate(self, value: Any) -> None:
        """Validate field value."""
        ...


class FieldMetadata:
    """Field metadata.

    This class stores metadata about a field including:
    - Field instance
    - Field name
    - Field type
    - Field options (required, unique, default)
    - Field validators
    """

    def __init__(
        self,
        field: FieldProtocol,
        name: str,
        required: bool = False,
        unique: bool = False,
        default: Any = None,
    ) -> None:
        """Initialize metadata.

        Args:
            field: Field instance
            name: Field name
            required: Whether field is required
            unique: Whether field value must be unique
            default: Default field value
        """
        self.field = field
        self.name = name
        self.required = required
        self.unique = unique
        self.default = default

    def validate(self, value: Any) -> None:
        """Validate field value.

        Args:
            value: Value to validate

        Raises:
            ValueError: If validation fails
        """
        self.field.validate(value)
