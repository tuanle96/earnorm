"""Model persistence implementation."""

from __future__ import annotations

from typing import cast

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.results import DeleteResult, InsertOneResult, UpdateResult

from earnorm.base.models.interfaces import ModelInterface
from earnorm.base.types import ContainerProtocol, DocumentType
from earnorm.di import container


class PersistenceError(Exception):
    """Persistence error.

    This exception is raised when persistence operations fail.
    """

    def __init__(self, message: str) -> None:
        """Initialize error.

        Args:
            message: Error message
        """
        self.message = message
        super().__init__(message)


class Persistence:
    """Model persistence.

    This class handles model persistence operations:
    - Save (insert/update)
    - Delete
    """

    async def save(self, model: ModelInterface) -> None:
        """Save model to database.

        Args:
            model: Model to save

        Raises:
            PersistenceError: If save fails
        """
        container_instance = cast(ContainerProtocol, container)
        registry = container_instance.registry
        db = registry.db

        # Get collection
        collection: AsyncIOMotorCollection[DocumentType] = db[
            cast(str, getattr(model.__class__, "collection", ""))
        ]

        # Get model data
        data = model.data.copy()

        # Convert ID to ObjectId
        if "_id" in data and isinstance(data["_id"], str):
            data["_id"] = ObjectId(data["_id"])

        try:
            # Insert or update
            if model.id:
                update_result: UpdateResult = await collection.update_one(
                    {"_id": ObjectId(model.id)}, {"$set": data}
                )
                if not update_result.modified_count:
                    raise PersistenceError(f"Failed to update model {model.id}")
            else:
                insert_result: InsertOneResult = await collection.insert_one(data)
                if not insert_result.inserted_id:
                    raise PersistenceError("Failed to insert model")
                setattr(model, "_data", {"_id": insert_result.inserted_id, **data})
        except Exception as e:
            raise PersistenceError(f"Failed to save model: {str(e)}") from e

    async def delete(self, model: ModelInterface) -> None:
        """Delete model from database.

        Args:
            model: Model to delete

        Raises:
            PersistenceError: If delete fails or model has no ID
        """
        if not model.id:
            raise PersistenceError("Cannot delete model without ID")

        container_instance = cast(ContainerProtocol, container)
        registry = container_instance.registry
        db = registry.db

        # Get collection
        collection: AsyncIOMotorCollection[DocumentType] = db[
            cast(str, getattr(model.__class__, "collection", ""))
        ]

        try:
            # Delete document
            result: DeleteResult = await collection.delete_one(
                {"_id": ObjectId(model.id)}
            )
            if not result.deleted_count:
                raise PersistenceError(f"Failed to delete model {model.id}")
        except Exception as e:
            raise PersistenceError(f"Failed to delete model: {str(e)}") from e
