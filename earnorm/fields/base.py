"""Base field implementation.

This module provides the base field class that all field types inherit from.
It handles:
- Field setup and initialization
- Value validation and conversion
- Type checking and constraints
- Comparison operations
"""

import logging
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    Generic,
    List,
    Optional,
    Pattern,
    Protocol,
    Type,
    TypeVar,
    Union,
    cast,
)

from earnorm.exceptions import DatabaseError
from earnorm.fields.types import ValidationContext
from earnorm.types.fields import ComparisonOperator, DatabaseValue

T = TypeVar("T")  # Field value type

# Type aliases for validation
ValidatorResult = bool  # Simplified to just bool for now
ValidatorCallable = Callable[[Any, ValidationContext], Coroutine[Any, Any, bool]]

logger = logging.getLogger(__name__)


class DatabaseAdapterProtocol(Protocol):
    """Protocol for database adapter interface."""

    async def convert_value(
        self, value: Any, field_type: str, target_type: Type[Any]
    ) -> Any:
        """Convert value between database and Python types."""
        ...


class EnvironmentProtocol(Protocol):
    """Protocol for environment interface."""

    @property
    def adapter(self) -> DatabaseAdapterProtocol:
        """Get database adapter."""
        ...


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
    - Descriptor protocol for attribute access

    Args:
        **kwargs: Field options passed to subclasses.

    Examples:
        >>> class StringField(BaseField[str]):
        ...     field_type = "string"
        ...     python_type = str
        ...
        >>> class User(BaseModel):
        ...     name = StringField(required=True)
        ...     age = IntegerField()
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
    compute: Optional[Callable[..., Coroutine[Any, Any, T]]]
    depends: List[str]
    validators: List[Callable[[Any, ValidationContext], Coroutine[Any, Any, None]]]
    env: EnvironmentProtocol

    # Field type information
    field_type: str = ""  # Database field type (e.g. "string", "integer", etc.)
    python_type: Type[T] = cast(Type[T], Any)  # Python type for the field

    def __init__(self, **kwargs: Any) -> None:
        """Initialize field with options.

        Args:
            **kwargs: Field options
        """
        self.name = ""
        self.model_name = ""
        self._value = None
        self._options = kwargs
        self.required = kwargs.get("required", False)
        self.readonly = kwargs.get("readonly", False)
        self.store = kwargs.get("store", True)
        self.index = kwargs.get("index", False)
        self.help = kwargs.get("help", "")
        self.compute = kwargs.get("compute")
        self.depends = kwargs.get("depends", [])
        self.validators = kwargs.get("validators", [])

    @property
    def comparison(self) -> FieldComparison:
        """Get field comparison helper.

        Returns:
            FieldComparison: Field comparison helper
        """
        return FieldComparison(self.name)

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

    async def validate(
        self, value: Any, context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Validate field value.

        Args:
            value: Value to validate
            context: Validation context with following keys:
                    - model: Model instance
                    - env: Environment instance
                    - operation: Operation type (create/write/search...)
                    - values: Values being validated
                    - field_name: Name of field being validated

        Returns:
            Validated value

        Raises:
            FieldValidationError: If validation fails
        """
        context = context or {}
        validation_context = ValidationContext(
            field=self,
            value=value,
            model=context.get("model"),
            env=context.get("env"),
            operation=context.get("operation"),
            values=context.get("values", dict()),
        )

        # Run validators
        for validator in self.validators:
            await validator(value, validation_context)

        return value

    async def __get__(
        self, instance: Any, owner: Optional[Type[Any]] = None
    ) -> Union["BaseField[T]", Optional[T]]:
        """Get field value from instance.

        This implements the descriptor protocol for attribute access.
        The process is:
        1. Return field instance if accessed on class
        2. Load from database if instance has data
        3. Return value

        Args:
            instance: Model instance
            owner: Model class

        Returns:
            Union[BaseField[T], Optional[T]]: Field instance or value

        Raises:
            DatabaseError: If database operation fails
            ValidationError: If value validation fails
        """
        # Return field instance if accessed on class
        if instance is None:
            return self

        try:
            # Get environment
            if not hasattr(instance, "env"):
                raise ValueError("Model instance has no environment")

            # Load from database if instance has data
            if hasattr(instance, "_has_data") and instance._has_data:
                value = await self._load_field_value(instance)
                if value is not None:
                    return value

            # Return None if no value found
            return None

        except Exception as e:
            # Log error
            logger.error(
                f"Failed to get field value: {str(e)}",
                extra={
                    "model": instance._name,
                    "record_id": instance.id,
                    "field": self.name,
                },
            )
            # Re-raise as database error
            if not isinstance(e, DatabaseError):
                raise DatabaseError(
                    message=f"Failed to get field value: {str(e)}",
                    backend="unknown",
                ) from e
            raise

    def __set__(self, instance: Any, value: Optional[T]) -> None:
        """Set field value on instance.

        This implements the descriptor protocol for attribute assignment.
        The process is:
        1. Skip if field is readonly
        2. Validate value

        Args:
            instance: Model instance
            value: Field value

        Raises:
            ValidationError: If value validation fails
            ValueError: If field is readonly
        """
        if self.readonly:
            raise ValueError(f"Field {self.name} is readonly")

        try:
            # Get environment
            if not hasattr(instance, "_env"):
                raise ValueError("Model instance has no environment")

            # Set value directly
            self._value = value

        except Exception as e:
            logger.error(
                f"Failed to set field value: {str(e)}",
                extra={
                    "model": instance._name,
                    "record_id": instance.id,
                    "field": self.name,
                    "value": value,
                },
            )
            raise

    async def _load_field_value(self, instance: Any) -> Optional[T]:
        """Load field value from database.

        Args:
            instance: Model instance

        Returns:
            Optional[T]: Field value

        Raises:
            DatabaseError: If database operation fails
            ValidationError: If value validation fails
        """
        # Get database adapter
        adapter = instance.env.adapter

        # Load record from database
        record = await adapter.read(type(instance), instance.id, fields=[self.name])

        if record:
            # Convert database value
            value = await self.from_db(record.get(self.name), adapter.backend_type)

            # Validate value
            return await self.validate(value)

        return None

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
            DatabaseValue: Converted value for database

        Raises:
            DatabaseError: If conversion fails
        """
        try:
            if not hasattr(self, "env"):
                raise ValueError("Field has no environment")

            return await self.env.adapter.convert_value(
                value, self.field_type, self.python_type
            )
        except Exception as e:
            raise DatabaseError(message=str(e), backend=backend) from e

    async def from_db(self, value: DatabaseValue, backend: str) -> Optional[T]:
        """Convert database value to Python format.

        Args:
            value: Value to convert
            backend: Database backend type

        Returns:
            Optional[T]: Converted value

        Raises:
            DatabaseError: If conversion fails
        """
        try:
            if not hasattr(self, "env"):
                raise ValueError("Field has no environment")

            return await self.env.adapter.convert_value(
                value, self.field_type, self.python_type
            )
        except Exception as e:
            raise DatabaseError(message=str(e), backend=backend) from e

    def get_backend_options(self, backend: str) -> Dict[str, Any]:
        """Get database-specific options.

        Args:
            backend: Database backend type

        Returns:
            Dict[str, Any]: Backend options

        Raises:
            ValueError: If backend is not supported
        """
        # This method is now empty as the field no longer uses backend-specific options
        return {}

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
