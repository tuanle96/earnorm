"""Database connection management."""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, cast
from urllib.parse import urlparse

from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from ..utils.singleton import Singleton


class ConnectionManager(metaclass=Singleton):
    """Manager for database connections."""

    def __init__(self) -> None:
        """Initialize connection manager."""
        self._client: Optional[AsyncIOMotorClient[Dict[str, Any]]] = None
        self._db: Optional[AsyncIOMotorDatabase[Dict[str, Any]]] = None
        self._pool_settings: Dict[str, Any] = {}
        self._health_check_task: Optional[asyncio.Task[None]] = None
        self._is_connected = False

    async def connect(
        self,
        uri: str,
        database: str,
        *,
        min_pool_size: int = 10,
        max_pool_size: int = 100,
        max_idle_time_ms: int = 10000,
        connect_timeout_ms: int = 20000,
        server_selection_timeout_ms: int = 30000,
        **kwargs: Any,
    ) -> None:
        """Connect to database."""
        # Parse connection URI
        parsed = urlparse(uri)
        if not parsed.hostname:
            raise ValueError("Invalid connection URI")

        # Store pool settings
        self._pool_settings = {
            "minPoolSize": min_pool_size,
            "maxPoolSize": max_pool_size,
            "maxIdleTimeMS": max_idle_time_ms,
            "connectTimeoutMS": connect_timeout_ms,
            "serverSelectionTimeoutMS": server_selection_timeout_ms,
            **kwargs,
        }

        try:
            # Create client
            client = AsyncIOMotorClient[Dict[str, Any]](uri, **self._pool_settings)
            self._client = client

            # Get database
            self._db = client[database]

            # Test connection
            await client.admin.command("ping")
            self._is_connected = True

            # Start health check
            self._start_health_check()
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            self._is_connected = False
            raise ConnectionError(f"Failed to connect to database: {str(e)}")

    def _start_health_check(self) -> None:
        """Start health check task."""
        if self._health_check_task is not None:
            self._health_check_task.cancel()

        self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def _health_check_loop(self) -> None:
        """Health check loop."""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                if self._client is not None:
                    await self._client.admin.command("ping")
            except Exception as e:
                self._is_connected = False
                # TODO: Add logging
                print(f"Health check failed: {str(e)}")

    async def disconnect(self) -> None:
        """Disconnect from database."""
        if self._client is not None:
            self._client.close()
            self._client = None
            self._db = None
            self._is_connected = False

        if self._health_check_task is not None:
            self._health_check_task.cancel()
            self._health_check_task = None

    def get_database(self) -> AsyncIOMotorDatabase[Dict[str, Any]]:
        """Get database instance."""
        if not self._is_connected or self._db is None:
            raise ConnectionError("Not connected to database")
        return self._db

    def get_collection(self, name: str) -> AsyncIOMotorCollection[Dict[str, Any]]:
        """Get collection by name."""
        return self.get_database()[name]

    async def ping(self) -> bool:
        """Check connection status."""
        try:
            if self._client is not None:
                await self._client.admin.command("ping")
                return True
        except Exception:
            pass
        return False

    def is_connected(self) -> bool:
        """Check if connected to database."""
        return self._is_connected

    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        if not self._is_connected or self._client is None:
            return {}

        return {
            "min_pool_size": self._pool_settings.get("minPoolSize", 0),
            "max_pool_size": self._pool_settings.get("maxPoolSize", 0),
            "active_connections": len(self._client.nodes),  # type: ignore
            "last_check": datetime.now(timezone.utc).isoformat(),
        }

    async def create_indexes(
        self, collection: str, indexes: List[Dict[str, Any]]
    ) -> None:
        """Create indexes for collection."""
        if not indexes:
            return

        coll = self.get_collection(collection)
        for index in indexes:
            await coll.create_index(**index)

    async def drop_indexes(self, collection: str) -> None:
        """Drop all indexes from collection."""
        coll = self.get_collection(collection)
        await coll.drop_indexes()

    async def list_indexes(self, collection: str) -> List[Dict[str, Any]]:
        """List all indexes in collection."""
        coll = self.get_collection(collection)
        cursor = coll.list_indexes()
        indexes = await cursor.to_list(None)
        return cast(List[Dict[str, Any]], indexes)
