"""Pool registry implementation.

This module provides a registry for managing database connection pool implementations.
It supports registration and retrieval of pool classes.

Examples:
    ```python
    # Register custom pool
    PoolRegistry.register("custom", CustomPool)

    # Get pool class
    pool_class = PoolRegistry.get("mongodb")
    pool = pool_class(uri="mongodb://localhost:27017")
    ```
"""

from typing import Any, Dict, Type, TypeVar

from earnorm.pool.backends.mongo.pool import MongoPool
from earnorm.pool.backends.mysql.pool import MySQLPool
from earnorm.pool.backends.postgres.pool import PostgresPool
from earnorm.pool.backends.redis.pool import RedisPool
from earnorm.pool.protocols.pool import PoolProtocol

# Define type variables for database and collection types
DB = TypeVar("DB")
COLL = TypeVar("COLL")


class PoolRegistry:
    """Pool registry for managing pool implementations."""

    _pools: Dict[str, Type[PoolProtocol[Any, Any]]] = {
        "mongodb": MongoPool,
        "redis": RedisPool,
        "mysql": MySQLPool,
        "postgres": PostgresPool,
    }

    @classmethod
    def register(cls, name: str, pool_class: Type[PoolProtocol[DB, COLL]]) -> None:
        """Register pool implementation.

        Args:
            name: Pool name
            pool_class: Pool class

        Examples:
            ```python
            # Register custom pool
            PoolRegistry.register("custom", CustomPool)
            ```
        """
        cls._pools[name] = pool_class  # type: ignore

    @classmethod
    def get(cls, name: str) -> Type[PoolProtocol[Any, Any]]:
        """Get pool class by name.

        Args:
            name: Pool name

        Returns:
            Pool class

        Raises:
            ValueError: If pool name is unknown

        Examples:
            ```python
            # Get MongoDB pool class
            pool_class = PoolRegistry.get("mongodb")
            pool = pool_class(uri="mongodb://localhost:27017")
            ```
        """
        if name not in cls._pools:
            raise ValueError(f"Unknown pool: {name}")

        return cls._pools[name]

    @classmethod
    def list(cls) -> Dict[str, Type[PoolProtocol[Any, Any]]]:
        """Get all registered pools.

        Returns:
            Dictionary of pool names and classes

        Examples:
            ```python
            # List all pools
            pools = PoolRegistry.list()
            for name, pool_class in pools.items():
                print(f"{name}: {pool_class.__name__}")
            ```
        """
        return cls._pools.copy()
