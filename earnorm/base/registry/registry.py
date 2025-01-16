"""Registry implementation for database and model management.

This module provides the Registry class for managing:
- Model registration and lookup by collection name
- Database connection for MongoDB operations
"""

from typing import Dict, Optional, Type

from motor.motor_asyncio import AsyncIOMotorDatabase

from earnorm.base.types import DocumentType, ModelProtocol
from earnorm.config.model import SystemConfig


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
        _config: SystemConfig instance

    Example:
        >>> registry = Registry()
        >>> registry.register_model(UserModel)
        >>> registry.set_database(db_instance)
    """

    def __init__(self) -> None:
        """Initialize registry with empty models and no database."""
        self._models: Dict[str, Type[ModelProtocol]] = {}
        self._db: Optional[AsyncIOMotorDatabase[DocumentType]] = None
        self._config: Optional[SystemConfig] = None

    @property
    def models(self) -> Dict[str, Type[ModelProtocol]]:
        """Get registered models.

        Returns:
            Dict mapping collection names to model classes

        Example:
            >>> registry = Registry()
            >>> models = registry.models
        """
        return self._models

    @property
    def db(self) -> AsyncIOMotorDatabase[DocumentType]:
        """Get database instance.

        Returns:
            MongoDB database instance

        Raises:
            RuntimeError: If database not initialized

        Example:
            >>> registry = Registry()
            >>> db = registry.db
        """
        if self._db is None:
            raise RuntimeError("Database not initialized")
        return self._db

    @property
    def config(self) -> SystemConfig:
        """Get system config instance.

        Returns:
            SystemConfig instance

        Raises:
            RuntimeError: If config not initialized

        Examples:
            >>> config = registry.config
            >>> print(config.mongo_uri)
        """
        if self._config is None:
            raise RuntimeError("Config not initialized")
        return self._config

    async def init_config(self, config_path: str) -> None:
        """Initialize system config from file.

        Args:
            config_path: Path to config file

        Raises:
            ConfigError: If config initialization fails
            FileNotFoundError: If config file not found
            ValueError: If config file is invalid

        Examples:
            >>> await registry.init_config("config.yaml")
        """
        # Load config from file
        self._config = await SystemConfig.load_config(config_path)

    def register_model(self, model_cls: Type[ModelProtocol]) -> None:
        """Register model class.

        Args:
            model_cls: Model class to register

        Raises:
            ValueError: If model collection name is missing
            TypeError: If model_cls does not implement ModelProtocol

        Example:
            >>> registry = Registry()
            >>> registry.register_model(UserModel)
        """
        # Check if model_cls implements required attributes
        required_attrs = ["_collection", "_abstract"]
        for attr in required_attrs:
            if not hasattr(model_cls, attr):
                raise TypeError(f"model_cls must have {attr} attribute")

        collection = model_cls.get_collection_name()
        abstract = getattr(model_cls, "_abstract", False)

        if not abstract:
            if not collection:
                raise ValueError("Model collection name is required")
            self._models[collection] = model_cls

    def get_model(self, collection: str) -> Optional[Type[ModelProtocol]]:
        """Get model class by collection name.

        Args:
            collection: Collection name

        Returns:
            Model class if found, None otherwise

        Raises:
            ValueError: If collection name is empty

        Example:
            >>> registry = Registry()
            >>> user_model = registry.get_model("users")
        """
        if not collection:
            raise ValueError("Collection name cannot be empty")
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
