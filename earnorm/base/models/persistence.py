"""Model persistence."""

from typing import cast

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from earnorm.base.types import ContainerProtocol, DocumentType, ModelProtocol
from earnorm.di import container


class PersistenceError(Exception):
    """Persistence operation error.

    This exception is raised when a persistence operation fails.
    It contains the original error message from the operation.

    Attributes:
        message: Error message from the operation
    """

    def __init__(self, message: str) -> None:
        """Initialize error.

        Args:
            message: Error message from the operation
        """
        self.message = message
        super().__init__(message)


class Persistence:
    """Model persistence manager.

    This class handles model persistence operations:
    - Save to database
    - Delete from database
    """

    async def save(self, model: ModelProtocol) -> None:
        """Save model to database.

        Args:
            model: Model instance to save

        Raises:
            PersistenceError: If save fails
        """
        # Get collection
        collection = await self._get_collection(model)

        # Convert to MongoDB format
        data = model.to_mongo()

        # Insert or update
        if model.id:
            await collection.update_one(
                {"_id": ObjectId(model.id)},
                {"$set": data},
            )
        else:
            result = await collection.insert_one(data)
            model.from_mongo({"_id": result.inserted_id})

    async def delete(self, model: ModelProtocol) -> None:
        """Delete model from database.

        Args:
            model: Model instance to delete

        Raises:
            PersistenceError: If delete fails
        """
        if not model.id:
            return

        # Get collection
        collection = await self._get_collection(model)

        # Delete document
        await collection.delete_one({"_id": ObjectId(model.id)})

    async def _get_collection(
        self, model: ModelProtocol
    ) -> AsyncIOMotorCollection[DocumentType]:
        """Get MongoDB collection for model.

        Args:
            model: Model instance

        Returns:
            AsyncIOMotorCollection[DocumentType]: MongoDB collection instance for the model

        Raises:
            PersistenceError: If collection cannot be accessed
        """
        container_instance = cast(ContainerProtocol, container)
        registry = container_instance.registry
        db = registry.db
        return db[model.get_collection_name()]
