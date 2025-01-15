"""
Core cache manager implementation for Redis-based caching in EarnORM.
"""

import asyncio
import json
import logging
from typing import Any, Awaitable, Optional

import redis.asyncio as redis
from bson import ObjectId
from redis.asyncio.client import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class ObjectIdEncoder(json.JSONEncoder):
    """JSON encoder that handles ObjectId."""

    def default(self, o: Any) -> Any:
        if isinstance(o, ObjectId):
            return str(o)
        return super().default(o)


class CacheManager:
    """
    Manages Redis-based caching operations with automatic reconnection and health checking.

    Args:
        redis_uri (Optional[str]): Redis connection URI. If None, caching is disabled.
        ttl (int): Default TTL for cached items in seconds.
        prefix (str): Prefix for all cache keys.
        max_retries (int): Maximum number of reconnection attempts.
        retry_delay (float): Initial delay between retries in seconds (uses exponential backoff).
        health_check_interval (float): Interval between health checks in seconds.
    """

    def __init__(
        self,
        redis_uri: Optional[str] = None,
        ttl: int = 3600,
        prefix: str = "earnorm:",
        max_retries: int = 3,
        retry_delay: float = 1.0,
        health_check_interval: float = 30.0,
    ):
        self.redis_uri = redis_uri
        self.ttl = ttl
        self.prefix = prefix
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.health_check_interval = health_check_interval

        self._client: Redis | None = None
        self._enabled = bool(redis_uri)
        self._connected = False
        self._health_check_task: Optional[asyncio.Task[None]] = None

        if not self._enabled:
            logger.warning(
                "Cache manager initialized without Redis URI - caching is disabled"
            )

    async def connect(self) -> None:
        """
        Establishes connection to Redis with retry mechanism.
        """
        if not self._enabled:
            return

        retries = 0
        delay = self.retry_delay

        while retries < self.max_retries:
            try:
                if self.redis_uri:
                    client = redis.from_url(self.redis_uri)
                    if isinstance(client, Redis):
                        await client.ping()
                        self._client = client
                        self._connected = True
                        logger.info("Successfully connected to Redis")

                        # Start health check task
                        if self._health_check_task is None:
                            self._health_check_task = asyncio.create_task(
                                self._health_check()
                            )

                        return

            except RedisError as e:
                retries += 1
                logger.warning(
                    f"Failed to connect to Redis (attempt {retries}/{self.max_retries}): {str(e)}"
                )

                if retries < self.max_retries:
                    await asyncio.sleep(delay)
                    delay *= 2  # Exponential backoff

        logger.error(
            "Failed to connect to Redis after maximum retries - caching disabled"
        )
        self._enabled = False
        self._connected = False

    async def disconnect(self) -> None:
        """
        Closes Redis connection and stops health check task.
        """
        if self._health_check_task is not None:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None

        if self._client is not None:
            await self._client.close()
            self._client = None

        self._connected = False
        logger.info("Disconnected from Redis")

    async def _health_check(self) -> None:
        """
        Periodically checks Redis connection health and attempts reconnection if needed.
        """
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)

                if self._client is None:
                    raise RedisError("No Redis client")

                await self._client.ping()

            except RedisError as e:
                logger.warning(f"Redis health check failed: {str(e)}")
                self._connected = False
                await self.connect()

            except asyncio.CancelledError:
                break

    def _make_key(self, key: str) -> str:
        """
        Prepends prefix to cache key.
        """
        return f"{self.prefix}{key}"

    async def get(self, key: str) -> Optional[Any]:
        """
        Retrieves value from cache.

        Args:
            key (str): Cache key without prefix

        Returns:
            Optional[Any]: Cached value if found, None otherwise
        """
        if not (self._enabled and self._connected and self._client):
            return None

        try:
            value = await self._client.get(self._make_key(key))
            if value is not None:
                return json.loads(value)
        except RedisError as e:
            logger.warning(f"Failed to get cache key '{key}': {str(e)}")
            self._connected = False

        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Sets value in cache with optional TTL.

        Args:
            key (str): Cache key without prefix
            value (Any): Value to cache (must be JSON serializable)
            ttl (Optional[int]): TTL in seconds, defaults to self.ttl

        Returns:
            bool: True if value was cached successfully
        """
        if not (self._enabled and self._connected and self._client):
            return False

        try:
            await self._client.set(
                self._make_key(key),
                json.dumps(value, cls=ObjectIdEncoder),
                ex=ttl or self.ttl,
            )
            return True
        except RedisError as e:
            logger.warning(f"Failed to set cache key '{key}': {str(e)}")
            self._connected = False
            return False

    async def delete(self, key: str) -> bool:
        """
        Deletes value from cache.

        Args:
            key (str): Cache key without prefix

        Returns:
            bool: True if value was deleted successfully
        """
        if not (self._enabled and self._connected and self._client):
            return False

        try:
            await self._client.delete(self._make_key(key))
            return True
        except RedisError as e:
            logger.warning(f"Failed to delete cache key '{key}': {str(e)}")
            self._connected = False
            return False

    async def clear(self, pattern: str = "*") -> bool:
        """
        Deletes all keys matching pattern.

        Args:
            pattern (str): Key pattern to match (appended to prefix)

        Returns:
            bool: True if keys were deleted successfully
        """
        if not (self._enabled and self._connected and self._client):
            return False

        try:
            keys = await self._client.keys(self._make_key(pattern))
            if keys:
                await self._client.delete(*keys)
            return True
        except RedisError as e:
            logger.warning(f"Failed to clear cache keys matching '{pattern}': {str(e)}")
            self._connected = False
            return False

    @property
    def enabled(self) -> bool:
        """Whether caching is enabled."""
        return self._enabled

    @property
    def connected(self) -> bool:
        """Whether connected to Redis."""
        return self._connected
