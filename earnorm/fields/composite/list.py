"""List field implementation.

This module provides list field type for handling sequences of values.
It supports:
- List validation
- Element validation
- Length validation
- Database type mapping
- List comparison operations

Examples:
    >>> class Post(Model):
    ...     tags = ListField(StringField())
    ...     comments = ListField(
    ...         EmbeddedField(Comment),
    ...         min_length=0,
    ...         max_length=1000
    ...     )
    ...     ratings = ListField(IntegerField(min_value=1, max_value=5))
    ...
    ...     # Query examples
    ...     has_tag = Post.find(Post.tags.contains("python"))
    ...     top_rated = Post.find(Post.ratings.average_greater_than(4.5))
    ...     popular = Post.find(Post.comments.length_greater_than(100))
"""

from typing import Any, Generic, List, Optional, TypeVar, Union, cast

from earnorm.exceptions import FieldValidationError
from earnorm.fields.base import BaseField
from earnorm.types.fields import ComparisonOperator, DatabaseValue, FieldComparisonMixin

# Type variable for list elements
T = TypeVar("T")


class ListField(BaseField[List[T]], FieldComparisonMixin, Generic[T]):
    """Field for list values.

    This field type handles sequences of values, with support for:
    - List validation
    - Element validation
    - Length validation
    - Database type mapping
    - List comparison operations

    Attributes:
        min_length: Minimum list length
        max_length: Maximum list length
        unique: Whether elements must be unique
        backend_options: Database backend options
    """

    min_length: Optional[int]
    max_length: Optional[int]
    unique: bool
    backend_options: dict[str, Any]

    def __init__(
        self,
        element_field: BaseField[T],
        *,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        unique: bool = False,
        **options: Any,
    ) -> None:
        """Initialize list field.

        Args:
            element_field: Field type for list elements
            min_length: Minimum list length
            max_length: Maximum list length
            unique: Whether elements must be unique
            **options: Additional field options
        """
        super().__init__(**options)

        # Store as protected attribute to avoid type issues
        object.__setattr__(self, "_element_field", element_field)
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

    async def validate(self, value: Any) -> None:
        """Validate list value.

        This method validates:
        - Value is a list
        - List length is within bounds
        - Elements are valid
        - Elements are unique (if required)

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

            value_list: List[Any] = cast(List[Any], value)

            # Validate length
            if self.min_length is not None and len(value_list) < self.min_length:
                raise FieldValidationError(
                    message=f"List must have at least {self.min_length} elements",
                    field_name=self.name,
                    code="min_length",
                )

            if self.max_length is not None and len(value_list) > self.max_length:
                raise FieldValidationError(
                    message=f"List must have at most {self.max_length} elements",
                    field_name=self.name,
                    code="max_length",
                )

            # Validate elements
            for i, element in enumerate(value_list):
                try:
                    await self.element_field.validate(element)
                except FieldValidationError as e:
                    raise FieldValidationError(
                        message=f"Invalid element at index {i}: {str(e)}",
                        field_name=self.name,
                        code="invalid_element",
                    ) from e

            # Validate uniqueness
            if self.unique and len(value_list) != len(set(value_list)):
                raise FieldValidationError(
                    message="List elements must be unique",
                    field_name=self.name,
                    code="not_unique",
                )

    async def convert(self, value: Any) -> Optional[List[T]]:
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
                import json

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
                        message=f"Invalid JSON array: {str(e)}",
                        field_name=self.name,
                        code="invalid_json",
                    ) from e

            if not isinstance(value, list):
                # Try to convert to list
                try:
                    value = list(value)
                except (TypeError, ValueError) as e:
                    raise FieldValidationError(
                        message=f"Cannot convert to list: {str(e)}",
                        field_name=self.name,
                        code="conversion_error",
                    ) from e

            # Convert elements
            result: List[T] = []
            for i, element in enumerate(cast(List[Any], value)):
                try:
                    converted = await self.element_field.convert(element)
                    if converted is not None:
                        result.append(converted)
                except FieldValidationError as e:
                    raise FieldValidationError(
                        message=f"Cannot convert element at index {i}: {str(e)}",
                        field_name=self.name,
                        code="conversion_error",
                    ) from e

            return result
        except Exception as e:
            raise FieldValidationError(
                message=f"Cannot convert to list: {str(e)}",
                field_name=self.name,
                code="conversion_error",
            ) from e

    async def to_db(self, value: Optional[List[T]], backend: str) -> DatabaseValue:
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
            # Convert elements
            result: List[DatabaseValue] = []
            for i, element in enumerate(value):
                try:
                    converted = await self.element_field.to_db(element, backend)
                    if converted is not None:
                        result.append(converted)
                except FieldValidationError as e:
                    raise FieldValidationError(
                        message=f"Cannot convert element at index {i}: {str(e)}",
                        field_name=self.name,
                        code="conversion_error",
                    ) from e

            return result
        except Exception as e:
            raise FieldValidationError(
                message=f"Cannot convert to database format: {str(e)}",
                field_name=self.name,
                code="conversion_error",
            ) from e

    async def from_db(self, value: DatabaseValue, backend: str) -> Optional[List[T]]:
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

            # Convert elements
            result: List[T] = []
            for i, element in enumerate(value):
                try:
                    converted = await self.element_field.from_db(element, backend)
                    if converted is not None:
                        result.append(converted)
                except FieldValidationError as e:
                    raise FieldValidationError(
                        message=f"Cannot convert element at index {i}: {str(e)}",
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

    def _prepare_value(self, value: Any) -> DatabaseValue:
        """Prepare list value for comparison.

        Converts value to list for database comparison.

        Args:
            value: Value to prepare

        Returns:
            Prepared list value or None
        """
        if value is None:
            return None

        try:
            if isinstance(value, list):
                return list(cast(List[Any], value))
            elif isinstance(value, (str, bytes)):
                return [value]
            return None
        except (TypeError, ValueError):
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

    def contains_all(self, values: List[T]) -> ComparisonOperator:
        """Check if list contains all values.

        Args:
            values: Values to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and values
        """
        prepared_values = [self._prepare_value(value) for value in values]
        return ComparisonOperator(self.name, "contains_all", prepared_values)

    def contains_any(self, values: List[T]) -> ComparisonOperator:
        """Check if list contains any of values.

        Args:
            values: Values to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and values
        """
        prepared_values = [self._prepare_value(value) for value in values]
        return ComparisonOperator(self.name, "contains_any", prepared_values)

    def length_equals(self, length: int) -> ComparisonOperator:
        """Check if list length equals value.

        Args:
            length: Length to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "length_eq", length)

    def length_greater_than(self, length: int) -> ComparisonOperator:
        """Check if list length is greater than value.

        Args:
            length: Length to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "length_gt", length)

    def length_less_than(self, length: int) -> ComparisonOperator:
        """Check if list length is less than value.

        Args:
            length: Length to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "length_lt", length)

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

    def sum_equals(self, value: Union[int, float]) -> ComparisonOperator:
        """Check if sum of numeric elements equals value.

        Args:
            value: Value to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "sum_eq", value)

    def sum_greater_than(self, value: Union[int, float]) -> ComparisonOperator:
        """Check if sum of numeric elements is greater than value.

        Args:
            value: Value to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "sum_gt", value)

    def sum_less_than(self, value: Union[int, float]) -> ComparisonOperator:
        """Check if sum of numeric elements is less than value.

        Args:
            value: Value to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "sum_lt", value)

    def average_equals(self, value: Union[int, float]) -> ComparisonOperator:
        """Check if average of numeric elements equals value.

        Args:
            value: Value to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "avg_eq", value)

    def average_greater_than(self, value: Union[int, float]) -> ComparisonOperator:
        """Check if average of numeric elements is greater than value.

        Args:
            value: Value to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "avg_gt", value)

    def average_less_than(self, value: Union[int, float]) -> ComparisonOperator:
        """Check if average of numeric elements is less than value.

        Args:
            value: Value to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "avg_lt", value)
