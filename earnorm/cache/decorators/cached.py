"""Cache decorator implementation."""

import functools
import hashlib
import inspect
import json
import logging
from typing import Any, Callable, Coroutine, Optional, TypeVar, Union, overload

from earnorm.cache.core.exceptions import CacheError
from earnorm.cache.core.manager import CacheManager
from earnorm.di import container

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Coroutine[Any, Any, Any]])


def _make_cached_decorator(
    ttl: Optional[int] = None,
    key_prefix: Optional[str] = None,
    manager: Optional[CacheManager] = None,
) -> Callable[[F], F]:
    """Creates the actual decorator function.

    Args:
        ttl: TTL for cached results in seconds
        key_prefix: Prefix for cache keys
        manager: Cache manager to use

    Returns:
        Callable: Decorator function
    """

    def decorator(func: F) -> F:
        if not inspect.iscoroutinefunction(func):
            raise TypeError("Cached decorator can only be used with async functions")

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get cache manager instance
            cache_manager = manager
            if cache_manager is None:
                try:
                    cache_manager = await container.get("cache_manager")
                except Exception as e:
                    # Log error but continue without caching
                    logger.warning("Failed to get cache manager: %s", e)
                    return await func(*args, **kwargs)

            if not cache_manager or not cache_manager.is_connected:
                return await func(*args, **kwargs)

            # Generate cache key
            if key_prefix:
                prefix = key_prefix
            else:
                # Get class and method names
                if args and hasattr(args[0], "__class__"):
                    cls = args[0].__class__
                    prefix = f"{cls.__module__}.{cls.__name__}.{func.__name__}"
                else:
                    prefix = f"{func.__module__}.{func.__name__}"

            # Hash arguments to create unique key
            arg_key = hashlib.sha256()

            # Add positional args
            for arg in args[1:]:  # Skip self
                arg_key.update(str(arg).encode())

            # Add keyword args (sorted for consistency)
            for key, value in sorted(kwargs.items()):
                arg_key.update(f"{key}:{value}".encode())

            cache_key = f"{prefix}:{arg_key.hexdigest()}"

            # Try to get from cache
            try:
                cached_value = await cache_manager.get(cache_key)
                if cached_value is not None:
                    return cached_value
            except CacheError as e:
                # Log error but continue without caching
                logger.warning("Failed to get cached value: %s", e)
                return await func(*args, **kwargs)

            # Call function and cache result
            result = await func(*args, **kwargs)

            try:
                # Verify result is JSON serializable
                json.dumps(result)
                await cache_manager.set(cache_key, result, ttl)
            except (TypeError, ValueError, CacheError) as e:
                # Log error but continue without caching
                logger.warning("Failed to cache result: %s", e)

            return result

        return wrapper  # type: ignore

    return decorator


@overload
def cached(func: F) -> F: ...


@overload
def cached(
    *,
    ttl: Optional[int] = None,
    key_prefix: Optional[str] = None,
    manager: Optional[CacheManager] = None,
) -> Callable[[F], F]: ...


def cached(
    func: Optional[F] = None,
    *,
    ttl: Optional[int] = None,
    key_prefix: Optional[str] = None,
    manager: Optional[CacheManager] = None,
) -> Union[F, Callable[[F], F]]:
    """Cache decorator for async functions.

    This decorator caches the results of async functions using the configured
    cache backend. It supports:
    - TTL configuration
    - Custom key prefixes
    - Custom cache managers
    - Automatic key generation from arguments
    - JSON serialization of results

    Args:
        func: Function to decorate
        ttl: TTL for cached results in seconds
        key_prefix: Prefix for cache keys
        manager: Cache manager to use

    Returns:
        Decorated function

    Examples:
        ```python
        # Basic usage
        @cached
        async def get_user(user_id: int) -> Dict[str, Any]:
            return await db.fetch_user(user_id)

        # With TTL
        @cached(ttl=300)
        async def get_stats() -> Dict[str, int]:
            return await calculate_stats()

        # With custom key prefix
        @cached(key_prefix="user")
        async def get_user_by_email(email: str) -> Dict[str, Any]:
            return await db.fetch_user_by_email(email)

        # With custom cache manager
        @cached(manager=redis_cache)
        async def get_config() -> Dict[str, Any]:
            return await load_config()
        ```

    Raises:
        TypeError: If decorated function is not async
        CacheError: If cache operation fails
    """
    if func is not None:
        return _make_cached_decorator()(func)
    return _make_cached_decorator(
        ttl=ttl,
        key_prefix=key_prefix,
        manager=manager,
    )
