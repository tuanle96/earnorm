"""Redis connection implementation."""

import time
from typing import Any, Coroutine

from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError

from earnorm.pool.decorators import with_resilience
from earnorm.pool.protocols.connection import ConnectionProtocol
from earnorm.pool.protocols.errors import ConnectionError, OperationError


class RedisConnection(ConnectionProtocol[Redis, Redis]):
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

    def __init__(self, client: Redis, **config: Any) -> None:
        """Initialize Redis connection.

        Args:
            client: Redis client instance
            **config: Additional configuration
        """
        self._client = client
        self._created_at = time.time()
        self._last_used_at = time.time()
        self._max_idle_time = config.get("max_idle_time", 300)
        self._max_lifetime = config.get("max_lifetime", 3600)

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

    def get_database(self) -> Redis:
        """Get Redis database instance.

        Returns:
            Redis instance
        """
        return self._client

    def get_collection(self, name: str) -> Redis:
        """Get Redis instance.

        Args:
            name: Collection name (ignored for Redis)

        Returns:
            Redis instance
        """
        return self._client

    @property
    def db(self) -> Redis:
        """Get Redis instance."""
        return self._client

    @property
    def collection(self) -> Redis:
        """Get Redis instance."""
        return self._client

    @with_resilience()
    async def _ping_impl(self) -> bool:
        """Internal ping implementation."""
        try:
            pong = await self._client.ping()  # type: ignore
            self.touch()
            return bool(pong)
        except (RedisConnectionError, TimeoutError) as e:
            raise ConnectionError(f"Failed to ping Redis: {str(e)}") from e

    async def ping(self) -> Coroutine[Any, Any, bool]:
        """Check connection health.

        Returns:
            True if connection is healthy

        Raises:
            ConnectionError: If connection is unhealthy
        """

        async def _ping() -> bool:
            return await self._ping_impl()

        return _ping()

    @with_resilience()
    async def _execute_impl(self, operation: str, *args: Any, **kwargs: Any) -> Any:
        """Internal execute implementation."""
        try:
            self.touch()
            method = getattr(self._client, operation)
            return await method(*args, **kwargs)
        except Exception as e:
            raise OperationError(
                f"Failed to execute operation {operation}: {str(e)}"
            ) from e

    async def execute_typed(
        self, operation: str, *args: Any, **kwargs: Any
    ) -> Coroutine[Any, Any, Any]:
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

    async def _close_impl(self) -> None:
        """Internal close implementation."""
        try:
            await self._client.close()
        except Exception as e:
            raise ConnectionError(f"Failed to close Redis connection: {str(e)}") from e

    async def close(self) -> Coroutine[Any, Any, None]:
        """Close connection.

        Raises:
            ConnectionError: If connection cannot be closed
        """

        async def _close() -> None:
            await self._close_impl()

        return _close()
