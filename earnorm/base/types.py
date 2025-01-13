"""Type definitions for EarnORM."""

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
    Union,
    runtime_checkable,
)

# Type aliases
JsonDict = Dict[str, Any]
ValueType = Union[str, int, float, bool, None, List[Any], Dict[str, Any]]

# Configuration types
IndexDict = Dict[str, Any]
AclDict = Dict[str, Any]
RuleDict = Dict[str, Any]
EventDict = Dict[str, List[Any]]
AuditConfig = Dict[str, Any]
CacheConfig = Dict[str, Any]
MetricsConfig = Dict[str, Any]
JsonEncoders = Dict[type, Callable[[Any], str]]

# Type variables
T = TypeVar("T")
ModelT = TypeVar("ModelT", bound="BaseModel")

# Function types
ValidatorFunc = Callable[[ModelT], Coroutine[Any, Any, None]]
ConstraintFunc = Callable[[ModelT], Coroutine[Any, Any, None]]


# Container protocols
@runtime_checkable
class PoolManager(Protocol):
    """Protocol for pool manager."""

    async def get_collection(self, name: str) -> Any:
        """Get collection by name."""
        ...


@runtime_checkable
class MetricsManager(Protocol):
    """Protocol for metrics manager."""

    async def track_operation(
        self, operation: str, collection: str, config: MetricsConfig
    ) -> None:
        """Track operation metrics."""
        ...


@runtime_checkable
class AclManager(Protocol):
    """Protocol for ACL manager."""

    async def check_access(self, model: "BaseModel") -> None:
        """Check access control."""
        ...


@runtime_checkable
class RuleManager(Protocol):
    """Protocol for rule manager."""

    async def check_rules(self, model: "BaseModel") -> None:
        """Check rules."""
        ...


@runtime_checkable
class Container(Protocol):
    """Protocol for container."""

    async def get(
        self, name: str
    ) -> Union[PoolManager, MetricsManager, AclManager, RuleManager]:
        """Get service by name."""
        ...


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
        """Find single document."""
        ...

    @classmethod
    async def find(cls, filter_: Dict[str, Any]) -> Sequence["BaseModel"]:
        """Find multiple documents."""
        ...
