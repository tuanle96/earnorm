"""MongoDB connection pool implementation."""

import asyncio
import logging
from typing import Any, AsyncContextManager, Optional, Set, TypeVar, cast

from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)

# pylint: disable=redefined-builtin
from earnorm.exceptions import ConnectionError, PoolExhaustedError
from earnorm.pool.backends.mongo.connection import MongoConnection
from earnorm.pool.core.circuit import CircuitBreaker
from earnorm.pool.core.retry import RetryPolicy
from earnorm.pool.protocols.connection import AsyncConnectionProtocol
from earnorm.pool.protocols.pool import AsyncPoolProtocol

DB = TypeVar("DB", bound=AsyncIOMotorDatabase[dict[str, Any]])
COLL = TypeVar("COLL", bound=AsyncIOMotorCollection[dict[str, Any]])

logger = logging.getLogger(__name__)


class MongoPool(AsyncPoolProtocol[DB, COLL]):
    """MongoDB connection pool implementation."""

    def __init__(
        self,
        uri: str,
        database: str,
        min_size: int = 1,
        max_size: int = 10,
        retry_policy: Optional[RetryPolicy] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize pool.

        Args:
            uri: MongoDB URI
            database: Database name
            min_size: Minimum pool size
            max_size: Maximum pool size
            retry_policy: Optional retry policy
            circuit_breaker: Optional circuit breaker
            **kwargs: Additional client options
        """
        self._uri = uri
        self._database = database
        self._min_size = min_size
        self._max_size = max_size
        self._retry_policy = retry_policy
        self._circuit_breaker = circuit_breaker
        self._kwargs = kwargs

        self._client: Optional[AsyncIOMotorClient[dict[str, Any]]] = None
        self._available: Set[AsyncConnectionProtocol[DB, COLL]] = set()
        self._in_use: Set[AsyncConnectionProtocol[DB, COLL]] = set()
        self._lock = asyncio.Lock()

    @property
    def backend(self) -> str:
        """Get backend name.

        Returns:
            str: Backend name
        """
        return "mongodb"

    @property
    def size(self) -> int:
        """Get current pool size."""
        return len(self._available) + len(self._in_use)

    @property
    def max_size(self) -> int:
        """Get maximum pool size."""
        return self._max_size

    @property
    def min_size(self) -> int:
        """Get minimum pool size."""
        return self._min_size

    @property
    def available(self) -> int:
        """Get number of available connections."""
        return len(self._available)

    @property
    def in_use(self) -> int:
        """Get number of connections in use."""
        return len(self._in_use)

    async def init(self) -> None:
        """Initialize pool.

        This method creates the initial connections.

        Raises:
            ConnectionError: If pool initialization fails
        """
        async with self._lock:
            try:
                # Create client
                self._client = AsyncIOMotorClient(
                    self._uri,
                    minPoolSize=self._min_size,
                    maxPoolSize=self._max_size,
                    **self._kwargs,
                )

                # Create initial connections
                for _ in range(self._min_size):
                    conn = self._create_connection()
                    self._available.add(conn)

                logger.info(
                    "Initialized MongoDB pool with %d connections",
                    self.size,
                )
            except Exception as e:
                raise ConnectionError(
                    f"Failed to initialize MongoDB pool: {e!s}",
                    backend=self.backend,
                ) from e

    async def clear(self) -> None:
        """Clear all connections."""
        async with self._lock:
            # Close all connections
            for conn in self._available | self._in_use:
                await conn.close()

            # Clear sets
            self._available.clear()
            self._in_use.clear()

            logger.info("Cleared all connections from pool")

    async def destroy(self) -> None:
        """Destroy pool and all connections."""
        if self._client:
            # Clear connections
            await self.clear()

            # Close client
            self._client.close()
            self._client = None

            logger.info("Destroyed MongoDB pool")

    async def acquire(self) -> AsyncConnectionProtocol[DB, COLL]:
        """Acquire connection from pool.

        Returns:
            AsyncConnectionProtocol: Connection instance

        Raises:
            PoolExhaustedError: If no connections are available
            ConnectionError: If connection creation fails
        """
        async with self._lock:
            # Get available connection or create new one
            if not self._available and self.size < self.max_size:
                try:
                    conn = self._create_connection()
                    self._available.add(conn)
                except Exception as e:
                    raise ConnectionError(
                        f"Failed to create connection: {e!s}",
                        backend=self.backend,
                    ) from e

            # Check if pool is exhausted
            if not self._available:
                raise PoolExhaustedError(
                    "Connection pool exhausted",
                    backend=self.backend,
                    pool_size=self.max_size,
                    active_connections=len(self._in_use),
                    waiting_requests=0,
                )

            # Get connection from available set
            conn = self._available.pop()
            self._in_use.add(conn)

            return conn

    async def release(self, conn: AsyncConnectionProtocol[DB, COLL]) -> None:
        """Release connection back to pool.

        Args:
            conn: Connection to release
        """
        async with self._lock:
            try:
                # Move connection back to available set
                self._in_use.remove(conn)
                if await conn.ping():
                    self._available.add(conn)
                else:
                    await conn.close()
            except ValueError:
                pass

    def _create_connection(self) -> AsyncConnectionProtocol[DB, COLL]:
        """Create new connection.

        Returns:
            New connection instance

        Raises:
            ConnectionError: If pool is not initialized
        """
        if not self._client:
            raise ConnectionError(
                "Pool not initialized",
                backend=self.backend,
            )

        return cast(
            AsyncConnectionProtocol[DB, COLL],
            MongoConnection(
                client=self._client,
                database=self._database,
                collection="",  # Empty string as default collection
                retry_policy=self._retry_policy,
                circuit_breaker=self._circuit_breaker,
            ),
        )

    async def connection(
        self,
    ) -> AsyncContextManager[AsyncConnectionProtocol[DB, COLL]]:
        """Get connection from pool.

        Returns:
            Connection instance

        Raises:
            PoolExhaustedError: If no connections are available
            ConnectionError: If connection creation fails
        """
        return _ConnectionManager(self)

    async def close(self) -> None:
        """Close pool and cleanup resources."""
        await self.destroy()

    async def health_check(self) -> bool:
        """Check pool health.

        Returns:
            True if pool is healthy
        """
        if not self._client:
            return False

        try:
            await self._client.admin.command("ping")
            return True
        except Exception:
            return False

    def get_stats(self) -> dict[str, Any]:
        """Get pool statistics."""
        return {
            "database": self._database,
            "size": self.size,
            "max_size": self.max_size,
            "min_size": self.min_size,
            "available": self.available,
            "in_use": self.in_use,
        }

    @property
    def database_name(self) -> str:
        """Get database name."""
        return self._database


class _ConnectionManager(AsyncContextManager[AsyncConnectionProtocol[DB, COLL]]):
    """Connection manager for MongoDB pool."""

    def __init__(self, pool: MongoPool[DB, COLL]) -> None:
        """Initialize connection manager.

        Args:
            pool: MongoDB pool
        """
        self.pool = pool
        self.conn: Optional[AsyncConnectionProtocol[DB, COLL]] = None

    async def __aenter__(self) -> AsyncConnectionProtocol[DB, COLL]:
        """Enter async context.

        Returns:
            Connection instance

        Raises:
            PoolExhaustedError: If no connections are available
            ConnectionError: If connection creation fails
        """
        self.conn = await self.pool.acquire()
        return self.conn

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context.

        Args:
            exc_type: Exception type
            exc_val: Exception value
            exc_tb: Traceback
        """
        if self.conn:
            await self.pool.release(self.conn)
