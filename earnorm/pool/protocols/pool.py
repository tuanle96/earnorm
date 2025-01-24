"""Pool protocol definitions.

This module defines protocols for connection pools, including connection
lifecycle management and pool statistics.

Examples:
    ```python
    class MyPool(PoolProtocol[MyDB, MyColl]):
        def _create_connection(self) -> ConnectionProtocol[MyDB, MyColl]:
            return MyConnection(self._client)

        async def acquire(self) -> ConnectionProtocol[MyDB, MyColl]:
            return await self._acquire_connection()

        async def release(self, connection: ConnectionProtocol[MyDB, MyColl]) -> None:
            await self._release_connection(connection)
    ```
"""

from typing import Any, AsyncContextManager, Coroutine, Dict, Protocol, TypeVar

from earnorm.pool.protocols.connection import ConnectionProtocol

# Type variables for database and collection types
# These must be invariant since they are used in both parameter and return positions
DBPool = TypeVar("DBPool")
CollPool = TypeVar("CollPool")


class PoolProtocol(Protocol[DBPool, CollPool]):
    """Protocol for connection pools.

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

    def _create_connection(self) -> ConnectionProtocol[DBPool, CollPool]:
        """Create new connection.

        Returns:
            New connection instance

        Raises:
            ConnectionError: If connection cannot be created
        """
        ...

    async def connection(
        self,
    ) -> AsyncContextManager[ConnectionProtocol[DBPool, CollPool]]:
        """Get connection from pool.

        Returns:
            Connection instance

        Raises:
            PoolError: If no connections are available
            ConnectionError: If connection is invalid
        """
        ...

    async def acquire(
        self,
    ) -> Coroutine[Any, Any, ConnectionProtocol[DBPool, CollPool]]:
        """Acquire connection from pool.

        Returns:
            Connection instance

        Raises:
            PoolError: If no connections are available
            ConnectionError: If connection is invalid
        """
        ...

    async def release(
        self, connection: ConnectionProtocol[DBPool, CollPool]
    ) -> Coroutine[Any, Any, None]:
        """Release connection back to pool.

        Args:
            connection: Connection to release

        Raises:
            PoolError: If connection cannot be released
        """
        ...

    async def clear(self) -> Coroutine[Any, Any, None]:
        """Clear all connections from pool.

        Raises:
            PoolError: If pool cannot be cleared
        """
        ...

    async def close(self) -> Coroutine[Any, Any, None]:
        """Close pool and cleanup resources.

        Raises:
            PoolError: If pool cannot be closed
        """
        ...

    async def health_check(self) -> Coroutine[Any, Any, bool]:
        """Check pool health.

        Returns:
            True if pool is healthy

        Raises:
            PoolError: If health check fails
        """
        ...

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics.

        Returns:
            Dictionary containing pool statistics
        """
        ...

    # get database name by property
    @property
    def database_name(self) -> str:
        """Get database name."""
        ...
