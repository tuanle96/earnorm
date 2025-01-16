"""MongoDB pool implementation."""

from typing import Any, Dict, Optional

from motor.motor_asyncio import AsyncIOMotorClient

from earnorm.pool.backends.mongo.connection import MongoConnection
from earnorm.pool.core.pool import BasePool


class MongoPool(BasePool[MongoConnection]):
    """MongoDB connection pool implementation."""

    def __init__(
        self,
        uri: str,
        database: str,
        min_size: int = 5,
        max_size: int = 20,
        timeout: float = 30.0,
        max_lifetime: int = 3600,
        idle_timeout: int = 300,
        validate_on_borrow: bool = True,
        test_on_return: bool = True,
        **config: Any,
    ) -> None:
        """Initialize MongoDB connection pool.

        Args:
            uri: MongoDB connection URI
            database: Database name
            min_size: Minimum pool size
            max_size: Maximum pool size
            timeout: Connection acquire timeout
            max_lifetime: Maximum connection lifetime
            idle_timeout: Maximum idle time
            validate_on_borrow: Validate connection on borrow
            test_on_return: Test connection on return
            **config: Additional configuration

        Examples:
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
        super().__init__(
            backend_type="mongodb",
            min_size=min_size,
            max_size=max_size,
            timeout=timeout,
            max_lifetime=max_lifetime,
            idle_timeout=idle_timeout,
            validate_on_borrow=validate_on_borrow,
            test_on_return=test_on_return,
            **config,
        )
        self._uri = uri
        self._database = database
        self._client: Optional[AsyncIOMotorClient[Dict[str, Any]]] = None

    @property
    def uri(self) -> str:
        """Get MongoDB URI."""
        return self._uri

    @property
    def database(self) -> str:
        """Get database name."""
        return self._database

    @property
    def min_size(self) -> int:
        """Get minimum pool size."""
        return self._min_size

    @property
    def max_size(self) -> int:
        """Get maximum pool size."""
        return self._max_size

    @property
    def timeout(self) -> float:
        """Get connection acquire timeout."""
        return self._timeout

    @property
    def max_lifetime(self) -> int:
        """Get maximum connection lifetime."""
        return self._max_lifetime

    @property
    def idle_timeout(self) -> int:
        """Get maximum idle time."""
        return self._idle_timeout

    async def _create_connection(self) -> MongoConnection:
        """Create new MongoDB connection.

        Returns:
            MongoConnection instance
        """
        client: AsyncIOMotorClient[Dict[str, Any]] = AsyncIOMotorClient(self._uri)
        return MongoConnection(client, self._database)

    async def _validate_connection(self, conn: MongoConnection) -> bool:
        """Validate MongoDB connection health.

        Args:
            conn: Connection to validate

        Returns:
            True if connection is healthy
        """
        return await conn.ping()

    async def close(self) -> None:
        """Close all connections and shutdown pool."""
        await super().close()
        if self._client:
            self._client.close()
