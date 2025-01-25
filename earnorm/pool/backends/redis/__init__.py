"""Redis backend implementation.

This module provides Redis connection pooling functionality for EarnORM.
It includes connection and pool implementations for Redis using the redis-py driver.

Example:
    >>> from earnorm.pool.backends.redis import RedisPool
    >>> pool = RedisPool(
    ...     host="localhost",
    ...     port=6379,
    ...     db=0,
    ...     min_size=5,
    ...     max_size=20
    ... )
    >>> await pool.init()
    >>> conn = await pool.acquire()
    >>> await conn.execute("set", "key", "value")
    True
    >>> await conn.execute("get", "key")
    "value"
    >>> await pool.release(conn)
    >>> await pool.close()
"""

from earnorm.pool.backends.redis.connection import RedisConnection
from earnorm.pool.backends.redis.pool import RedisPool

__all__ = [
    "RedisConnection",
    "RedisPool",
]
