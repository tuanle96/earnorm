"""Redis connection implementation."""

from typing import Any

from redis.asyncio import Redis
from redis.exceptions import ConnectionError, TimeoutError

from earnorm.pool.core.connection import BaseConnection


class RedisConnection(BaseConnection):
    """Redis connection implementation."""

    def __init__(self, client: Redis, **config: Any) -> None:
        """Initialize Redis connection.

        Args:
            client: Redis client instance
            **config: Additional configuration

        Examples:
            >>> from redis.asyncio import Redis
            >>> client = Redis(host="localhost", port=6379)
            >>> conn = RedisConnection(client)
            >>> await conn.ping()
            True
            >>> await conn.execute("set", "key", "value")
            True
            >>> await conn.execute("get", "key")
            "value"
        """
        super().__init__()
        self._client = client

    async def ping(self) -> bool:
        """Check connection health.

        Returns:
            True if connection is healthy
        """
        try:
            pong = await self._client.ping()  # type: ignore
            return bool(pong)
        except (ConnectionError, TimeoutError):
            return False

    async def close(self) -> None:
        """Close connection."""
        await super().close()
        await self._client.close()

    async def execute(self, operation: str, *args: Any, **kwargs: Any) -> Any:
        """Execute Redis operation.

        Args:
            operation: Operation name (e.g. get, set, delete)
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Operation result

        Examples:
            >>> # Set key
            >>> await conn.execute("set", "key", "value")
            True

            >>> # Get key
            >>> await conn.execute("get", "key")
            "value"

            >>> # Delete key
            >>> await conn.execute("delete", "key")
            1

            >>> # Hash operations
            >>> await conn.execute("hset", "hash", "field", "value")
            1
            >>> await conn.execute("hget", "hash", "field")
            "value"

            >>> # List operations
            >>> await conn.execute("lpush", "list", "value")
            1
            >>> await conn.execute("rpop", "list")
            "value"

            >>> # Set operations
            >>> await conn.execute("sadd", "set", "value")
            1
            >>> await conn.execute("smembers", "set")
            {"value"}

            >>> # Sorted set operations
            >>> await conn.execute("zadd", "zset", 1.0, "value")
            1
            >>> await conn.execute("zrange", "zset", 0, -1)
            ["value"]
        """
        self.touch()
        method = getattr(self._client, operation)
        return await method(*args, **kwargs)
