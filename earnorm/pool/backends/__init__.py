"""Database backend implementations.

This module provides database backend implementations for EarnORM connection pooling.
Currently supported backends:
- MongoDB (using Motor driver)
- Redis (using redis-py driver)
- PostgreSQL (coming soon)

Example:
    >>> from earnorm.pool.backends.mongo import MongoPool
    >>> pool = MongoPool(
    ...     uri="mongodb://localhost:27017",
    ...     database="test",
    ...     min_size=5,
    ...     max_size=20
    ... )
    >>> await pool.init()
    >>> conn = await pool.acquire()
    >>> await conn.execute("find_one", "users", {"name": "John"})
    {"_id": "...", "name": "John", "age": 30}
    >>> await pool.release(conn)
    >>> await pool.close()

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

from earnorm.pool.backends.mongo.connection import MongoConnection
from earnorm.pool.backends.mongo.pool import MongoPool
from earnorm.pool.backends.redis.connection import RedisConnection
from earnorm.pool.backends.redis.pool import RedisPool

__all__ = [
    # MongoDB
    "MongoPool",
    "MongoConnection",
    # Redis
    "RedisPool",
    "RedisConnection",
]
