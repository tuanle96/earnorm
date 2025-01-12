"""Base model implementation."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, get_type_hints

from bson import ObjectId
from pydantic import BaseModel as PydanticBaseModel

from .schema import schema_manager

T = TypeVar("T", bound="BaseModel")


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
        json_encoders = {ObjectId: str, datetime: lambda dt: dt.isoformat()}

    def __init_subclass__(cls, **kwargs):
        """Register model with schema manager."""
        super().__init_subclass__(**kwargs)
        schema_manager.register_model(cls)

    @classmethod
    def get_collection(cls) -> str:
        """Get collection name."""
        return cls._collection

    @classmethod
    def get_indexes(cls) -> List[Dict[str, Any]]:
        """Get index configurations."""
        return cls._indexes

    @classmethod
    def add_index(cls, keys: List[tuple], unique: bool = False, **kwargs):
        """Add an index configuration."""
        cls._indexes.append({"keys": keys, "unique": unique, **kwargs})

    async def save(self, *args, **kwargs) -> T:
        """Save document to database."""
        # TODO: Implement save logic
        pass

    @classmethod
    async def find_one(cls: Type[T], *args, **kwargs) -> Optional[T]:
        """Find a single document."""
        # TODO: Implement find_one logic
        pass

    @classmethod
    async def find(cls: Type[T], *args, **kwargs) -> List[T]:
        """Find multiple documents."""
        # TODO: Implement find logic
        pass

    @classmethod
    async def delete_one(cls, *args, **kwargs) -> bool:
        """Delete a single document."""
        # TODO: Implement delete_one logic
        pass

    @classmethod
    async def delete_many(cls, *args, **kwargs) -> int:
        """Delete multiple documents."""
        # TODO: Implement delete_many logic
        pass
