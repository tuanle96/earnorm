"""Connection protocol definitions.

This module defines protocols for database connections, including type-safe
database operations and connection lifecycle management.

Examples:
    ```python
    class MyConnection(ConnectionProtocol[MyDB, MyColl]):
        async def ping(self) -> bool:
            return await self._client.ping()

        async def close(self) -> None:
            await self._client.close()

        async def execute_typed(self, operation: str, **kwargs: Any) -> Any:
            return await getattr(self._client, operation)(**kwargs)
    ```
"""

from typing import Any, Coroutine, Protocol, TypeVar

from earnorm.pool.protocols.database import DatabaseProtocol

# Reuse type variables from database protocol
DBType = TypeVar("DBType", covariant=True)
CollType = TypeVar("CollType", covariant=True)


class ConnectionLifecycle(Protocol):
    """Protocol for connection lifecycle management."""

    @property
    def created_at(self) -> float:
        """Get connection creation timestamp."""
        ...

    @property
    def last_used_at(self) -> float:
        """Get last usage timestamp."""
        ...

    @property
    def idle_time(self) -> float:
        """Get idle time in seconds."""
        ...

    @property
    def lifetime(self) -> float:
        """Get lifetime in seconds."""
        ...

    @property
    def is_stale(self) -> bool:
        """Check if connection is stale."""
        ...

    def touch(self) -> None:
        """Update last used timestamp."""
        ...

    async def ping(self) -> Coroutine[Any, Any, bool]:
        """Check connection health.

        Returns:
            True if connection is healthy

        Raises:
            ConnectionError: If connection is unhealthy
        """
        ...

    async def close(self) -> Coroutine[Any, Any, None]:
        """Close connection.

        Raises:
            ConnectionError: If connection cannot be closed
        """
        ...


class ConnectionOperations(Protocol[DBType, CollType]):
    """Protocol for connection operations."""

    async def execute_typed(
        self,
        operation: str,
        **kwargs: Any,
    ) -> Coroutine[Any, Any, Any]:
        """Execute typed operation.

        Args:
            operation: Operation name
            **kwargs: Operation arguments

        Returns:
            Operation result

        Raises:
            OperationError: If operation fails
            ConnectionError: If connection is unhealthy
        """
        ...


class ConnectionProtocol(
    ConnectionLifecycle,
    ConnectionOperations[DBType, CollType],
    DatabaseProtocol[DBType, CollType],
):
    """Protocol for database connections.

    Type Parameters:
        DBType: The database type (e.g. AsyncIOMotorDatabase)
        CollType: The collection type (e.g. AsyncIOMotorCollection)
    """

    pass
