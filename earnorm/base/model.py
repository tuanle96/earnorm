"""Base model implementation."""

from __future__ import annotations

import logging
from typing import Any, ClassVar, List, Optional, Type, TypeVar, cast

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorCursor
from pymongo.client_session import ClientSession

from earnorm.base.models.interfaces import ModelInterface
from earnorm.base.models.lifecycle import Lifecycle
from earnorm.base.models.persistence import Persistence
from earnorm.base.models.validation import Validator
from earnorm.base.types import ContainerProtocol, DocumentType
from earnorm.cache import cached
from earnorm.di import container

logger = logging.getLogger(__name__)

T = TypeVar("T", bound="BaseModel")


class BaseModel(ModelInterface):
    """Base model class.

    This class provides base functionality for all models including:
    - CRUD operations
    - Validation
    - Lifecycle hooks
    - Caching
    - MongoDB integration

    Class Attributes:
        name: Model name
        collection: MongoDB collection name
        abstract: Whether model is abstract
        indexes: List of MongoDB indexes
    """

    # Class attributes
    name: ClassVar[str] = ""
    collection: ClassVar[str] = ""
    abstract: ClassVar[bool] = False
    indexes: ClassVar[List[DocumentType]] = []

    def __init__(self, **data: Any) -> None:
        """Initialize model instance.

        Args:
            **data: Model data
        """
        self._data: DocumentType = data
        self._validator = Validator()
        self._persistence = Persistence()
        self._lifecycle = Lifecycle()

    @property
    def id(self) -> Optional[str]:
        """Get document ID."""
        return str(self._data["_id"]) if "_id" in self._data else None

    @property
    def data(self) -> DocumentType:
        """Get model data."""
        return self._data

    @classmethod
    def get_collection_name(cls) -> str:
        """Get collection name."""
        return cls.collection

    @classmethod
    def get_name(cls) -> str:
        """Get model name."""
        return cls.name

    @classmethod
    def get_indexes(cls) -> List[DocumentType]:
        """Get model indexes."""
        return cls.indexes

    async def validate(self) -> None:
        """Validate model data."""
        await self._validator.validate(self)

    async def save(self) -> None:
        """Save model to database."""
        await self._lifecycle.before_save(self)
        await self.validate()
        await self._persistence.save(self)
        await self._lifecycle.after_save(self)

    async def delete(self) -> None:
        """Delete model from database."""
        await self._lifecycle.before_delete(self)
        await self._persistence.delete(self)
        await self._lifecycle.after_delete(self)

    @classmethod
    @cached(ttl=300)
    async def get_by_id(cls: Type[T], id: str) -> Optional[T]:
        """Get model by ID.

        Args:
            id: Model ID

        Returns:
            Optional[T]: Model instance if found
        """
        container_instance = cast(ContainerProtocol, container)
        registry = container_instance.registry
        db = registry.db
        collection = db[cls.collection]

        data = await collection.find_one({"_id": ObjectId(id)})
        return cls(**data) if data else None

    @classmethod
    @cached(ttl=300)
    async def find(
        cls: Type[T],
        filter: DocumentType,
        sort: Optional[List[tuple[str, int]]] = None,
        limit: Optional[int] = None,
        skip: Optional[int] = None,
        collection: Optional[AsyncIOMotorCollection[DocumentType]] = None,
        session: Optional[ClientSession] = None,
    ) -> List[ModelInterface]:
        """Find models by filter.

        Args:
            filter: Filter conditions
            sort: Sort specification
            limit: Maximum number of results
            skip: Number of records to skip
            collection: Optional collection instance
            session: Optional client session

        Returns:
            List[ModelInterface]: List of model instances
        """
        if collection is None:
            container_instance = cast(ContainerProtocol, container)
            registry = container_instance.registry
            db = registry.db
            collection = db[cls.collection]

        cursor: AsyncIOMotorCursor[DocumentType] = collection.find(
            filter, session=session
        )

        if sort:
            cursor = cursor.sort(sort)
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)

        documents: List[DocumentType] = cast(
            List[DocumentType], await cursor.to_list(length=None)  # type: ignore
        )
        return [cls(**doc) for doc in documents]

    @classmethod
    @cached(ttl=300)
    async def count(
        cls,
        filter: DocumentType,
        collection: Optional[AsyncIOMotorCollection[DocumentType]] = None,
        session: Optional[ClientSession] = None,
    ) -> int:
        """Count models by filter.

        Args:
            filter: Filter conditions
            collection: Optional collection instance
            session: Optional client session

        Returns:
            int: Number of models
        """
        if collection is None:
            container_instance = cast(ContainerProtocol, container)
            registry = container_instance.registry
            db = registry.db
            collection = db[cls.collection]

        return await collection.count_documents(filter, session=session)  # type: ignore

    def __str__(self) -> str:
        """Get string representation."""
        return f"{self.__class__.__name__}({self.id})"

    def __repr__(self) -> str:
        """Get string representation."""
        return self.__str__()
