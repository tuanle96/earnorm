"""Pool protocol definition."""

from typing import Any, Dict, Generic, Protocol, TypeVar

from earnorm.pool.protocols.connection import ConnectionProtocol

C = TypeVar("C", bound=ConnectionProtocol)


class PoolProtocol(Protocol, Generic[C]):
    """Protocol for connection pools."""

    @property
    def backend_type(self) -> str:
        """Get backend type identifier."""
        ...

    @property
    def size(self) -> int:
        """Get current pool size."""
        ...

    @property
    def available(self) -> int:
        """Get number of available connections."""
        ...

    async def init(self, **config: Dict[str, Any]) -> None:
        """Initialize pool with minimum connections."""
        ...

    async def acquire(self) -> C:
        """Acquire connection from pool."""
        ...

    async def release(self, conn: C) -> None:
        """Release connection back to pool."""
        ...

    async def close(self) -> None:
        """Close all connections and shutdown pool."""
        ...
