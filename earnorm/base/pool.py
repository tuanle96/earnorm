"""MongoDB connection pool manager."""

from typing import Any, Dict, Optional, Protocol, TypeVar, cast

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorClientSession

T = TypeVar("T")


# Protocol definitions
class MongoDatabase(Protocol):
    """Protocol for MongoDB database."""

    def __getitem__(self, name: str) -> "MongoCollection":
        """Get collection by name."""
        ...


class MongoCollection(Protocol):
    """Protocol for MongoDB collection."""

    async def find_one(
        self, filter: Dict[str, Any], *args: Any, **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        """Find single document."""
        ...

    async def find(self, filter: Dict[str, Any], *args: Any, **kwargs: Any) -> Any:
        """Find multiple documents."""
        ...

    async def insert_one(
        self, document: Dict[str, Any], *args: Any, **kwargs: Any
    ) -> Any:
        """Insert single document."""
        ...

    async def update_one(
        self, filter: Dict[str, Any], update: Dict[str, Any], *args: Any, **kwargs: Any
    ) -> Any:
        """Update single document."""
        ...

    async def delete_one(
        self, filter: Dict[str, Any], *args: Any, **kwargs: Any
    ) -> Any:
        """Delete single document."""
        ...


class MongoPoolManager:
    """MongoDB connection pool manager.

    A singleton class that manages MongoDB connection pools.
    Provides connection pooling, monitoring and health checking.
    Should be initialized through DI container.

    Example:
        container = Container()
        pool_manager = container.get(MongoPoolManager)
        db = pool_manager.get_database()
    """

    def __init__(self) -> None:
        """Initialize pool manager."""
        self._pools: Dict[str, AsyncIOMotorClient[Any]] = {}
        self._default_pool: Optional[AsyncIOMotorClient[Any]] = None
        self._database = "earnbase"

    def get_pool(self, uri: Optional[str] = None) -> AsyncIOMotorClient[Any]:
        """Get or create connection pool.

        Args:
            uri: MongoDB connection URI. If not provided, uses default pool.

        Returns:
            Connection pool instance
        """
        if uri is None:
            if self._default_pool is None:
                self._default_pool = self._create_pool("mongodb://localhost:27017")
            return self._default_pool

        if uri not in self._pools:
            self._pools[uri] = self._create_pool(uri)
        return self._pools[uri]

    def _create_pool(self, uri: str) -> AsyncIOMotorClient[Any]:
        """Create new connection pool.

        Args:
            uri: MongoDB connection URI

        Returns:
            New connection pool instance
        """
        return AsyncIOMotorClient(
            uri,
            maxPoolSize=20,
            minPoolSize=5,
            maxIdleTimeMS=300000,  # 5 minutes
            waitQueueTimeoutMS=30000,  # 30 seconds
        )

    def get_database(
        self, pool: Optional[AsyncIOMotorClient[Any]] = None
    ) -> MongoDatabase:
        """Get database from pool.

        Args:
            pool: Connection pool to use. If not provided, uses default pool.

        Returns:
            Database instance
        """
        pool = pool or self.get_pool()
        return cast(MongoDatabase, pool[self._database])

    def get_collection(
        self, collection: str, pool: Optional[AsyncIOMotorClient[Any]] = None
    ) -> MongoCollection:
        """Get collection from pool.

        Args:
            collection: Collection name
            pool: Connection pool to use. If not provided, uses default pool.

        Returns:
            Collection instance
        """
        db = self.get_database(pool)
        return db[collection]

    async def start_session(
        self, pool: Optional[AsyncIOMotorClient[Any]] = None
    ) -> AsyncIOMotorClientSession:
        """Start new database session.

        Args:
            pool: Connection pool to use. If not provided, uses default pool.

        Returns:
            New database session
        """
        pool = pool or self.get_pool()
        return await pool.start_session()

    def close_pool(self, uri: Optional[str] = None) -> None:
        """Close connection pool.

        Args:
            uri: URI of pool to close. If not provided, closes default pool.
        """
        if uri is None and self._default_pool is not None:
            self._default_pool.close()
            self._default_pool = None
            return

        if uri in self._pools:
            self._pools[uri].close()
            del self._pools[uri]

    def close_all(self) -> None:
        """Close all connection pools."""
        if self._default_pool is not None:
            self._default_pool.close()
            self._default_pool = None

        for pool in self._pools.values():
            pool.close()
        self._pools.clear()
