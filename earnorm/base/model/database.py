"""Database model implementation.

This module provides the base implementation for database models.
It includes CRUD operations and JSON serialization.

Examples:
    >>> class User(DatabaseModel):
    ...     name: str
    ...     age: int
    ...     
    ...     __collection__ = "users"
    >>> 
    >>> # Create and save user
    >>> user = User(name="John", age=25)
    >>> await user.save()
    >>> 
    >>> # Query users
    >>> users = await User.find(User.age > 18)
"""

from typing import Any, Dict, List, Optional, Type, TypeVar

from bson import ObjectId
from pydantic import BaseModel, ConfigDict

from earnorm.base.database.adapter import DatabaseAdapter
from earnorm.base.registry import ModelRegistry
from earnorm.types import DatabaseModel as DatabaseModelProtocol
from earnorm.types import JsonDict

ModelT = TypeVar("ModelT", bound="DatabaseModel")


class DatabaseModel(BaseModel, DatabaseModelProtocol):
    """Base class for all database models.

    This class provides base functionality for all database models.
    It includes CRUD operations and JSON serialization.

    Attributes:
        id: Document ID
        __collection__: Collection name for model
    """

    id: Optional[ObjectId] = None
    __collection__: str

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def _get_adapter(cls) -> DatabaseAdapter[Any]:
        """Get database adapter for model.

        Returns:
            Database adapter

        Raises:
            KeyError: If no adapter registered for model
        """
        return ModelRegistry().get(cls)

    async def save(self: ModelT) -> ModelT:
        """Save model to database.

        Returns:
            Saved model with ID

        Raises:
            KeyError: If no adapter registered for model
        """
        adapter = self._get_adapter()
        if self.id is None:
            return await adapter.insert(self)
        return await adapter.update(self)

    @classmethod
    async def save_many(cls: Type[ModelT], models: List[ModelT]) -> List[ModelT]:
        """Save multiple models to database.

        Args:
            models: Models to save

        Returns:
            Saved models with IDs

        Raises:
            KeyError: If no adapter registered for model
        """
        adapter = cls._get_adapter()
        to_insert = [model for model in models if model.id is None]
        to_update = [model for model in models if model.id is not None]

        results = []
        if to_insert:
            results.extend(await adapter.insert_many(to_insert))
        if to_update:
            results.extend(await adapter.update_many(to_update))
        return results

    async def delete(self) -> None:
        """Delete model from database.

        Raises:
            KeyError: If no adapter registered for model
            ValueError: If model has no ID
        """
        adapter = self._get_adapter()
        await adapter.delete(self)

    @classmethod
    async def delete_many(cls: Type[ModelT], models: List[ModelT]) -> None:
        """Delete multiple models from database.

        Args:
            models: Models to delete

        Raises:
            KeyError: If no adapter registered for model
            ValueError: If any model has no ID
        """
        adapter = cls._get_adapter()
        await adapter.delete_many(models)

    @classmethod
    async def find(cls: Type[ModelT], *args: Any, **kwargs: Any) -> List[ModelT]:
        """Find models matching criteria.

        Args:
            *args: Positional arguments passed to query
            **kwargs: Keyword arguments passed to query

        Returns:
            List of matching models

        Raises:
            KeyError: If no adapter registered for model
        """
        adapter = cls._get_adapter()
        return await adapter.query(cls).filter(*args, **kwargs).all()

    @classmethod
    async def find_one(
        cls: Type[ModelT], *args: Any, **kwargs: Any
    ) -> Optional[ModelT]:
        """Find first model matching criteria.

        Args:
            *args: Positional arguments passed to query
            **kwargs: Keyword arguments passed to query

        Returns:
            Matching model or None

        Raises:
            KeyError: If no adapter registered for model
        """
        adapter = cls._get_adapter()
        return await adapter.query(cls).filter(*args, **kwargs).first()

    def to_dict(self) -> JsonDict:
        """Convert model to dictionary.

        Returns:
            Model as dictionary
        """
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DatabaseModel":
        """Create model from dictionary.

        Args:
            data: Dictionary representation of model

        Returns:
            Model instance
        """
        return cls(**data)
