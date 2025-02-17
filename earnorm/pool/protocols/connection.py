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
StoreType = TypeVar("StoreType", covariant=True)


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


class AsyncOperations(Protocol[DBType, StoreType]):
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
    AsyncLifecycle, AsyncOperations[DBType, StoreType], Protocol
):
    """Protocol for async database connections.

    This protocol defines the interface that all async database connections must implement.
    It provides methods for getting stores and managing the connection lifecycle.

    Type Parameters:
        DBType: The database type (e.g. AsyncIOMotorDatabase)
        StoreType: The store type (e.g. AsyncIOMotorCollection for MongoDB, Table for SQL)
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

    def get_store(self, name: str) -> StoreType:
        """Get store instance.

        Args:
            name: Store name (e.g. collection in MongoDB, table in SQL)

        Returns:
            Store instance

        Raises:
            ValueError: If store name is empty
        """
        ...

    @property
    def db(self) -> DBType:
        """Get database instance."""
        ...

    @property
    def store(self) -> StoreType:
        """Get current store instance."""
        ...

    def set_store(self, name: str) -> None:
        """Set current store name.

        Args:
            name: Store name (e.g. collection in MongoDB, table in SQL)

        Raises:
            ValueError: If store name is empty
        """
        ...
