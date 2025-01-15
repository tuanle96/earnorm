"""
Cache decorator implementation for EarnORM.
"""

import functools
import hashlib
import inspect
import json
from typing import Any, Callable, Coroutine, Optional, TypeVar, Union, cast, overload

from earnorm.cache.core.manager import CacheManager

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Coroutine[Any, Any, Any]])


def _make_cached_decorator(
    ttl: Optional[int] = None,
    key_prefix: Optional[str] = None,
    manager: Optional[CacheManager] = None,
) -> Callable[[F], F]:
    """Creates the actual decorator function."""

    def decorator(func: F) -> F:
        if not inspect.iscoroutinefunction(func):
            raise TypeError("Cached decorator can only be used with async functions")

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get cache manager instance
            cache_manager = manager
            if cache_manager is None:
                from earnorm import di

                cache_manager = di.get("cache_manager")

            if (
                not cache_manager
                or not cache_manager.enabled
                or not cache_manager.connected
            ):
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
            cached_value = await cache_manager.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Call function and cache result
            result = await func(*args, **kwargs)

            try:
                # Verify result is JSON serializable
                json.dumps(result)
                await cache_manager.set(cache_key, result, ttl)
            except (TypeError, ValueError):
                pass  # Skip caching if result can't be serialized

            return result

        return cast(F, wrapper)

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
    """
    Decorator for caching method results.

    Args:
        ttl (Optional[int]): TTL for cached results in seconds. Defaults to manager's TTL.
        key_prefix (Optional[str]): Prefix for cache keys. Defaults to "{module}.{class}.{method}".
        manager (Optional[CacheManager]): Cache manager to use. Defaults to global instance.

    Returns:
        Callable: Decorated method that uses caching

    Example:
        ```python
        class User(models.BaseModel):
            name = fields.String(required=True)
            email = fields.Email(required=True)

            @cached(ttl=300)  # Cache for 5 minutes
            async def get_profile(self):
                return {
                    "name": self.name,
                    "email": self.email
                }
        ```
    """
    if func is not None:
        return _make_cached_decorator()(func)
    return _make_cached_decorator(ttl, key_prefix, manager)
