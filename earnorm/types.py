"""Type definitions for EarnORM.

This module provides all type definitions used throughout EarnORM:

Core Types:
- ModelInterface: Protocol for model classes
- FieldProtocol: Protocol for field classes
- ValidatorFunc: Type for validator functions

Model Types:
- BaseModel: Base class for all models
- Model: Regular persisted model
- TransientModel: Temporary model
- AbstractModel: Abstract base model
- ModelName: Type for model technical names
- FieldName: Type for field names
- RecordID: Type for record IDs

Field Types:
- FieldValue: Union type for field values
- FieldOptions: Type for field options
- ComputeMethod: Type for compute methods
- FieldDependencies: Type for field dependencies

Domain Types:
- DomainOperator: Comparison operators for domain expressions
- JsonDict: Dictionary with JSON-serializable values

Examples:
    >>> from earnorm.types import Model, TransientModel, AbstractModel
    >>>
    >>> class Partner(Model):
    ...     _name = 'res.partner'
    ...     _description = 'Partner'
    ...
    >>> class Wizard(TransientModel):
    ...     _name = 'res.wizard'
    ...     _description = 'Temporary Wizard'
    ...
    ...     state = fields.Char()
    >>>
    >>> class Base(AbstractModel):
    ...     _name = 'base'
    ...     _description = 'Abstract Base'
    ...
    ...     active = fields.Boolean(default=True)
"""

from typing import (
    TYPE_CHECKING,
    Any,
    AsyncContextManager,
    Callable,
    ClassVar,
    Dict,
    List,
    Literal,
    Optional,
    Protocol,
    Set,
    Type,
    TypeAlias,
    TypeVar,
    Union,
    runtime_checkable,
)

# Type variables
T = TypeVar("T")  # Generic type
V = TypeVar("V")  # Field value type

# Domain operator type
DomainOperator: TypeAlias = Literal[
    "=",
    "!=",
    ">",
    ">=",
    "<",
    "<=",
    "in",
    "not in",
    "like",
    "ilike",
    "not like",
    "not ilike",
    "=like",
    "=ilike",
    "contains",
    "not contains",
]

# JSON-serializable types
JsonValue = Union[str, int, float, bool, None, List[Any], Dict[str, Any]]
JsonDict: TypeAlias = Dict[str, Any]

# Domain value type
ValueType = Union[str, int, float, bool, None]

# Model and field types
ModelName = str  # e.g. "res.partner"
FieldName = str  # e.g. "name"
RecordID = int  # Record ID type

# Field value types
FieldValue = Union[str, int, float, bool, List[Any], Dict[str, Any], None]
DatabaseValue = Any

# Field option types
FieldOptions = Dict[str, Any]

# Compute method type
ComputeMethod = Callable[..., Any]

# Field dependency type
FieldDependencies = Set[str]

# Type for validator functions
ValidatorFunc = Callable[[Any], None]

if TYPE_CHECKING:
    from earnorm.base.model.base import BaseModel as BaseModelType
    from earnorm.fields.base import Field

    M = TypeVar("M", bound="BaseModelType")  # Model type
    F = TypeVar("F", bound="Field[Any]")  # Field type with Any type parameter
else:
    M = TypeVar("M")  # Model type at runtime
    F = TypeVar("F")  # Field type at runtime


@runtime_checkable
class ModelProtocol(Protocol):
    """Protocol for stored models.

    This protocol defines the interface that all stored models must implement.
    It provides methods for CRUD operations and database interaction.

    Examples:
        >>> class User(StoredModel):
        ...     _name = 'data.user'
        ...     _description = 'User Data'
        ...
        ...     name = StringField(required=True)
        ...     age = IntegerField()
        ...
        ...     async def update_age(self, new_age: int) -> 'User':
        ...         return await self.write({'age': new_age})
    """

    _store: ClassVar[bool]
    """Whether model supports storage."""

    _name: ClassVar[str]
    """Technical name of the model."""

    _description: ClassVar[Optional[str]]
    """User-friendly description."""

    _table: ClassVar[Optional[str]]
    """Database table name."""

    _sequence: ClassVar[Optional[str]]
    """ID sequence name."""

    id: int

    def to_dict(self) -> JsonDict:
        """Convert model to dictionary.

        Returns:
            Dictionary representation of model
        """
        ...

    def from_dict(self, data: JsonDict) -> None:
        """Update model from dictionary.

        Args:
            data: Dictionary data to update from
        """
        ...

    @classmethod
    async def browse(cls: Type[M], ids: Union[int, List[int]]) -> Union[M, List[M]]:
        """Browse records by IDs.

        Args:
            ids: Record ID or list of record IDs

        Returns:
            Single record or list of records
        """
        ...

    @classmethod
    async def create(cls, values: Dict[str, Any]) -> "ModelProtocol":
        """Create a new record."""
        ...

    async def write(self, values: Dict[str, Any]) -> "ModelProtocol":
        """Update record with values."""
        ...

    async def unlink(self) -> bool:
        """Delete record from database."""
        ...

    async def with_transaction(self) -> AsyncContextManager["ModelProtocol"]:
        """Get transaction context manager."""
        ...

    async def _prefetch_field(self, field: "Field[Any]") -> None:
        """Setup prefetching for field."""
        ...


# Type alias for database model
DatabaseModel = ModelProtocol


@runtime_checkable
class FieldProtocol(Protocol[V]):
    """Protocol for field classes.

    This protocol defines the interface that all field classes must implement.
    It provides methods for validation, conversion, and database interaction.

    Type Parameters:
        V: Field value type

    Examples:
        >>> class StringField(Field[str]):
        ...     def validate(self, value: Any) -> None:
        ...         if not isinstance(value, str):
        ...             raise ValidationError("Value must be string")
    """

    name: str
    """Field name."""

    required: bool
    """Whether field is required."""

    readonly: bool
    """Whether field is readonly."""

    default: Optional[V]
    """Default value for field."""

    compute: Optional[ComputeMethod]
    """Compute method for field."""

    compute_depends: FieldDependencies
    """Dependencies for compute method."""

    def __init__(self, **options: Any) -> None:
        """Initialize field with options."""
        ...

    def setup(self, model: Any) -> None:
        """Set up field for model.

        Args:
            model: Model class to set up field for
        """
        ...

    def setup_triggers(self) -> None:
        """Set up field triggers for computed fields."""
        ...

    def validate(self, value: Any) -> None:
        """Validate field value.

        Args:
            value: Value to validate

        Raises:
            ValidationError: If validation fails
        """
        ...

    def convert(self, value: Any) -> V:
        """Convert value to field type.

        Args:
            value: Value to convert

        Returns:
            Converted value

        Raises:
            ValidationError: If conversion fails
        """
        ...

    def to_db(self, value: V) -> DatabaseValue:
        """Convert value to database format.

        Args:
            value: Value to convert

        Returns:
            Value in database format
        """
        ...

    def from_db(self, value: DatabaseValue) -> V:
        """Convert value from database format.

        Args:
            value: Value to convert

        Returns:
            Value in field format
        """
        ...
