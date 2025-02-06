"""Environment module.

This module provides the environment class that manages the application state.
It integrates with the DI container and provides access to all services.
"""

import logging
from typing import TYPE_CHECKING, Any, Optional, Type, TypeVar

from earnorm.base.database.adapter import DatabaseAdapter
from earnorm.types import DatabaseModel
from earnorm.types.models import ModelProtocol

if TYPE_CHECKING:
    from earnorm.config.data import SystemConfigData

logger = logging.getLogger(__name__)

T = TypeVar("T")


class Environment:
    """Application environment.

    This class manages:
    - Configuration
    - Database connections
    - Model registry

    It integrates with the DI container and follows the singleton pattern.
    All services are accessed through the DI container.

    Examples:
        >>> env = Environment.get_instance()
        >>> await env.init(config)
        >>> adapter = await env.get_adapter()
        >>> User = env.get_model('res.users')
    """

    # Singleton instance
    _instance: Optional["Environment"] = None

    def __init__(self) -> None:
        """Initialize environment."""
        if Environment._instance is not None:
            raise RuntimeError("Environment already initialized")

        self._initialized = False
        self._adapter: Optional[DatabaseAdapter[DatabaseModel]] = None

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

    async def init(self, config: "SystemConfigData") -> None:
        """Initialize environment.

        Args:
            config: System configuration data

        This method:
        1. Registers config in DI container
        2. Initializes services through DI container
        3. Sets up service dependencies
        """
        if self._initialized:
            logger.warning("Environment already initialized")
            return

        try:
            from earnorm.di import container

            # Register config
            container.register("config", config)

            # Get services from DI container
            self._adapter = await container.get("database_adapter")

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
        2. Stops event bus
        """
        if not self._initialized:
            return

        try:
            from earnorm.di import container

            # Get services from DI container
            if container.has("database_adapter"):
                adapter = await container.get("database_adapter")
                await adapter.close()

            # check if event bus is registered
            if container.has("event_bus"):
                events = await container.get("event_bus")
                await events.destroy()

            # Reset state
            self._initialized = False

            logger.info("Environment cleaned up successfully")

        except Exception as e:
            logger.error("Failed to cleanup environment: %s", str(e))
            raise RuntimeError(f"Environment cleanup failed: {e}") from e

    async def get_service(self, name: str, required: bool = True) -> Any:
        """Get service from DI container.

        Args:
            name: Service name
            required: Whether service is required

        Returns:
            Service instance

        Raises:
            RuntimeError: If service not found and required=True
        """
        from earnorm.di import container

        service = await container.get(name)
        if service is None and required:
            raise RuntimeError(f"Service {name} not found in DI container")
        return service

    @property
    def adapter(self) -> DatabaseAdapter[DatabaseModel]:
        """Get database adapter synchronously.

        Returns:
            Database adapter instance

        Raises:
            RuntimeError: If adapter not initialized
        """
        if not self._initialized:
            raise RuntimeError("Environment not initialized")
        if self._adapter is None:
            raise RuntimeError("Adapter not initialized. Call init() first")
        return self._adapter

    async def get_model(self, name: str) -> Type[ModelProtocol]:
        """Get model by name.

        Args:
            name: Model name

        Returns:
            Model class implementing ModelProtocol

        Raises:
            ValueError: If model not found
        """
        model = await self.get_service(f"model.{name}", required=False)
        if model is None:
            raise ValueError(f"Model {name} not found")
        return model
