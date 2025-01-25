"""Redis event backend implementation.

This module provides a Redis-based event backend using Redis Pub/Sub.
It implements the EventBackend protocol using redis-py's asyncio client.

Features:
- Asynchronous Redis operations
- JSON serialization for events
- Pattern-based subscriptions
- Health checks
- Connection pooling

Examples:
    ```python
    from earnorm.events.backends.redis import RedisBackend
    from earnorm.events.core.event import Event

    # Create backend
    backend = RedisBackend(
        host="localhost",
        port=6379,
        db=0,
        password="secret",
        max_connections=10
    )

    # Initialize and connect
    await backend.init()

    # Publish event
    event = Event(name="user.created", data={"id": "123"})
    await backend.publish(event)

    # Subscribe to events
    await backend.subscribe("user.*")
    ```
"""

import logging
from typing import Any, Dict, Optional, cast

from redis.asyncio import Redis  # type: ignore

from earnorm.di import container
from earnorm.events.backends.base import EventBackend
from earnorm.events.core.event import Event
from earnorm.events.core.exceptions import RedisConnectionError
from earnorm.pool.backends.redis.pool import RedisPool

logger = logging.getLogger(__name__)


class RedisBackend(EventBackend):
    """Redis event backend.

    This backend uses Redis Pub/Sub for event distribution.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize backend.

        Args:
            host: Redis host
            port: Redis port
            db: Redis database
            password: Redis password
            **kwargs: Additional Redis options
        """
        super().__init__()
        self._host = host
        self._port = port
        self._db = db
        self._password = password
        self._kwargs = kwargs
        self._pool: Optional[RedisPool[Redis]] = None

    @property
    def id(self) -> str:
        """Get backend ID."""
        return f"redis_{self._host}:{self._port}/{self._db}"

    @property
    def data(self) -> Dict[str, Any]:
        """Get backend data."""
        return {
            "host": self._host,
            "port": self._port,
            "db": self._db,
            "connected": self._pool is not None,
        }

    async def init(self, **config: Any) -> None:
        """Initialize backend.

        This method gets the Redis pool from the container.

        Args:
            **config: Configuration options (unused)
        """
        try:
            # Get Redis pool from container
            pool = await container.get("redis_pool")
            if not pool:
                raise RedisConnectionError("Redis pool not found in container")

            self._pool = cast(RedisPool[Redis], pool)
        except Exception as e:
            raise RedisConnectionError(f"Failed to get Redis pool: {str(e)}") from e

    async def destroy(self) -> None:
        """Destroy backend.

        This method releases the Redis pool reference.
        """
        self._pool = None

    async def publish(self, event: Event) -> None:
        """Publish event.

        This method publishes an event to Redis Pub/Sub.

        Args:
            event: Event to publish
        """
        if not self._pool:
            raise RedisConnectionError("Redis pool not initialized")

        try:
            conn = await self._pool.acquire()
            try:
                await conn.execute("publish", channel=event.name, message=event.data)
            finally:
                await self._pool.release(conn)
        except Exception as e:
            raise RedisConnectionError(f"Failed to publish event: {str(e)}") from e

    async def subscribe(self, pattern: str) -> None:
        """Subscribe to events.

        This method subscribes to events matching a pattern.

        Args:
            pattern: Event pattern to match
        """
        if not self._pool:
            raise RedisConnectionError("Redis pool not initialized")

        try:
            conn = await self._pool.acquire()
            try:
                await conn.execute("psubscribe", pattern=pattern)
            finally:
                await self._pool.release(conn)
        except Exception as e:
            raise RedisConnectionError(f"Failed to subscribe: {str(e)}") from e

    async def unsubscribe(self, pattern: str) -> None:
        """Unsubscribe from events.

        This method unsubscribes from events matching a pattern.

        Args:
            pattern: Event pattern to unsubscribe from
        """
        if not self._pool:
            raise RedisConnectionError("Redis pool not initialized")

        try:
            conn = await self._pool.acquire()
            try:
                await conn.execute("punsubscribe", pattern=pattern)
            finally:
                await self._pool.release(conn)
        except Exception as e:
            raise RedisConnectionError(f"Failed to unsubscribe: {str(e)}") from e
