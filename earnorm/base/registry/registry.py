"""Registry implementation for database and model management.

This module provides the Registry class for managing:
- Model registration and lookup by collection name
- Database connection for MongoDB operations
"""

from typing import Dict, Optional, Type

from motor.motor_asyncio import AsyncIOMotorDatabase

from earnorm.base.models.interfaces import ModelInterface
from earnorm.base.types import DocumentType


class Registry:
    """Model and database registry.

    This class manages:
    - Model registration and lookup by collection name
    - Database connection for MongoDB operations

    The registry acts as a central point for:
    - Mapping between collection names and model classes
    - Providing access to the MongoDB database instance

    Attributes:
        _models: Dict mapping collection names to model classes
        _db: MongoDB database instance

    Example:
        >>> registry = Registry()
        >>> registry.register_model(UserModel)
        >>> registry.set_database(db_instance)
    """

    def __init__(self) -> None:
        """Initialize registry with empty models and no database."""
        self._models: Dict[str, Type[ModelInterface]] = {}
        self._db: Optional[AsyncIOMotorDatabase[DocumentType]] = None

    @property
    def models(self) -> Dict[str, Type[ModelInterface]]:
        """Get registered models.

        Returns:
            Dict mapping collection names to model classes

        Example:
            >>> registry = Registry()
            >>> models = registry.models
        """
        return self._models

    @property
    def db(self) -> Optional[AsyncIOMotorDatabase[DocumentType]]:
        """Get database instance.

        Returns:
            MongoDB database instance if set, None otherwise

        Example:
            >>> registry = Registry()
            >>> db = registry.db
        """
        return self._db

    def register_model(self, model_cls: Type[ModelInterface]) -> None:
        """Register model class.

        Args:
            model_cls: Model class to register

        Example:
            >>> registry = Registry()
            >>> registry.register_model(UserModel)
        """
        collection = getattr(model_cls, "_collection", "")
        abstract = getattr(model_cls, "_abstract", False)

        if not abstract and collection:
            self._models[collection] = model_cls

    def get_model(self, collection: str) -> Optional[Type[ModelInterface]]:
        """Get model class by collection name.

        Args:
            collection: Collection name

        Returns:
            Model class if found, None otherwise

        Example:
            >>> registry = Registry()
            >>> user_model = registry.get_model("users")
        """
        return self._models.get(collection)

    def set_database(self, db: AsyncIOMotorDatabase[DocumentType]) -> None:
        """Set database instance.

        Args:
            db: MongoDB database instance

        Example:
            >>> registry = Registry()
            >>> registry.set_database(db_instance)
        """
        self._db = db
