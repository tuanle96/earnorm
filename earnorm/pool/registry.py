"""Pool registry implementation.

This module provides a registry for managing database connection pool instances.
It supports registration and retrieval of pool instances.

Examples:
    ```python
    # Register pool instance
    pool = CustomPool(uri="custom://localhost")
    PoolRegistry.register("custom", pool)

    # Get pool instance
    pool = PoolRegistry.get("mongodb")
    ```
"""

from typing import Any, Dict, TypeVar

from earnorm.pool.protocols.connection import AsyncConnectionProtocol
from earnorm.pool.protocols.pool import AsyncPoolProtocol

# Define type variables for database and collection types
DB = TypeVar("DB")
COLL = TypeVar("COLL")


class PoolRegistry:
    """Pool registry for managing pool instances."""

    _pools: Dict[str, AsyncPoolProtocol[Any, Any]] = {}

    @classmethod
    def register(cls, name: str, pool: AsyncPoolProtocol[Any, Any]) -> None:
        """Register pool instance.

        Args:
            name: Pool name
            pool: Pool instance

        Examples:
            ```python
            # Register pool instance
            pool = CustomPool(uri="custom://localhost")
            PoolRegistry.register("custom", pool)
            ```
        """
        cls._pools[name] = pool

    @classmethod
    def get(cls, name: str) -> AsyncPoolProtocol[Any, Any]:
        """Get pool instance by name.

        Args:
            name: Pool name

        Returns:
            Pool instance

        Raises:
            ValueError: If pool name is unknown

        Examples:
            ```python
            # Get MongoDB pool instance
            pool = PoolRegistry.get("mongodb")
            ```
        """
        if name not in cls._pools:
            raise ValueError(f"Unknown pool: {name}")

        return cls._pools[name]

    @classmethod
    def list(cls) -> Dict[str, AsyncPoolProtocol[Any, Any]]:
        """Get all registered pools.

        Returns:
            Dictionary of pool names and instances

        Examples:
            ```python
            # List all pools
            pools = PoolRegistry.list()
            for name, pool in pools.items():
                print(f"{name}: {pool}")
            ```
        """
        return cls._pools.copy()

    @classmethod
    async def validate_connection(cls, conn: AsyncConnectionProtocol[Any, Any]) -> bool:
        """Check connection validity"""
        try:
            return bool(await conn.ping())
        except Exception:
            return False
