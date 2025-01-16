"""Type definitions for EarnORM."""

from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    Generic,
    List,
    Optional,
    Protocol,
    Type,
    TypeVar,
    Union,
    runtime_checkable,
)

from motor.motor_asyncio import AsyncIOMotorDatabase

from earnorm.fields.composite.dict import DictField
from earnorm.fields.composite.list import ListField
from earnorm.fields.primitive.boolean import BooleanField
from earnorm.fields.primitive.datetime import DateTimeField
from earnorm.fields.primitive.number import FloatField, IntegerField
from earnorm.fields.primitive.string import StringField

M = TypeVar("M", bound="ModelProtocol")
V = TypeVar("V")  # Value type for fields
T = TypeVar("T", bound="ModelProtocol")

DocumentType = Dict[str, Any]
ModelHook = Callable[[M], Coroutine[Any, Any, None]]

# Query types
FilterDict = Dict[str, Any]
SortItem = tuple[str, int]  # (field, direction)
ProjectionDict = Dict[str, int]
QueryParams = Dict[str, Any]


# Field types
class StringFieldType(Protocol):
    """Protocol for string field."""

    name: str
    required: bool
    unique: bool
    default: str

    def convert(self, value: Any) -> str: ...
    def to_mongo(self, value: Optional[str]) -> Optional[str]: ...
    def from_mongo(self, value: Any) -> str: ...


class IntegerFieldType(Protocol):
    """Protocol for integer field."""

    name: str
    required: bool
    unique: bool
    default: int

    def convert(self, value: Any) -> int: ...
    def to_mongo(self, value: Optional[int]) -> Optional[int]: ...
    def from_mongo(self, value: Any) -> int: ...


class BooleanFieldType(Protocol):
    """Protocol for boolean field."""

    name: str
    required: bool
    unique: bool
    default: bool

    def convert(self, value: Any) -> bool: ...
    def to_mongo(self, value: Optional[bool]) -> Optional[bool]: ...
    def from_mongo(self, value: Any) -> bool: ...


class FloatFieldType(Protocol):
    """Protocol for float field."""

    name: str
    required: bool
    unique: bool
    default: float

    def convert(self, value: Any) -> float: ...
    def to_mongo(self, value: Optional[float]) -> Optional[float]: ...
    def from_mongo(self, value: Any) -> float: ...


class ListFieldType(Protocol):
    """Protocol for list field."""

    name: str
    required: bool
    unique: bool
    default: List[Any]

    def convert(self, value: Any) -> List[Any]: ...
    def to_mongo(self, value: Optional[List[Any]]) -> Optional[List[Any]]: ...
    def from_mongo(self, value: Any) -> List[Any]: ...


class DictFieldType(Protocol):
    """Protocol for dict field."""

    name: str
    required: bool
    unique: bool
    default: Dict[str, Any]

    def convert(self, value: Any) -> Dict[str, Any]: ...
    def to_mongo(self, value: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]: ...
    def from_mongo(self, value: Any) -> Dict[str, Any]: ...


