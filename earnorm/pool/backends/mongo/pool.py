"""MongoDB connection pool implementation."""

from typing import Any, TypeVar, cast

from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)

from earnorm.exceptions import ConnectionError as DatabaseConnectionError
from earnorm.pool.backends.base.pool import BasePool
from earnorm.pool.core.circuit import CircuitBreaker
from earnorm.pool.core.retry import RetryPolicy
from earnorm.pool.protocols.connection import AsyncConnectionProtocol

from .connection import MongoConnection

DBType = TypeVar("DBType", bound=AsyncIOMotorDatabase[dict[str, Any]])
CollType = TypeVar("CollType", bound=AsyncIOMotorCollection[dict[str, Any]])


class MongoPool(BasePool[DBType, CollType]):
    """MongoDB connection pool implementation."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 27017,
        database: str = "test",
        collection: str = "test",
        username: str | None = None,
        password: str | None = None,
        auth_source: str | None = None,
        auth_mechanism: str | None = None,
        pool_size: int = 10,
        min_size: int = 2,
        max_size: int = 20,
        max_idle_time: int = 300,
        max_lifetime: int = 3600,
        retry_policy: RetryPolicy | None = None,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        """Initialize MongoDB pool.

        Args:
            host: MongoDB host
            port: MongoDB port
            database: Database name
            collection: Collection name
            username: Username for authentication
            password: Password for authentication
            auth_source: Authentication source
            auth_mechanism: Authentication mechanism
            pool_size: Initial pool size
            min_size: Minimum pool size
            max_size: Maximum pool size
            max_idle_time: Maximum idle time in seconds
            max_lifetime: Maximum lifetime in seconds
            retry_policy: Retry policy
            circuit_breaker: Circuit breaker
        """
        super().__init__(
            pool_size=pool_size,
            min_size=min_size,
            max_size=max_size,
            max_idle_time=max_idle_time,
            max_lifetime=max_lifetime,
            retry_policy=retry_policy,
            circuit_breaker=circuit_breaker,
        )

        self._host = host
        self._port = port
        self._database = database
        self._collection = collection
        self._username = username
        self._password = password
        self._auth_source = auth_source
        self._auth_mechanism = auth_mechanism
        self._client: AsyncIOMotorClient[dict[str, Any]] | None = None

    def _create_connection(self) -> AsyncConnectionProtocol[DBType, CollType]:
        """Create a new connection.

        Returns:
            AsyncConnectionProtocol: New connection

        Raises:
            DatabaseConnectionError: If connection creation fails
        """
        if not self._client:
            raise DatabaseConnectionError("Pool is not connected")

        return cast(
            AsyncConnectionProtocol[DBType, CollType],
            MongoConnection(
                client=self._client,
                database=self._database,
                collection=self._collection,
                max_idle_time=self._max_idle_time,
                max_lifetime=self._max_lifetime,
                retry_policy=self._retry_policy,
                circuit_breaker=self._circuit_breaker,
            ),
        )

    async def connect(self) -> None:
        """Connect to MongoDB."""
        if not self._client:
            self._client = AsyncIOMotorClient(
                host=self._host,
                port=self._port,
                username=self._username,
                password=self._password,
                authSource=self._auth_source,
                authMechanism=self._auth_mechanism,
            )

    async def disconnect(self) -> None:
        """Disconnect from MongoDB."""
        if self._client:
            self._client.close()
            self._client = None

    async def ping(self) -> bool:
        """Check pool health.

        Returns:
            bool: True if pool is healthy
        """
        try:
            if not self._client:
                return False
            await self._client.admin.command("ping")
            return True
        except Exception:
            return False

    def get_stats(self) -> dict[str, Any]:
        """Get pool statistics."""
        stats = super().get_stats()
        stats.update(
            {
                "host": self._host,
                "port": self._port,
                "database": self._database,
                "collection": self._collection,
            }
        )
        return stats

    @property
    def database_name(self) -> str:
        """Get database name."""
        return self._database
