"""Pool manager implementation."""

import logging
from typing import Any, Dict, Optional, Type, TypeVar

from earnorm.pool.protocols.connection import ConnectionProtocol
from earnorm.pool.protocols.pool import PoolProtocol

logger = logging.getLogger(__name__)

C = TypeVar("C", bound=ConnectionProtocol)
P = TypeVar("P", bound=PoolProtocol[Any])


class PoolManager:
    """Pool manager implementation."""

    def __init__(self) -> None:
        """Initialize pool manager."""
        self._pools: Dict[str, PoolProtocol[Any]] = {}
        self._pool_types: Dict[str, Type[PoolProtocol[Any]]] = {}

    def register_pool_type(self, backend_type: str, pool_type: Type[P]) -> None:
        """Register pool type.

        Args:
            backend_type: Backend type identifier
            pool_type: Pool type class

        Examples:
            >>> from earnorm.pool.backends.mongo.pool import MongoPool
            >>> manager = PoolManager()
            >>> manager.register_pool_type("mongodb", MongoPool)
            >>> pool = await manager.create_pool(
            ...     "mongodb",
            ...     uri="mongodb://localhost:27017",
            ...     database="test"
            ... )
            >>> await pool.init()
            >>> conn = await pool.acquire()
            >>> await conn.execute("find_one", "users", {"name": "John"})
            {"_id": "...", "name": "John", "age": 30}
            >>> await pool.release(conn)
            >>> await pool.close()
        """
        self._pool_types[backend_type] = pool_type

    async def create_pool(
        self, backend_type: str, pool_name: Optional[str] = None, **config: Any
    ) -> PoolProtocol[Any]:
        """Create pool instance.

        Args:
            backend_type: Backend type identifier
            pool_name: Pool name (optional)
            **config: Pool configuration

        Returns:
            Pool instance

        Raises:
            ValueError: If backend type is not registered
        """
        if backend_type not in self._pool_types:
            raise ValueError(f"Unknown backend type: {backend_type}")

        pool_type = self._pool_types[backend_type]
        pool = pool_type(**config)

        if pool_name:
            if pool_name in self._pools:
                raise ValueError(f"Pool already exists: {pool_name}")
            self._pools[pool_name] = pool

        return pool

    def get_pool(self, pool_name: str) -> Optional[PoolProtocol[Any]]:
        """Get pool by name.

        Args:
            pool_name: Pool name

        Returns:
            Pool instance or None if not found
        """
        return self._pools.get(pool_name)

    async def close_all(self) -> None:
        """Close all pools."""
        for pool in self._pools.values():
            await pool.close()
        self._pools.clear()
