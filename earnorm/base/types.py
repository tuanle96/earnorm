"""Type definitions for EarnORM."""

from typing import Any, Dict, List, Optional, Protocol, Type, TypeVar, runtime_checkable


@runtime_checkable
class ModelProtocol(Protocol):
    """Protocol for model classes."""

    _name: str
    _collection: str
    _abstract: bool
    _data: Dict[str, Any]
    _indexes: List[Dict[str, Any]]
    _validators: List[Any]
    _constraints: List[Any]
    _acl: Dict[str, Any]
    _rules: Dict[str, Any]
    _events: Dict[str, List[Any]]
    _audit: Dict[str, Any]
    _cache: Dict[str, Any]
    _metrics: Dict[str, Any]
    _json_encoders: Dict[type, Any]

    @property
    def id(self) -> Any:
        """Get record ID."""
        ...

    @property
    def ids(self) -> List[Any]:
        """Get record IDs."""
        ...

    @property
    def collection(self) -> str:
        """Get collection name."""
        ...

    @property
    def collection_name(self) -> str:
        """Get collection name."""
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

    async def delete(self) -> None:
        """Delete record."""
        ...

    def __iter__(self) -> Any:
        """Iterate over record fields."""
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
        """Get indexes."""
        ...

    @classmethod
    async def find_one(
        cls, domain: Any = None, **kwargs: Any
    ) -> Optional["ModelProtocol"]:
        """Find one record."""
        ...

    @classmethod
    async def find(cls, domain: Any = None, **kwargs: Any) -> List["ModelProtocol"]:
        """Find records."""
        ...


M_co = TypeVar("M_co", bound=ModelProtocol, covariant=True)


class RecordSetProtocol(Protocol[M_co]):
    """Protocol for recordset."""

    def __init__(
        self, model_cls: Type[M_co], records: Optional[List[M_co]] = None
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


class RegistryProtocol(Protocol):
    """Protocol for registry."""

    def __init__(self) -> None:
        """Initialize registry."""
        ...

    def add_scan_path(self, package_name: str) -> None:
        """Add package to scan for models."""
        ...

    def get(self, collection: str) -> Optional[Type[ModelProtocol]]:
        """Get model class by collection name."""
        ...

    def __getitem__(self, collection: str) -> RecordSetProtocol[ModelProtocol]:
        """Get recordset for collection."""
        ...
