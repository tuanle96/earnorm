"""Base class for all database adapters.

This module defines the low-level interface for database operations.
It provides core CRUD operations without any ORM-specific logic.

Examples:
    >>> from earnorm.base.database import DatabaseAdapter
    >>> class CustomAdapter(DatabaseAdapter):
    ...     async def create(self, store: str, values: dict):
    ...         # Implement raw create logic
    ...         pass
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union, cast

from earnorm.pool.protocols import AsyncPoolProtocol
from earnorm.pool.protocols.pool import AsyncConnectionProtocol

# Type variables for database and collection
DBType = TypeVar("DBType", bound=AsyncConnectionProtocol[Any, Any])
CollType = TypeVar("CollType")

logger = logging.getLogger(__name__)


class DatabaseAdapter(ABC, Generic[DBType, CollType]):
    """Base class for all database adapters.

    This class defines the low-level interface that all database-specific adapters
    must implement. It provides methods for basic CRUD operations without any
    ORM-specific logic.

    The term "store" is used as a generic term for:
    - Collections in MongoDB
    - Tables in SQL databases
    - Other storage structures in different databases

    Type Parameters:
        DBType: Database connection type (must implement AsyncConnectionProtocol)
        CollType: Collection/Table type

    Attributes:
        pool: Connection pool instance
        logger: Logger instance for this class
    """

    def __init__(
        self, pool: AsyncPoolProtocol[DBType, CollType], *, env: Optional[Any] = None
    ) -> None:
        """Initialize database adapter.

        Args:
            pool: Connection pool instance
            env: Optional environment instance
        """
        self._env = env
        self._pool = pool
        self.logger = logging.getLogger(self.__class__.__name__)

    @property
    def env(self) -> Any:
        """Get environment instance."""
        return self._env

    @env.setter
    def env(self, value: Any) -> None:
        """Set environment instance."""
        self._env = value

    @property
    def pool(self) -> AsyncPoolProtocol[DBType, CollType]:
        """Get connection pool.

        Returns:
            AsyncPoolProtocol: Connection pool instance

        Raises:
            RuntimeError: If pool is not initialized
        """
        if not self._pool:
            raise RuntimeError("Pool not initialized")
        return self._pool

    async def init(self) -> None:
        """Initialize adapter.

        This method:
        1. Initializes pool if not already initialized
        2. Sets up any adapter-specific initialization

        Raises:
            RuntimeError: If pool initialization fails
        """
        await self._init_adapter()

    @abstractmethod
    async def _init_adapter(self) -> None:
        """Initialize adapter-specific functionality.

        This method should be implemented by subclasses to handle any
        adapter-specific initialization after the pool is set up.
        """
        pass

    async def close(self) -> None:
        """Close adapter and connection pool."""
        if self._pool:
            await self._pool.close()
        self._pool = None

    async def get_connection(self) -> DBType:
        """Get database connection from pool.

        Returns:
            DBType: Database connection

        Raises:
            RuntimeError: If pool is not initialized
        """
        conn = await self.pool.acquire()
        return cast(DBType, conn)

    @abstractmethod
    async def create(
        self,
        store: str,
        values: Union[Dict[str, Any], List[Dict[str, Any]]],
    ) -> Union[str, List[str]]:
        """Create record(s) in database.

        Args:
            store: Store name (collection in MongoDB, table in SQL)
            values: Values to create

        Returns:
            Created record ID(s)
        """
        pass

    @abstractmethod
    async def read(
        self,
        store: str,
        id_or_ids: Union[str, List[str]],
        fields: Optional[List[str]] = None,
    ) -> Union[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        """Read record(s) from database.

        Args:
            store: Store name (collection in MongoDB, table in SQL)
            id_or_ids: Record ID(s)
            fields: Fields to read

        Returns:
            Record data
        """
        pass

    @abstractmethod
    async def update(
        self,
        store: str,
        ids: List[str],
        values: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Update record(s) in database.

        Args:
            store: Store name (collection in MongoDB, table in SQL)
            ids: List of record IDs to update
            values: Values to update

        Returns:
            Number of updated records
        """
        pass

    @abstractmethod
    async def delete(
        self,
        store: str,
        ids: List[str],
    ) -> Optional[int]:
        """Delete record(s) from database.

        Args:
            store: Store name (collection in MongoDB, table in SQL)
            ids: List of record IDs to delete

        Returns:
            Number of deleted records
        """
        pass

    @property
    @abstractmethod
    def backend_type(self) -> str:
        """Get database backend type."""
        pass

    @abstractmethod
    async def create_store(self, name: str) -> None:
        """Create a new store.

        Args:
            name: Store name (collection in MongoDB, table in SQL)
        """
        pass

    @abstractmethod
    async def drop_store(self, name: str) -> None:
        """Drop a store.

        Args:
            name: Store name (collection in MongoDB, table in SQL)
        """
        pass

    @abstractmethod
    async def store_exists(self, name: str) -> bool:
        """Check if store exists.

        Args:
            name: Store name (collection in MongoDB, table in SQL)

        Returns:
            True if exists, False otherwise
        """
        pass

    @abstractmethod
    async def search(
        self,
        store: str,
        filter: Optional[Dict[str, Any]] = None,
        fields: Optional[List[str]] = None,
        offset: int = 0,
        limit: Optional[int] = None,
        order: Optional[str] = None,
    ) -> List[str]:
        """Search records with filter conditions.

        Args:
            store: Store name (collection/table)
            filter: Query conditions
            fields: Fields to return (projection)
            offset: Number of records to skip
            limit: Max number of records to return
            order: Sort order (field_name asc/desc)

        Returns:
            List of record IDs

        Examples:
            >>> # Find users age > 20, get name and email
            >>> await adapter.search(
            ...     store="users",
            ...     filter={"age": {"$gt": 20}},
            ...     fields=["_id"],
            ...     limit=10
            ... )
        """
        pass
