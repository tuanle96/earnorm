"""MongoDB connection management."""

from typing import Any, Dict, Optional

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database


class ConnectionManager:
    """Manages MongoDB connections."""

    def __init__(self, uri: str, database: str, **options: Dict[str, Any]) -> None:
        """Initialize connection manager.

        Args:
            uri: MongoDB connection URI
            database: Database name
            **options: Additional connection options
        """
        self.uri = uri
        self.database = database
        self.options = options
        self._client: Optional[MongoClient] = None
        self._db: Optional[Database] = None

    def connect(self) -> None:
        """Establish database connection."""
        if not self._client:
            self._client = MongoClient(self.uri, **self.options)
            self._db = self._client[self.database]

    def disconnect(self) -> None:
        """Close database connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None

    def get_database(self) -> Database:
        """Get database instance."""
        if not self._db:
            self.connect()
        return self._db

    def get_collection(self, name: str) -> Collection:
        """Get collection by name."""
        return self.get_database()[name]

    def __enter__(self) -> "ConnectionManager":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.disconnect()
