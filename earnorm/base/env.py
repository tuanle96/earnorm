"""Environment module.

This module provides the environment class that manages the application state.
It integrates with the DI container and provides access to all services.
"""

import logging
from typing import Any, Optional, Type, TypeVar

from earnorm.base.database.adapter import DatabaseAdapter
from earnorm.base.model.meta import BaseModel
from earnorm.cache import CacheManager
from earnorm.config import SystemConfig
from earnorm.di import container
from earnorm.events.core.bus import EventBus
from earnorm.types import DatabaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T")


class Environment:
    """Application environment.

    This class manages:
    - Configuration
    - Database connections
    - Model registry
    - Cache manager
    - Event bus

    It integrates with the DI container and follows the singleton pattern.
    All services are accessed through the DI container.

    Examples:
        >>> env = Environment.get_instance()
        >>> await env.init(config)
        >>> User = env.get_model('res.users')
        >>> cache = env.cache_manager
        >>> events = env.event_bus
    """

    # Singleton instance
    _instance: Optional["Environment"] = None

    def __init__(self) -> None:
        """Initialize environment."""
        if Environment._instance is not None:
            raise RuntimeError("Environment already initialized")

        self._initialized = False
        self._cache_manager: Optional[CacheManager] = None
        self._adapter: Optional[DatabaseAdapter[DatabaseModel]] = None
        self._event_bus: Optional[EventBus] = None
        Environment._instance = self

    @classmethod
    def get_instance(cls) -> "Environment":
        """Get singleton instance.

        Returns:
            Environment instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def init(self, config: SystemConfig) -> None:
        """Initialize environment.

        Args:
            config: System configuration

        This method:
        1. Registers config in DI container
        2. Initializes services through DI container
        3. Sets up service dependencies
        """
        if self._initialized:
            logger.warning("Environment already initialized")
            return

        try:
            # Register config
            container.register("config", config)

            # Get services from DI container
            self._cache_manager = await container.get("cache_manager")
            self._adapter = await container.get("database_adapter")
            self._event_bus = await container.get("event_bus")

            # Register self in container
            container.register("env", self)

            self._initialized = True
            logger.info("Environment initialized successfully")

        except Exception as e:
            logger.error("Failed to initialize environment: %s", str(e))
            raise RuntimeError(f"Environment initialization failed: {e}") from e

    async def destroy(self) -> None:
        """Cleanup environment.

        This method:
        1. Closes database connections
        2. Cleans up caches
        3. Stops event bus
        """
        if not self._initialized:
            return

        try:
            # Get services from DI container
            adapter = await container.get("database_adapter")
            cache = await container.get("cache_manager")
            events = await container.get("event_bus")

            # Cleanup services
            if adapter:
                await adapter.close()
            if cache:
                await cache.cleanup()
                await cache.close()
            if events:
                await events.destroy()

            # Reset state
            self._initialized = False

            logger.info("Environment cleaned up successfully")

        except Exception as e:
            logger.error("Failed to cleanup environment: %s", str(e))
            raise RuntimeError(f"Environment cleanup failed: {e}") from e

    def get_service(self, name: str, required: bool = True) -> Any:
        """Get service from DI container.

        Args:
            name: Service name
            required: Whether service is required

        Returns:
            Service instance

        Raises:
            RuntimeError: If service not found and required=True
        """
        service = container.get(name)
        if service is None and required:
            raise RuntimeError(f"Service {name} not found in DI container")
        return service

    @property
    def cache_manager(self) -> CacheManager:
        """Get cache manager.

        Returns:
            Cache manager instance
        """
        return self.get_service("cache_manager")

    @property
    def adapter(self) -> DatabaseAdapter[DatabaseModel]:
        """Get database adapter.

        Returns:
            Database adapter instance
        """
        return self.get_service("database_adapter")

    @property
    def event_bus(self) -> EventBus:
        """Get event bus.

        Returns:
            Event bus instance
        """
        return self.get_service("event_bus")

    def get_model(self, name: str) -> Type[BaseModel]:
        """Get model by name.

        Args:
            name: Model name

        Returns:
            Model class

        Raises:
            ValueError: If model not found
        """
        model = self.get_service(f"model.{name}", required=False)
        if model is None:
            raise ValueError(f"Model {name} not found")
        return model
