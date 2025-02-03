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

import logging
from typing import Any, Dict, TypeVar

from earnorm.exceptions import PoolError
from earnorm.pool.protocols.connection import AsyncConnectionProtocol
from earnorm.pool.protocols.pool import AsyncPoolProtocol

logger = logging.getLogger(__name__)

# Define type variables for database and collection types
DB = TypeVar("DB")
COLL = TypeVar("COLL")


class PoolNotFoundError(PoolError):
    """Raised when pool is not found in registry."""

    def __init__(self, message: str) -> None:
        """Initialize error.

        Args:
            message: Error message
        """
        super().__init__(message, backend="unknown")


class PoolRegistry:
    """Pool registry for managing pool instances."""

    _pools: Dict[str, AsyncPoolProtocol[Any, Any]] = {}

    @classmethod
    def register(cls, name: str, pool: AsyncPoolProtocol[Any, Any]) -> None:
        """Register pool instance.

        Args:
            name: Pool name
            pool: Pool instance

        Raises:
            ValueError: If name is empty
            TypeError: If pool is not an AsyncPoolProtocol instance
        """
        if not name:
            raise ValueError("Pool name cannot be empty")

        # Check if pool implements required protocol methods
        required_methods = ["acquire", "release", "init", "close"]
        missing_methods = [
            method for method in required_methods if not hasattr(pool, method)
        ]

        if missing_methods:
            raise TypeError(
                f"Pool must implement AsyncPoolProtocol. Missing methods: {', '.join(missing_methods)}"
            )

        logger.debug("Registering pool: %s", name)
        cls._pools[name] = pool
        logger.info("Successfully registered pool: %s", name)

    @classmethod
    def get(cls, name: str) -> AsyncPoolProtocol[Any, Any]:
        """Get pool instance by name.

        This is a synchronous operation that returns the pool instance directly.
        The pool itself may have async operations, but getting it from registry is sync.

        Args:
            name: Pool name

        Returns:
            Pool instance

        Raises:
            ValueError: If name is empty
            PoolNotFoundError: If pool is not found
        """
        if not name:
            logger.error("Pool name cannot be empty")
            raise ValueError("Pool name cannot be empty")

        logger.debug("Getting pool: %s", name)
        if name not in cls._pools:
            logger.error("Pool not found: %s", name)
            raise PoolNotFoundError(f"Pool {name} not found")

        logger.debug("Found pool: %s", name)
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
        logger.debug("Listing all pools")
        return cls._pools.copy()

    @classmethod
    async def validate_connection(cls, conn: AsyncConnectionProtocol[Any, Any]) -> bool:
        """Check connection validity.

        Args:
            conn: Connection to validate

        Returns:
            bool: True if connection is valid, False otherwise
        """
        try:
            logger.debug("Validating connection")
            is_valid = bool(await conn.ping())
            logger.debug("Connection validation result: %s", is_valid)
            return is_valid
        except Exception as e:
            logger.error("Connection validation failed: %s", str(e))
            return False
