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
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Protocol,
    Set,
    TypeAlias,
    TypeVar,
    Union,
    runtime_checkable,
)

from bson import ObjectId

# Type variables
V = TypeVar("V", covariant=True)  # Field value type

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

# Generic type variables
T = TypeVar("T")  # Generic type

if TYPE_CHECKING:
    from earnorm.base.model.base import BaseModel as BaseModelType
    from earnorm.fields.base import Field

    M = TypeVar("M", bound="BaseModelType")  # Model type
    F = TypeVar("F", bound="Field[Any]")  # Field type with Any type parameter
else:
    M = TypeVar("M")  # Model type at runtime
    F = TypeVar("F")  # Field type at runtime


@runtime_checkable
class DatabaseModel(Protocol):
    """Protocol for database models.

    This protocol defines the interface that all database models must implement.
    It provides methods for converting between Python objects and database formats.

    Examples:
        >>> class User(DatabaseModel):
        ...     def __init__(self, name: str, age: int) -> None:
        ...         self.id: Optional[ObjectId] = None
        ...         self.name = name
        ...         self.age = age
        ...
        ...     def to_dict(self) -> Dict[str, Any]:
        ...         return {
        ...             "_id": self.id,
        ...             "name": self.name,
        ...             "age": self.age,
        ...         }
        ...
        ...     @classmethod
        ...     def from_dict(cls, data: Dict[str, Any]) -> "User":
        ...         user = cls(name=data["name"], age=data["age"])
        ...         user.id = data.get("_id")
        ...         return user
    """

    id: Optional[ObjectId]
    """Document ID in database."""

    __collection__: str
    """Collection name in database."""

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary.

        Returns:
            Dictionary representation of model
        """
        ...

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DatabaseModel":
        """Create model from dictionary.

        Args:
            data: Dictionary representation of model

        Returns:
            Model instance
        """
        ...
