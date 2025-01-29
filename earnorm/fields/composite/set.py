"""Set field implementation.

This module provides set field type for handling unique collections of values.
It supports:
- Set validation
- Item validation
- Length validation
- Database type mapping
- Set comparison operations

Examples:
    >>> class Product(Model):
    ...     tags = SetField(StringField())
    ...     categories = SetField(
    ...         StringField(),
    ...         min_length=1,
    ...         max_length=5,
    ...     )
    ...
    ...     # Query examples
    ...     has_tag = Product.find(Product.tags.contains("python"))
    ...     tech_products = Product.find(Product.categories.is_subset({"tech", "software"}))
    ...     popular = Product.find(Product.tags.length_greater_than(5))
"""

from typing import Any, Generic, List, Optional, Sequence, Set, TypeVar, Union, cast

from earnorm.exceptions import FieldValidationError
from earnorm.fields.base import BaseField
from earnorm.types.fields import ComparisonOperator, DatabaseValue, FieldComparisonMixin

# Type variable for set items
T = TypeVar("T")


class SetField(BaseField[Set[T]], FieldComparisonMixin, Generic[T]):
    """Field for set values.

    This field type handles unique collections of values, with support for:
    - Set validation
    - Item validation
    - Length validation
    - Database type mapping
    - Set comparison operations

    Attributes:
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
        return object.__getattribute__(self, "_field")

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

            value_set: Set[Any] = cast(Set[Any], value)

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

    def _prepare_value(self, value: Any) -> DatabaseValue:
        """Prepare set value for comparison.

        Converts value to list for database comparison.

        Args:
            value: Value to prepare

        Returns:
            Prepared list value or None
        """
        if value is None:
            return None

        try:
            if isinstance(value, (set, list)):
                return list(cast(Union[Set[Any], List[Any]], value))
            elif isinstance(value, (str, bytes)):
                return [value]
            return None
        except (TypeError, ValueError):
            return None

    def contains(self, value: T) -> ComparisonOperator:
        """Check if set contains value.

        Args:
            value: Value to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "contains", self._prepare_value(value))

    def not_contains(self, value: T) -> ComparisonOperator:
        """Check if set does not contain value.

        Args:
            value: Value to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "not_contains", self._prepare_value(value))

    def contains_all(self, values: Union[Set[T], List[T]]) -> ComparisonOperator:
        """Check if set contains all values.

        Args:
            values: Values to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and values
        """
        prepared_values = [self._prepare_value(value) for value in values]
        return ComparisonOperator(self.name, "contains_all", prepared_values)

    def contains_any(self, values: Union[Set[T], List[T]]) -> ComparisonOperator:
        """Check if set contains any of values.

        Args:
            values: Values to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and values
        """
        prepared_values = [self._prepare_value(value) for value in values]
        return ComparisonOperator(self.name, "contains_any", prepared_values)

    def length_equals(self, length: int) -> ComparisonOperator:
        """Check if set length equals value.

        Args:
            length: Length to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "length_eq", length)

    def length_greater_than(self, length: int) -> ComparisonOperator:
        """Check if set length is greater than value.

        Args:
            length: Length to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "length_gt", length)

    def length_less_than(self, length: int) -> ComparisonOperator:
        """Check if set length is less than value.

        Args:
            length: Length to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "length_lt", length)

    def is_empty(self) -> ComparisonOperator:
        """Check if set is empty.

        Returns:
            ComparisonOperator: Comparison operator with field name
        """
        return ComparisonOperator(self.name, "is_empty", None)

    def is_not_empty(self) -> ComparisonOperator:
        """Check if set is not empty.

        Returns:
            ComparisonOperator: Comparison operator with field name
        """
        return ComparisonOperator(self.name, "is_not_empty", None)

    def is_subset(self, other: Union[Set[T], List[T]]) -> ComparisonOperator:
        """Check if set is subset of another set.

        Args:
            other: Set to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "is_subset", self._prepare_value(other))

    def is_superset(self, other: Union[Set[T], List[T]]) -> ComparisonOperator:
        """Check if set is superset of another set.

        Args:
            other: Set to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "is_superset", self._prepare_value(other))

    def is_disjoint(self, other: Union[Set[T], List[T]]) -> ComparisonOperator:
        """Check if set has no elements in common with another set.

        Args:
            other: Set to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "is_disjoint", self._prepare_value(other))

    def equals(self, other: Union[Set[T], List[T]]) -> ComparisonOperator:
        """Check if set equals another set.

        Args:
            other: Set to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "equals", self._prepare_value(other))

    def not_equals(self, other: Union[Set[T], List[T]]) -> ComparisonOperator:
        """Check if set does not equal another set.

        Args:
            other: Set to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "not_equals", self._prepare_value(other))

    async def convert(self, value: Any) -> Optional[Set[T]]:
        """Convert value to set.

        This method converts:
        - Set to set
        - Sequence to set
        - None to None

        Args:
            value: Value to convert

        Returns:
            Converted set value or None

        Raises:
            FieldValidationError: If conversion fails
        """
        if value is None:
            return None

        try:
            if isinstance(value, set):
                items = cast(Set[Any], value)
            elif isinstance(value, Sequence):
                items = set(cast(Sequence[Any], value))
            else:
                raise ValueError(f"Cannot convert {type(value).__name__} to set")

            # Convert each item
            converted_items: Set[T] = set()
            for item in items:
                converted_item = await self.field.convert(item)
                if converted_item is not None:
                    converted_items.add(converted_item)

            return converted_items

        except (TypeError, ValueError) as e:
            raise FieldValidationError(
                message=str(e),
                field_name=self.name,
                code="conversion_error",
            ) from e

    async def to_db(self, value: Optional[Set[T]], backend: str) -> DatabaseValue:
        """Convert set to database value.

        This method converts:
        - Set to list
        - None to None

        Args:
            value: Value to convert
            backend: Database backend type

        Returns:
            Database value
        """
        if value is None:
            return None

        db_items: List[DatabaseValue] = []
        for item in value:
            db_item = await self.field.to_db(item, backend=backend)
            if db_item is not None:
                db_items.append(db_item)

        return db_items

    async def from_db(self, value: DatabaseValue, backend: str) -> Optional[Set[T]]:
        """Convert database value to set.

        This method converts:
        - List to set
        - None to None

        Args:
            value: Value to convert
            backend: Database backend type

        Returns:
            Set value or None
        """
        if value is None:
            return None

        if not isinstance(value, list):
            raise FieldValidationError(
                message=f"Expected list from database, got {type(value).__name__}",
                field_name=self.name,
                code="invalid_type",
            )

        items: Set[T] = set()
        for item in value:
            converted_item = await self.field.from_db(item, backend=backend)
            if converted_item is not None:
                items.add(converted_item)

        return items
