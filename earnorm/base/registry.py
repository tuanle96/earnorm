"""Model registry for EarnORM."""

import importlib
import inspect
import logging
import pkgutil
from typing import Any, Dict, List, Optional, Protocol, Set, Type, runtime_checkable

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.collection import IndexModel

from .model import BaseModel
from .recordset import RecordSet

logger = logging.getLogger(__name__)


@runtime_checkable
class ModelProtocol(Protocol):
    """Protocol for model classes."""

    _collection: str
    _abstract: bool
    _data: Dict[str, Any]
    _indexes: List[IndexModel]
    _validators: List[Any]
    _constraints: List[Any]
    _acl: List[Any]
    _rules: List[Any]
    _events: Dict[str, List[Any]]


class Registry:
    """Registry for model classes.

    The registry discovers and registers all model classes that inherit from BaseModel,
    including abstract models. This allows accessing both concrete models for database
    operations and abstract models for their business logic.

    Example:
        ```python
        from earnorm.di import container

        # Get registry from container
        registry = container.registry()

        # Access concrete models
        users = registry['users']
        products = registry['products']

        # Access abstract models
        mail_thread = registry['mail.thread']
        mail_thread.send_mail(mail_object)

        # Database operations only work on concrete models
        active_users = await users.search([
            ('is_active', '=', True)
        ])
        ```
    """

    def __init__(self) -> None:
        """Initialize registry."""
        self._models: Dict[str, Type[BaseModel]] = {}
        self._db: Optional[AsyncIOMotorDatabase[dict[str, Any]]] = None
        self._discovered = False
        self._scan_paths: Set[str] = set()

    def add_scan_path(self, package_name: str) -> None:
        """Add package to scan for models.

        Args:
            package_name: Package name to scan
        """
        self._scan_paths.add(package_name)
        self._discovered = False  # Force rediscovery

    def _get_collection_name(self, model_cls: Type[BaseModel]) -> str:
        """Get collection name for model class.

        The collection name is determined in the following order:
        1. _collection attribute if defined
        2. _name attribute if defined (Odoo style)
        3. Lowercase class name

        Args:
            model_cls: Model class

        Returns:
            Collection name
        """
        if hasattr(model_cls, "_collection"):
            return model_cls._collection
        if hasattr(model_cls, "_name"):
            return model_cls._name
        return model_cls.__name__.lower()

    def _discover_models(self) -> None:
        """Discover models in registered packages.

        Recursively scans packages for model classes that inherit from BaseModel.
        All models (both concrete and abstract) are registered with the registry.
        """
        if self._discovered:
            return

        def scan_module(module_name: str) -> None:
            """Scan module for model classes."""
            try:
                module = importlib.import_module(module_name)
                logger.debug(f"Scanning module: {module_name}")

                # Get all classes defined in module
                for name, obj in inspect.getmembers(module):
                    if (
                        inspect.isclass(obj)
                        and issubclass(obj, BaseModel)
                        and obj != BaseModel
                    ):
                        # Register both concrete and abstract models
                        collection = self._get_collection_name(obj)
                        self._models[collection] = obj
                        logger.info(
                            f"Registered model {name} as {collection} "
                            f"({'abstract' if getattr(obj, '_abstract', False) else 'concrete'})"
                        )

                # Scan submodules
                if hasattr(module, "__path__"):
                    for _, name, _ in pkgutil.iter_modules(module.__path__):
                        scan_module(f"{module_name}.{name}")

            except ImportError as e:
                logger.warning(f"Failed to import {module_name}: {e}")

        # Add default scan path if none specified
        if not self._scan_paths:
            self._scan_paths.add("earnorm")

        # Start scan from registered packages
        for package in self._scan_paths:
            scan_module(package)

        self._discovered = True
        logger.info(f"Discovered {len(self._models)} models")

    def reload_models(self) -> None:
        """Reload all models.

        This will clear the registry and rediscover all models.
        """
        self._models.clear()
        self._discovered = False
        self._discover_models()

    def get_concrete_models(self) -> List[Type[BaseModel]]:
        """Get list of concrete model classes.

        Returns:
            List of concrete model classes
        """
        if not self._discovered:
            self._discover_models()

        return [
            model_cls
            for model_cls in self._models.values()
            if not getattr(model_cls, "_abstract", False)
        ]

    def get_abstract_models(self) -> List[Type[BaseModel]]:
        """Get list of abstract model classes.

        Returns:
            List of abstract model classes
        """
        if not self._discovered:
            self._discover_models()

        return [
            model_cls
            for model_cls in self._models.values()
            if getattr(model_cls, "_abstract", False)
        ]

    def __getitem__(self, collection: str) -> RecordSet[ModelProtocol]:
        """Get recordset for collection.

        Auto-discovers models if not already done.

        Args:
            collection: Collection name

        Returns:
            RecordSet for the model

        Raises:
            KeyError: If model not found
        """
        # Discover models on first access
        if not self._discovered:
            self._discover_models()

        model_cls = self.get(collection)
        if model_cls is None:
            raise KeyError(f"Model not found: {collection}")
        return RecordSet(model_cls)

    def get(self, collection: str) -> Optional[Type[BaseModel]]:
        """Get model class by collection name.

        Auto-discovers models if not already done.

        Args:
            collection: Collection name

        Returns:
            Model class or None if not found
        """
        # Discover models on first access
        if not self._discovered:
            self._discover_models()

        return self._models.get(collection)

    async def init_db(self, db: AsyncIOMotorDatabase[dict[str, Any]]) -> None:
        """Initialize database collections and indexes for all models.

        Args:
            db: Motor database instance
        """
        self._db = db

        # Discover models before initializing
        if not self._discovered:
            self._discover_models()

        # Initialize collections and indexes for concrete models only
        for model_cls in self._models.values():
            if not getattr(model_cls, "_abstract", False):
                collection = model_cls._collection
                if hasattr(model_cls, "_indexes"):
                    await db[collection].create_indexes(model_cls._indexes)

    @property
    def db(self) -> Optional[AsyncIOMotorDatabase[dict[str, Any]]]:
        """Get database instance."""
        return self._db

    def __contains__(self, collection: str) -> bool:
        """Check if collection exists.

        Auto-discovers models if not already done.

        Args:
            collection: Collection name

        Returns:
            bool: True if collection exists
        """
        # Discover models on first access
        if not self._discovered:
            self._discover_models()

        return collection in self._models

    def __iter__(self):
        """Iterate over registered models.

        Auto-discovers models if not already done.

        Yields:
            tuple: (collection, model_cls)
        """
        # Discover models on first access
        if not self._discovered:
            self._discover_models()

        return iter(self._models.items())

    def __len__(self) -> int:
        """Get number of registered models.

        Auto-discovers models if not already done.

        Returns:
            int: Number of models
        """
        # Discover models on first access
        if not self._discovered:
            self._discover_models()

        return len(self._models)


# Registry is now managed by container in earnorm.di.container
# See container.registry() to get the global instance
