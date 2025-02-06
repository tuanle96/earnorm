"""Tuple field implementation.

This module provides tuple field type for handling fixed-length sequences of values.
It supports:
- Tuple validation
- Element validation
- Length validation
- Database type mapping
- Tuple comparison operations

Examples:
    >>> class Point(Model):
    ...     coordinates = TupleField(
    ...         (FloatField(), FloatField(), FloatField()),
    ...         required=True
    ...     )
    ...     bounds = TupleField(
    ...         (FloatField(min_value=0), FloatField(min_value=0))
    ...     )
    ...
    ...     # Query examples
    ...     origin = Point.find(Point.coordinates.equals((0, 0, 0)))
    ...     in_range = Point.find(Point.bounds.contains(5.0))
"""

import json
from typing import (
    Any,
    Dict,
    Generic,
    List,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    TypeVar,
    Union,
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


class TupleField(BaseField[Tuple[T, ...]], FieldComparisonMixin, Generic[T]):
    """Field for tuple values.

    This field type handles fixed-length sequences of values, with support for:
    - Tuple validation
    - Element validation
    - Database type mapping
    - Tuple comparison operations

    Attributes:
        element_fields: Tuple of field types for elements
        backend_options: Database backend options
    """

    element_fields: Tuple[BaseField[T], ...]  # type: ignore
    backend_options: Dict[str, Any]

    def __init__(
        self,
        element_fields: Sequence[BaseField[T]],
        **options: Any,
    ) -> None:
        """Initialize tuple field.

        Args:
            element_fields: Sequence of field types for elements
            **options: Additional field options
        """
        super().__init__(**options)

        # Store as protected attribute to avoid type issues
        object.__setattr__(self, "_element_fields", tuple(element_fields))

        # Initialize backend options using mappers
        self.backend_options = {}
        for backend in ["mongodb", "postgres", "mysql"]:
            mapper = get_mapper(backend)
            self.backend_options[backend] = {
                "type": mapper.get_field_type(self),
                **mapper.get_field_options(self),
            }

    @property
    def element_fields(self) -> Tuple[BaseField[T], ...]:
        """Get element fields."""
        return object.__getattribute__(self, "_element_fields")

    async def setup(self, name: str, model_name: str) -> None:
        """Set up the field.

        Args:
            name: Field name
            model_name: Model name
        """
        await super().setup(name, model_name)
        for i, field in enumerate(self.element_fields):
            await field.setup(f"{name}[{i}]", model_name)

    async def validate(
        self, value: Any, context: Optional[Dict[str, Any]] = None
    ) -> Optional[Tuple[T, ...]]:
        """Validate tuple value.

        This method validates:
        - Value can be converted to tuple
        - Length matches number of element fields
        - Elements are valid

        Args:
            value: Value to validate
            context: Validation context with following keys:
                    - model: Model instance
                    - env: Environment instance
                    - operation: Operation type (create/write/search...)
                    - values: Values being validated
                    - field_name: Name of field being validated

        Returns:
            Optional[Tuple[T, ...]]: The validated tuple value

        Raises:
            FieldValidationError: If validation fails
        """
        value = await super().validate(value, context)

        if value is not None:
            # Convert to tuple if needed
            try:
                if not isinstance(value, tuple):
                    value = tuple(value)
            except (TypeError, ValueError) as e:
                raise FieldValidationError(
                    message=f"Cannot convert to tuple: {str(e)}",
                    field_name=self.name,
                    code="invalid_type",
                    context=context,
                )

            value_tuple: Tuple[Any, ...] = cast(Tuple[Any, ...], value)

            # Validate length
            expected_length = len(self.element_fields)
            if len(value_tuple) != expected_length:
                raise FieldValidationError(
                    message=f"Tuple must have exactly {expected_length} elements",
                    field_name=self.name,
                    code="invalid_length",
                    context=context,
                )

            # Create element context
            element_context = {
                **(context or {}),
                "parent_field": self,
                "parent_value": value_tuple,
                "validation_path": (
                    f"{context.get('validation_path', '')}.{self.name}"
                    if context
                    else self.name
                ),
            }

            # Validate elements
            validated_elements: List[T] = []
            for i, (element, field) in enumerate(zip(value_tuple, self.element_fields)):
                try:
                    element_context["index"] = i
                    validated = await field.validate(element, element_context)
                    if validated is not None:
                        validated_elements.append(validated)
                except FieldValidationError as e:
                    raise FieldValidationError(
                        message=f"Invalid element at index {i}: {str(e)}",
                        field_name=self.name,
                        code="invalid_element",
                        context=element_context,
                    ) from e

            return tuple(validated_elements)

        return None

    async def convert(self, value: Any) -> Optional[Tuple[T, ...]]:
        """Convert value to tuple.

        Args:
            value: Value to convert

        Returns:
            Converted tuple value or None

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
                    if not isinstance(value, (list, tuple)):
                        raise FieldValidationError(
                            message="JSON value must be an array",
                            field_name=self.name,
                            code="invalid_json",
                        )
                except json.JSONDecodeError as e:
                    raise FieldValidationError(
                        message=f"Invalid JSON array: {str(e)}",
                        field_name=self.name,
                        code="invalid_json",
                    ) from e

            # Convert to tuple
            try:
                value = tuple(cast(Sequence[Any], value))
            except (TypeError, ValueError) as e:
                raise FieldValidationError(
                    message=f"Cannot convert to tuple: {str(e)}",
                    field_name=self.name,
                    code="conversion_error",
                ) from e

            # Validate length
            expected_length = len(self.element_fields)
            if len(value) != expected_length:
                raise FieldValidationError(
                    message=f"Tuple must have exactly {expected_length} elements",
                    field_name=self.name,
                    code="invalid_length",
                )

            # Convert elements
            result: List[T] = []
            for i, (element, field) in enumerate(zip(value, self.element_fields)):  # type: ignore
                try:
                    converted = await field.convert(element)
                    if converted is not None:
                        result.append(converted)
                except FieldValidationError as e:
                    raise FieldValidationError(
                        message=f"Cannot convert element at index {i}: {str(e)}",
                        field_name=self.name,
                        code="conversion_error",
                    ) from e

            return tuple(result)

        except Exception as e:
            raise FieldValidationError(
                message=f"Cannot convert to tuple: {str(e)}",
                field_name=self.name,
                code="conversion_error",
            ) from e

    async def to_db(
        self, value: Optional[Tuple[T, ...]], backend: str
    ) -> DatabaseValue:
        """Convert tuple to database format.

        Args:
            value: Tuple value to convert
            backend: Database backend type

        Returns:
            Converted tuple value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            result: List[DatabaseValue] = []
            for element, field in zip(value, self.element_fields):
                db_value = await field.to_db(element, backend)
                result.append(db_value)
            return result
        except Exception as e:
            raise FieldValidationError(
                message=f"Cannot convert tuple to database format: {str(e)}",
                field_name=self.name,
                code="db_conversion_error",
            ) from e

    async def from_db(
        self, value: DatabaseValue, backend: str
    ) -> Optional[Tuple[T, ...]]:
        """Convert database value to tuple.

        Args:
            value: Database value to convert
            backend: Database backend type

        Returns:
            Converted tuple value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        if not isinstance(value, (list, tuple)):
            raise FieldValidationError(
                message=f"Database value must be a list or tuple, got {type(value).__name__}",
                field_name=self.name,
                code="invalid_db_type",
            )

        try:
            result: List[T] = []
            for i, (element, field) in enumerate(zip(value, self.element_fields)):
                try:
                    converted = await field.from_db(element, backend)
                    if converted is not None:
                        result.append(converted)
                except Exception as e:
                    raise FieldValidationError(
                        message=f"Cannot convert database value at index {i}: {str(e)}",
                        field_name=self.name,
                        code="db_conversion_error",
                    ) from e

            return tuple(result)
        except Exception as e:
            raise FieldValidationError(
                message=f"Cannot convert database value to tuple: {str(e)}",
                field_name=self.name,
                code="db_conversion_error",
            ) from e

    def _prepare_value(self, value: Any) -> DatabaseValue:
        """Prepare tuple value for comparison.

        Args:
            value: Value to prepare

        Returns:
            Prepared tuple value or None
        """
        if value is None:
            return None

        try:
            if isinstance(value, (list, tuple)):
                return [
                    getattr(field, "_prepare_value")(x)
                    for x, field in zip(value, self.element_fields)  # type: ignore
                ]
            return [getattr(self.element_fields[0], "_prepare_value")(value)]
        except (TypeError, ValueError, AttributeError):
            return None

    def equals(self, value: Union[Tuple[T, ...], List[T]]) -> ComparisonOperator:
        """Check if tuple equals value.

        Args:
            value: Value to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "equals", self._prepare_value(value))

    def not_equals(self, value: Union[Tuple[T, ...], List[T]]) -> ComparisonOperator:
        """Check if tuple does not equal value.

        Args:
            value: Value to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "not_equals", self._prepare_value(value))

    def contains(self, value: T) -> ComparisonOperator:
        """Check if tuple contains value.

        Args:
            value: Value to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "contains", self._prepare_value(value))

    def not_contains(self, value: T) -> ComparisonOperator:
        """Check if tuple does not contain value.

        Args:
            value: Value to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "not_contains", self._prepare_value(value))

    def contains_all(self, values: Union[Tuple[T, ...], List[T]]) -> ComparisonOperator:
        """Check if tuple contains all values.

        Args:
            values: Values to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and values
        """
        return ComparisonOperator(
            self.name, "contains_all", self._prepare_value(values)
        )

    def contains_any(self, values: Union[Tuple[T, ...], List[T]]) -> ComparisonOperator:
        """Check if tuple contains any value.

        Args:
            values: Values to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and values
        """
        return ComparisonOperator(
            self.name, "contains_any", self._prepare_value(values)
        )

    def starts_with(self, value: T) -> ComparisonOperator:
        """Check if tuple starts with value.

        Args:
            value: Value to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "starts_with", self._prepare_value(value))

    def ends_with(self, value: T) -> ComparisonOperator:
        """Check if tuple ends with value.

        Args:
            value: Value to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "ends_with", self._prepare_value(value))

    def is_empty(self) -> ComparisonOperator:
        """Check if tuple is empty.

        Returns:
            ComparisonOperator: Comparison operator with field name
        """
        return ComparisonOperator(self.name, "is_empty", None)

    def is_not_empty(self) -> ComparisonOperator:
        """Check if tuple is not empty.

        Returns:
            ComparisonOperator: Comparison operator with field name
        """
        return ComparisonOperator(self.name, "is_not_empty", None)
