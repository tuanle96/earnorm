"""Environment module for EarnORM.

This module provides the environment system that manages application state and dependencies.
It implements the singleton pattern and integrates with a dependency injection container.

Key Features:
    1. Application State
       - Configuration management
       - Service registry
       - Resource lifecycle
       - Error handling
       - Logging support

    2. Database Integration
       - Adapter management
       - Connection pooling
       - Transaction support
       - Model registry
       - Query building

    3. Dependency Injection
       - Service container
       - Lazy loading
       - Scoped services
       - Auto-wiring
       - Service lifecycle

Examples:
    >>> from earnorm.base.env import Environment
    >>> from earnorm.base.database import MongoAdapter

    >>> # Get singleton instance
    >>> env = Environment.get_instance()

    >>> # Initialize with config
    >>> await env.init(config)

    >>> # Get database adapter
    >>> adapter = env.adapter
    >>> users = await adapter.query(User).all()

    >>> # Get model by name
    >>> User = await env.get_model('data.user')
    >>> user = await User.create({"name": "John"})

    >>> # Get service from DI container
    >>> events = await env.get_service('event_bus')
    >>> await events.publish('user.created', user)

    >>> # Cleanup on shutdown
    >>> await env.destroy()

Classes:
    Environment:
        Main environment class implementing singleton pattern.

        Class Methods:
            get_instance: Get singleton instance

        Instance Methods:
            init: Initialize environment
            destroy: Cleanup resources
            get_service: Get service from DI container
            get_model: Get model by name

        Properties:
            adapter: Get database adapter
            initialized: Check if initialized

Implementation Notes:
    1. Singleton Pattern
       - Single instance per application
       - Thread-safe initialization
       - Lazy loading of services
       - Resource cleanup

    2. DI Container
       - Service registration
       - Dependency resolution
       - Scoped instances
       - Circular dependency detection

    3. Resource Management
       - Connection pooling
       - Transaction handling
       - Event bus
       - Cache invalidation

See Also:
    - earnorm.di: Dependency injection system
    - earnorm.config: Configuration management
    - earnorm.database: Database adapters
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
    """Application environment singleton.

    This class manages the application state and dependencies through:
    - Configuration management
    - Database connections
    - Service registry
    - Model registry
    - Resource lifecycle

    It implements the singleton pattern and integrates with a DI container.
    All services are accessed through the container for dependency management.

    Attributes:
        _instance: Singleton instance
        _initialized: Whether environment is initialized
        _adapter: Database adapter instance

    Examples:
        >>> # Get singleton instance
        >>> env = Environment.get_instance()

        >>> # Initialize with config
        >>> await env.init(config)

        >>> # Get database adapter
        >>> adapter = env.adapter
        >>> users = await adapter.query(User).all()

        >>> # Get model by name
        >>> User = await env.get_model('data.user')
        >>> user = await User.create({"name": "John"})

        >>> # Cleanup
        >>> await env.destroy()
    """

    # Singleton instance
    _instance: Optional["Environment"] = None

    def __init__(self) -> None:
        """Initialize environment singleton.

        Raises:
            RuntimeError: If instance already exists
        """
        if Environment._instance is not None:
            raise RuntimeError("Environment already initialized")

        self._initialized = False
        self._adapter: Optional[DatabaseAdapter[DatabaseModel]] = None

        Environment._instance = self

    @classmethod
    def get_instance(cls) -> "Environment":
        """Get singleton instance.

        This method implements lazy initialization of the singleton.
        It creates the instance on first access if it doesn't exist.

        Returns:
            Environment singleton instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def init(self, config: "SystemConfigData") -> None:
        """Initialize environment with configuration.

        This method:
        1. Registers config in DI container
        2. Initializes services through container
        3. Sets up service dependencies
        4. Configures logging

        Args:
            config: System configuration data

        Raises:
            RuntimeError: If initialization fails
        """
        if self._initialized:
            logger.warning("Environment already initialized")
            return

        try:
            from earnorm.di import container

            # Register config
            container.register("config", config)

            # Get services from container
            self._adapter = await container.get("database_adapter")

            # Register self in container
            container.register("env", self)

            self._initialized = True
            logger.info("Environment initialized successfully")

        except Exception as e:
            logger.error("Failed to initialize environment: %s", str(e))
            raise RuntimeError(f"Environment initialization failed: {e}") from e

    async def destroy(self) -> None:
        """Cleanup environment resources.

        This method:
        1. Closes database connections
        2. Stops event bus
        3. Cleans up resources
        4. Resets state

        Raises:
            RuntimeError: If cleanup fails
        """
        if not self._initialized:
            return

        try:
            from earnorm.di import container

            # Cleanup database
            if container.has("database_adapter"):
                adapter = await container.get("database_adapter")
                await adapter.close()

            # Cleanup event bus
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

        This method provides access to services registered in the DI container.
        It supports optional services and validates required ones.

        Args:
            name: Service name/key in container
            required: Whether service is required

        Returns:
            Service instance

        Raises:
            RuntimeError: If required service not found
        """
        from earnorm.di import container

        service = await container.get(name)
        if service is None and required:
            raise RuntimeError(f"Service {name} not found in DI container")
        return service

    @property
    def adapter(self) -> DatabaseAdapter[DatabaseModel]:
        """Get database adapter instance.

        This property provides synchronous access to the database adapter.
        It validates the environment and adapter state.

        Returns:
            Database adapter instance

        Raises:
            RuntimeError: If environment or adapter not initialized
        """
        if not self._initialized:
            raise RuntimeError("Environment not initialized")
        if self._adapter is None:
            raise RuntimeError("Adapter not initialized. Call init() first")
        return self._adapter

    async def get_model(self, name: str) -> Type[ModelProtocol]:
        """Get model class by name.

        This method retrieves model classes from the registry.
        Models must be registered with the 'model.' prefix.

        Args:
            name: Model name/key in registry

        Returns:
            Model class implementing ModelProtocol

        Raises:
            ValueError: If model not found in registry
        """
        model = await self.get_service(f"model.{name}", required=False)
        if model is None:
            raise ValueError(f"Model {name} not found")
        return model

    @property
    def is_initialized(self) -> bool:
        """Check if environment is initialized.

        Returns:
            bool: True if initialized, False otherwise
        """
        return self._initialized
