"""Cache implementation for EarnORM."""

from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast

from motor.motor_asyncio import AsyncIOMotorClientSession

T = TypeVar("T")
CacheKey = Union[str, int, tuple[Any, ...]]
CacheValue = Union[Dict[str, Any], List[Any], str, int, float, bool, None]


class Cache:
    """Cache implementation."""

    def __init__(self) -> None:
        """Initialize cache."""
        self._cache: Dict[str, Dict[str, Any]] = {
            "value": {},  # Cached values
            "expire": {},  # Expiration timestamps
        }

    def get(self, key: CacheKey) -> Optional[CacheValue]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        cache_key = str(key)
        if cache_key not in self._cache["value"]:
            return None

        # Check expiration
        if cache_key in self._cache["expire"]:
            expire = self._cache["expire"][cache_key]
            if expire and expire < datetime.now():
                self.delete(key)
                return None

        return self._cache["value"][cache_key]

    def set(
        self,
        key: CacheKey,
        value: CacheValue,
        ttl: Optional[int] = None,
    ) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        cache_key = str(key)
        self._cache["value"][cache_key] = value

        if ttl:
            self._cache["expire"][cache_key] = datetime.now() + timedelta(seconds=ttl)

    def delete(self, key: CacheKey) -> None:
        """Delete value from cache.

        Args:
            key: Cache key
        """
        cache_key = str(key)
        self._cache["value"].pop(cache_key, None)
        self._cache["expire"].pop(cache_key, None)

    def clear(self) -> None:
        """Clear all cached values."""
        self._cache["value"].clear()
        self._cache["expire"].clear()


def cached(
    ttl: Optional[int] = None,
    key_pattern: Optional[str] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Cache decorator.

    Args:
        ttl: Time to live in seconds
        key_pattern: Cache key pattern with placeholders for args/kwargs

    Returns:
        Decorated function
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            # Generate cache key
            if key_pattern:
                # Replace placeholders in pattern
                cache_key = key_pattern.format(*args, **kwargs)
            else:
                # Default key: function_name:arg1:arg2:kwarg1=val1:...
                parts = [func.__name__]
                parts.extend(str(arg) for arg in args)
                parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(parts)

            # Skip caching for database sessions
            if any(isinstance(arg, AsyncIOMotorClientSession) for arg in args):
                return await func(*args, **kwargs)
            if any(
                isinstance(arg, AsyncIOMotorClientSession) for arg in kwargs.values()
            ):
                return await func(*args, **kwargs)

            # Check cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cast(T, cached_value)

            # Call function
            result = await func(*args, **kwargs)

            # Cache result
            cache.set(cache_key, result, ttl)
            return result

        return wrapper

    return decorator


# Global cache instance
cache = Cache()
