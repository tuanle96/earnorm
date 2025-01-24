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

from typing import Any, Coroutine, Dict, Optional, TypeVar, cast

from redis.asyncio import Redis

from earnorm.pool.backends.redis.connection import RedisConnection
from earnorm.pool.circuit import CircuitBreaker
from earnorm.pool.decorators import with_resilience
from earnorm.pool.protocols.connection import ConnectionProtocol
from earnorm.pool.protocols.errors import ConnectionError, PoolError, PoolExhaustedError
from earnorm.pool.protocols.pool import PoolProtocol
from earnorm.pool.retry import RetryPolicy

DB = TypeVar("DB", bound=Redis)
COLL = TypeVar("COLL", bound=Redis)
T = TypeVar("T", bound=RedisConnection)


class RedisPool(PoolProtocol[DB, COLL]):
    """Redis connection pool implementation."""

    def __init__(
        self,
        uri: str,
        min_size: int = 1,
        max_size: int = 10,
        max_idle_time: float = 300,
        max_lifetime: float = 3600,
        retry_policy: Optional[RetryPolicy] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ) -> None:
        """Initialize Redis connection pool.

        Args:
            uri: Redis URI
            min_size: Minimum pool size
            max_size: Maximum pool size
            max_idle_time: Maximum idle time in seconds
            max_lifetime: Maximum lifetime in seconds
            retry_policy: Retry policy configuration
            circuit_breaker: Circuit breaker configuration
        """
        self._uri = uri
        self._min_size = min_size
        self._max_size = max_size
        self._max_idle_time = max_idle_time
        self._max_lifetime = max_lifetime
        self._retry_policy = retry_policy
        self._circuit_breaker = circuit_breaker

        self._pool: Dict[int, ConnectionProtocol[DB, COLL]] = {}
        self._acquiring = 0

    @property
    def min_size(self) -> int:
        """Get minimum pool size."""
        return self._min_size

    @property
    def max_size(self) -> int:
        """Get maximum pool size."""
        return self._max_size

    @property
    def size(self) -> int:
        """Get current pool size."""
        return len(self._pool)

    @property
    def in_use(self) -> int:
        """Get number of connections in use."""
        return self._acquiring

    def get_connection(self) -> ConnectionProtocol[DB, COLL]:
        """Get current connection."""
        if not self._pool:
            raise ConnectionError("No connection available")
        return next(iter(self._pool.values()))

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics.

        Returns:
            Dictionary containing pool statistics:
            - min_size: Minimum pool size
            - max_size: Maximum pool size
            - current_size: Current pool size
            - in_use: Number of connections in use
        """
        return {
            "min_size": self._min_size,
            "max_size": self._max_size,
            "current_size": len(self._pool),
            "in_use": self._acquiring,
        }

    @with_resilience()
    async def _create_connection_impl(self) -> ConnectionProtocol[DB, COLL]:
        """Internal create connection implementation."""
        try:
            client = Redis.from_url(self._uri)  # type: ignore
            conn = cast(
                ConnectionProtocol[DB, COLL],
                RedisConnection(
                    client=client,
                    retry_policy=self._retry_policy,
                    circuit_breaker=self._circuit_breaker,
                ),
            )
            return conn
        except Exception as e:
            raise ConnectionError(f"Failed to create Redis connection: {str(e)}") from e

    @with_resilience()
    async def _validate_connection_impl(
        self, conn: ConnectionProtocol[DB, COLL]
    ) -> bool:
        """Internal validate connection implementation."""
        try:
            result = await conn.ping()
            return bool(result)
        except Exception:
            return False

    @with_resilience()
    async def _acquire_impl(self) -> ConnectionProtocol[DB, COLL]:
        """Internal acquire implementation."""
        if len(self._pool) >= self._max_size and self._acquiring >= self._max_size:
            raise PoolExhaustedError("Redis connection pool exhausted")

        self._acquiring += 1
        try:
            conn = await self._create_connection_impl()
            if not await self._validate_connection_impl(conn):
                raise ConnectionError("Failed to validate Redis connection")
            self._pool[id(conn)] = conn
            return conn
        except Exception as e:
            self._acquiring -= 1
            raise ConnectionError(
                f"Failed to acquire Redis connection: {str(e)}"
            ) from e

    async def acquire(self) -> Coroutine[Any, Any, ConnectionProtocol[DB, COLL]]:
        """Acquire connection from pool.

        Returns:
            Redis connection

        Raises:
            PoolExhaustedError: If pool is exhausted
            ConnectionError: If connection cannot be created
        """

        async def _acquire() -> ConnectionProtocol[DB, COLL]:
            return await self._acquire_impl()

        return _acquire()

    @with_resilience()
    async def _release_impl(self, conn: ConnectionProtocol[DB, COLL]) -> None:
        """Internal release implementation."""
        conn_id = id(conn)
        if conn_id not in self._pool:
            raise ConnectionError("Connection not from this pool")

        try:
            if not await self._validate_connection_impl(conn):
                await self._remove_impl(conn)
                return

            self._pool[conn_id] = conn
            self._acquiring -= 1
        except Exception as e:
            raise ConnectionError(
                f"Failed to release Redis connection: {str(e)}"
            ) from e

    async def release(
        self, connection: ConnectionProtocol[DB, COLL]
    ) -> Coroutine[Any, Any, None]:
        """Release connection back to pool.

        Args:
            connection: Connection to release

        Raises:
            ConnectionError: If connection cannot be released
        """

        async def _release() -> None:
            await self._release_impl(connection)

        return _release()

    @with_resilience()
    async def _remove_impl(self, conn: ConnectionProtocol[DB, COLL]) -> None:
        """Internal remove implementation."""
        conn_id = id(conn)
        if conn_id not in self._pool:
            return

        try:
            await conn.close()
            del self._pool[conn_id]
            self._acquiring -= 1
        except Exception as e:
            raise ConnectionError(f"Failed to remove Redis connection: {str(e)}") from e

    @with_resilience()
    async def _clear_impl(self) -> None:
        """Internal clear implementation."""
        try:
            for conn in list(self._pool.values()):
                await self._remove_impl(conn)
        except Exception as e:
            raise PoolError(f"Failed to clear Redis pool: {str(e)}") from e

    async def clear(self) -> Coroutine[Any, Any, None]:
        """Clear all connections in pool.

        Raises:
            PoolError: If pool cannot be cleared
        """

        async def _clear() -> None:
            await self._clear_impl()

        return _clear()

    async def close(self) -> Coroutine[Any, Any, None]:
        """Close pool.

        Raises:
            PoolError: If pool cannot be closed
        """

        async def _close() -> None:
            await self._clear_impl()

        return _close()

    async def __aenter__(self) -> "RedisPool[DB, COLL]":
        """Enter async context.

        Returns:
            Pool instance
        """
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        """Exit async context.

        Args:
            exc_type: Exception type
            exc: Exception instance
            tb: Traceback
        """
        await self.close()

    async def health_check(self) -> Coroutine[Any, Any, bool]:
        """Check pool health.

        Returns:
            True if pool is healthy
        """

        async def _health_check() -> bool:
            try:
                conn = await self._acquire_impl()
                try:
                    result = await conn.ping()
                    return bool(result)
                finally:
                    await self._release_impl(conn)
            except Exception:
                return False

        return _health_check()

    @property
    def available(self) -> bool:
        """Check if pool is available."""
        return bool(self._pool)

    async def init(self) -> None:
        """Initialize pool."""
        self._pool = await Redis.from_url(self._uri)  # type: ignore

    def _create_connection(self) -> ConnectionProtocol[DB, COLL]:
        """Create new Redis connection.

        Returns:
            Redis connection
        """
        client = Redis.from_url(self._uri)  # type: ignore
        return cast(
            ConnectionProtocol[DB, COLL],
            RedisConnection(
                client=client,
                retry_policy=self._retry_policy,
                circuit_breaker=self._circuit_breaker,
            ),
        )

    async def _close_connection(self, conn: ConnectionProtocol[DB, COLL]) -> None:
        """Close Redis connection.

        Args:
            conn: Redis connection
        """
        await conn.close()
