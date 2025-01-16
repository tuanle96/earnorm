"""MongoDB backend implementation.

This module provides MongoDB connection pooling functionality for EarnORM.
It includes connection and pool implementations for MongoDB using the Motor driver.

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
"""

from earnorm.pool.backends.mongo.connection import MongoConnection
from earnorm.pool.backends.mongo.pool import MongoPool

__all__ = [
    "MongoPool",
    "MongoConnection",
]
