"""Set field implementation.

This module provides set field type for handling unique collections of values.
It supports:
- Set validation
- Item validation
- Length validation
- Database type mapping

Examples:
    >>> class Product(Model):
    ...     tags = SetField(StringField())
    ...     categories = SetField(
    ...         StringField(),
    ...         min_length=1,
    ...         max_length=5,
    ...     )
"""

from typing import Any, Generic, Optional, Sequence, TypeVar, cast

from earnorm.exceptions import FieldValidationError
from earnorm.fields.base import BaseField
from earnorm.fields.types import DatabaseValue

# Type variable for set items
T = TypeVar("T")


class SetField(BaseField[set[T]], Generic[T]):
    """Field for set values.

    This field type handles unique collections of values, with support for:
    - Set validation
    - Item validation
    - Length validation
    - Database type mapping

    Attributes:
        field: Field type for set items
        min_length: Minimum set length
        max_length: Maximum set length
        backend_options: Database backend options
    """

    min_length: Optional[int]
    max_length: Optional[int]
    backend_options: dict[str, Any]

    def __init__(
        self,
        field: BaseField[T],
        *,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        **options: Any,
    ) -> None:
        """Initialize set field.

        Args:
            field: Field type for set items
            min_length: Minimum set length
            max_length: Maximum set length
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
        """Validate set value.

        This method validates:
        - Value is set type
        - Set length is within limits
        - Each item is valid

        Args:
            value: Value to validate

        Raises:
            FieldValidationError: If validation fails
        """
        await super().validate(value)

        if value is not None:
            if not isinstance(value, set):
                raise FieldValidationError(
                    message=f"Value must be a set, got {type(value).__name__}",
                    field_name=self.name,
                    code="invalid_type",
                )

            value_set = cast(set[Any], value)

            # Check length
            if self.min_length is not None and len(value_set) < self.min_length:
                raise FieldValidationError(
                    message=f"Set must have at least {self.min_length} items",
                    field_name=self.name,
                    code="min_length",
                )

            if self.max_length is not None and len(value_set) > self.max_length:
                raise FieldValidationError(
                    message=f"Set cannot have more than {self.max_length} items",
                    field_name=self.name,
                    code="max_length",
                )

            # Validate each item
            for item in value_set:
                try:
                    await self.field.validate(item)
                except FieldValidationError as e:
                    raise FieldValidationError(
                        message=f"Invalid item {item!r}: {str(e)}",
                        field_name=self.name,
                        code="invalid_item",
                    ) from e

    async def convert(self, value: Any) -> Optional[set[T]]:
        """Convert value to set.

        Handles:
        - None values
        - Set values
        - Sequence values

        Args:
            value: Value to convert

        Returns:
            Converted set value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            if isinstance(value, set):
                items = cast(set[Any], value)
            elif isinstance(value, Sequence):
                items = set(cast(Sequence[Any], value))
            else:
                raise TypeError(f"Cannot convert {type(value).__name__} to set")

            # Convert each item
            result: set[T] = set()
            for item in items:
                try:
                    converted = await self.field.convert(item)
                    if converted is not None:
                        result.add(converted)
                except FieldValidationError as e:
                    raise FieldValidationError(
                        message=f"Cannot convert item {item!r}: {str(e)}",
                        field_name=self.name,
                        code="conversion_error",
                    ) from e

            return result
        except (TypeError, ValueError) as e:
            raise FieldValidationError(
                message=f"Cannot convert value to set: {str(e)}",
                field_name=self.name,
                code="conversion_error",
            ) from e

    async def to_db(self, value: Optional[set[T]], backend: str) -> DatabaseValue:
        """Convert set to database format.

        Args:
            value: Set value to convert
            backend: Database backend type

        Returns:
            Converted set value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            # Convert each item
            result: list[Any] = []
            for item in value:
                try:
                    converted = await self.field.to_db(item, backend)
                    if converted is not None:
                        result.append(converted)
                except FieldValidationError as e:
                    raise FieldValidationError(
                        message=f"Cannot convert item {item!r}: {str(e)}",
                        field_name=self.name,
                        code="conversion_error",
                    ) from e

            return result
        except Exception as e:
            raise FieldValidationError(
                message=f"Cannot convert set to database format: {str(e)}",
                field_name=self.name,
                code="conversion_error",
            ) from e

    async def from_db(self, value: DatabaseValue, backend: str) -> Optional[set[T]]:
        """Convert database value to set.

        Args:
            value: Database value to convert
            backend: Database backend type

        Returns:
            Converted set value or None

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
            result: set[T] = set()
            for item in value_list:
                try:
                    converted = await self.field.from_db(item, backend)
                    if converted is not None:
                        result.add(converted)
                except FieldValidationError as e:
                    raise FieldValidationError(
                        message=f"Cannot convert item {item!r}: {str(e)}",
                        field_name=self.name,
                        code="conversion_error",
                    ) from e

            return result
        except Exception as e:
            raise FieldValidationError(
                message=f"Cannot convert database value to set: {str(e)}",
                field_name=self.name,
                code="conversion_error",
            ) from e
