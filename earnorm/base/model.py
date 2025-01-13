"""Base model implementation."""

from datetime import datetime, timezone
from functools import wraps
from typing import Any, Awaitable, Callable, Dict, List, Optional, Type, TypeVar, cast

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClientSession, AsyncIOMotorCursor
from pydantic import BaseModel as PydanticBaseModel

from ..cache.cache import cache, cached
from ..validation.decorators import validates
from ..validation.validators import ValidationError
from .connection import ConnectionManager
from .recordset import RecordSet
from .schema import schema_manager

T = TypeVar("T", bound="BaseModel")
HookType = Callable[..., Awaitable[None]]
ModelType = TypeVar("ModelType", bound="BaseModel")


def hook(func: HookType) -> HookType:
    """Decorator for lifecycle hooks."""

    @wraps(func)
    async def wrapper(self: "BaseModel", *args: Any, **kwargs: Any) -> None:
        return await func(self, *args, **kwargs)

    return cast(HookType, wrapper)


class BaseModel(PydanticBaseModel):
    """Base model with MongoDB support."""

    # Collection configuration
    _collection: str
    _abstract: bool = False  # Set to True to skip collection creation
    _indexes: List[Dict[str, Any]] = []  # List of index configurations

    # Common fields
    id: Optional[ObjectId] = None

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True
        json_encoders: Dict[Type[Any], Any] = {
            ObjectId: str,
            datetime: lambda dt: (
                dt if isinstance(dt, datetime) else datetime.now(timezone.utc)
            ).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        }

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Register model with schema manager."""
        super().__init_subclass__(**kwargs)
        schema_manager.register_model(cls)

    # Lifecycle Hooks
    @hook
    async def before_validate(self) -> None:
        """Hook called before validation."""
        pass

    @hook
    async def after_validate(self) -> None:
        """Hook called after validation."""
        pass

    @hook
    async def before_create(self) -> None:
        """Hook called before creating a new document."""
        pass

    @hook
    async def after_create(self) -> None:
        """Hook called after successful creation."""
        pass

    @hook
    async def before_update(self) -> None:
        """Hook called before updating document."""
        pass

    @hook
    async def after_update(self) -> None:
        """Hook called after successful update."""
        pass

    @hook
    async def before_delete(self) -> None:
        """Hook called before deleting document."""
        pass

    @hook
    async def after_delete(self) -> None:
        """Hook called after successful deletion."""
        pass

    @hook
    async def before_save(self) -> None:
        """Hook called before saving document (create or update)."""
        pass

    @hook
    async def after_save(self) -> None:
        """Hook called after successful save."""
        pass

    @classmethod
    def get_collection(cls) -> str:
        """Get collection name."""
        return cls._collection

    @classmethod
    def get_indexes(cls) -> List[Dict[str, Any]]:
        """Get index configurations."""
        return cls._indexes

    @classmethod
    def add_index(
        cls, keys: List[tuple[str, int]], unique: bool = False, **kwargs: Any
    ) -> None:
        """Add an index configuration."""
        cls._indexes.append({"keys": keys, "unique": unique, **kwargs})

    @validates
    async def _validate(self) -> None:
        """Run model validation."""
        # Run before validation hook
        await self.before_validate()

        # Get validation methods
        methods: List[Callable[..., Any]] = []
        for name in dir(self):
            if name.startswith("validate_"):
                method = getattr(self, name)
                if callable(method):
                    methods.append(method)

        # Run validation methods
        for method in methods:
            try:
                await method()
            except ValidationError as e:
                if not e.field:
                    e.field = method.__name__.replace("validate_", "")
                raise e

        # Run after validation hook
        await self.after_validate()

    async def save(
        self,
        session: Optional[AsyncIOMotorClientSession] = None,
    ) -> bool:
        """Save document (create or update)."""
        # Validate before save
        try:
            await self._validate()
        except ValidationError as e:
            raise ValueError(f"Validation failed for field {e.field}: {e.message}")

        await self.before_save()

        if self.id is None:
            # Create new document
            await self.before_create()

            conn = ConnectionManager()
            collection = conn.get_collection(self.get_collection())

            doc = self.model_dump(exclude={"id"})
            result = await collection.insert_one(doc, session=session)

            self.id = result.inserted_id
            await self.after_create()
        else:
            # Update existing document
            await self.before_update()

            conn = ConnectionManager()
            collection = conn.get_collection(self.get_collection())

            doc = self.model_dump(exclude={"id"})
            result = await collection.update_one(
                {"_id": self.id},
                {"$set": doc},
                session=session,
            )

            if result.modified_count == 0:
                return False

            await self.after_update()

        await self.after_save()
        # Invalidate cache
        cache.delete(f"{self.__class__.__name__}:find_one:{{'_id':{self.id}}}")
        cache.delete(f"{self.__class__.__name__}:find")
        return True

    @classmethod
    @cached(ttl=300, key_pattern="{0.__name__}:find_one:{1}")
    async def find_one(
        cls: Type[ModelType],
        filter: Optional[Dict[str, Any]] = None,
        session: Optional[AsyncIOMotorClientSession] = None,
        **kwargs: Any,
    ) -> Optional[RecordSet[ModelType]]:
        """Find single document.

        Args:
            filter: Query filter
            session: Optional database session
            **kwargs: Additional arguments for find_one

        Returns:
            RecordSet containing single document or None if not found
        """
        conn = ConnectionManager()
        collection = conn.get_collection(cls.get_collection())

        doc = await collection.find_one(filter or {}, session=session, **kwargs)
        if doc is None:
            return None

        return RecordSet(cls, [cls.model_validate(doc)])

    @classmethod
    @cached(ttl=300, key_pattern="{0.__name__}:find:{1}")
    async def find(
        cls: Type[ModelType],
        filter: Optional[Dict[str, Any]] = None,
        session: Optional[AsyncIOMotorClientSession] = None,
        **kwargs: Any,
    ) -> RecordSet[ModelType]:
        """Find multiple documents.

        Args:
            filter: Query filter
            session: Optional database session
            **kwargs: Additional arguments for find

        Returns:
            RecordSet containing found documents
        """
        conn = ConnectionManager()
        collection = conn.get_collection(cls.get_collection())

        cursor = cast(
            AsyncIOMotorCursor[Dict[str, Any]],
            collection.find(filter or {}, session=session, **kwargs),
        )
        docs = cast(List[Dict[str, Any]], await cursor.to_list(length=None))

        return RecordSet(cls, [cls.model_validate(doc) for doc in docs])

    async def delete(
        self,
        session: Optional[AsyncIOMotorClientSession] = None,
    ) -> bool:
        """Delete document.

        Args:
            session: Optional database session

        Returns:
            bool: True if successful
        """
        if self.id is None:
            return False

        await self.before_delete()

        conn = ConnectionManager()
        collection = conn.get_collection(self.get_collection())

        result = await collection.delete_one({"_id": self.id}, session=session)

        if result.deleted_count == 0:
            return False

        await self.after_delete()
        # Invalidate cache
        cache.delete(f"{self.__class__.__name__}:find_one:{{'_id':{self.id}}}")
        cache.delete(f"{self.__class__.__name__}:find")
        return True

    @classmethod
    async def create(
        cls,
        data: Dict[str, Any],
        session: Optional[AsyncIOMotorClientSession] = None,
    ) -> "BaseModel":
        """Create new document.

        Args:
            data: Document data
            session: Optional database session

        Returns:
            Created document
        """
        instance = cls(**data)
        await instance.save(session=session)
        return instance

    @classmethod
    async def update(
        cls: Type[ModelType],
        filter: Dict[str, Any],
        update: Dict[str, Any],
        session: Optional[AsyncIOMotorClientSession] = None,
    ) -> RecordSet[ModelType]:
        """Update documents.

        Args:
            filter: Query filter
            update: Update operations
            session: Optional database session

        Returns:
            RecordSet containing updated documents
        """
        conn = ConnectionManager()
        collection = conn.get_collection(cls.get_collection())

        result = await collection.update_many(filter, update, session=session)
        if result.modified_count > 0:
            # Return updated documents
            return await cls.find(filter, session=session)
        return RecordSet(cls, [])

    @classmethod
    async def delete_many(
        cls,
        filter: Dict[str, Any],
        session: Optional[AsyncIOMotorClientSession] = None,
    ) -> bool:
        """Delete multiple documents.

        Args:
            filter: Query filter
            session: Optional database session

        Returns:
            bool: True if successful
        """
        conn = ConnectionManager()
        collection = conn.get_collection(cls.get_collection())

        result = await collection.delete_many(filter, session=session)
        return result.deleted_count > 0

    @classmethod
    async def count(
        cls,
        filter: Optional[Dict[str, Any]] = None,
        session: Optional[AsyncIOMotorClientSession] = None,
    ) -> int:
        """Count documents.

        Args:
            filter: Query filter
            session: Optional database session

        Returns:
            Number of documents
        """
        conn = ConnectionManager()
        collection = conn.get_collection(cls.get_collection())

        return await collection.count_documents(filter or {}, session=session)

    @classmethod
    async def exists(
        cls,
        filter: Dict[str, Any],
        session: Optional[AsyncIOMotorClientSession] = None,
    ) -> bool:
        """Check if documents exist.

        Args:
            filter: Query filter
            session: Optional database session

        Returns:
            bool: True if documents exist
        """
        return await cls.count(filter, session=session) > 0
