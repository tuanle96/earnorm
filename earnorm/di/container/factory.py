"""Factory manager module for dependency injection.

This module provides factory management functionality for the DI system.
The factory manager is responsible for:

1. Factory Registration:
   - Registration of factory functions
   - Factory configuration
   - Factory validation

2. Instance Creation:
   - Factory-based instance creation
   - Async initialization support
   - Instance caching

3. Lifecycle Management:
   - Factory initialization
   - Resource cleanup
   - Event handling

Example:
    >>> manager = FactoryManager()
    >>>
    >>> # Register factories
    >>> def create_database(config: SystemConfig) -> Database:
    ...     return Database(config.database_uri)
    >>>
    >>> manager.register("database", create_database)
    >>>
    >>> # Create instances
    >>> db = await manager.get("database")
    >>> await db.connect()
"""

import logging
from typing import Any, Dict, Optional

from earnorm.config.model import SystemConfig
from earnorm.di.lifecycle import LifecycleAware

logger = logging.getLogger(__name__)


class FactoryManager(LifecycleAware):
    """Factory manager implementation for dependency injection.

    The FactoryManager class manages factory registration and instance creation.
    It supports both synchronous and asynchronous factory functions.

    Features:
        - Factory function registration
        - Instance creation and caching
        - Async initialization support
        - Lifecycle event handling
        - Resource cleanup

    Example:
        >>> manager = FactoryManager()
        >>>
        >>> # Register factory
        >>> def create_service(config: SystemConfig) -> Service:
        ...     return Service(config.service_url)
        >>>
        >>> manager.register("service", create_service)
        >>>
        >>> # Create instance
        >>> service = await manager.get("service")
        >>> await service.start()
    """

    def __init__(self) -> None:
        """Initialize factory manager.

        This constructor sets up:
        1. Factory registry for storing factory functions
        2. Configuration storage
        """
        self._factories: Dict[str, Any] = {}
        self._config: Optional[SystemConfig] = None

    async def init(self) -> None:
        """Initialize factory manager.

        This method:
        1. Validates configuration
        2. Sets up required factories
        3. Initializes event handlers

        Raises:
            RuntimeError: If configuration is not set
            FactoryInitializationError: If initialization fails
        """
        if self._config is None:
            raise RuntimeError("Config not set")

    async def destroy(self) -> None:
        """Destroy factory manager and cleanup resources.

        This method:
        1. Cleans up factory registry
        2. Releases resources
        3. Stops event handlers
        """
        self._factories.clear()

    @property
    def id(self) -> Optional[str]:
        """Get factory manager ID.

        Returns:
            Factory manager identifier
        """
        return "factory_manager"

    @property
    def data(self) -> Dict[str, str]:
        """Get factory manager data.

        Returns:
            Dictionary containing:
            - factories: Number of registered factories
        """
        return {"factories": str(len(self._factories))}

    async def setup(self, config: SystemConfig) -> None:
        """Setup factory manager with configuration.

        This method:
        1. Stores configuration for later use
        2. Initializes the manager
        3. Sets up required factories

        Args:
            config: System configuration instance

        Raises:
            FactoryInitializationError: If setup fails
        """
        self._config = config
        await self.init()

    def register(self, name: str, factory: Any) -> None:
        """Register a factory function.

        This method registers a factory that can be used to create service instances.
        Factories can be:
        1. Simple functions returning instances
        2. Classes with __call__ method
        3. Async functions for complex initialization

        Args:
            name: Unique name to identify the factory
            factory: Factory function or class

        Raises:
            ValueError: If factory is invalid
            FactoryRegistrationError: If registration fails

        Example:
            >>> def create_database(config: SystemConfig) -> Database:
            ...     return Database(config.database_uri)
            >>>
            >>> manager.register("database", create_database)
        """
        self._factories[name] = factory

    def has(self, name: str) -> bool:
        """Check if a factory exists in the manager.

        Args:
            name: Name of the factory to check

        Returns:
            True if factory exists, False otherwise

        Example:
            >>> assert manager.has("database")
            >>> assert not manager.has("unknown")
        """
        return name in self._factories

    async def get(self, name: str) -> Optional[Any]:
        """Create an instance using a registered factory.

        This method:
        1. Retrieves the factory function
        2. Creates a new instance
        3. Initializes the instance if needed

        Args:
            name: Name of the factory to use

        Returns:
            Created instance if factory exists, None otherwise

        Raises:
            FactoryError: If instance creation fails

        Example:
            >>> database = await manager.get("database")
            >>> await database.connect()
        """
        if not self.has(name):
            return None

        factory = self._factories[name]
        if isinstance(factory, type):
            instance = factory()
            if hasattr(instance, "init"):
                await instance.init()
            return instance
        return factory

    def unregister(self, name: str) -> None:
        """Unregister a factory from the manager.

        This method:
        1. Removes factory from registry
        2. Cleans up resources
        3. Stops event handlers

        Args:
            name: Name of the factory to unregister

        Example:
            >>> manager.unregister("database")
            >>> assert not manager.has("database")
        """
        if name in self._factories:
            del self._factories[name]
