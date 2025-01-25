"""Connection protocol definitions.

This module defines protocols for database connections with async-first approach.
All operations are async by default.

Examples:
    ```python
    class MyConnection(AsyncConnectionProtocol[MyDB, MyColl]):
        async def ping(self) -> bool:
            return await self._client.ping()

        async def execute[T](self, operation: str, **kwargs: Any) -> T:
            return await getattr(self._client, operation)(**kwargs)
    ```
"""

from typing import Any, Protocol, TypeVar

# Type variables
DBType = TypeVar("DBType", covariant=True)
CollType = TypeVar("CollType", covariant=True)


class AsyncLifecycle(Protocol):
    """Protocol for async lifecycle management."""

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

    async def ping(self) -> bool:
        """Check connection health.

        Returns:
            True if connection is healthy
        """
        ...

    async def close(self) -> None:
        """Close connection."""
        ...


class AsyncOperations(Protocol[DBType, CollType]):
    """Protocol for async operations."""

    async def execute(self, operation: str, **kwargs: Any) -> Any:
        """Execute typed operation.

        Args:
            operation: Operation name
            **kwargs: Operation arguments

        Returns:
            Operation result
        """
        ...


class AsyncConnectionProtocol(
    AsyncLifecycle, AsyncOperations[DBType, CollType], Protocol
):
    """Protocol for async database connections.

    This protocol defines the interface that all async database connections must implement.
    It provides methods for getting collections and managing the connection lifecycle.

    Type Parameters:
        DBType: The database type (e.g. AsyncIOMotorDatabase)
        CollType: The collection type (e.g. AsyncIOMotorCollection)
    """

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

    async def ping(self) -> bool:
        """Check connection health."""
        ...

    async def close(self) -> None:
        """Close connection."""
        ...

    async def execute(self, operation: str, **kwargs: Any) -> Any:
        """Execute operation."""
        ...

    async def connect(self) -> None:
        """Connect to database.

        Raises:
            ConnectionError: If connection fails
        """
        ...

    async def disconnect(self) -> None:
        """Disconnect from database."""
        ...

    def get_database(self) -> DBType:
        """Get database instance.

        Returns:
            Database instance
        """
        ...

    def get_collection(self, name: str) -> CollType:
        """Get collection instance.

        Args:
            name: Collection name

        Returns:
            Collection instance

        Raises:
            ValueError: If collection name is empty
        """
        ...

    @property
    def db(self) -> DBType:
        """Get database instance."""
        ...

    @property
    def collection(self) -> CollType:
        """Get collection instance."""
        ...
