"""Field-related type definitions."""

from datetime import datetime
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Protocol,
    Set,
    Tuple,
    TypeVar,
    Union,
    runtime_checkable,
)

from bson import ObjectId
from bson.decimal128 import Decimal128

# Field value types
FieldValue = Union[str, int, float, bool, List[Any], Dict[str, Any], None]
DatabaseValue = Union[
    None,
    bool,
    int,
    float,
    str,
    Dict[str, Any],
    List[Any],
    datetime,
    Decimal128,
    ObjectId,
]

# Field option types
FieldOptions = Dict[str, Any]
BackendOptions = Dict[str, Dict[str, Any]]

# Compute method type
ComputeMethod = Callable[..., Any]

# Field dependency type
FieldDependencies = Set[str]

# Type for validator functions
ValidatorFunc = Callable[[Any], None]
ValidatorResult = Union[bool, Tuple[bool, str]]
ValidatorCallable = Callable[[Any], Awaitable[ValidatorResult]]

# Generic type for field values
V = TypeVar("V")  # Field value type


@runtime_checkable
class FieldComparisonMixin(Protocol):
    """Mixin class for field-specific comparison operations.

    This class provides default implementations for comparison operations.
    Fields can override these methods to provide type-specific comparison behavior.
    """

    name: str  # Field name for error messages

    def _prepare_value(self, value: Any) -> DatabaseValue:
        """Prepare value for comparison.

        This method should be overridden by fields to handle type-specific
        value preparation (e.g. string case conversion, number formatting).

        Args:
            value: Value to prepare

        Returns:
            DatabaseValue: Prepared value
        """
        return value

    def _prepare_pattern(self, pattern: str) -> str:
        """Prepare pattern for string matching.

        This method should be overridden by string fields to handle
        case sensitivity and other string matching options.

        Args:
            pattern: Pattern to prepare

        Returns:
            str: Prepared pattern
        """
        return pattern

    def _prepare_list(self, values: List[Any]) -> List[Any]:
        """Prepare list values for comparison.

        This method should be overridden by list fields to handle
        item type conversion and validation.

        Args:
            values: List values to prepare

        Returns:
            List[Any]: Prepared list values
        """
        return values


@runtime_checkable
class ValidatorProtocol(Protocol):
    """Protocol for validator functions.

    This protocol defines the interface for field validators.
    Validators must be async callables that return either:
    - bool: True if valid, False if invalid
    - Tuple[bool, str]: (is_valid, error_message)
    """

    async def __call__(self, value: Any) -> ValidatorResult:
        """Validate value.

        Args:
            value: Value to validate

        Returns:
            ValidatorResult: True if valid, or (False, error_message) if invalid
        """
        ...


@runtime_checkable
class FieldProtocol(Protocol[V]):
    """Protocol for field types.

    This protocol defines the interface that all fields must implement.
    It includes:
    - Field metadata (name, required, unique)
    - Field operations (validate, convert)
    - Database operations (to_db, from_db)
    """

    name: str
    required: bool
    unique: bool
    validators: List[ValidatorProtocol]
    backend_options: BackendOptions

    async def validate(self, value: Any) -> None:
        """Validate field value.

        Args:
            value: Value to validate

        Raises:
            ValidationError: If validation fails
        """
        ...

    async def convert(self, value: Any) -> V:
        """Convert value to field type.

        Args:
            value: Value to convert

        Returns:
            V: Converted value

        Raises:
            ValidationError: If conversion fails
        """
        ...

    async def to_db(self, value: V, backend: str) -> DatabaseValue:
        """Convert to database format.

        Args:
            value: Value to convert
            backend: Database backend type

        Returns:
            DatabaseValue: Database value
        """
        ...

    async def from_db(self, value: DatabaseValue, backend: str) -> V:
        """Convert from database format.

        Args:
            value: Database value
            backend: Database backend type

        Returns:
            V: Field value
        """
        ...


@runtime_checkable
class RelationProtocol(Protocol[V]):
    """Protocol for relation field types.

    This protocol defines the interface for relation fields.
    It includes:
    - Relation metadata (model, related_name)
    - Relation operations (get_related, set_related)
    - Relation configuration (on_delete, lazy)
    """

    model: type
    related_name: str
    on_delete: str
    lazy: bool

    async def get_related(self, instance: Any) -> V:
        """Get related instance.

        Args:
            instance: Model instance

        Returns:
            V: Related instance
        """
        ...

    async def set_related(self, instance: Any, value: V) -> None:
        """Set related instance.

        Args:
            instance: Model instance
            value: Related instance
        """
        ...

    async def delete_related(self, instance: Any) -> None:
        """Delete related instance.

        Args:
            instance: Model instance
        """
        ...


class ComparisonOperator:
    """Class for field comparison operations.

    This class represents a comparison operation between a field and a value.
    It includes the field name, operator, and comparison value.

    Examples:
        >>> name_eq = ComparisonOperator('name', '=', 'John')
        >>> age_gt = ComparisonOperator('age', '>', 18)
    """

    def __init__(self, field_name: str, operator: str, value: Any) -> None:
        """Initialize comparison operator.

        Args:
            field_name: Field name
            operator: Comparison operator
            value: Comparison value
        """
        self.field_name = field_name
        self.operator = operator
        self.value = value

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dict[str, Any]: Dictionary representation
        """
        return {"field": self.field_name, "op": self.operator, "value": self.value}

    def __str__(self) -> str:
        """Convert to string.

        Returns:
            str: String representation
        """
        return f"{self.field_name} {self.operator} {self.value}"


__all__ = [
    "FieldValue",
    "DatabaseValue",
    "FieldOptions",
    "BackendOptions",
    "ComputeMethod",
    "FieldDependencies",
    "ValidatorFunc",
    "ValidatorResult",
    "ValidatorCallable",
    "FieldComparisonMixin",
    "ValidatorProtocol",
    "FieldProtocol",
    "RelationProtocol",
    "ComparisonOperator",
    "V",
]