@runtime_checkable
class ModelProtocol(Protocol):
    """Protocol for model classes."""

    _name: str
    _collection: str
    _abstract: bool
    _data: DocumentType
    _indexes: List[DocumentType]
    __annotations__: Dict[str, Any]

    def __getattr__(self, name: str) -> Any:
        """Get dynamic attribute."""
        ...

    @property
    def data(self) -> DocumentType:
        """Get model data."""
        ...

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dict representation."""
        ...

    def to_mongo(self) -> Dict[str, Any]:
        """Convert model to MongoDB representation."""
        ...

    def from_mongo(self, data: Dict[str, Any]) -> None:
        """Convert MongoDB data to model."""
        ...

    @classmethod
    def get_collection_name(cls) -> str:
        """Get collection name."""
        ...

    @classmethod
    def get_name(cls) -> str:
        """Get model name."""
        ...

    @classmethod
    def get_indexes(cls) -> List[DocumentType]:
        """Get model indexes."""
        ...

    @classmethod
    async def search(
        cls: Type[M], domain: Optional[List[Any]] = None, **kwargs: Any
    ) -> "RecordSetProtocol[M]":
        """Search records and return RecordSet."""
        ...

    @classmethod
    async def browse(cls: Type[M], ids: List[str]) -> "RecordSetProtocol[M]":
        """Browse records by IDs."""
        ...

    @classmethod
    async def find_one(
        cls: Type[M], domain: Optional[List[Any]] = None, **kwargs: Any
    ) -> "RecordSetProtocol[M]":
        """Find single record."""
        ...

    @property
    def id(self) -> Optional[str]:
        """Get record ID."""
        ...

    async def validate(self) -> None:
        """Validate record."""
        ...

    async def save(self) -> None:
        """Save record."""
        ...

    async def delete(self) -> None:
        """Delete record."""
        ...


@runtime_checkable
class FieldProtocol(Protocol, Generic[V]):
    """Protocol for field classes.

    This protocol defines the interface that all field classes must implement.
    It includes methods for validation, conversion, and serialization of field values.

    Type Parameters:
        V: The Python type this field represents (str, int, bool, etc.)

    Attributes:
        name: Name of the field
        required: Whether field is required
        unique: Whether field value must be unique
        default: Default field value
    """

    name: str
    required: bool
    unique: bool
    default: V

    def __get__(
        self, instance: Optional[ModelProtocol], owner: Type[ModelProtocol]
    ) -> Union[V, "FieldProtocol[V]"]:
        """Get field value."""
        ...

    def __set__(self, instance: Optional[ModelProtocol], value: Any) -> None:
        """Set field value."""
        ...

    def __delete__(self, instance: Optional[ModelProtocol]) -> None:
        """Delete field value."""
        ...

    def convert(self, value: Any) -> V:
        """Convert value to field type."""
        ...

    def to_mongo(self, value: Optional[V]) -> Any:
        """Convert value to MongoDB format."""
        ...

    def from_mongo(self, value: Any) -> V:
        """Convert value from MongoDB format."""
        ...


@runtime_checkable
class RecordSetProtocol(Protocol[T]):
    """Protocol for recordset.

    This protocol defines the interface that all recordset classes must implement.
    It provides methods for querying, filtering, and manipulating sets of records.
    When accessing attributes not found in the recordset, it delegates to the first record.

    Type Parameters:
        T: The type of model this recordset contains

    Examples:
        >>> class User(Model):
        ...     email = fields.StringField()
        ...     age = fields.IntegerField()
        ...     active = fields.BooleanField()
        ...     tags = fields.ListField(fields.StringField())
        ...     metadata = fields.DictField()
        ...     created_at = fields.DateTimeField(auto_now_add=True)

        >>> users = await User.search([["active", "=", True]])
        >>> users.email  # Returns StringField
        >>> users.age  # Returns IntegerField
        >>> users.active  # Returns BooleanField
        >>> users.tags  # Returns ListField[str]
        >>> users.metadata  # Returns DictField
        >>> users.created_at  # Returns DateTimeField
    """

    def __init__(self, model_cls: Type[T], records: Optional[List[T]] = None) -> None:
        """Initialize recordset."""
        ...

    def __getattr__(self, name: str) -> Union[
        StringField,
        IntegerField,
        FloatField,
        BooleanField,
        ListField[Any],
        DictField,
        DateTimeField,
    ]:
        """Get attribute from first record.

        This method is called when an attribute is not found in the RecordSet.
        It delegates the attribute lookup to the first record in the set.
        The return type will be the exact field class as defined in the model.

        Args:
            name: Name of the attribute to get

        Returns:
            Field instance with the exact class type as defined in the model

        Examples:
            >>> class User(Model):
            ...     email = fields.StringField()
            ...     age = fields.IntegerField()
            ...     active = fields.BooleanField()
            ...     tags = fields.ListField(fields.StringField())
            ...     metadata = fields.DictField()
            ...     created_at = fields.DateTimeField(auto_now_add=True)

            >>> users = await User.search([["active", "=", True]])
            >>> email = users.email  # Returns actual StringField instance
            >>> age = users.age     # Returns actual IntegerField instance
            >>> active = users.active  # Returns actual BooleanField instance
            >>> tags = users.tags  # Returns actual ListField[str] instance
            >>> metadata = users.metadata  # Returns actual DictField instance
            >>> created_at = users.created_at  # Returns actual DateTimeField instance
            >>> print(type(email))  # <class 'earnorm.fields.primitive.string.StringField'>
            >>> print(isinstance(email, StringField))  # True
        """
        ...

    def __getitem__(self, index: int) -> T:
        """Get record by index."""
        ...

    def __len__(self) -> int:
        """Get number of records."""
        ...

    def __iter__(self) -> Any:
        """Iterate over records."""
        ...

    @property
    def ids(self) -> List[str]:
        """Get list of record IDs."""
        ...

    @classmethod
    async def create(cls, model_cls: Type[T], **kwargs: Any) -> "RecordSetProtocol[T]":
        """Create new record."""
        ...

    async def write(self, values: DocumentType) -> bool:
        """Update records with values."""
        ...

    async def unlink(self) -> bool:
        """Delete records."""
        ...

    def filtered(self, func: Callable[[T], bool]) -> "RecordSetProtocol[T]":
        """Filter records using predicate function."""
        ...

    def filtered_domain(self, domain: List[Any]) -> "RecordSetProtocol[T]":
        """Filter records using domain expression."""
        ...

    def sorted(self, key: str, reverse: bool = False) -> "RecordSetProtocol[T]":
        """Sort records by field."""
        ...

    def mapped(self, field: str) -> List[Any]:
        """Map field values from records."""
        ...

    async def ensure_one(self) -> None:
        """Ensure recordset contains exactly one record."""
        ...

    async def exists(self) -> bool:
        """Check if recordset contains any records."""
        ...

    async def count(self) -> int:
        """Get number of records."""
        ...

    async def first(self) -> Optional[T]:
        """Get first record or None."""
        ...

    async def all(self) -> List[T]:
        """Get all records."""
        ...


@runtime_checkable
class RegistryProtocol(Protocol):
    """Protocol for registry."""

    _models: Dict[str, Type[ModelProtocol]]
    _db: Optional[AsyncIOMotorDatabase[DocumentType]]

    def add_scan_path(self, package_name: str) -> None:
        """Add package to scan for models."""
        ...

    def get(self, collection: str) -> Optional[Type[ModelProtocol]]:
        """Get model class by collection name."""
        ...

    def __getitem__(self, collection: str) -> "RecordSetProtocol[ModelProtocol]":
        """Get recordset for collection."""
        ...

    @property
    def db(self) -> AsyncIOMotorDatabase[DocumentType]:
        """Get database instance."""
        ...


class ContainerProtocol(Protocol):
    """Container protocol."""

    @property
    def registry(self) -> RegistryProtocol:
        """Get registry instance."""
        ...
