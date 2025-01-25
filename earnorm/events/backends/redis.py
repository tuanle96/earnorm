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

import json
import logging
from typing import Any, Dict, Optional, cast

# pylint: disable=no-name-in-module,import-error
# pyright: ignore[import]
import redis.asyncio as redis
from redis.exceptions import RedisError

from earnorm.di import container
from earnorm.events.backends.base import EventBackend
from earnorm.events.core.event import Event
from earnorm.events.core.exceptions import RedisConnectionError, PublishError
from earnorm.pool.backends.redis import RedisConnection, RedisPool

logger = logging.getLogger(__name__)


class RedisBackend(EventBackend):
    """Redis event backend.

    This class implements the EventBackend protocol using Redis as the
    message broker. It handles connection management, serialization,
    and Redis-specific operations.

    Features:
    - JSON serialization for events
    - Connection pooling and management
    - Pattern-based subscriptions
    - Health checks via PING

    Attributes:
        _host: Redis host address
        _port: Redis port number
        _db: Redis database number
        _password: Optional Redis password
        _kwargs: Additional Redis client options
        _client: Redis client instance
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize Redis backend.

        Args:
            host: Redis host address (default: "localhost")
            port: Redis port number (default: 6379)
            db: Redis database number (default: 0)
            password: Redis password (optional)
            **kwargs: Additional Redis client options
                - max_connections: Max connections in pool
                - socket_timeout: Socket timeout in seconds
                - socket_connect_timeout: Connect timeout in seconds
                - retry_on_timeout: Whether to retry on timeout
                - health_check_interval: Health check interval in seconds

        Examples:
            ```python
            # Basic initialization
            backend = RedisBackend()

            # Custom configuration
            backend = RedisBackend(
                host="redis.example.com",
                port=6380,
                db=1,
                password="secret",
                max_connections=20,
                socket_timeout=5.0
            )
            ```
        """
        super().__init__()
        self._host = host
        self._port = port
        self._db = db
        self._password = password
        self._kwargs = kwargs
        self._client: Optional[redis.Redis] = None
        self._pool: Optional[RedisPool[redis.Redis, redis.Redis]] = None

    @property
    def id(self) -> str:
        """Get backend ID.

        Returns:
            str: Backend identifier in format "redis:host:port/db"
        """
        return f"redis:{self._host}:{self._port}/{self._db}"

    @property
    def data(self) -> Dict[str, Any]:
        """Get backend data.

        Returns:
            Dict containing backend configuration:
            - host: Redis host
            - port: Redis port
            - db: Redis database
        """
        return {
            "host": self._host,
            "port": self._port,
            "db": self._db,
        }

    @property
    def is_connected(self) -> bool:
        """Check if connected to Redis.

        Returns:
            bool: True if client exists and is connected
        """
        return self._client is not None

    async def connect(self) -> None:
        """Connect to Redis using pool from DI container."""
        try:
            # Get Redis pool from container
            pool = await container.get("redis_pool")
            if not pool:
                raise RedisConnectionError("Redis pool not found in container")

            self._pool = cast(RedisPool[redis.Redis, redis.Redis], pool)

            # Get connection from pool
            async with await self._pool.connection() as conn:
                self._client = cast(redis.Redis, conn)
                await self._client.ping()  # type: ignore
                logger.info(
                    "Connected to Redis at %s:%s/%s", self._host, self._port, self._db
                )
        except RedisError as e:
            logger.error("Failed to connect to Redis: %s", str(e))
            raise RedisConnectionError(f"Failed to connect to Redis: {str(e)}") from e

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._client and self._pool:
            await self._pool.release(RedisConnection(self._client))
            self._client = None
            self._pool = None
            logger.info(
                "Disconnected from Redis at %s:%s/%s",
                self._host,
                self._port,
                self._db,
            )

    async def publish(self, event: Event) -> None:
        """Publish event to Redis.

        This method serializes the event to JSON and publishes it using
        Redis PUBLISH command.

        Args:
            event: Event to publish

        Raises:
            PublishError: If publish fails
            ConnectionError: If not connected to Redis

        Examples:
            ```python
            event = Event(name="user.created", data={"id": "123"})
            await backend.publish(event)
            ```
        """
        if not self._client:
            raise RedisConnectionError("Not connected to Redis")

        try:
            # Serialize event
            event_data = json.dumps(
                {
                    "name": event.name,
                    "data": event.data,
                    "metadata": event.metadata,
                }
            )

            # Publish to channel
            await self._client.publish(event.name, event_data)  # type: ignore
            logger.debug("Published event %s", event.name)
        except (RedisError, TypeError) as e:
            logger.error("Failed to publish event %s: %s", event.name, str(e))
            raise PublishError(f"Failed to publish event: {str(e)}") from e

    async def subscribe(self, pattern: str) -> None:
        """Subscribe to events matching pattern.

        This method subscribes to Redis channels matching the pattern
        using PSUBSCRIBE command.

        Args:
            pattern: Event pattern to match (Redis glob-style)

        Raises:
            ConnectionError: If not connected to Redis or subscription fails

        Examples:
            ```python
            # Subscribe to all user events
            await backend.subscribe("user.*")

            # Subscribe to specific event
            await backend.subscribe("user.created")
            ```
        """
        if not self._client:
            raise RedisConnectionError("Not connected to Redis")

        try:
            pubsub = self._client.pubsub()  # type: ignore
            await pubsub.psubscribe(pattern)
            logger.info("Subscribed to pattern %s", pattern)
        except RedisError as e:
            logger.error("Failed to subscribe to pattern %s: %s", pattern, str(e))
            raise RedisConnectionError(f"Failed to subscribe to pattern: {str(e)}") from e
