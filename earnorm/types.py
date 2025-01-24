"""Type definitions for EarnORM.

This module provides all type definitions used throughout EarnORM:

Core Types:
- ModelInterface: Protocol for model classes
- FieldProtocol: Protocol for field classes
- ValidatorFunc: Type for validator functions

Model Types:
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

from abc import abstractmethod
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
    Type,
    TypeAlias,
    TypeVar,
    Union,
    runtime_checkable,
)

from earnorm.base.env import Environment

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
class ModelInterface(Protocol):
    """Protocol for model classes.

    This protocol defines the interface that all model classes must implement.
    It includes methods for converting between Python objects and database documents.

    Attributes:
        data: Dictionary containing the model's data
        id: Model's unique identifier
    """

    data: Dict[str, Any]

    @property
    @abstractmethod
    def id(self) -> Optional[str]:
        """Get model ID.

        Returns:
            Model's unique identifier or None if not saved
        """
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dict representation.

        Returns:
            Dict containing the model's data in Python format
        """
        pass

    @abstractmethod
    def to_db(self, backend: str) -> Dict[str, Any]:
        """Convert model to database representation.

        Args:
            backend: Database backend type ('mongodb', 'postgres', 'mysql')

        Returns:
            Dict containing the model's data in database format
        """
        pass

    @abstractmethod
    def from_db(self, data: Dict[str, Any], backend: str) -> None:
        """Convert database data to model.

        Args:
            data: Dict containing the model's data in database format
            backend: Database backend type ('mongodb', 'postgres', 'mysql')
        """
        pass

    @classmethod
    @abstractmethod
    async def find_by_id(cls, id: str) -> Optional["ModelInterface"]:
        """Find model by ID.

        Args:
            id: Model ID

        Returns:
            Model instance if found, None otherwise
        """
        pass


@runtime_checkable
class FieldProtocol(Protocol[V]):
    """Protocol for field interface.

    This protocol defines the interface that all field classes must implement.
    It includes methods for validation, conversion, and database interaction.

    Attributes:
        name: Field name
        model_name: Model name
        relational: Whether this is a relational field
        comodel_name: Related model name for relational fields
    """

    name: str
    model_name: str
    relational: bool
    comodel_name: str

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
            Converted value
        """
        ...

    def get_model(self) -> Type["BaseModel"]:
        """Get related model class for relational fields.

        Returns:
            Related model class
        """
        ...

    def setup(self, name: str, model_name: str) -> None:
        """Setup field with name and model.

        Args:
            name: Field name
            model_name: Model name
        """
        ...

    def setup_triggers(self) -> None:
        """Setup field triggers."""
        ...

    def copy(self) -> "FieldProtocol[V]":
        """Create copy of field.

        Returns:
            New field instance with same configuration
        """
        ...

    def to_db(self, value: Any, backend: str) -> DatabaseValue:
        """Convert Python value to database format.

        Args:
            value: Value to convert
            backend: Database backend type ('mongodb', 'postgres', 'mysql')

        Returns:
            Database value
        """
        ...

    def from_db(self, value: DatabaseValue, backend: str) -> V:
        """Convert database value to Python format.

        Args:
            value: Database value
            backend: Database backend type ('mongodb', 'postgres', 'mysql')

        Returns:
            Python value
        """
        ...

    @property
    def compute(self) -> Optional[ComputeMethod]:
        """Get compute method.

        Returns:
            Compute method or None if not computed
        """
        ...

    @compute.setter
    def compute(self, method: ComputeMethod) -> None:
        """Set compute method.

        Args:
            method: Compute method
        """
        ...

    @property
    def compute_depends(self) -> FieldDependencies:
        """Get compute dependencies.

        Returns:
            Set of field names that this field depends on
        """
        ...

    @compute_depends.setter
    def compute_depends(self, depends: FieldDependencies) -> None:
        """Set compute dependencies.

        Args:
            depends: Set of field names that this field depends on
        """
        ...


class BaseModel:
    """Base class for all models.

    This class provides common functionality for all model types.

    Attributes:
        _auto: Whether to create database backend
        _register: Whether to register in model registry
        _abstract: Whether this is an abstract model
        _transient: Whether this is a transient model
        _name: Technical name of the model
        _description: User-readable name of the model
        _inherit: Parent models to inherit from
        _inherits: Parent models to delegate to
        _order: Default ordering
        _rec_name: Field to use for record name
    """

    _auto: bool = True
    _register: bool = True
    _abstract: bool = False
    _transient: bool = False

    _name: str
    _description: Optional[str] = None
    _inherit: Optional[Union[str, List[str]]] = None
    _inherits: Dict[str, str] = {}
    _order: str = "id"
    _rec_name: Optional[str] = None

    def __init__(self, env: Environment) -> None:
        """Initialize model instance.

        Args:
            env: Current environment
        """
        self.env = env
        self._inherited_fields: Dict[str, FieldProtocol[Any]] = {}
        self._delegated_fields: Dict[str, FieldProtocol[Any]] = {}


class Model(BaseModel):
    """Regular persisted model.

    This is the standard model type that persists to database.
    """

    pass


class TransientModel(Model):
    """Temporary model that is automatically cleaned up.

    This model type is used for temporary data like wizards.
    Records are automatically deleted after some time.
    """

    _auto: bool = True
    _transient: bool = True


class AbstractModel(Model):
    """Abstract base model that is not persisted.

    This model type is used as a base class for other models.
    It cannot be instantiated directly.
    """

    _auto: bool = False
    _abstract: bool = True


class ModelProtocol(Protocol):
    """Protocol for model types."""

    __collection__: str
    __tablename__: str
    id: Any

    @classmethod
    async def get(cls, id: Any) -> "ModelProtocol":
        """Get model instance by ID."""
        ...
