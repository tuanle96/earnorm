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

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional, Type

from earnorm.base.database.adapter import DatabaseAdapter
from earnorm.di import container
from earnorm.types.models import ModelProtocol

if TYPE_CHECKING:
    from earnorm.config.data import SystemConfigData

logger = logging.getLogger(__name__)


class Environment:
    """Application environment singleton."""

    _instance: Optional[Environment] = None
    _initialized: bool = False
    _adapter: Optional[DatabaseAdapter[Any, Any]] = None
    _logger: Optional[logging.Logger] = None

    def __init__(self) -> None:
        """Initialize environment."""
        if Environment._instance is not None:
            raise RuntimeError("Environment already instantiated")
        Environment._instance = self
        self._logger = logging.getLogger(__name__)

    @property
    def logger(self) -> logging.Logger:
        """Get logger instance.

        Returns:
            Logger instance for environment

        Raises:
            RuntimeError: If logger is not initialized
        """
        if self._logger is None:
            raise RuntimeError("Logger not initialized")
        return self._logger

    @logger.setter
    def logger(self, value: logging.Logger) -> None:
        """Set logger instance.

        Args:
            value: Logger instance to use
        """
        self._logger = value

    @classmethod
    def get_instance(cls) -> Environment:
        """Get singleton instance.

        This method implements the singleton pattern, ensuring only one Environment
        instance exists per application. If no instance exists, it creates one.

        Returns:
            Environment instance

        Examples:
            >>> env1 = Environment.get_instance()
            >>> env2 = Environment.get_instance()
            >>> assert env1 is env2  # Same instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def init(self, config: "SystemConfigData") -> None:
        """Initialize environment.

        This method:
        1. Loads configuration
        2. Sets up services
        3. Initializes database
        4. Registers models

        Args:
            config: System configuration data

        Raises:
            RuntimeError: If already initialized
        """
        if self._initialized:
            raise RuntimeError("Environment already initialized")

        # Register config in container
        container.register("config", config)

        # Get adapter from container
        self._adapter = await container.get("database_adapter")
        if self._adapter is None:
            raise RuntimeError("Failed to get database adapter")

        # Inject env into adapter
        self._adapter.env = self

        # Initialize adapter
        await self._adapter.init()

        self._initialized = True
        self.logger.info("Environment initialized successfully")

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
        service = await container.get(name)
        if service is None and required:
            raise RuntimeError(f"Service {name} not found in DI container")
        return service

    @property
    def adapter(self) -> DatabaseAdapter[Any, Any]:
        """Get database adapter.

        Returns:
            Database adapter instance

        Raises:
            RuntimeError: If environment is not initialized
        """
        if not self._initialized:
            raise RuntimeError("Environment not initialized")

        if self._adapter is None:
            raise RuntimeError("Database adapter not found")

        # Inject env into adapter
        self._adapter.env = self

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
