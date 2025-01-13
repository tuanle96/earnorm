"""Schema management for EarnORM."""

from typing import Any, Dict, List, Type, TypeVar

from motor.motor_asyncio import AsyncIOMotorCollection

from .connection import connection_manager

T = TypeVar("T")


class SchemaManager:
    """Schema manager for EarnORM."""

    def __init__(self) -> None:
        """Initialize schema manager."""
        self._models: Dict[str, Type[Any]] = {}
        self._initialized = False

    def register_model(self, model: Type[T]) -> None:
        """Register model with schema manager.

        Args:
            model: Model class to register
        """
        if hasattr(model, "_collection") and not getattr(model, "_abstract", False):
            collection = getattr(model, "_collection")
            self._models[collection] = model

    async def init_collections(self) -> None:
        """Initialize collections and indexes."""
        if self._initialized:
            return

        for collection, model in self._models.items():
            # Get collection
            db_collection: AsyncIOMotorCollection[Dict[str, str]] = (
                connection_manager.get_collection(collection)
            )

            # Create indexes
            indexes: List[Dict[str, Any]] = getattr(model, "_indexes", [])
            if indexes:
                for index in indexes:
                    await db_collection.create_index(**index)

        self._initialized = True


# Global schema manager instance
schema_manager = SchemaManager()
