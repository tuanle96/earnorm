"""Base field implementation.

This module provides the base field class that all field types inherit from.
It handles:
- Field setup and initialization
- Value validation and conversion
- Type checking and constraints
- Comparison operations
"""

from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    Generic,
    List,
    Optional,
    Pattern,
    Tuple,
    TypeVar,
    Union,
    cast,
    overload,
)

from earnorm.exceptions import FieldValidationError
from earnorm.fields.adapters.base import DatabaseAdapter
from earnorm.fields.types import ValidationContext
from earnorm.types.fields import ComparisonOperator, DatabaseValue

T = TypeVar("T")  # Field value type

# Type aliases for validation
ValidatorResult = Union[bool, Tuple[bool, str]]
ValidatorCallable = Callable[[Any], Coroutine[Any, Any, ValidatorResult]]


class FieldComparison:
    """Helper class for field comparisons.

    This class provides comparison methods that return ComparisonOperator instances
    instead of boolean values. This avoids conflicts with Python's built-in
    comparison methods.

    Supported operators:
    - Basic comparisons: eq, ne, gt, ge, lt, le
    - List operations: in_, not_in
    - String operations: like, ilike, regex, iregex
    - Null checks: is_null, is_not_null
    - Range operations: between, not_between
    - Array operations: contains, not_contains, all, any, size
    - String operations: starts_with, ends_with, length
    - Document operations: exists, not_exists
    """

    def __init__(self, field_name: str) -> None:
        """Initialize field comparison.

        Args:
            field_name: Name of the field being compared
        """
        self.field_name = field_name

    def eq(self, other: Any) -> ComparisonOperator:
        """Equal comparison.

        Args:
            other: Value to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.field_name, "=", other)

    def ne(self, other: Any) -> ComparisonOperator:
        """Not equal comparison.

        Args:
            other: Value to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.field_name, "!=", other)

    def gt(self, other: Any) -> ComparisonOperator:
        """Greater than comparison.

        Args:
            other: Value to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.field_name, ">", other)

    def ge(self, other: Any) -> ComparisonOperator:
        """Greater than or equal comparison.

        Args:
            other: Value to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.field_name, ">=", other)

    def lt(self, other: Any) -> ComparisonOperator:
        """Less than comparison.

        Args:
            other: Value to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.field_name, "<", other)

    def le(self, other: Any) -> ComparisonOperator:
        """Less than or equal comparison.

        Args:
            other: Value to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.field_name, "<=", other)

    def in_(self, values: List[Any]) -> ComparisonOperator:
        """Check if field value is in list.

        Args:
            values: List of values to check against

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.field_name, "in", values)

    def not_in(self, values: List[Any]) -> ComparisonOperator:
        """Check if field value is not in list.

        Args:
            values: List of values to check against

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.field_name, "not_in", values)

    def like(self, pattern: str) -> ComparisonOperator:
        """Case-sensitive pattern matching.

        Args:
            pattern: Pattern to match against (using SQL LIKE syntax)
                % - Match any sequence of characters
                _ - Match any single character

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.field_name, "like", pattern)

    def ilike(self, pattern: str) -> ComparisonOperator:
        """Case-insensitive pattern matching.

        Args:
            pattern: Pattern to match against (using SQL LIKE syntax)
                % - Match any sequence of characters
                _ - Match any single character

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.field_name, "ilike", pattern)

    def regex(self, pattern: Union[str, Pattern[str]]) -> ComparisonOperator:
        """Case-sensitive regular expression matching.

        Args:
            pattern: Regular expression pattern to match against

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.field_name, "regex", pattern)

    def iregex(self, pattern: Union[str, Pattern[str]]) -> ComparisonOperator:
        """Case-insensitive regular expression matching.

        Args:
            pattern: Regular expression pattern to match against

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.field_name, "iregex", pattern)

    def is_null(self) -> ComparisonOperator:
        """Check if field value is null.

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.field_name, "is_null", None)

    def is_not_null(self) -> ComparisonOperator:
        """Check if field value is not null.

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.field_name, "is_not_null", None)

    def between(self, start: Any, end: Any) -> ComparisonOperator:
        """Check if field value is between start and end (inclusive).

        Args:
            start: Start value
            end: End value

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.field_name, "between", (start, end))

    def not_between(self, start: Any, end: Any) -> ComparisonOperator:
        """Check if field value is not between start and end (inclusive).

        Args:
            start: Start value
            end: End value

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.field_name, "not_between", (start, end))

    # Array operations
    def contains(self, value: Any) -> ComparisonOperator:
        """Check if array field contains value.

        Args:
            value: Value to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.field_name, "contains", value)

    def not_contains(self, value: Any) -> ComparisonOperator:
        """Check if array field does not contain value.

        Args:
            value: Value to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.field_name, "not_contains", value)

    def all(self, values: List[Any]) -> ComparisonOperator:
        """Check if array field contains all values.

        Args:
            values: List of values that must all be present

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.field_name, "all", values)

    def any(self, values: List[Any]) -> ComparisonOperator:
        """Check if array field contains any of the values.

        Args:
            values: List of values to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.field_name, "any", values)

    def size(self, size: int) -> ComparisonOperator:
        """Check array or string field length.

        Args:
            size: Expected length

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.field_name, "size", size)

    # String operations
    def starts_with(
        self, prefix: str, case_sensitive: bool = True
    ) -> ComparisonOperator:
        """Check if string field starts with prefix.

        Args:
            prefix: String prefix to check for
            case_sensitive: Whether to perform case-sensitive comparison

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        operator = "starts_with" if case_sensitive else "istarts_with"
        return ComparisonOperator(self.field_name, operator, prefix)

    def ends_with(self, suffix: str, case_sensitive: bool = True) -> ComparisonOperator:
        """Check if string field ends with suffix.

        Args:
            suffix: String suffix to check for
            case_sensitive: Whether to perform case-sensitive comparison

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        operator = "ends_with" if case_sensitive else "iends_with"
        return ComparisonOperator(self.field_name, operator, suffix)

    def length(self, length: int) -> ComparisonOperator:
        """Check string field length.

        Args:
            length: Expected length

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.field_name, "length", length)

    # Document operations
    def exists(self, field: str) -> ComparisonOperator:
        """Check if document field exists.

        Args:
            field: Field name to check for existence

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.field_name, "exists", field)

    def not_exists(self, field: str) -> ComparisonOperator:
        """Check if document field does not exist.

        Args:
            field: Field name to check for non-existence

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.field_name, "not_exists", field)

    def matches(self, query: Dict[str, Any]) -> ComparisonOperator:
        """Check if document field matches query.

        Args:
            query: Query dictionary to match against

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.field_name, "matches", query)


class BaseField(Generic[T]):
    """Base class for all field types.

    This class provides common functionality for all fields:
    - Field setup and initialization
    - Value validation and conversion
    - Type checking and constraints
    - Comparison operations for filtering

    Args:
        **kwargs: Field options passed to subclasses.
    """

    name: str
    model_name: str
    _value: Optional[T]
    _options: Dict[str, Any]
    required: bool
    readonly: bool
    store: bool
    index: bool
    help: str

    def __init__(self, **kwargs: Any) -> None:
        """Initialize field.

        Args:
            **kwargs: Field options passed to subclasses.
        """
        self.name: str = ""
        self.model_name: str = ""
        self._value: Optional[T] = None
        self._options = kwargs
        self.required = kwargs.get("required", True)
        self.readonly = kwargs.get("readonly", False)
        self.store = kwargs.get("store", True)
        self.index = kwargs.get("index", False)
        self.help = kwargs.get("help", "")
        self.compute = kwargs.get("compute")
        self.depends = kwargs.get("depends", [])
        self.validators = kwargs.get("validators", [])
        self.adapters: Dict[str, DatabaseAdapter[T]] = {}
        self._comparison = FieldComparison(self.name)

    @property
    def comparison(self) -> FieldComparison:
        """Get field comparison helper.

        Returns:
            FieldComparison: Field comparison helper
        """
        self._comparison.field_name = self.name  # Update field name in case it changed
        return self._comparison

    @property
    def default(self) -> Optional[Any]:
        """Get field default value.

        Returns:
            Optional[Any]: Default value or None if not set
        """
        return self._options.get("default")

    async def setup(self, name: str, model_name: str) -> None:
        """Set up the field.

        Args:
            name: Field name.
            model_name: Model name.
        """
        self.name = name
        self.model_name = model_name

    def register_adapter(self, adapter: DatabaseAdapter[T]) -> None:
        """Register database adapter.

        Args:
            adapter: Database adapter instance
        """
        self.adapters[adapter.backend_name] = adapter

    async def validate(self, value: Optional[T]) -> Optional[T]:
        """Validate field value.

        Args:
            value: Value to validate

        Returns:
            Optional[T]: Validated value

        Raises:
            FieldValidationError: If validation fails
        """
        # Skip validation for None values if field is not required
        if value is None:
            if self.required:
                raise FieldValidationError(
                    message=f"Field '{self.name}' is required",
                    field_name=self.name,
                    code="validation_error",
                )
            return None

        # Create validation context
        context = ValidationContext(
            field=self,
            value=value,
            metadata={},
        )

        # Run validators
        for validator in self.validators:
            try:
                await validator.validate(value, context)
            except FieldValidationError as e:
                raise FieldValidationError(
                    message=f"{self.name}: {e.message}",
                    field_name=self.name,
                    code=e.code or "validation_error",
                ) from e

        return value

    @overload
    def __get__(self, instance: None, owner: Any) -> "BaseField[T]": ...

    @overload
    def __get__(self, instance: Any, owner: Any) -> Optional[T]: ...

    def __get__(
        self, instance: Optional[Any], owner: Any
    ) -> Union["BaseField[T]", Optional[T]]:
        """Get field value.

        This method implements the descriptor protocol.
        When accessed through the class, returns the field instance.
        When accessed through an instance, returns the field value.

        Args:
            instance: Model instance or None
            owner: Model class

        Returns:
            Field instance when accessed through class,
            field value when accessed through instance
        """
        if instance is None:
            return self
        return self._value

    def __set__(self, instance: Any, value: Optional[T]) -> None:
        """Set field value.

        Args:
            instance: Model instance.
            value: Value to set.
        """
        self._value = value

    async def convert(self, value: Any) -> Optional[T]:
        """Convert value to field type.

        This method should be overridden by subclasses to implement
        type-specific conversion logic.

        Args:
            value: Value to convert

        Returns:
            Optional[T]: Converted value
        """
        return cast(Optional[T], value)

    async def to_db(self, value: Optional[T], backend: str) -> DatabaseValue:
        """Convert Python value to database format.

        Args:
            value: Value to convert
            backend: Database backend type

        Returns:
            DatabaseValue: Database value

        Raises:
            ValueError: If backend is not supported
        """
        if backend not in self.adapters:
            raise ValueError(f"Unsupported backend: {backend}")
        return await self.adapters[backend].to_db_value(value)

    async def from_db(self, value: DatabaseValue, backend: str) -> Optional[T]:
        """Convert database value to Python format.

        Args:
            value: Database value
            backend: Database backend type

        Returns:
            Optional[T]: Python value

        Raises:
            ValueError: If backend is not supported
        """
        if backend not in self.adapters:
            raise ValueError(f"Unsupported backend: {backend}")
        return await self.adapters[backend].from_db_value(value)

    def get_backend_options(self, backend: str) -> Dict[str, Any]:
        """Get database-specific options.

        Args:
            backend: Database backend type

        Returns:
            Dict[str, Any]: Backend options

        Raises:
            ValueError: If backend is not supported
        """
        if backend not in self.adapters:
            raise ValueError(f"Unsupported backend: {backend}")
        return {
            "type": self.adapters[backend].get_field_type(),
            **self.adapters[backend].get_field_options(),
        }

    def setup_triggers(self) -> None:
        """Setup compute triggers.

        This method is called after field setup to initialize any compute triggers.
        It should be overridden by subclasses that need trigger functionality.
        """
        if self.compute:
            # TODO: Implement compute triggers
            pass

    def copy(self) -> "BaseField[T]":
        """Create copy of field.

        Returns:
            BaseField[T]: New field instance with same configuration
        """
        return self.__class__(**self._options)
