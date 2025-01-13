"""Base model protocol."""

from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    List,
    Optional,
    Protocol,
    Sequence,
    TypeVar,
    runtime_checkable,
)

# Type aliases
IndexDict = Dict[str, Any]
AclDict = Dict[str, Any]
RuleDict = Dict[str, Any]
EventDict = Dict[str, List[Any]]
AuditConfig = Dict[str, Any]
CacheConfig = Dict[str, Any]
MetricsConfig = Dict[str, Any]
JsonEncoders = Dict[type, Callable[[Any], str]]

# Type variables
ModelT = TypeVar("ModelT", bound="BaseModel")

# Function types
ValidatorFunc = Callable[[ModelT], Coroutine[Any, Any, None]]
ConstraintFunc = Callable[[ModelT], Coroutine[Any, Any, None]]


@runtime_checkable
class BaseModel(Protocol):
    """Base model protocol."""

    _collection: str
    _data: Dict[str, Any]
    _indexes: IndexDict
    _validators: List[ValidatorFunc[Any]]
    _constraints: List[ConstraintFunc[Any]]
    _acl: AclDict
    _rules: RuleDict
    _events: Dict[str, List[ValidatorFunc[Any]]]
    _audit: AuditConfig
    _cache: CacheConfig
    _metrics: MetricsConfig
    _json_encoders: JsonEncoders

    async def save(self) -> None:
        """Save model to database."""
        ...

    async def delete(self) -> None:
        """Delete model from database."""
        ...

    @classmethod
    async def find_one(cls, filter_: Dict[str, Any]) -> Optional["BaseModel"]:
        """Find single document.

        Args:
            filter_: Query filter

        Returns:
            Model instance if found, None otherwise
        """
        ...

    @classmethod
    async def find(cls, filter_: Dict[str, Any]) -> Sequence["BaseModel"]:
        """Find multiple documents.

        Args:
            filter_: Query filter

        Returns:
            List of model instances
        """
        ...
