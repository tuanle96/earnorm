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

from typing import Any, TypeVar, cast

from redis.asyncio import Redis

from earnorm.exceptions import ConnectionError as DatabaseConnectionError
from earnorm.pool.backends.base.pool import BasePool
from earnorm.pool.core.circuit import CircuitBreaker
from earnorm.pool.core.retry import RetryPolicy
from earnorm.pool.protocols.connection import AsyncConnectionProtocol

from .connection import RedisConnection

DB = TypeVar("DB", bound=Redis)


class RedisPool(BasePool[DB, None]):
    """Redis connection pool implementation."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        username: str | None = None,
        password: str | None = None,
        pool_size: int = 10,
        min_size: int = 2,
        max_size: int = 20,
        max_idle_time: int = 300,
        max_lifetime: int = 3600,
        retry_policy: RetryPolicy | None = None,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        """Initialize Redis pool.

        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            username: Username for authentication
            password: Password for authentication
            pool_size: Initial pool size
            min_size: Minimum pool size
            max_size: Maximum pool size
            max_idle_time: Maximum idle time in seconds
            max_lifetime: Maximum lifetime in seconds
            retry_policy: Retry policy
            circuit_breaker: Circuit breaker
        """
        super().__init__(
            pool_size=pool_size,
            min_size=min_size,
            max_size=max_size,
            max_idle_time=max_idle_time,
            max_lifetime=max_lifetime,
            retry_policy=retry_policy,
            circuit_breaker=circuit_breaker,
        )

        self._host = host
        self._port = port
        self._db = db
        self._username = username
        self._password = password
        self._client: Redis | None = None

    def _create_connection(self) -> AsyncConnectionProtocol[DB, None]:
        """Create a new connection.

        Returns:
            AsyncConnectionProtocol: New connection

        Raises:
            DatabaseConnectionError: If connection creation fails
        """
        if not self._client:
            raise DatabaseConnectionError("Pool is not connected")

        return cast(
            AsyncConnectionProtocol[DB, None],
            RedisConnection(
                client=self._client,
                max_idle_time=self._max_idle_time,
                max_lifetime=self._max_lifetime,
                retry_policy=self._retry_policy,
                circuit_breaker=self._circuit_breaker,
            ),
        )

    async def connect(self) -> None:
        """Connect to Redis."""
        if not self._client:
            self._client = Redis(
                host=self._host,
                port=self._port,
                db=self._db,
                username=self._username,
                password=self._password,
            )

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._client:
            await self._client.close()
            self._client = None

    async def ping(self) -> bool:
        """Check pool health.

        Returns:
            bool: True if pool is healthy
        """
        try:
            if not self._client:
                return False
            await self._client.ping()  # type: ignore
            return True
        except Exception:
            return False

    def get_stats(self) -> dict[str, Any]:
        """Get pool statistics."""
        stats = super().get_stats()
        stats.update(
            {
                "host": self._host,
                "port": self._port,
                "db": self._db,
            }
        )
        return stats

    @property
    def database_name(self) -> str:
        """Get database name."""
        return str(self._db)

    async def init(self) -> None:
        """Initialize pool."""
        async with self._lock:
            for _ in range(self._min_size):
                conn = self._create_connection()
                self._available.append(conn)

    async def _create_initial_connections(self) -> None:
        """Create initial connections."""
        for _ in range(self._min_size):
            conn = self._create_connection()
            self._available.append(conn)

    async def _close_connection(self, conn: AsyncConnectionProtocol[DB, None]) -> None:
        """Close Redis connection.

        Args:
            conn: Redis connection
        """
        await conn.close()

    async def _validate_connection(
        self, conn: AsyncConnectionProtocol[DB, None]
    ) -> bool:
        """Validate connection."""
        try:
            result = await conn.ping()
            return bool(result)
        except Exception:
            return False
