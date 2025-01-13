"""Application initialization for EarnORM."""

import importlib
import inspect
from pathlib import Path
from typing import List, Optional, Type, Union

from earnorm.base.model import BaseModel
from earnorm.di.container import container, env


class EarnORMApp:
    """EarnORM application manager.

    This class manages the application lifecycle, including:
    - Container initialization
    - Model registration
    - Database setup

    Example:
        ```python
        from earnorm.app import create_app

        app = create_app()

        # Register models manually
        app.register_model(User)
        app.register_model(Product)

        # Or auto-discover models in modules
        app.discover_models(['myapp.models'])

        # Initialize app
        await app.init(
            mongo_uri="mongodb://localhost:27017",
            database="myapp"
        )
        ```
    """

    def __init__(self) -> None:
        """Initialize application."""
        self._initialized = False
        self._models: List[Type[BaseModel]] = []

    def register_model(self, model: Type[BaseModel]) -> None:
        """Register model with the application.

        Args:
            model: Model class to register
        """
        if not inspect.isclass(model) or not issubclass(model, BaseModel):
            raise TypeError(f"Expected BaseModel subclass, got {type(model)}")

        # Add to internal registry
        if model not in self._models:
            self._models.append(model)

        # Register with env if initialized
        if self._initialized:
            env.register(model)

    def discover_models(self, modules: List[str]) -> None:
        """Auto-discover and register models from modules.

        Args:
            modules: List of module paths to scan
        """
        for module_path in modules:
            module = importlib.import_module(module_path)

            # Get all classes defined in module
            for name, obj in inspect.getmembers(module):
                if (
                    inspect.isclass(obj)
                    and issubclass(obj, BaseModel)
                    and obj != BaseModel
                ):
                    self.register_model(obj)

    async def init(self, mongo_uri: str, database: str, **kwargs) -> None:
        """Initialize application.

        Args:
            mongo_uri: MongoDB connection URI
            database: Database name
            **kwargs: Additional configuration
        """
        if self._initialized:
            return

        # Initialize container
        await container.init_resources(mongo_uri=mongo_uri, database=database, **kwargs)

        # Register all models
        for model in self._models:
            env.register(model)

        self._initialized = True

    async def cleanup(self) -> None:
        """Cleanup application resources."""
        if not self._initialized:
            return

        await container.cleanup()
        self._initialized = False


def create_app() -> EarnORMApp:
    """Create new EarnORM application.

    Returns:
        New EarnORMApp instance
    """
    return EarnORMApp()
