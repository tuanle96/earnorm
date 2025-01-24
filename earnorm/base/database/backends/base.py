"""Database backend base classes.

This module provides the base classes and interfaces for database operations.
It defines the contract that all database backends must implement.

Examples:
    ```python
    from earnorm.base.database.backends.base import DatabaseBackend

    class PostgresBackend(DatabaseBackend):
        async def connect(self):
            return await create_postgres_pool()
    ```
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncContextManager, Dict, Generic, List, TypeVar

from earnorm.di.lifecycle import LifecycleAware

T = TypeVar("T")
QueryResult = TypeVar("QueryResult")


class DatabaseBackend(ABC, Generic[QueryResult], LifecycleAware):
    """Abstract database backend.

    This class defines the interface that all database backends must implement.
    It provides methods for connection management, query execution, and transactions.

    Examples:
        ```python
        class MongoBackend(DatabaseBackend[Dict[str, Any]]):
            async def connect(self):
                return await create_mongo_pool()

            async def execute(self, query):
                return await self.collection.find(query)
        ```
    """

    def __init__(self) -> None:
        """Initialize backend."""
        self._id: str = ""
        self._data: Dict[str, Any] = {}

    @property
    def id(self) -> str:
        """Get backend ID."""
        return self._id

    @property
    def data(self) -> Dict[str, Any]:
        """Get backend data."""
        return self._data

    async def init(self) -> None:
        """Initialize backend."""
        await self.connect()

    async def destroy(self) -> None:
        """Destroy backend."""
        await self.close()

    @abstractmethod
    async def connect(self) -> AsyncContextManager[Any]:
        """Get database connection.

        Returns:
            Database connection context manager

        Examples:
            ```python
            async with backend.connect() as conn:
                await conn.execute(query)
            ```
        """
        pass

    @abstractmethod
    async def execute(self, query: Any) -> QueryResult:
        """Execute database query.

        Args:
            query: Query to execute

        Returns:
            Query results

        Examples:
            ```python
            results = await backend.execute(query)
            ```
        """
        pass

    @abstractmethod
    async def execute_many(self, queries: List[Any]) -> List[QueryResult]:
        """Execute multiple queries.

        Args:
            queries: Queries to execute

        Returns:
            Query results

        Examples:
            ```python
            results = await backend.execute_many(queries)
            ```
        """
        pass

    @abstractmethod
    async def transaction(self) -> AsyncContextManager[Any]:
        """Get transaction context.

        Returns:
            Transaction context manager

        Examples:
            ```python
            async with backend.transaction() as tx:
                await tx.execute(query1)
                await tx.execute(query2)
            ```
        """
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check database health.

        Returns:
            Health check results containing:
            - status: "healthy" or "unhealthy"
            - details: Additional health check information
            - latency: Connection latency in milliseconds
            - pool_stats: Connection pool statistics
            - error: Error message if unhealthy

        Examples:
            ```python
            health = await backend.health_check()
            print(health)
            {
                "status": "healthy",
                "details": {
                    "version": "5.0.0",
                    "uptime": 3600,
                },
                "latency": 5.2,
                "pool_stats": {
                    "total": 10,
                    "idle": 8,
                    "active": 2,
                },
                "error": None
            }
            ```
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close database connection.

        This method should clean up any resources used by the backend,
        including closing all connections in the pool.

        Examples:
            ```python
            await backend.close()
            ```
        """
        pass

    @abstractmethod
    async def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics.

        Returns:
            Pool statistics containing:
            - total: Total number of connections
            - idle: Number of idle connections
            - active: Number of active connections
            - min_size: Minimum pool size
            - max_size: Maximum pool size
            - wait_count: Number of waiters for connections
            - max_wait_time: Maximum wait time in seconds

        Examples:
            ```python
            stats = await backend.get_pool_stats()
            print(stats)
            {
                "total": 10,
                "idle": 8,
                "active": 2,
                "min_size": 5,
                "max_size": 20,
                "wait_count": 0,
                "max_wait_time": 30.0
            }
            ```
        """
        pass
