"""List field implementation.

This module provides list field type for handling sequences of values.
It supports:
- List validation
- Element validation
- Length validation
- Uniqueness validation
- Database type mapping
- List comparison operations

Examples:
    >>> class Product(Model):
    ...     tags = ListField(
    ...         StringField(),
    ...         min_length=1,
    ...         unique=True
    ...     )
    ...     prices = ListField(
    ...         DecimalField(min_value=0),
    ...         required=True
    ...     )
    ...
    ...     # Query examples
    ...     tagged = Product.find(Product.tags.contains("sale"))
    ...     expensive = Product.find(Product.prices.average_greater_than(100))
"""

import json
from collections.abc import Sequence
from typing import (
    Any,
    Generic,
    Protocol,
    TypeVar,
    cast,
)

from earnorm.database.mappers import get_mapper
from earnorm.exceptions import FieldValidationError
from earnorm.fields.base import BaseField
from earnorm.types.fields import ComparisonOperator, DatabaseValue, FieldComparisonMixin


class Comparable(Protocol):
    """Protocol for comparable types."""

    def __lt__(self, other: Any) -> bool: ...
    def __gt__(self, other: Any) -> bool: ...


T = TypeVar("T", bound=Comparable)


class ListField(BaseField[list[T]], FieldComparisonMixin, Generic[T]):
    """Field for list values.

    This field type handles sequences of values, with support for:
    - List validation
    - Element validation
    - Length validation
    - Uniqueness validation
    - Database type mapping
    - List comparison operations

    Attributes:
        _element_field: Field type for elements
        min_length: Minimum list length
        max_length: Maximum list length
        unique: Whether elements must be unique
        backend_options: Database backend options
    """

    _element_field: BaseField[T]
    min_length: int | None
    max_length: int | None
    unique: bool
    backend_options: dict[str, Any]

    def __init__(
        self,
        element_field: BaseField[T],
        *,
        min_length: int | None = None,
        max_length: int | None = None,
        unique: bool = False,
        **options: Any,
    ) -> None:
        """Initialize list field.

        Args:
            element_field: Field type for elements
            min_length: Minimum list length
            max_length: Maximum list length
            unique: Whether elements must be unique
            **options: Additional field options
        """
        super().__init__(**options)

        # Store element field as protected attribute
        object.__setattr__(self, "_element_field", element_field)
        self.min_length = min_length
        self.max_length = max_length
        self.unique = unique

        # Initialize backend options using mappers
        self.backend_options = {}
        for backend in ["mongodb", "postgres", "mysql"]:
            mapper = get_mapper(backend)
            self.backend_options[backend] = {
                "type": mapper.get_field_type(self),
                **mapper.get_field_options(self),
            }

    @property
    def element_field(self) -> BaseField[T]:
        """Get element field instance."""
        return object.__getattribute__(self, "_element_field")

    async def setup(self, name: str, model_name: str) -> None:
        """Set up the field.

        Args:
            name: Field name
            model_name: Model name
        """
        await super().setup(name, model_name)
        await self.element_field.setup(f"{name}[]", model_name)

    async def validate(self, value: Any, context: dict[str, Any] | None = None) -> list[T] | None:
        """Validate list value.

        This method validates:
        - Value can be converted to list
        - List length is within bounds
        - Elements are valid
        - Elements are unique if required

        Args:
            value: Value to validate
            context: Validation context with following keys:
                    - model: Model instance
                    - env: Environment instance
                    - operation: Operation type (create/write/search...)
                    - values: Values being validated
                    - field_name: Name of field being validated

        Returns:
            Optional[List[T]]: The validated list value

        Raises:
            FieldValidationError: If validation fails
        """
        value = await super().validate(value, context)

        if value is not None:
            # Convert to list if needed
            try:
                if not isinstance(value, list):
                    value = list(value)
            except (TypeError, ValueError) as e:
                raise FieldValidationError(
                    message=f"Cannot convert to list: {e!s}",
                    field_name=self.name,
                    code="invalid_type",
                    context=context,
                )

            value_list: list[Any] = cast(list[Any], value)

            # Validate length
            if self.min_length is not None and len(value_list) < self.min_length:
                raise FieldValidationError(
                    message=f"List must have at least {self.min_length} elements",
                    field_name=self.name,
                    code="min_length",
                    context=context,
                )
            if self.max_length is not None and len(value_list) > self.max_length:
                raise FieldValidationError(
                    message=f"List must have at most {self.max_length} elements",
                    field_name=self.name,
                    code="max_length",
                    context=context,
                )

            # Create element context
            element_context = {
                **(context or {}),
                "parent_field": self,
                "parent_value": value_list,
                "validation_path": (f"{context.get('validation_path', '')}.{self.name}" if context else self.name),
            }

            # Validate elements
            validated_elements: list[T] = []
            for i, element in enumerate(value_list):
                try:
                    element_context["index"] = i
                    validated = await self.element_field.validate(element, element_context)
                    if validated is not None:
                        validated_elements.append(validated)
                except FieldValidationError as e:
                    raise FieldValidationError(
                        message=f"Invalid element at index {i}: {e!s}",
                        field_name=self.name,
                        code="invalid_element",
                        context=element_context,
                    ) from e

            # Validate uniqueness
            if self.unique and validated_elements:
                seen: set[T] = set()
                duplicates: list[int] = []
                for i, element in enumerate(validated_elements):
                    if element in seen:
                        duplicates.append(i)
                    seen.add(element)

                if duplicates:
                    indices = [str(idx) for idx in duplicates]
                    raise FieldValidationError(
                        message=f"Duplicate elements at indices: {', '.join(indices)}",
                        field_name=self.name,
                        code="duplicate_elements",
                        context=element_context,
                    )

            return validated_elements

        return None

    async def convert(self, value: Any) -> list[T] | None:
        """Convert value to list.

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
            if isinstance(value, str):
                # Try to parse as JSON array
                try:
                    value = json.loads(value)
                    if not isinstance(value, list):
                        raise FieldValidationError(
                            message="JSON value must be an array",
                            field_name=self.name,
                            code="invalid_json",
                        )
                except json.JSONDecodeError as e:
                    raise FieldValidationError(
                        message=f"Invalid JSON array: {e!s}",
                        field_name=self.name,
                        code="invalid_json",
                    ) from e

            # Convert to list
            try:
                value = list(cast(Sequence[Any], value))
            except (TypeError, ValueError) as e:
                raise FieldValidationError(
                    message=f"Cannot convert to list: {e!s}",
                    field_name=self.name,
                    code="conversion_error",
                ) from e

            # Validate length
            if self.min_length is not None and len(value) < self.min_length:
                raise FieldValidationError(
                    message=f"List must have at least {self.min_length} elements",
                    field_name=self.name,
                    code="min_length",
                )
            if self.max_length is not None and len(value) > self.max_length:
                raise FieldValidationError(
                    message=f"List must have at most {self.max_length} elements",
                    field_name=self.name,
                    code="max_length",
                )

            # Convert elements
            result: list[T] = []
            for i, element in enumerate(value):
                try:
                    converted = await self.element_field.convert(element)
                    if converted is not None:
                        result.append(converted)
                except FieldValidationError as e:
                    raise FieldValidationError(
                        message=f"Cannot convert element at index {i}: {e!s}",
                        field_name=self.name,
                        code="conversion_error",
                    ) from e

            # Validate uniqueness
            if self.unique and result:
                seen: set[T] = set()
                duplicates: list[int] = []
                for i, element in enumerate(result):
                    if element in seen:
                        duplicates.append(i)
                    seen.add(element)

                if duplicates:
                    indices = [str(idx) for idx in duplicates]
                    raise FieldValidationError(
                        message=f"Duplicate elements at indices: {', '.join(indices)}",
                        field_name=self.name,
                        code="duplicate_elements",
                    )

            return result

        except Exception as e:
            raise FieldValidationError(
                message=f"Cannot convert to list: {e!s}",
                field_name=self.name,
                code="conversion_error",
            ) from e

    async def to_db(self, value: list[T] | None, backend: str) -> DatabaseValue:
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
            result: list[DatabaseValue] = []
            for element in value:
                db_value = await self.element_field.to_db(element, backend)
                result.append(db_value)
            return result
        except Exception as e:
            raise FieldValidationError(
                message=f"Cannot convert list to database format: {e!s}",
                field_name=self.name,
                code="db_conversion_error",
            ) from e

    async def from_db(self, value: DatabaseValue, backend: str) -> list[T] | None:
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

        if not isinstance(value, list):
            raise FieldValidationError(
                message=f"Database value must be a list, got {type(value).__name__}",
                field_name=self.name,
                code="invalid_db_type",
            )

        try:
            result: list[T] = []
            for i, element in enumerate(value):
                try:
                    converted = await self.element_field.from_db(element, backend)
                    if converted is not None:
                        result.append(converted)
                except Exception as e:
                    raise FieldValidationError(
                        message=f"Cannot convert database value at index {i}: {e!s}",
                        field_name=self.name,
                        code="db_conversion_error",
                    ) from e

            return result
        except Exception as e:
            raise FieldValidationError(
                message=f"Cannot convert database value to list: {e!s}",
                field_name=self.name,
                code="db_conversion_error",
            ) from e

    def _prepare_value(self, value: Any) -> DatabaseValue:
        """Prepare list value for comparison.

        Args:
            value: Value to prepare

        Returns:
            Prepared list value or None
        """
        if value is None:
            return None

        try:
            if isinstance(value, (list, tuple)):
                return [self.element_field._prepare_value(x) for x in cast(Sequence[T], value)]
            return [self.element_field._prepare_value(value)]
        except (TypeError, ValueError, AttributeError):
            return None

    def contains(self, value: T) -> ComparisonOperator:
        """Check if list contains value.

        Args:
            value: Value to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "contains", self._prepare_value(value))

    def not_contains(self, value: T) -> ComparisonOperator:
        """Check if list does not contain value.

        Args:
            value: Value to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "not_contains", self._prepare_value(value))

    def contains_all(self, values: list[T] | Sequence[T]) -> ComparisonOperator:
        """Check if list contains all values.

        Args:
            values: Values to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and values
        """
        return ComparisonOperator(self.name, "contains_all", self._prepare_value(values))

    def contains_any(self, values: list[T] | Sequence[T]) -> ComparisonOperator:
        """Check if list contains any value.

        Args:
            values: Values to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and values
        """
        return ComparisonOperator(self.name, "contains_any", self._prepare_value(values))

    def length_equals(self, length: int) -> ComparisonOperator:
        """Check if list length equals value.

        Args:
            length: Length to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "length_equals", length)

    def length_greater_than(self, length: int) -> ComparisonOperator:
        """Check if list length is greater than value.

        Args:
            length: Length to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "length_greater_than", length)

    def length_less_than(self, length: int) -> ComparisonOperator:
        """Check if list length is less than value.

        Args:
            length: Length to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "length_less_than", length)

    def is_empty(self) -> ComparisonOperator:
        """Check if list is empty.

        Returns:
            ComparisonOperator: Comparison operator with field name
        """
        return ComparisonOperator(self.name, "is_empty", None)

    def is_not_empty(self) -> ComparisonOperator:
        """Check if list is not empty.

        Returns:
            ComparisonOperator: Comparison operator with field name
        """
        return ComparisonOperator(self.name, "is_not_empty", None)

    def sum_equals(self, value: int | float) -> ComparisonOperator:
        """Check if sum of list elements equals value.

        Args:
            value: Value to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "sum_equals", value)

    def sum_greater_than(self, value: int | float) -> ComparisonOperator:
        """Check if sum of list elements is greater than value.

        Args:
            value: Value to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "sum_greater_than", value)

    def sum_less_than(self, value: int | float) -> ComparisonOperator:
        """Check if sum of list elements is less than value.

        Args:
            value: Value to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "sum_less_than", value)

    def average_equals(self, value: int | float) -> ComparisonOperator:
        """Check if average of list elements equals value.

        Args:
            value: Value to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "average_equals", value)

    def average_greater_than(self, value: int | float) -> ComparisonOperator:
        """Check if average of list elements is greater than value.

        Args:
            value: Value to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "average_greater_than", value)

    def average_less_than(self, value: int | float) -> ComparisonOperator:
        """Check if average of list elements is less than value.

        Args:
            value: Value to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "average_less_than", value)
