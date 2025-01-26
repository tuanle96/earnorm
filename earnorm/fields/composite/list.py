"""List field implementation.

This module provides list field type for handling lists of values.
It supports:
- List validation
- Item validation
- Length validation
- Unique items
- Database type mapping

Examples:
    >>> class Product(Model):
    ...     tags = ListField(StringField(), unique=True)
    ...     prices = ListField(DecimalField(max_digits=10, decimal_places=2))
    ...     images = ListField(FileField(allowed_types=["image/*"]))
"""

from typing import Any, Generic, Optional, Sequence, TypeVar, cast

from earnorm.exceptions import FieldValidationError
from earnorm.fields.base import BaseField
from earnorm.fields.types import DatabaseValue

# Type variable for list items
T = TypeVar("T")


class ListField(BaseField[list[T]], Generic[T]):
    """Field for lists of values.

    This field type handles lists of values, with support for:
    - List validation
    - Item validation
    - Length validation
    - Unique items
    - Database type mapping

    Attributes:
        field: Field type for list items
        min_length: Minimum list length
        max_length: Maximum list length
        unique: Whether items must be unique
        backend_options: Database backend options
    """

    min_length: Optional[int]
    max_length: Optional[int]
    unique: bool
    backend_options: dict[str, Any]

    def __init__(
        self,
        field: BaseField[T],
        *,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        unique: bool = False,
        **options: Any,
    ) -> None:
        """Initialize list field.

        Args:
            field: Field type for list items
            min_length: Minimum list length
            max_length: Maximum list length
            unique: Whether items must be unique
            **options: Additional field options

        Raises:
            ValueError: If min_length or max_length are invalid
        """
        if min_length is not None and min_length < 0:
            raise ValueError("min_length must be non-negative")
        if max_length is not None and max_length < 0:
            raise ValueError("max_length must be non-negative")
        if (
            min_length is not None
            and max_length is not None
            and min_length > max_length
        ):
            raise ValueError("min_length cannot be greater than max_length")

        super().__init__(**options)

        # Store field as protected attribute
        object.__setattr__(self, "_field", field)
        self.min_length = min_length
        self.max_length = max_length
        self.unique = unique

        # Initialize backend options
        self.backend_options = {
            "mongodb": {"type": "array"},
            "postgres": {"type": "JSONB"},
            "mysql": {"type": "JSON"},
        }

    @property
    def field(self) -> BaseField[T]:
        """Get field instance."""
        return cast(BaseField[T], object.__getattribute__(self, "_field"))

    async def validate(self, value: Any) -> None:
        """Validate list value.

        This method validates:
        - Value is list type
        - List length is within limits
        - Items are unique if required
        - Each item is valid

        Args:
            value: Value to validate

        Raises:
            FieldValidationError: If validation fails
        """
        await super().validate(value)

        if value is not None:
            if not isinstance(value, list):
                raise FieldValidationError(
                    message=f"Value must be a list, got {type(value).__name__}",
                    field_name=self.name,
                    code="invalid_type",
                )

            value_list = cast(list[Any], value)

            # Check length
            if self.min_length is not None and len(value_list) < self.min_length:
                raise FieldValidationError(
                    message=f"List must have at least {self.min_length} items",
                    field_name=self.name,
                    code="min_length",
                )

            if self.max_length is not None and len(value_list) > self.max_length:
                raise FieldValidationError(
                    message=f"List cannot have more than {self.max_length} items",
                    field_name=self.name,
                    code="max_length",
                )

            # Check uniqueness
            if self.unique:
                seen: set[Any] = set()
                for item in value_list:
                    if item in seen:
                        raise FieldValidationError(
                            message="List items must be unique",
                            field_name=self.name,
                            code="not_unique",
                        )
                    seen.add(item)

            # Validate each item
            for i, item in enumerate(value_list):
                try:
                    await self.field.validate(item)
                except FieldValidationError as e:
                    raise FieldValidationError(
                        message=f"Invalid item at index {i}: {str(e)}",
                        field_name=self.name,
                        code="invalid_item",
                    ) from e

    async def convert(self, value: Any) -> Optional[list[T]]:
        """Convert value to list.

        Handles:
        - None values
        - List values
        - Sequence values

        Args:
            value: Value to convert

        Returns:
            Converted list value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            if isinstance(value, list):
                items = cast(list[Any], value)
            elif isinstance(value, Sequence):
                items = list(cast(Sequence[Any], value))
            else:
                raise TypeError(f"Cannot convert {type(value).__name__} to list")

            # Convert each item
            result: list[T] = []
            for i, item in enumerate(items):
                try:
                    converted = await self.field.convert(item)
                    if converted is not None:
                        result.append(converted)
                except FieldValidationError as e:
                    raise FieldValidationError(
                        message=f"Cannot convert item at index {i}: {str(e)}",
                        field_name=self.name,
                        code="conversion_error",
                    ) from e

            return result
        except (TypeError, ValueError) as e:
            raise FieldValidationError(
                message=f"Cannot convert value to list: {str(e)}",
                field_name=self.name,
                code="conversion_error",
            ) from e

    async def to_db(self, value: Optional[list[T]], backend: str) -> DatabaseValue:
        """Convert list to database format.

        Args:
            value: List value to convert
            backend: Database backend type

        Returns:
            Converted list value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            # Convert each item
            result: list[Any] = []
            for i, item in enumerate(value):
                try:
                    converted = await self.field.to_db(item, backend)
                    result.append(converted)
                except FieldValidationError as e:
                    raise FieldValidationError(
                        message=f"Cannot convert item at index {i}: {str(e)}",
                        field_name=self.name,
                        code="conversion_error",
                    ) from e

            return result
        except Exception as e:
            raise FieldValidationError(
                message=f"Cannot convert list to database format: {str(e)}",
                field_name=self.name,
                code="conversion_error",
            ) from e

    async def from_db(self, value: DatabaseValue, backend: str) -> Optional[list[T]]:
        """Convert database value to list.

        Args:
            value: Database value to convert
            backend: Database backend type

        Returns:
            Converted list value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            if not isinstance(value, list):
                raise TypeError(
                    f"Expected list from database, got {type(value).__name__}"
                )

            value_list = cast(list[Any], value)

            # Convert each item
            result: list[T] = []
            for i, item in enumerate(value_list):
                try:
                    converted = await self.field.from_db(item, backend)
                    if converted is not None:
                        result.append(converted)
                except FieldValidationError as e:
                    raise FieldValidationError(
                        message=f"Cannot convert item at index {i}: {str(e)}",
                        field_name=self.name,
                        code="conversion_error",
                    ) from e

            return result
        except Exception as e:
            raise FieldValidationError(
                message=f"Cannot convert database value to list: {str(e)}",
                field_name=self.name,
                code="conversion_error",
            ) from e
