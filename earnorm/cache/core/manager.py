"""
Core cache manager implementation for Redis-based caching in EarnORM.
"""

import asyncio
import functools
import json
import logging
import random
import time
from dataclasses import dataclass
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
    TypeVar,
    cast,
)

import redis.asyncio as redis
from bson import ObjectId
from redis.asyncio.client import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

T = TypeVar("T")


def with_retry(max_retries: int = 3, delay: float = 0.1) -> Callable[..., Awaitable[T]]:
    """Retry decorator for cache operations.

    Args:
        max_retries: Maximum number of retries
        delay: Initial delay between retries (uses exponential backoff)
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(self: "CacheManager", *args: Any, **kwargs: Any) -> T:
            retries = 0
            current_delay = delay

            while retries < max_retries:
                try:
                    return await func(self, *args, **kwargs)
                except RedisError as e:
                    retries += 1
                    if retries == max_retries:
                        logger.error(
                            f"Operation failed after {max_retries} retries: {str(e)}"
                        )
                        raise

                    logger.warning(
                        f"Operation failed (attempt {retries}/{max_retries}): {str(e)}"
                    )
                    await asyncio.sleep(current_delay)
                    current_delay *= 2  # Exponential backoff

                    # Try to reconnect
                    self._connected = False
                    await self.connect()

            return cast(T, None)

        return wrapper

    return decorator


class ObjectIdEncoder(json.JSONEncoder):
    """JSON encoder that handles ObjectId."""

    def default(self, o: Any) -> Any:
        if isinstance(o, ObjectId):
            return str(o)
        return super().default(o)


class DistributedLock:
    """Distributed lock implementation using Redis."""

    def __init__(self, client: Redis, name: str, timeout: int = 10) -> None:
        self.client = client
        self.name = f"lock:{name}"
        self.timeout = timeout
        self._owner: Optional[str] = None

    async def __aenter__(self) -> bool:
        return await self.acquire()

    async def __aexit__(self, *args: Any) -> None:
        await self.release()

    async def acquire(self) -> bool:
        """Acquire lock with retry.

        Returns:
            bool: True if lock was acquired
        """
        self._owner = f"{id(self)}:{time.time()}"
        retries = 5
        while retries > 0:
            # SET NX with expiry
            locked = await self.client.set(
                self.name, self._owner, nx=True, ex=self.timeout
            )
            if locked:
                return True
            retries -= 1
            await asyncio.sleep(0.2)
        return False

    async def release(self) -> None:
        """Release lock if owner."""
        if self._owner:
            # Only delete if we still own the lock
            current = await self.client.get(self.name)
            # Since decode_responses=True, current is already a string
            if current and current == self._owner:
                await self.client.delete(self.name)

    async def extend(self, additional_time: int) -> bool:
        """Extend lock timeout if owner.

        Args:
            additional_time: Additional seconds to extend lock

        Returns:
            bool: True if lock was extended
        """
        if not self._owner:
            return False

        current = await self.client.get(self.name)
        if current and current.decode() == self._owner:
            # Extend timeout
            return bool(
                await self.client.expire(self.name, self.timeout + additional_time)
            )

        return False

    async def is_locked(self) -> bool:
        """Check if lock is currently held.

        Returns:
            bool: True if lock exists
        """
        return bool(await self.client.exists(self.name))

    async def force_unlock(self) -> bool:
        """Force unlock regardless of owner.

        Returns:
            bool: True if lock was deleted
        """
        return bool(await self.client.delete(self.name))


class BatchInvalidator:
    """Batch cache invalidation."""

    def __init__(self, cache_manager: "CacheManager", max_size: int = 1000) -> None:
        self.cache_manager = cache_manager
        self.keys: Set[str] = set()
        self.patterns: Set[str] = set()
        self.max_size = max_size

    async def add_key(self, key: str) -> bool:
        """Add key to batch.

        Args:
            key: Cache key to add

        Returns:
            bool: True if key was added, False if batch is full
        """
        if self.size >= self.max_size:
            return False
        self.keys.add(key)
        return True

    async def add_pattern(self, pattern: str) -> bool:
        """Add pattern to batch.

        Args:
            pattern: Cache key pattern to add

        Returns:
            bool: True if pattern was added, False if batch is full
        """
        if self.size >= self.max_size:
            return False
        self.patterns.add(pattern)
        return True

    @property
    def size(self) -> int:
        """Get total number of keys and patterns in batch."""
        return len(self.keys) + len(self.patterns)

    def reset(self) -> None:
        """Reset batch to empty state."""
        self.keys.clear()
        self.patterns.clear()

    async def invalidate(self) -> None:
        """Invalidate all keys and patterns in batch."""
        if not self.size:
            return

        # Get lock
        async with DistributedLock(self.cache_manager._client, "batch_invalidate"):
            # Delete keys
            if self.keys:
                await self.cache_manager._client.delete(*self.keys)

            # Delete patterns
            for pattern in self.patterns:
                keys = await self.cache_manager._client.keys(pattern)
                if keys:
                    await self.cache_manager._client.delete(*keys)

            # Reset batch
            self.reset()


@dataclass
class CacheMetrics:
    """Cache metrics."""

    hits: int = 0
    misses: int = 0
    errors: int = 0
    total_operations: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if self.total_operations == 0:
            return 0.0
        return self.hits / self.total_operations

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dict."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "errors": self.errors,
            "total_operations": self.total_operations,
            "hit_rate": self.hit_rate,
        }


class MetricsCollector:
    """Collect and track cache metrics."""

    def __init__(self) -> None:
        self._metrics = CacheMetrics()
        self._start_time = time.time()
        self._sample_rate = 1.0  # Sample 100% by default
        self._last_reset = time.time()

    def record_hit(self) -> None:
        """Record cache hit."""
        if self._should_sample():
            self._metrics.hits += 1
            self._metrics.total_operations += 1

    def record_miss(self) -> None:
        """Record cache miss."""
        if self._should_sample():
            self._metrics.misses += 1
            self._metrics.total_operations += 1

    def record_error(self) -> None:
        """Record cache error."""
        if self._should_sample():
            self._metrics.errors += 1
            self._metrics.total_operations += 1

    def _should_sample(self) -> bool:
        """Check if current operation should be sampled."""
        return random.random() < self._sample_rate

    def set_sample_rate(self, rate: float) -> None:
        """Set sampling rate.

        Args:
            rate: Sampling rate between 0 and 1
        """
        if not 0 <= rate <= 1:
            raise ValueError("Sample rate must be between 0 and 1")
        self._sample_rate = rate

    def reset(self) -> None:
        """Reset all metrics."""
        self._metrics = CacheMetrics()
        self._last_reset = time.time()

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        metrics = self._metrics.to_dict()
        metrics.update(
            {
                "uptime": time.time() - self._start_time,
                "time_since_reset": time.time() - self._last_reset,
                "sample_rate": self._sample_rate,
            }
        )
        return metrics

    def to_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        metrics = self.get_metrics()

        # Add metric help and type
        lines.extend(
            [
                "# HELP cache_hits Total number of cache hits",
                "# TYPE cache_hits counter",
                f"cache_hits {metrics['hits']}",
                "# HELP cache_misses Total number of cache misses",
                "# TYPE cache_misses counter",
                f"cache_misses {metrics['misses']}",
                "# HELP cache_errors Total number of cache errors",
                "# TYPE cache_errors counter",
                f"cache_errors {metrics['errors']}",
                "# HELP cache_operations Total number of cache operations",
                "# TYPE cache_operations counter",
                f"cache_operations {metrics['total_operations']}",
                "# HELP cache_hit_rate Cache hit rate",
                "# TYPE cache_hit_rate gauge",
                f"cache_hit_rate {metrics['hit_rate']}",
                "# HELP cache_uptime Cache uptime in seconds",
                "# TYPE cache_uptime gauge",
                f"cache_uptime {metrics['uptime']}",
                "# HELP cache_time_since_reset Time since last metrics reset in seconds",
                "# TYPE cache_time_since_reset gauge",
                f"cache_time_since_reset {metrics['time_since_reset']}",
                "# HELP cache_sample_rate Current sampling rate",
                "# TYPE cache_sample_rate gauge",
                f"cache_sample_rate {metrics['sample_rate']}",
            ]
        )

        return "\n".join(lines)


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
        self._batch: Optional[BatchInvalidator] = None
        self._metrics = MetricsCollector()

        if not self._enabled:
            logger.warning(
                "Cache manager initialized without Redis URI - caching is disabled"
            )

    async def connect(self) -> bool:
        """Connect to Redis server with retry.

        Returns:
            bool: True if connected successfully
        """
        if not self._enabled:
            return False

        if self._connected and self._client:
            return True

        retries = 0
        current_delay = self.retry_delay

        while retries < self.max_retries:
            try:
                # Create Redis client
                self._client = redis.Redis.from_url(
                    self.redis_uri, decode_responses=True, encoding="utf-8"
                )

                # Test connection
                await self._client.ping()
                self._connected = True

                # Start health check
                if not self._health_check_task:
                    self._health_check_task = asyncio.create_task(self._health_check())

                logger.info("Successfully connected to Redis")
                return True

            except RedisError as e:
                retries += 1
                if retries == self.max_retries:
                    logger.error(
                        f"Failed to connect to Redis after {self.max_retries} attempts: {str(e)}"
                    )
                    return False

                logger.warning(
                    f"Failed to connect to Redis (attempt {retries}/{self.max_retries}): {str(e)}"
                )
                await asyncio.sleep(current_delay)
                current_delay *= 2  # Exponential backoff

        return False

    async def disconnect(self) -> None:
        """Disconnect from Redis server."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None

        if self._client:
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

    @with_retry()
    async def get(self, key: str) -> Optional[Any]:
        """Retrieves value from cache with metrics."""
        if not (self._enabled and self._connected and self._client):
            return None

        try:
            value = await self._client.get(self._make_key(key))
            if value is not None:
                self._metrics.record_hit()
                return json.loads(value)
            self._metrics.record_miss()
        except RedisError as e:
            self._metrics.record_error()
            raise

        return None

    @with_retry()
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Sets value in cache with metrics."""
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
            self._metrics.record_error()
            raise

    @with_retry()
    async def delete(self, key: str) -> bool:
        """Deletes value from cache with retry."""
        if not (self._enabled and self._connected and self._client):
            return False

        await self._client.delete(self._make_key(key))
        return True

    @with_retry()
    async def delete_pattern(self, pattern: str) -> bool:
        """Deletes all keys matching pattern with retry."""
        if not (self._enabled and self._connected and self._client):
            return False

        # Get all keys matching pattern
        pattern_with_prefix = self._make_key(pattern)
        keys = await self._client.keys(pattern_with_prefix)

        if keys:
            # Delete all matched keys
            await self._client.delete(*keys)
        return True

    @with_retry()
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

    @with_retry()
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache.

        Args:
            key: Cache key to check

        Returns:
            bool: True if key exists
        """
        if not (self._enabled and self._connected and self._client):
            return False

        try:
            return bool(await self._client.exists(self._make_key(key)))
        except RedisError as e:
            self._metrics.record_error()
            raise

    @property
    def enabled(self) -> bool:
        """Whether caching is enabled."""
        return self._enabled

    @property
    def connected(self) -> bool:
        """Whether connected to Redis."""
        return self._connected

    def batch(self) -> BatchInvalidator:
        """Get batch invalidator."""
        if not self._batch:
            self._batch = BatchInvalidator(self)
        return self._batch

    async def invalidate_batch(self) -> None:
        """Invalidate current batch."""
        if self._batch:
            await self._batch.invalidate()

    async def with_lock(self, name: str, timeout: int = 10) -> DistributedLock:
        """Get distributed lock."""
        if not self._client:
            raise RedisError("No Redis client")
        return DistributedLock(self._client, name, timeout)

    def get_metrics(self) -> Dict[str, Any]:
        """Get cache metrics."""
        return self._metrics.get_metrics()

    @with_retry()
    async def keys(self, pattern: str) -> List[str]:
        """Get all keys matching pattern.

        Args:
            pattern: Key pattern to match

        Returns:
            List of matching keys
        """
        if not (self._enabled and self._connected and self._client):
            return []

        try:
            # Get keys with prefix
            pattern_with_prefix = self._make_key(pattern)
            keys = await self._client.keys(pattern_with_prefix)

            # Remove prefix from keys before returning
            prefix_len = len(self.prefix)
            return [key[prefix_len:] for key in keys]

        except RedisError as e:
            self._metrics.record_error()
            logger.error(f"Failed to get keys matching pattern '{pattern}': {str(e)}")
            return []
