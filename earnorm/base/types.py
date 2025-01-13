"""Type definitions for EarnORM."""

from typing import Any, Dict, List, Optional, Protocol, Type, TypeVar, runtime_checkable

from motor.motor_asyncio import AsyncIOMotorDatabase


@runtime_checkable
class ModelProtocol(Protocol):
    """Protocol for model classes."""

    _name: str
    _collection: str
    _abstract: bool
    _data: Dict[str, Any]
    _indexes: List[Dict[str, Any]]

    @classmethod
    def get_collection_name(cls) -> str:
        """Get collection name."""
        ...

    @classmethod
    def get_indexes(cls) -> List[Dict[str, Any]]:
        """Get model indexes."""
        ...

    @classmethod
    async def find_one(
        cls, domain: Optional[List[Any]] = None, **kwargs: Any
    ) -> Optional["ModelProtocol"]:
        """Find single document."""
        ...

    @property
    def id(self) -> Optional[str]:
        """Get record ID."""
        ...

    @property
    def data(self) -> Dict[str, Any]:
        """Get record data."""
        ...

    async def validate(self) -> None:
        """Validate record."""
        ...

    async def save(self) -> None:
        """Save record."""
        ...


@runtime_checkable
class FieldProtocol(Protocol):
    """Protocol for field classes."""

    name: str
    required: bool
    unique: bool
    default: Any

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
