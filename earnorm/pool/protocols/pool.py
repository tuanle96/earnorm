"""Pool protocol definitions.

This module defines protocols for connection pools with async-first approach.
All operations are async by default.

Examples:
    ```python
    class MyPool(AsyncPoolProtocol[MyDB, MyColl]):
        def _create_connection(self) -> AsyncConnectionProtocol[MyDB, MyColl]:
            return MyConnection(self._client)

        async def acquire(self) -> AsyncConnectionProtocol[MyDB, MyColl]:
            return await self._acquire_connection()
    ```
"""

from typing import Any, AsyncContextManager, Dict, Protocol, TypeVar

from earnorm.pool.protocols.connection import AsyncConnectionProtocol

# Type variables for database and collection types
DBPool = TypeVar("DBPool")
CollPool = TypeVar("CollPool")


class AsyncPoolProtocol(Protocol[DBPool, CollPool]):
    """Protocol for async connection pools.

    Type Parameters:
        DBPool: The database type (e.g. AsyncIOMotorDatabase)
        CollPool: The collection type (e.g. AsyncIOMotorCollection)
    """

    @property
    def size(self) -> int:
        """Get current pool size."""
        ...

    @property
    def max_size(self) -> int:
        """Get maximum pool size."""
        ...

    @property
    def min_size(self) -> int:
        """Get minimum pool size."""
        ...

    @property
    def available(self) -> int:
        """Get number of available connections."""
        ...

    @property
    def in_use(self) -> int:
        """Get number of connections in use."""
        ...

    def _create_connection(self) -> AsyncConnectionProtocol[DBPool, CollPool]:
        """Create new connection.

        Returns:
            New connection instance
        """
        ...

    async def connection(
        self,
    ) -> AsyncContextManager[AsyncConnectionProtocol[DBPool, CollPool]]:
        """Get connection from pool.

        Returns:
            Connection instance
        """
        ...

    async def acquire(self) -> AsyncConnectionProtocol[DBPool, CollPool]:
        """Acquire connection from pool.

        Returns:
            Connection instance
        """
        ...

    async def release(
        self, connection: AsyncConnectionProtocol[DBPool, CollPool]
    ) -> None:
        """Release connection back to pool.

        Args:
            connection: Connection to release
        """
        ...

    async def clear(self) -> None:
        """Clear all connections from pool."""
        ...

    async def close(self) -> None:
        """Close pool and cleanup resources."""
        ...

    async def health_check(self) -> bool:
        """Check pool health.

        Returns:
            True if pool is healthy
        """
        ...

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics.

        Returns:
            Dictionary containing pool statistics
        """
        ...

    @property
    def database_name(self) -> str:
        """Get database name."""
        ...
