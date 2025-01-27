"""Query cache implementation.

This module provides caching mechanism for query results.
It supports both in-memory and Redis caching.

Examples:
    >>> # Using in-memory cache
    >>> cache = InMemoryCache()
    >>> cache.set("key", ["result1", "result2"], ttl=60)
    >>> results = cache.get("key")
    >>>
    >>> # Using Redis cache
    >>> cache = RedisCache(redis_url="redis://localhost:6379/0")
    >>> cache.set("key", ["result1", "result2"], ttl=60)
    >>> results = cache.get("key")
"""

import pickle
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, Generic, List, Optional, TypeVar, cast

from earnorm.types import DatabaseModel

ModelT = TypeVar("ModelT", bound=DatabaseModel)
RedisT = TypeVar("RedisT")


class QueryCache(Generic[ModelT], ABC):
    """Base class for query cache implementations.

    This class defines the interface for query caching.
    Specific cache implementations should inherit from this class.

    Args:
        ModelT: Type of model being cached
    """

    @abstractmethod
    def get(self, key: str) -> Optional[List[ModelT]]:
        """Get cached results.

        Args:
            key: Cache key

        Returns:
            Cached results or None if not found
        """
        pass

    @abstractmethod
    def set(self, key: str, value: List[ModelT], ttl: Optional[int] = None) -> None:
        """Set cache value.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete cached value.

        Args:
            key: Cache key
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all cached values."""
        pass


class InMemoryCache(QueryCache[ModelT]):
    """In-memory query cache implementation.

    This class provides a simple in-memory cache using a dictionary.
    Cache entries expire after their TTL.
    """

    def __init__(self) -> None:
        """Initialize in-memory cache."""
        self._cache: Dict[str, tuple[bytes, Optional[datetime]]] = {}

    def get(self, key: str) -> Optional[List[ModelT]]:
        """Get cached results.

        Args:
            key: Cache key

        Returns:
            Cached results or None if not found/expired
        """
        if key not in self._cache:
            return None

        value, expires_at = self._cache[key]
        if expires_at and expires_at <= datetime.now():
            del self._cache[key]
            return None

        return cast(List[ModelT], pickle.loads(value))

    def set(self, key: str, value: List[ModelT], ttl: Optional[int] = None) -> None:
        """Set cache value.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        expires_at = None
        if ttl is not None:
            expires_at = datetime.now() + timedelta(seconds=ttl)

        # Pickle value to preserve type information
        pickled = pickle.dumps(value)
        self._cache[key] = (pickled, expires_at)

    def delete(self, key: str) -> None:
        """Delete cached value.

        Args:
            key: Cache key
        """
        self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()


class RedisCache(QueryCache[ModelT]):
    """Redis query cache implementation.

    This class provides a Redis-based cache implementation.
    It requires the redis-py package.

    Args:
        redis_url: Redis connection URL
        prefix: Key prefix for cache entries
    """

    def __init__(self, redis_url: str, prefix: str = "query_cache:") -> None:
        """Initialize Redis cache.

        Args:
            redis_url: Redis connection URL
            prefix: Key prefix for cache entries
        """
        try:
            from redis import Redis
        except ImportError as e:
            raise ImportError(
                "redis-py package is required for RedisCache. "
                "Install it with: pip install redis"
            ) from e

        self._redis = Redis.from_url(redis_url)  # type: ignore
        self._prefix = prefix

    def _make_key(self, key: str) -> str:
        """Make Redis key with prefix.

        Args:
            key: Original key

        Returns:
            Redis key with prefix
        """
        return f"{self._prefix}{key}"

    def get(self, key: str) -> Optional[List[ModelT]]:
        """Get cached results.

        Args:
            key: Cache key

        Returns:
            Cached results or None if not found
        """
        value = self._redis.get(self._make_key(key))  # type: ignore
        if value is None:
            return None

        # Unpickle value to restore type information
        return cast(List[ModelT], pickle.loads(value))  # type: ignore

    def set(self, key: str, value: List[ModelT], ttl: Optional[int] = None) -> None:
        """Set cache value.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        # Pickle value to preserve type information
        pickled = pickle.dumps(value)
        redis_key = self._make_key(key)

        if ttl is not None:
            self._redis.setex(redis_key, ttl, pickled)  # type: ignore
        else:
            self._redis.set(redis_key, pickled)  # type: ignore

    def delete(self, key: str) -> None:
        """Delete cached value.

        Args:
            key: Cache key
        """
        self._redis.delete(self._make_key(key))  # type: ignore

    def clear(self) -> None:
        """Clear all cached values."""
        pattern = f"{self._prefix}*"
        keys = self._redis.keys(pattern)  # type: ignore
        if keys:
            self._redis.delete(*keys)  # type: ignore
