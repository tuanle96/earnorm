"""Tuple field implementation.

This module provides tuple field type for handling fixed-length sequences of values.
It supports:
- Type validation for each element
- Length validation
- Database type mapping
- Custom validation rules

Examples:
    >>> class Product(Model):
    ...     # Tuple of (width, height, depth) in centimeters
    ...     dimensions = TupleField(
    ...         fields=(
    ...             NumberField(min_value=0),  # width
    ...             NumberField(min_value=0),  # height
    ...             NumberField(min_value=0),  # depth
    ...         ),
    ...         required=True,
    ...     )
    ...     # Tuple of (latitude, longitude)
    ...     location = TupleField(
    ...         fields=(
    ...             NumberField(min_value=-90, max_value=90),  # latitude
    ...             NumberField(min_value=-180, max_value=180),  # longitude
    ...         ),
    ...         nullable=True,
    ...     )
"""

from typing import Any, Generic, List, Optional, Sequence, Tuple, TypeVar

from earnorm.exceptions import FieldValidationError
from earnorm.fields.base import BaseField
from earnorm.fields.types import DatabaseValue

# Type variable for tuple elements
T = TypeVar("T")


class TupleField(BaseField[Tuple[T, ...]], Generic[T]):
    """Field for fixed-length sequences of values.

    This field type handles tuples of values, with support for:
    - Type validation for each element
    - Length validation
    - Database type mapping
    - Custom validation rules

    Attributes:
        fields: Sequence of fields for validating tuple elements
        backend_options: Database backend options
    """

    fields: Sequence[BaseField[T]]
    backend_options: dict[str, Any]

    def __init__(
        self,
        fields: Sequence[BaseField[T]],
        **options: Any,
    ) -> None:
        """Initialize tuple field.

        Args:
            fields: Sequence of fields for validating tuple elements
            **options: Additional field options
        """
        super().__init__(**options)

        if not fields:
            raise ValueError("TupleField requires at least one field")

        self.fields = fields

        # Initialize backend options
        self.backend_options = {
            "mongodb": {"type": "array"},
            "postgres": {"type": "JSONB"},
            "mysql": {"type": "JSON"},
        }

    async def validate(self, value: Any) -> None:
        """Validate tuple value.

        This method validates:
        - Value is a sequence
        - Value length matches fields length
        - Each element is valid according to its field

        Args:
            value: Value to validate

        Raises:
            FieldValidationError: If validation fails
        """
        await super().validate(value)

        if value is not None:
            if not isinstance(value, (tuple, list)):
                raise FieldValidationError(
                    message=f"Value must be a tuple or list, got {type(value).__name__}",
                    field_name=self.name,
                    code="invalid_type",
                )

            value_list: List[Any] = list(
                value  # type: ignore
            )  # Convert to list for consistent handling
            if len(value_list) != len(self.fields):
                raise FieldValidationError(
                    message=f"Expected {len(self.fields)} elements, got {len(value_list)}",
                    field_name=self.name,
                    code="invalid_length",
                )

            # Validate each element
            for i, (field, element) in enumerate(zip(self.fields, value_list)):
                try:
                    await field.validate(element)  # type: ignore
                except FieldValidationError as e:
                    raise FieldValidationError(
                        message=f"Invalid element at index {i}: {str(e)}",
                        field_name=self.name,
                        code="invalid_element",
                    ) from e

    async def convert(self, value: Any) -> Optional[Tuple[T, ...]]:
        """Convert value to tuple.

        Handles:
        - None values
        - Tuple values
        - List values
        - JSON array values

        Args:
            value: Value to convert

        Returns:
            Converted tuple or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            if isinstance(value, (tuple, list)):
                value_list: List[Any] = list(
                    value  # type: ignore
                )  # Convert to list for consistent handling
                if len(value_list) != len(self.fields):
                    raise FieldValidationError(
                        message=f"Expected {len(self.fields)} elements, got {len(value_list)}",
                        field_name=self.name,
                        code="invalid_length",
                    )

                # Convert each element
                result: List[T] = []
                for i, (field, element) in enumerate(zip(self.fields, value_list)):
                    try:
                        converted = await field.convert(element)  # type: ignore
                        result.append(converted)  # type: ignore
                    except FieldValidationError as e:
                        raise FieldValidationError(
                            message=f"Invalid element at index {i}: {str(e)}",
                            field_name=self.name,
                            code="invalid_element",
                        ) from e

                return tuple(result)
            elif isinstance(value, str):
                # Try to parse as JSON array
                import json

                try:
                    data = json.loads(value)
                    if not isinstance(data, list):
                        raise FieldValidationError(
                            message="JSON value must be an array",
                            field_name=self.name,
                            code="invalid_json",
                        )

                    data_list: List[Any] = list(
                        data  # type: ignore
                    )  # Convert to list for consistent handling
                    if len(data_list) != len(self.fields):
                        raise FieldValidationError(
                            message=f"Expected {len(self.fields)} elements, got {len(data_list)}",
                            field_name=self.name,
                            code="invalid_length",
                        )

                    # Convert each element
                    result: List[T] = []
                    for i, (field, element) in enumerate(zip(self.fields, data_list)):
                        try:
                            converted = await field.convert(element)  # type: ignore
                            result.append(converted)  # type: ignore
                        except FieldValidationError as e:
                            raise FieldValidationError(
                                message=f"Invalid element at index {i}: {str(e)}",
                                field_name=self.name,
                                code="invalid_element",
                            ) from e

                    return tuple(result)
                except json.JSONDecodeError as e:
                    raise FieldValidationError(
                        message=f"Invalid JSON array: {str(e)}",
                        field_name=self.name,
                        code="invalid_json",
                    ) from e
            else:
                value_type = type(value).__name__
                raise FieldValidationError(
                    message=f"Cannot convert {value_type} to tuple",
                    field_name=self.name,
                    code="conversion_error",
                )
        except (TypeError, ValueError) as e:
            raise FieldValidationError(
                message=str(e),
                field_name=self.name,
                code="conversion_error",
            ) from e

    async def to_db(
        self, value: Optional[Tuple[T, ...]], backend: str
    ) -> DatabaseValue:
        """Convert tuple to database format.

        Args:
            value: Tuple to convert
            backend: Database backend type

        Returns:
            Converted tuple or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            # Convert each element
            value_list: List[Any] = list(
                value
            )  # Convert to list for consistent handling
            result: List[Any] = []
            for i, (field, element) in enumerate(zip(self.fields, value_list)):
                try:
                    converted = await field.to_db(element, backend)  # type: ignore
                    result.append(converted)
                except FieldValidationError as e:
                    raise FieldValidationError(
                        message=f"Invalid element at index {i}: {str(e)}",
                        field_name=self.name,
                        code="invalid_element",
                    ) from e

            return result
        except Exception as e:
            raise FieldValidationError(
                message=f"Cannot convert to database format: {str(e)}",
                field_name=self.name,
                code="conversion_error",
            ) from e

    async def from_db(
        self, value: DatabaseValue, backend: str
    ) -> Optional[Tuple[T, ...]]:
        """Convert database value to tuple.

        Args:
            value: Database value to convert
            backend: Database backend type

        Returns:
            Converted tuple or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            if not isinstance(value, (tuple, list)):
                raise TypeError(
                    f"Expected list from database, got {type(value).__name__}"
                )

            value_list: List[Any] = list(
                value  # type: ignore
            )  # Convert to list for consistent handling
            if len(value_list) != len(self.fields):
                raise FieldValidationError(
                    message=f"Expected {len(self.fields)} elements, got {len(value_list)}",
                    field_name=self.name,
                    code="invalid_length",
                )

            # Convert each element
            result: List[T] = []
            for i, (field, element) in enumerate(zip(self.fields, value_list)):
                try:
                    converted = await field.from_db(element, backend)  # type: ignore
                    result.append(converted)  # type: ignore
                except FieldValidationError as e:
                    raise FieldValidationError(
                        message=f"Invalid element at index {i}: {str(e)}",
                        field_name=self.name,
                        code="invalid_element",
                    ) from e

            return tuple(result)
        except Exception as e:
            raise FieldValidationError(
                message=f"Cannot convert database value: {str(e)}",
                field_name=self.name,
                code="conversion_error",
            ) from e
