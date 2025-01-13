"""Model registry for EarnORM."""

import importlib.util
import inspect
import logging
import os
import pkgutil
import sys
from typing import Any, Dict, List, Optional, Set, Type, cast

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.operations import IndexModel

from earnorm.base.recordset import RecordSet
from earnorm.base.types import ModelProtocol, RegistryProtocol

logger = logging.getLogger(__name__)


class Registry(RegistryProtocol):
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
        self._models: Dict[str, Type[ModelProtocol]] = {}
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

    def _get_collection_name(self, model_cls: Type[ModelProtocol]) -> str:
        """Get collection name for model class.

        The collection name is determined by calling get_collection_name()
        on the model class.

        Args:
            model_cls: Model class

        Returns:
            Collection name
        """
        return model_cls.get_collection_name()

    def _is_model_class(self, obj: Any) -> bool:
        """Check if object is a model class."""
        # Import BaseModel here to avoid circular import
        from earnorm.base.model import BaseModel as _BaseModel

        return (
            inspect.isclass(obj)
            and hasattr(obj, "_collection")
            and hasattr(obj, "_name")
            and issubclass(obj, _BaseModel)
            and obj is not _BaseModel
        )

    def _discover_models(self) -> None:
        """Discover models in registered packages.

        Recursively scans packages for model classes that inherit from BaseModel.
        All models (both concrete and abstract) are registered with the registry.
        """
        if self._discovered:
            return

        def scan_module(module_path: str) -> None:
            """Scan module for model classes."""
            try:
                # Handle both package names and file paths
                if os.path.isfile(module_path):
                    # Import from file path
                    module_name = os.path.splitext(os.path.basename(module_path))[0]
                    spec = importlib.util.spec_from_file_location(
                        module_name, module_path
                    )
                    if spec is None or spec.loader is None:
                        logger.warning(f"Failed to load module spec: {module_path}")
                        return
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)
                else:
                    # Import from package name
                    module = importlib.import_module(module_path)

                logger.debug(f"Scanning module: {module_path}")

                # Get all classes defined in module
                for name, obj in inspect.getmembers(module):
                    if self._is_model_class(obj):
                        # Register both concrete and abstract models
                        collection = self._get_collection_name(obj)
                        self._models[collection] = obj
                        logger.info(
                            "Registered model {} as {} ({})".format(
                                name,
                                collection,
                                (
                                    "abstract"
                                    if getattr(obj, "_abstract", False)
                                    else "concrete"
                                ),
                            )
                        )

                # Scan submodules if it's a package
                if hasattr(module, "__path__"):
                    paths = cast(List[str], module.__path__)
                    for _, name, _ in pkgutil.iter_modules(paths):
                        scan_module(f"{module_path}.{name}")

            except ImportError as e:
                logger.warning(f"Failed to import {module_path}: {e}")

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

    def get_concrete_models(self) -> List[Type[ModelProtocol]]:
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

    def get_abstract_models(self) -> List[Type[ModelProtocol]]:
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
        """Get empty RecordSet for model.

        Args:
            collection: Collection name

        Returns:
            Empty RecordSet for model

        Raises:
            KeyError: If model not found
        """
        model_cls = self.get(collection)
        if model_cls is None:
            raise KeyError(f"Model not found: {collection}")
        return RecordSet(model_cls, [])

    def get(self, collection: str) -> Optional[Type[ModelProtocol]]:
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
                collection = self._get_collection_name(model_cls)
                indexes = [IndexModel(idx) for idx in model_cls.get_indexes()]
                if indexes:
                    await db[collection].create_indexes(indexes)

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

    def register_model(self, model: Type[ModelProtocol]) -> None:
        """Register model directly.

        Args:
            model: Model class to register
        """
        collection = self._get_collection_name(model)
        self._models[collection] = model
        logger.info(
            f"Registered model {model.__name__} as {collection} "
            f"({'abstract' if getattr(model, '_abstract', False) else 'concrete'})"
        )

    def get_model(self, model_name: str) -> Optional[Type[ModelProtocol]]:
        """Get model class by name.

        Args:
            model_name: Name of the model class

        Returns:
            Model class or None if not found
        """
        # Discover models on first access
        if not self._discovered:
            self._discover_models()

        # Try exact match first
        if model_name in self._models:
            return self._models[model_name]

        # Try case-insensitive match
        lower_name = model_name.lower()
        for name, model in self._models.items():
            if name.lower() == lower_name:
                return model

        return None
