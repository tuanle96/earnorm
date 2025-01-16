"""Redis cache backend implementation."""

from typing import Any, Dict, List, Tuple, Union, cast

from earnorm.cache.backends.base import CacheBackend
from earnorm.pool.backends.redis.pool import RedisPool
from earnorm.utils.json import dumps, loads


class RedisBackend(CacheBackend):
    """Redis cache backend implementation."""

    def __init__(self, pool: RedisPool) -> None:
        """Initialize Redis cache backend.

        Args:
            pool: Redis connection pool

        Examples:
            >>> pool = RedisPool(host="localhost", port=6379, db=0)
            >>> backend = RedisBackend(pool)
            >>> await backend.set("key", "value")
            True
            >>> await backend.get("key")
            "value"
            >>> await backend.delete("key")
            1
        """
        self._pool = pool

    @property
    def is_connected(self) -> bool:
        """Check if backend is connected.

        Returns:
            bool: True if backend is connected, False otherwise.
        """
        return self._pool.available > 0

    async def get(self, key: str) -> Any:
        """Get value by key.

        Args:
            key: Cache key

        Returns:
            Any: Cached value or None if not found
        """
        conn = await self._pool.acquire()
        try:
            value = await conn.execute("get", key)
            if value is not None:
                return loads(value)
            return None
        finally:
            await self._pool.release(conn)

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Union[int, None] = None,
    ) -> bool:
        """Set value by key.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds

        Returns:
            bool: True if value was set, False otherwise
        """
        conn = await self._pool.acquire()
        try:
            value = dumps(value)
            if ttl is not None:
                return cast(bool, await conn.execute("setex", key, ttl, value))
            return cast(bool, await conn.execute("set", key, value))
        finally:
            await self._pool.release(conn)

    async def delete(self, *keys: str) -> int:
        """Delete keys.

        Args:
            *keys: Cache keys to delete

        Returns:
            int: Number of keys deleted
        """
        if not keys:
            return 0

        conn = await self._pool.acquire()
        try:
            return cast(int, await conn.execute("del", *keys))
        finally:
            await self._pool.release(conn)

    async def exists(self, key: str) -> bool:
        """Check if key exists.

        Args:
            key: Cache key

        Returns:
            bool: True if key exists, False otherwise
        """
        conn = await self._pool.acquire()
        try:
            return cast(bool, await conn.execute("exists", key))
        finally:
            await self._pool.release(conn)

    async def clear(self) -> bool:
        """Clear all keys.

        Returns:
            bool: True if all keys were cleared, False otherwise
        """
        conn = await self._pool.acquire()
        try:
            await conn.execute("flushdb")
            return True
        finally:
            await self._pool.release(conn)

    async def scan(self, pattern: str) -> List[str]:
        """Scan keys by pattern.

        Args:
            pattern: Key pattern to match

        Returns:
            List[str]: List of matching keys
        """
        conn = await self._pool.acquire()
        try:
            cursor = "0"
            keys: List[str] = []
            while True:
                cursor, chunk = cast(
                    Tuple[str, List[str]],
                    await conn.execute("scan", cursor, "match", pattern),
                )
                keys.extend(chunk)
                if cursor == "0":
                    break
            return keys
        finally:
            await self._pool.release(conn)

    async def info(self) -> Dict[str, str]:
        """Get backend info.

        Returns:
            Dict[str, str]: Backend information
        """
        conn = await self._pool.acquire()
        try:
            info = await conn.execute("info")
            return {
                "type": "redis",
                "version": info.get("redis_version", "unknown"),
                "used_memory": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", "unknown"),
                "uptime_in_seconds": info.get("uptime_in_seconds", "unknown"),
            }
        finally:
            await self._pool.release(conn)
