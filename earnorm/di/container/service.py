"""Service manager module for dependency injection.

This module provides service management functionality for the DI system.
The service manager is responsible for:

1. Service Registration:
   - Registration with different lifecycles (singleton/transient)
   - Service instance caching
   - Service initialization

2. Service Retrieval:
   - Synchronous and asynchronous retrieval
   - Lifecycle-aware instance creation
   - Instance caching for singletons

3. Lifecycle Management:
   - Service initialization
   - Resource cleanup
   - Event handling

Example:
    >>> manager = ServiceManager()
    >>>
    >>> # Register services
    >>> manager.register("config", SystemConfig())
    >>> manager.register("database", Database, "transient")
    >>>
    >>> # Get services
    >>> config = await manager.get("config")
    >>> db = await manager.get("database")
"""

import logging
from typing import Any, Dict, Optional

from earnorm.config.model import SystemConfig
from earnorm.di.lifecycle import LifecycleAware
from earnorm.di.lifecycle.manager import LifecycleManager

logger = logging.getLogger(__name__)


class ServiceManager(LifecycleAware):
    """Service manager implementation for dependency injection.

    The ServiceManager class manages service registration, retrieval, and lifecycle.
    It supports both singleton and transient services, with async initialization.

    Features:
        - Service registration with lifecycle management
        - Synchronous and asynchronous service retrieval
        - Instance caching for singleton services
        - Lifecycle event handling
        - Resource cleanup

    Example:
        >>> manager = ServiceManager()
        >>>
        >>> # Register services
        >>> manager.register("config", SystemConfig())
        >>> manager.register("database", Database, "transient")
        >>>
        >>> # Get services
        >>> config = await manager.get("config")
        >>> db = await manager.get("database")
    """

    def __init__(self) -> None:
        """Initialize service manager.

        This constructor sets up:
        1. Service registry for storing service definitions
        2. Instance cache for singleton services
        3. Lifecycle manager for handling service lifecycles
        4. Configuration storage
        """
        self._services: Dict[str, Any] = {}
        self._instances: Dict[str, Any] = {}
        self._lifecycle = LifecycleManager()
        self._config: Optional[SystemConfig] = None

    async def init(self) -> None:
        """Initialize service manager.

        This method:
        1. Validates configuration
        2. Initializes lifecycle manager
        3. Sets up event handlers

        Raises:
            RuntimeError: If configuration is not set
            ServiceInitializationError: If initialization fails
        """
        if self._config is None:
            raise RuntimeError("Config not set")
        await self._lifecycle.init(self)

    async def destroy(self) -> None:
        """Destroy service manager and cleanup resources.

        This method:
        1. Destroys all managed services
        2. Clears instance cache
        3. Cleans up lifecycle manager
        """
        await self._lifecycle.destroy_all()

    @property
    def id(self) -> Optional[str]:
        """Get service manager ID.

        Returns:
            Service manager identifier
        """
        return "service_manager"

    @property
    def data(self) -> Dict[str, str]:
        """Get service manager data.

        Returns:
            Dictionary containing:
            - services: Number of registered services
            - instances: Number of cached instances
        """
        return {
            "services": str(len(self._services)),
            "instances": str(len(self._instances)),
        }

    async def setup(self, config: SystemConfig) -> None:
        """Setup service manager with configuration.

        This method:
        1. Stores configuration for later use
        2. Initializes the manager
        3. Sets up required services

        Args:
            config: System configuration instance

        Raises:
            ServiceInitializationError: If setup fails
        """
        self._config = config
        await self.init()

    def register(self, name: str, service: Any, lifecycle: str = "singleton") -> None:
        """Register a service with the manager.

        This method registers a service that can be retrieved using get() or get_sync().
        Services can be registered with different lifecycles:
        - singleton: One instance shared across the application
        - transient: New instance created for each request

        Args:
            name: Unique name to identify the service
            service: Service instance or class to register
            lifecycle: Service lifecycle ("singleton" or "transient")

        Raises:
            ValueError: If lifecycle is invalid
            ServiceInitializationError: If service initialization fails

        Example:
            >>> manager.register("config", SystemConfig())
            >>> manager.register("database", Database, "transient")
        """
        self._services[name] = {"service": service, "lifecycle": lifecycle}

    def has(self, name: str) -> bool:
        """Check if a service exists in the manager.

        Args:
            name: Name of the service to check

        Returns:
            True if service exists, False otherwise

        Example:
            >>> assert manager.has("config")
            >>> assert not manager.has("unknown")
        """
        return name in self._services

    async def get_sync(self, name: str) -> Optional[Any]:
        """Get a service instance synchronously.

        This method attempts to retrieve a service synchronously.
        It should only be used for services that:
        1. Are already initialized
        2. Don't require async initialization

        Args:
            name: Name of the service to retrieve

        Returns:
            Service instance if found and initialized, None otherwise

        Example:
            >>> config = await manager.get_sync("config")
            >>> assert isinstance(config, SystemConfig)
        """
        if not self.has(name):
            return None

        # Get service info
        service_info = self._services[name]
        service = service_info["service"]
        lifecycle = service_info["lifecycle"]

        # Return cached instance for singletons
        if lifecycle == "singleton" and name in self._instances:
            return self._instances[name]

        # Create new instance
        instance = await self._create_instance_sync(service)

        # Cache singleton instances
        if lifecycle == "singleton":
            self._instances[name] = instance

        return instance

    async def get(self, name: str) -> Optional[Any]:
        """Get a service instance asynchronously.

        This method supports services that require async initialization.
        It should be used when:
        1. Service has async initialization logic
        2. Service depends on other async services
        3. Service creation involves async operations

        Args:
            name: Name of the service to retrieve

        Returns:
            Service instance if found, None otherwise

        Example:
            >>> database = await manager.get("database")
            >>> await database.connect()
        """
        if not self.has(name):
            return None

        # Get service info
        service_info = self._services[name]
        service = service_info["service"]
        lifecycle = service_info["lifecycle"]

        # Return cached instance for singletons
        if lifecycle == "singleton" and name in self._instances:
            return self._instances[name]

        # Create new instance
        instance = await self._create_instance(service)

        # Cache singleton instances
        if lifecycle == "singleton":
            self._instances[name] = instance

        return instance

    async def _create_instance_sync(self, service: Any) -> Any:
        """Create a service instance synchronously.

        This method creates a new instance of a service without async initialization.

        Args:
            service: Service class or instance to instantiate

        Returns:
            Created service instance

        Raises:
            ServiceInitializationError: If instance creation fails
        """
        if isinstance(service, type):
            return service()
        return service

    async def _create_instance(self, service: Any) -> Any:
        """Create a service instance asynchronously.

        This method creates a new instance of a service with async initialization.

        Args:
            service: Service class or instance to instantiate

        Returns:
            Created service instance

        Raises:
            ServiceInitializationError: If instance creation fails
        """
        if isinstance(service, type):
            instance = service()
            if hasattr(instance, "init"):
                await instance.init()
            return instance
        return service

    def unregister(self, name: str) -> None:
        """Unregister a service from the manager.

        This method:
        1. Removes service from registry
        2. Removes cached instance if any
        3. Cleans up resources

        Args:
            name: Name of the service to unregister

        Example:
            >>> manager.unregister("config")
            >>> assert not manager.has("config")
        """
        if name in self._services:
            del self._services[name]
        if name in self._instances:
            del self._instances[name]
