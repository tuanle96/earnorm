"""Core connection pooling implementations.

This module provides base implementations for connection pooling in EarnORM.
It includes base classes for connections and pools that can be extended by
specific database backend implementations.

Example:
    >>> from earnorm.pool.core import BasePool, BaseConnection
    >>> from typing import Any
    >>>
    >>> class MyConnection(BaseConnection):
    ...     async def ping(self) -> bool:
    ...         return True
    ...
    ...     async def execute(self, operation: str, *args: Any, **kwargs: Any) -> Any:
    ...         return {"result": "success"}
    >>>
    >>> class MyPool(BasePool[MyConnection]):
    ...     async def _create_connection(self) -> MyConnection:
    ...         return MyConnection()
    ...
    ...     async def _validate_connection(self, conn: MyConnection) -> bool:
    ...         return await conn.ping()
    >>>
    >>> pool = MyPool(backend_type="custom")
    >>> await pool.init()
    >>> conn = await pool.acquire()
    >>> await conn.execute("test")
    {"result": "success"}
    >>> await pool.release(conn)
    >>> await pool.close()
"""

from earnorm.pool.core.connection import BaseConnection
from earnorm.pool.core.pool import BasePool

__all__ = [
    "BasePool",
    "BaseConnection",
]
