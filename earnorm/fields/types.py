"""Type definitions for field types.

This module provides type definitions and protocols for field types.
It includes:
- Base protocols for models and fields
- Type definitions for validators and field values
- Generic type variables for type safety
"""

from datetime import datetime
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Protocol,
    Tuple,
    TypeVar,
    Union,
    runtime_checkable,
)

from bson import ObjectId
from bson.decimal128 import Decimal128

from earnorm.base.model.base import BaseModel

# Type variables
T = TypeVar("T")  # Generic value type
M = TypeVar("M", bound=BaseModel)  # Model type

# Type aliases
ValidatorResult = Union[bool, Tuple[bool, str]]
ValidatorCallable = Callable[[Any], Awaitable[ValidatorResult]]
FieldValue = Union[None, bool, int, float, str, Dict[str, Any], List[Any], Any]
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
BackendOptions = Dict[str, Dict[str, Any]]


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
class ModelProtocol(Protocol):
    """Protocol for model types.

    This protocol defines the interface that all models must implement.
    It includes:
    - Model identity (id, env)
    - Model operations (get, validate)
    - Model metadata (name, fields)
    """

    id: str
    env: Any
    name: str
    fields: Dict[str, "FieldProtocol[Any]"]

    @classmethod
    async def get(cls, env: Any, id: str) -> "ModelProtocol":
        """Get model instance by ID.

        Args:
            env: Environment instance
            id: Model ID

        Returns:
            ModelProtocol: Model instance
        """
        ...

    async def validate(self) -> None:
        """Validate model instance.

        This method validates all fields of the model.

        Raises:
            ValidationError: If validation fails
        """
        ...

    async def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary.

        Returns:
            Dict[str, Any]: Model data
        """
        ...


@runtime_checkable
class RelationProtocol(Protocol[T]):
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

    async def get_related(self, instance: Any) -> T:
        """Get related instance.

        Args:
            instance: Model instance

        Returns:
            T: Related instance
        """
        ...

    async def set_related(self, instance: Any, value: T) -> None:
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


@runtime_checkable
class FieldProtocol(Protocol[T]):
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

    async def convert(self, value: Any) -> T:
        """Convert value to field type.

        Args:
            value: Value to convert

        Returns:
            T: Converted value

        Raises:
            ValidationError: If conversion fails
        """
        ...

    async def to_db(self, value: T, backend: str) -> DatabaseValue:
        """Convert to database format.

        Args:
            value: Value to convert
            backend: Database backend type

        Returns:
            DatabaseValue: Database value
        """
        ...

    async def from_db(self, value: DatabaseValue, backend: str) -> T:
        """Convert from database format.

        Args:
            value: Database value
            backend: Database backend type

        Returns:
            T: Field value
        """
        ...


class ComparisonOperator:
    """Class representing a comparison operation between a field and a value.

    This class is used to build comparison expressions for filtering queries.
    It stores the field name, operator and comparison value.

    Args:
        field_name: Name of the field being compared
        operator: Comparison operator (=, !=, >, >=, <, <=)
        value: Value to compare against
    """

    def __init__(self, field_name: str, operator: str, value: Any) -> None:
        """Initialize comparison operator.

        Args:
            field_name: Name of the field being compared
            operator: Comparison operator (=, !=, >, >=, <, <=)
            value: Value to compare against
        """
        self.field_name = field_name
        self.operator = operator
        self.value = value

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format.

        Returns:
            Dict[str, Any]: Dictionary with field name, operator and value
        """
        return {
            "field": self.field_name,
            "operator": self.operator,
            "value": self.value,
        }

    def __str__(self) -> str:
        """String representation.

        Returns:
            str: String representation of comparison
        """
        return f"{self.field_name} {self.operator} {self.value}"
