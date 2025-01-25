"""Protocol definitions for connection pooling.

This module provides protocol definitions for connection pooling,
including connection, database, operations, and pool protocols.
"""

from .connection import AsyncConnectionProtocol, AsyncLifecycle, AsyncOperations
from .database import AsyncDatabaseProtocol, DatabaseAware
from .operations import MongoOperation, RedisOperation
from .pool import AsyncPoolProtocol

__all__ = [
    "AsyncConnectionProtocol",
    "AsyncLifecycle",
    "AsyncOperations",
    "AsyncDatabaseProtocol",
    "DatabaseAware",
    "MongoOperation",
    "RedisOperation",
    "AsyncPoolProtocol",
]
