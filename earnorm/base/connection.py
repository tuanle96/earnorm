"""MongoDB connection management."""

from typing import Dict, Optional

from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)


class ConnectionManager:
    """MongoDB connection manager."""

    def __init__(self) -> None:
        """Initialize connection manager."""
        self._client: Optional[AsyncIOMotorClient[Dict[str, str]]] = None
        self._db: Optional[AsyncIOMotorDatabase[Dict[str, str]]] = None
        self._collections: Dict[str, AsyncIOMotorCollection[Dict[str, str]]] = {}

    def connect(self, uri: str, database: str) -> None:
        """Connect to MongoDB.

        Args:
            uri: MongoDB connection URI
            database: Database name
        """
        self._client = AsyncIOMotorClient[Dict[str, str]](uri)
        self._db = self._client[database]

    def get_collection(self, name: str) -> AsyncIOMotorCollection[Dict[str, str]]:
        """Get collection by name.

        Args:
            name: Collection name

        Returns:
            Collection instance
        """
        if name not in self._collections:
            if self._db is None:
                raise RuntimeError("Not connected to database")
            self._collections[name] = self._db[name]
        return self._collections[name]

    def close(self) -> None:
        """Close database connection."""
        if self._client is not None:
            self._client.close()
            self._client = None
            self._db = None
            self._collections.clear()


# Global connection manager instance
connection_manager = ConnectionManager()
