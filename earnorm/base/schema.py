"""Database schema management."""

from typing import Dict, List, Optional, Type, Union

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from .model import BaseModel


class SchemaManager:
    """Manager for database schema."""

    def __init__(self):
        self._models: Dict[str, Type[BaseModel]] = {}
        self._db: Optional[AsyncIOMotorDatabase] = None

    def set_database(self, db: AsyncIOMotorDatabase) -> None:
        """Set database connection."""
        self._db = db

    def register_model(self, model: Type[BaseModel]) -> None:
        """Register a model for schema management."""
        if not hasattr(model, "_collection"):
            return
        self._models[model._collection] = model

    async def create_collection(self, model: Type[BaseModel]) -> None:
        """Create collection for model if it doesn't exist."""
        if not self._db:
            raise RuntimeError("Database not set")

        # Skip if model doesn't need collection
        if getattr(model, "_abstract", False):
            return

        collection = model._collection
        collections = await self._db.list_collection_names()

        if collection not in collections:
            # Create collection
            await self._db.create_collection(collection)

            # Create indexes
            indexes = []

            # Add unique index for _id
            indexes.append({"keys": [("_id", 1)], "unique": True})

            # Add model-specific indexes
            if hasattr(model, "_indexes"):
                indexes.extend(model._indexes)

            # Create all indexes
            for index in indexes:
                await self._db[collection].create_index(**index)

    async def update_collection(self, model: Type[BaseModel]) -> None:
        """Update collection schema and indexes."""
        if not self._db:
            raise RuntimeError("Database not set")

        # Skip if model doesn't need collection
        if getattr(model, "_abstract", False):
            return

        collection = model._collection

        # Update indexes
        if hasattr(model, "_indexes"):
            current_indexes = await self._db[collection].list_indexes()
            current_index_keys = {tuple(idx["key"].items()) for idx in current_indexes}

            # Add new indexes
            for index in model._indexes:
                keys = tuple(index["keys"].items())
                if keys not in current_index_keys:
                    await self._db[collection].create_index(**index)

            # Remove old indexes
            model_index_keys = {tuple(idx["keys"].items()) for idx in model._indexes}
            for index in current_indexes:
                keys = tuple(index["key"].items())
                if keys not in model_index_keys and keys != (
                    ("_id", 1),
                ):  # Don't remove _id index
                    await self._db[collection].drop_index(index["name"])

    async def upgrade(self) -> None:
        """Upgrade all registered models."""
        if not self._db:
            raise RuntimeError("Database not set")

        for model in self._models.values():
            await self.create_collection(model)
            await self.update_collection(model)


# Global schema manager instance
schema_manager = SchemaManager()
