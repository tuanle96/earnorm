"""Redis connection implementation."""

import time
from collections.abc import Awaitable
from typing import Any, TypeVar, cast

from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from earnorm.exceptions import DatabaseConnectionError, OperationError
from earnorm.pool.core.circuit import CircuitBreaker
from earnorm.pool.core.decorators import with_resilience
from earnorm.pool.core.retry import RetryPolicy
from earnorm.pool.protocols.connection import AsyncConnectionProtocol

DB = TypeVar("DB", bound=Redis)


class RedisConnection(AsyncConnectionProtocol[DB, None]):
    """Redis connection implementation.

    Examples:
        >>> from redis.asyncio import Redis
        >>> client = Redis(host="localhost", port=6379)
        >>> conn = RedisConnection(client)
        >>> await conn.ping()
        True
        >>> await conn.execute_typed("set", "key", "value")
        True
        >>> await conn.execute_typed("get", "key")
        "value"
    """

    def __init__(
        self,
        client: Redis,
        max_idle_time: int = 300,
        max_lifetime: int = 3600,
        retry_policy: RetryPolicy | None = None,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        """Initialize Redis connection.

        Args:
            client: Redis client
            max_idle_time: Maximum idle time in seconds
            max_lifetime: Maximum lifetime in seconds
            retry_policy: Retry policy
            circuit_breaker: Circuit breaker
        """
        self._client = client
        self._max_idle_time = max_idle_time
        self._max_lifetime = max_lifetime
        self._retry_policy = retry_policy
        self._circuit_breaker = circuit_breaker

        self._created_at = time.time()
        self._last_used_at = time.time()

    @property
    def created_at(self) -> float:
        """Get connection creation timestamp."""
        return self._created_at

    @property
    def last_used_at(self) -> float:
        """Get last usage timestamp."""
        return self._last_used_at

    @property
    def idle_time(self) -> float:
        """Get idle time in seconds."""
        return time.time() - self._last_used_at

    @property
    def lifetime(self) -> float:
        """Get lifetime in seconds."""
        return time.time() - self._created_at

    @property
    def is_stale(self) -> bool:
        """Check if connection is stale."""
        return (
            self.idle_time > self._max_idle_time or self.lifetime > self._max_lifetime
        )

    def touch(self) -> None:
        """Update last used timestamp."""
        self._last_used_at = time.time()

    @with_resilience()
    async def _ping_impl(self) -> bool:
        """Internal ping implementation."""
        try:
            result = await self.execute("ping")
            self.touch()
            return bool(result)
        except (RedisConnectionError, RedisTimeoutError) as e:
            raise DatabaseConnectionError(f"Failed to ping Redis: {e!s}") from e

    async def ping(self) -> bool:
        """Check connection health."""
        return await self._ping_impl()

    async def close(self) -> None:
        """Close connection."""
        await self._client.close()

    @with_resilience()
    async def _execute_impl(self, operation: str, **kwargs: Any) -> Any:
        """Internal execute implementation."""
        try:
            self.touch()
            method = getattr(self._client, operation)
            result = await method(**kwargs)
            return result
        except Exception as e:
            raise OperationError(
                f"Failed to execute operation {operation}: {e!s}"
            ) from e

    async def execute(self, operation: str, **kwargs: Any) -> Any:
        """Execute Redis operation.

        Args:
            operation: Operation name
            **kwargs: Operation arguments

        Returns:
            Operation result

        Raises:
            OperationError: If operation fails
        """
        return await self._execute_impl(operation, **kwargs)

    def get_database(self) -> DB:
        """Get database instance."""
        return cast(DB, self._client)

    def get_collection(self, name: str) -> None:
        """Get collection instance."""
        raise NotImplementedError("Redis does not support collections")

    @property
    def db(self) -> DB:
        """Get database instance."""
        return self.get_database()

    @property
    def collection(self) -> None:
        """Get collection instance."""
        return self.get_collection("")

    async def connect(self) -> None:
        """Connect to Redis.

        Raises:
            ConnectionError: If connection fails
        """
        try:
            await self.ping()
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Redis: {e!s}") from e

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        await self.close()

    async def execute_typed(
        self, operation: str, *args: Any, **kwargs: Any
    ) -> Awaitable[Any]:
        """Execute Redis operation.

        Args:
            operation: Operation name (e.g. get, set, delete)
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Operation result

        Examples:
            >>> # Set key
            >>> await conn.execute_typed("set", "key", "value")
            True

            >>> # Get key
            >>> await conn.execute_typed("get", "key")
            "value"

            >>> # Delete key
            >>> await conn.execute_typed("delete", "key")
            1

            >>> # Hash operations
            >>> await conn.execute_typed("hset", "hash", "field", "value")
            1
            >>> await conn.execute_typed("hget", "hash", "field")
            "value"

            >>> # List operations
            >>> await conn.execute_typed("lpush", "list", "value")
            1
            >>> await conn.execute_typed("rpop", "list")
            "value"

            >>> # Set operations
            >>> await conn.execute_typed("sadd", "set", "value")
            1
            >>> await conn.execute_typed("smembers", "set")
            {"value"}

            >>> # Sorted set operations
            >>> await conn.execute_typed("zadd", "zset", 1.0, "value")
            1
            >>> await conn.execute_typed("zrange", "zset", 0, -1)
            ["value"]
        """

        async def _execute() -> Any:
            return await self._execute_impl(operation, *args, **kwargs)

        return _execute()
