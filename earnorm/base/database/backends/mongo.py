"""MongoDB backend implementation.

This module provides MongoDB backend implementation for EarnORM.
It implements DatabaseBackend interface for MongoDB.

Examples:
    ```python
    from earnorm.base.database.backends.mongo import MongoBackend

    backend = MongoBackend(
        uri="mongodb://localhost:27017",
        database="test"
    )
    await backend.connect()

    # Execute query
    query = MongoQuery("users", filter={"name": "test"})
    result = await backend.execute(query)
    ```
"""

import contextlib
import time
from typing import Any, AsyncContextManager, AsyncGenerator, Dict, List, Optional, cast

from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)

from earnorm.base.database.backends.base import DatabaseBackend
from earnorm.base.database.query.backends.mongo import MongoQuery
from earnorm.pool.backends.mongo import MongoPool

Document = Dict[str, Any]
DBType = AsyncIOMotorDatabase[Document]
CollType = AsyncIOMotorCollection[Document]


class MongoBackend(DatabaseBackend[Document]):
    """MongoDB backend implementation.

    This class implements DatabaseBackend interface for MongoDB.

    Examples:
        ```python
        backend = MongoBackend(
            uri="mongodb://localhost:27017",
            database="test",
            min_pool_size=5,
            max_pool_size=20
        )
        await backend.connect()
        ```
    """

    def __init__(
        self,
        uri: str,
        database: str,
        min_pool_size: int = 5,
        max_pool_size: int = 20,
        max_idle_time: int = 300,
        connection_timeout: float = 30.0,
        **options: Any,
    ) -> None:
        """Initialize backend.

        Args:
            uri: MongoDB connection URI
            database: Database name
            min_pool_size: Minimum pool size
            max_pool_size: Maximum pool size
            max_idle_time: Maximum idle time in seconds
            connection_timeout: Connection timeout in seconds
            **options: Additional MongoDB options
        """
        super().__init__()
        self._uri = uri
        self._database = database
        self._min_pool_size = min_pool_size
        self._max_pool_size = max_pool_size
        self._max_idle_time = max_idle_time
        self._connection_timeout = connection_timeout
        self._options = options
        self._pool: Optional[MongoPool[DBType, CollType]] = None

    async def connect(self) -> AsyncContextManager[AsyncIOMotorClient[Document]]:
        """Connect to MongoDB.

        Returns:
            MongoDB client

        Examples:
            ```python
            async with await backend.connect() as client:
                db = client[database_name]
                await db.command("ping")
            ```
        """
        if self._pool is None:
            self._pool = MongoPool[DBType, CollType](
                uri=self._uri,
                database=self._database,
                min_size=self._min_pool_size,
                max_size=self._max_pool_size,
                max_idle_time=self._max_idle_time,
                **self._options,
            )
            await self._pool.init()

        @contextlib.asynccontextmanager
        async def _connect() -> AsyncGenerator[AsyncIOMotorClient[Document], None]:
            if not self._pool:
                raise RuntimeError("Pool not initialized")
            conn = await (await self._pool.acquire())
            client = cast(AsyncIOMotorClient[Document], conn)
            try:
                yield client
            finally:
                await (await self._pool.release(conn))

        return _connect()

    async def execute(self, query: MongoQuery[Document]) -> Document:
        """Execute MongoDB query.

        Args:
            query: MongoDB query

        Returns:
            Query results

        Examples:
            ```python
            query = MongoQuery("users", filter={"name": "test"})
            result = await backend.execute(query)
            ```
        """
        async with await self.connect() as client:
            collection = self._get_collection(client, query.collection)
            cursor = collection.find(
                filter=query.filter,
                projection=query.projection,
                skip=query.skip,
                limit=query.limit,
                sort=query.sort,
                allow_disk_use=query.allow_disk_use,
            )
            docs = [doc async for doc in cursor]
            return {"results": docs}

    async def execute_many(self, queries: List[MongoQuery[Document]]) -> List[Document]:
        """Execute multiple MongoDB queries.

        Args:
            queries: MongoDB queries

        Returns:
            Query results

        Examples:
            ```python
            queries = [
                MongoQuery("users", filter={"name": "test1"}),
                MongoQuery("users", filter={"name": "test2"})
            ]
            results = await backend.execute_many(queries)
            ```
        """
        async with await self.connect() as client:
            results: List[Document] = []
            for query in queries:
                collection = self._get_collection(client, query.collection)
                cursor = collection.find(
                    filter=query.filter,
                    projection=query.projection,
                    skip=query.skip,
                    limit=query.limit,
                    sort=query.sort,
                    allow_disk_use=query.allow_disk_use,
                )
                docs = [doc async for doc in cursor]
                results.append({"results": docs})
            return results

    def _get_collection(
        self, client: AsyncIOMotorClient[Document], name: str
    ) -> AsyncIOMotorCollection[Document]:
        """Get MongoDB collection.

        Args:
            client: MongoDB client
            name: Collection name

        Returns:
            MongoDB collection
        """
        db = client[self._database]
        return db[name]

    async def health_check(self) -> Dict[str, Any]:
        """Check MongoDB health.

        This method implements DatabaseBackend.health_check().
        It performs a full health check including:
        - MongoDB server ping
        - Connection latency measurement
        - Pool health verification

        Returns:
            Health check result containing:
            - status: "healthy" or "unhealthy"
            - details: Additional health check information
            - latency: Connection latency in milliseconds
            - error: Error message if unhealthy
            - pool_health: Pool health check result

        Examples:
            ```python
            health = await backend.health_check()
            print(health)
            {
                "status": "healthy",
                "details": {"ok": 1.0},
                "latency": 5.2,
                "error": None,
                "pool_health": True
            }
            ```
        """
        try:
            start = time.monotonic()
            async with await self.connect() as client:
                result = await client.admin.command("ping")
                latency = (time.monotonic() - start) * 1000

                # Check pool health
                pool_health = (
                    await (await self._pool.health_check()) if self._pool else False
                )

                return {
                    "status": "healthy",
                    "details": result,
                    "latency": latency,
                    "error": None,
                    "pool_health": pool_health,
                }

        except Exception as e:
            return {
                "status": "unhealthy",
                "details": None,
                "latency": None,
                "error": str(e),
                "pool_health": False,
            }

    async def close(self) -> None:
        """Close backend and release all resources.

        This method closes the connection pool and releases all resources.

        Examples:
            ```python
            await backend.close()
            ```
        """
        if self._pool:
            await (await self._pool.close())
            self._pool = None

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
        if not self._pool:
            return {
                "total": 0,
                "idle": 0,
                "active": 0,
                "min_size": 0,
                "max_size": 0,
                "wait_count": 0,
                "max_wait_time": 30.0,
            }
        return self._pool.get_stats()
