"""Numeric field types."""

from typing import Any, List, Optional, Type

from earnorm.fields.base import Field
from earnorm.validators import validate_range
from earnorm.validators.types import ValidatorFunc


class IntegerField(Field[int]):
    """Integer field."""

    def _get_field_type(self) -> Type[int]:
        """Get field type.

        Returns:
            Type object representing integer type
        """
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
            if not hasattr(self._metadata, "validators"):
                self._metadata.validators = []  # type: ignore
            self._metadata.validators.append(validate_range(min_value, max_value))  # type: ignore

    def convert(self, value: Any) -> int:
        """Convert value to integer.

        Args:
            value: Value to convert

        Returns:
            Converted integer value or 0 if value is None

        Examples:
            >>> field = IntegerField()
            >>> field.convert("42")
            42
            >>> field.convert(3.14)
            3
            >>> field.convert(None)
            0
        """
        if value is None:
            return 0
        return int(value)

    def to_mongo(self, value: Optional[int]) -> int:
        """Convert Python integer to MongoDB integer.

        Args:
            value: Integer value to convert

        Returns:
            MongoDB integer value or 0 if value is None

        Examples:
            >>> field = IntegerField()
            >>> field.to_mongo(42)
            42
            >>> field.to_mongo(None)
            0
        """
        if value is None:
            return 0
        return int(value)

    def from_mongo(self, value: Any) -> int:
        """Convert MongoDB integer to Python integer.

        Args:
            value: MongoDB value to convert

        Returns:
            Python integer value or 0 if value is None

        Examples:
            >>> field = IntegerField()
            >>> field.from_mongo(42)
            42
            >>> field.from_mongo(None)
            0
        """
        if value is None:
            return 0
        return int(value)


class FloatField(Field[float]):
    """Float field."""

    def _get_field_type(self) -> Type[float]:
        """Get field type.

        Returns:
            Type object representing float type
        """
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
            if not hasattr(self._metadata, "validators"):
                self._metadata.validators = []  # type: ignore
            self._metadata.validators.append(validate_range(min_value, max_value))  # type: ignore

    def convert(self, value: Any) -> float:
        """Convert value to float.

        Args:
            value: Value to convert

        Returns:
            Converted float value or 0.0 if value is None

        Examples:
            >>> field = FloatField()
            >>> field.convert("3.14")
            3.14
            >>> field.convert(42)
            42.0
            >>> field.convert(None)
            0.0
        """
        if value is None:
            return 0.0
        return float(value)

    def to_mongo(self, value: Optional[float]) -> float:
        """Convert Python float to MongoDB float.

        Args:
            value: Float value to convert

        Returns:
            MongoDB float value or 0.0 if value is None

        Examples:
            >>> field = FloatField()
            >>> field.to_mongo(3.14)
            3.14
            >>> field.to_mongo(None)
            0.0
        """
        if value is None:
            return 0.0
        return float(value)

    def from_mongo(self, value: Any) -> float:
        """Convert MongoDB float to Python float.

        Args:
            value: MongoDB value to convert

        Returns:
            Python float value or 0.0 if value is None

        Examples:
            >>> field = FloatField()
            >>> field.from_mongo(3.14)
            3.14
            >>> field.from_mongo(None)
            0.0
        """
        if value is None:
            return 0.0
        return float(value)
