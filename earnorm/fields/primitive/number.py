"""Numeric field types."""

from typing import Any, List, Optional, Type

from earnorm.fields.base import Field
from earnorm.validators import validate_range
from earnorm.validators.types import ValidatorFunc


class IntegerField(Field[int]):
    """Integer field."""

    def _get_field_type(self) -> Type[Any]:
        """Get field type."""
        return int

    def __init__(
        self,
        *,
        required: bool = False,
        unique: bool = False,
        default: Any = None,
        validators: Optional[List[ValidatorFunc]] = None,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize field.

        Args:
            required: Whether field is required
            unique: Whether field value must be unique
            default: Default value
            validators: List of validator functions
            min_value: Minimum allowed value
            max_value: Maximum allowed value
        """
        super().__init__(
            required=required,
            unique=unique,
            default=default,
            validators=validators,
            **kwargs,
        )
        if min_value is not None or max_value is not None:
            self._metadata.validators.append(validate_range(min_value, max_value))

    def convert(self, value: Any) -> int:
        """Convert value to integer."""
        if value is None:
            return 0
        return int(value)

    def to_mongo(self, value: Optional[int]) -> int:
        """Convert Python integer to MongoDB integer."""
        if value is None:
            return 0
        return int(value)

    def from_mongo(self, value: Any) -> int:
        """Convert MongoDB integer to Python integer."""
        if value is None:
            return 0
        return int(value)


class FloatField(Field[float]):
    """Float field."""

    def _get_field_type(self) -> Type[Any]:
        """Get field type."""
        return float

    def __init__(
        self,
        *,
        required: bool = False,
        unique: bool = False,
        default: Any = None,
        validators: Optional[List[ValidatorFunc]] = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize field.

        Args:
            required: Whether field is required
            unique: Whether field value must be unique
            default: Default value
            validators: List of validator functions
            min_value: Minimum allowed value
            max_value: Maximum allowed value
        """
        super().__init__(
            required=required,
            unique=unique,
            default=default,
            validators=validators,
            **kwargs,
        )
        if min_value is not None or max_value is not None:
            self._metadata.validators.append(validate_range(min_value, max_value))

    def convert(self, value: Any) -> float:
        """Convert value to float."""
        if value is None:
            return 0.0
        return float(value)

    def to_mongo(self, value: Optional[float]) -> float:
        """Convert Python float to MongoDB float."""
        if value is None:
            return 0.0
        return float(value)

    def from_mongo(self, value: Any) -> float:
        """Convert MongoDB float to Python float."""
        if value is None:
            return 0.0
        return float(value)
