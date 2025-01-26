"""Redis connection pool implementation.

This module implements a connection pool for Redis using the aioredis driver.
It provides connection lifecycle management, retry mechanism, and circuit breaker.

Examples:
    ```python
    pool = RedisPool(
        uri="redis://localhost:6379",
        min_size=1,
        max_size=10,
        max_idle_time=300,
        max_lifetime=3600,
        retry_policy=RetryPolicy(
            max_retries=3,
            base_delay=1.0,
            max_delay=5.0,
        ),
        circuit_breaker=CircuitBreaker(
            failure_threshold=5,
            reset_timeout=30.0,
            half_open_timeout=5.0,
        ),
    )

    async with pool.connection() as conn:
        await conn.execute_typed(
            "get",
            key="test",
        )
    ```
"""

import asyncio
import logging
from typing import Any, AsyncContextManager, Optional, Set, TypeVar, cast

try:
    from redis.asyncio import Redis
except ImportError as e:
    raise ImportError(
        "Redis package is not installed. Please install it with: "
        "pip install 'redis[hiredis]>=4.2.0'"
    ) from e

from earnorm.exceptions import PoolExhaustedError, RedisConnectionError
from earnorm.pool.backends.redis.connection import RedisConnection
from earnorm.pool.core.circuit import CircuitBreaker
from earnorm.pool.core.retry import RetryPolicy
from earnorm.pool.protocols.connection import AsyncConnectionProtocol
from earnorm.pool.protocols.pool import AsyncPoolProtocol

DB = TypeVar("DB", bound=Redis)
COLL = TypeVar("COLL", bound=None)

logger = logging.getLogger(__name__)


class RedisPool(AsyncPoolProtocol[DB, COLL]):
    """Redis connection pool implementation."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        username: str | None = None,
        password: str | None = None,
        min_size: int = 2,
        max_size: int = 20,
        retry_policy: RetryPolicy | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize Redis pool.

        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            username: Username for authentication
            password: Password for authentication
            min_size: Minimum pool size
            max_size: Maximum pool size
            retry_policy: Retry policy
            circuit_breaker: Circuit breaker
            **kwargs: Additional client options
        """
        self._host = host
        self._port = port
        self._db = db
        self._username = username
        self._password = password
        self._min_size = min_size
        self._max_size = max_size
        self._retry_policy = retry_policy
        self._circuit_breaker = circuit_breaker
        self._kwargs = kwargs

        self._client: Redis | None = None
        self._available: Set[AsyncConnectionProtocol[DB, COLL]] = set()
        self._in_use: Set[AsyncConnectionProtocol[DB, COLL]] = set()
        self._lock = asyncio.Lock()

    @property
    def backend(self) -> str:
        """Get backend name.

        Returns:
            str: Backend name
        """
        return "redis"

    def _create_connection(self) -> AsyncConnectionProtocol[DB, COLL]:
        """Create a new connection.

        Returns:
            AsyncConnectionProtocol: New connection

        Raises:
            ConnectionError: If connection creation fails
        """
        if not self._client:
            raise RedisConnectionError("Pool is not connected")

        return cast(
            AsyncConnectionProtocol[DB, COLL],
            RedisConnection(
                client=self._client,
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

    async def init(self) -> None:
        """Initialize pool.

        This method creates the initial connections.

        Raises:
            ConnectionError: If pool initialization fails
        """
        async with self._lock:
            try:
                # Create client if not exists
                if not self._client:
                    self._client = Redis(
                        host=self._host,
                        port=self._port,
                        db=self._db,
                        username=self._username,
                        password=self._password,
                        **self._kwargs,
                    )

                # Create initial connections
                for _ in range(self._min_size):
                    conn = self._create_connection()
                    self._available.add(conn)

                logger.info(
                    "Initialized Redis pool with %d connections",
                    self.size,
                )
            except Exception as e:
                raise RedisConnectionError(
                    f"Failed to initialize Redis pool: {e!s}",
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
        await self.clear()
        if self._client:
            await self._client.close()
            self._client = None
        logger.info("Destroyed Redis pool")

    async def close(self) -> None:
        """Close pool and cleanup resources."""
        await self.destroy()

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
                    raise RedisConnectionError(
                        f"Failed to create connection: {e!s}",
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

    async def health_check(self) -> bool:
        """Check pool health.

        Returns:
            True if pool is healthy
        """
        if not self._client:
            return False

        try:
            result = await self._client.ping()  # type: ignore
            return bool(result)
        except Exception as e:
            logger.error("Failed to ping Redis: %s", str(e))
            return False

    def get_stats(self) -> dict[str, Any]:
        """Get pool statistics."""
        return {
            "host": self._host,
            "port": self._port,
            "db": self._db,
            "size": self.size,
            "max_size": self.max_size,
            "min_size": self.min_size,
            "available": self.available,
            "in_use": self.in_use,
        }

    @property
    def database_name(self) -> str:
        """Get database name."""
        return str(self._db)


class _ConnectionManager(AsyncContextManager[AsyncConnectionProtocol[DB, COLL]]):
    """Connection manager for Redis pool."""

    def __init__(self, pool: RedisPool[DB, COLL]) -> None:
        """Initialize connection manager.

        Args:
            pool: Redis pool
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
