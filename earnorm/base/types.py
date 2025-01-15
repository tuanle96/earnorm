"""Type definitions for EarnORM."""

from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
    Type,
    TypeVar,
    runtime_checkable,
)

from motor.motor_asyncio import AsyncIOMotorDatabase
from typing_extensions import Self


@runtime_checkable
class ModelProtocol(Protocol):
    """Protocol for model classes."""

    _name: str
    _collection: str
    _abstract: bool
    _data: Dict[str, Any]
    _indexes: List[Dict[str, Any]]
    __annotations__: Dict[str, Any]

    def __getattr__(self, name: str) -> Any:
        """Get dynamic attribute."""
        ...

    @property
    def data(self) -> Dict[str, Any]:
        """Get model data."""
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
    def get_indexes(cls) -> List[Dict[str, Any]]:
        """Get model indexes."""
        ...

    @classmethod
    async def search(
        cls, domain: Optional[List[Any]] = None, **kwargs: Any
    ) -> "RecordSetProtocol[Self]":
        """Search records and return RecordSet."""
        ...

    @classmethod
    async def browse(cls, ids: List[str]) -> "RecordSetProtocol[Self]":
        """Browse records by IDs."""
        ...

    @classmethod
    async def find_one(
        cls, domain: Optional[List[Any]] = None, **kwargs: Any
    ) -> "RecordSetProtocol[Self]":
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
class FieldProtocol(Protocol):
    """Protocol for field classes."""

    name: str
    required: bool
    unique: bool
    default: Any

    def __get__(
        self, instance: Optional["ModelProtocol"], owner: Type["ModelProtocol"]
    ) -> Any:
        """Get field value."""
        ...

    def __set__(self, instance: Optional["ModelProtocol"], value: Any) -> None:
        """Set field value."""
        ...

    def __delete__(self, instance: Optional["ModelProtocol"]) -> None:
        """Delete field value."""
        ...

    def convert(self, value: Any) -> Any:
        """Convert value to field type."""
        ...

    def to_mongo(self, value: Any) -> Any:
        """Convert value to MongoDB format."""
        ...

    def from_mongo(self, value: Any) -> Any:
        """Convert value from MongoDB format."""
        ...


M = TypeVar("M", bound=ModelProtocol)
F = TypeVar("F", bound=FieldProtocol)
M_co = TypeVar("M_co", bound=ModelProtocol, covariant=True)


@runtime_checkable
class RecordSetProtocol(Protocol[M_co]):
    """Protocol for recordset."""

    def __init__(
        self, model_cls: type[M_co], records: Optional[List[M_co]] = None
    ) -> None:
        """Initialize recordset."""
        ...

    def __getitem__(self, index: int) -> M_co:
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

    async def create(self, values: Dict[str, Any]) -> "RecordSetProtocol[M_co]":
        """Create new record."""
        ...

    async def write(self, values: Dict[str, Any]) -> bool:
        """Update records with values."""
        ...

    async def unlink(self) -> bool:
        """Delete records."""
        ...

    def filtered(self, func: Callable[[M_co], bool]) -> "RecordSetProtocol[M_co]":
        """Filter records using predicate function."""
        ...

    def filtered_domain(self, domain: List[Any]) -> "RecordSetProtocol[M_co]":
        """Filter records using domain expression."""
        ...

    def sorted(self, key: str, reverse: bool = False) -> "RecordSetProtocol[M_co]":
        """Sort records by field."""
        ...

    def mapped(self, field: str) -> List[Any]:
        """Map field values from records."""
        ...

    def ensure_one(self) -> M_co:
        """Ensure recordset contains exactly one record."""
        ...

    def exists(self) -> bool:
        """Check if recordset contains any records."""
        ...

    def count(self) -> int:
        """Get number of records."""
        ...

    def first(self) -> Optional[M_co]:
        """Get first record or None."""
        ...

    def last(self) -> Optional[M_co]:
        """Get last record or None."""
        ...


@runtime_checkable
class RegistryProtocol(Protocol):
    """Protocol for registry."""

    _models: Dict[str, Type[ModelProtocol]]
    _db: Optional[AsyncIOMotorDatabase[Dict[str, Any]]]

    def add_scan_path(self, package_name: str) -> None:
        """Add package to scan for models."""
        ...

    def get(self, collection: str) -> Optional[Type[ModelProtocol]]:
        """Get model class by collection name."""
        ...

    def __getitem__(self, collection: str) -> RecordSetProtocol[ModelProtocol]:
        """Get recordset for collection."""
        ...
