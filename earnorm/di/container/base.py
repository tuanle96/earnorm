"""Container module for dependency injection.

This module provides the base container implementation for the dependency injection system.
The container is responsible for:

1. Service Management:
   - Registration of services with different lifecycles (singleton/transient)
   - Service retrieval and caching
   - Service lifecycle management

2. Factory Management:
   - Registration of factory functions
   - Factory-based service creation
   - Async factory support

3. Dependency Resolution:
   - Service dependency tracking
   - Circular dependency detection
   - Dependency order resolution

4. Lifecycle Management:
   - Service initialization
   - Resource cleanup
   - Event handling

Example:
    >>> container = Container()
    >>> container.register("config", SystemConfig())
    >>> container.register_factory("database", create_database)
    >>>
    >>> # Get service
    >>> config = await container.get("config")
    >>> db = await container.get("database")
"""

import logging
from typing import Any, Callable, Dict

from earnorm.config.model import SystemConfig
from earnorm.di.container.factory import FactoryManager
from earnorm.di.container.interfaces import ContainerInterface
from earnorm.di.container.service import ServiceManager
from earnorm.di.resolver.dependency import DependencyResolver
from earnorm.exceptions import ServiceNotFoundError

logger = logging.getLogger(__name__)


class Container(ContainerInterface):
    """Container implementation for dependency injection.

    The Container class provides a central registry for all services and their dependencies.
    It manages service lifecycles, factory creation, and dependency resolution.

    Features:
        - Service registration with lifecycle management
        - Factory function support
        - Dependency resolution
        - Caching for singleton services
        - Async initialization support

    Example:
        >>> container = Container()
        >>>
        >>> # Register services
        >>> container.register("service", MyService())
        >>> container.register_factory("factory", create_service)
        >>>
        >>> # Get services
        >>> service = await container.get("service")
        >>> factory = await container.get("factory")
    """

    def __init__(self) -> None:
        """Initialize container with required managers.

        This constructor sets up:
        1. Service manager for service lifecycle management
        2. Factory manager for factory-based service creation
        3. Dependency resolver for handling service dependencies
        4. Cache for storing singleton instances
        """
        self._service_manager: ServiceManager = ServiceManager()
        self._factory_manager: FactoryManager = FactoryManager()
        self._resolver: DependencyResolver = DependencyResolver()
        self._cache: Dict[str, Any] = {}

    async def init(self, config: SystemConfig) -> None:
        """Initialize container and all managers.

        This method:
        1. Sets up the service manager with configuration
        2. Initializes the factory manager
        3. Configures the dependency resolver

        Args:
            config: System configuration instance containing all settings

        Raises:
            ServiceInitializationError: If service initialization fails
            FactoryError: If factory initialization fails
            CircularDependencyError: If circular dependencies are detected
        """
        # Initialize service manager
        await self._service_manager.setup(config)

        # Initialize factory manager
        await self._factory_manager.setup(config)

        # Initialize resolver
        await self._resolver.setup(config)

    def register(self, name: str, service: Any, lifecycle: str = "singleton") -> None:
        """Register a service with the container.

        This method registers a service that can later be retrieved using get().
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
            >>> container.register("config", SystemConfig())
            >>> container.register("database", Database, "transient")
        """
        self._service_manager.register(name, service, lifecycle)

    def register_factory(self, name: str, factory: Callable[..., Any]) -> None:
        """Register a factory function for creating services.

        Factory functions are used when:
        1. Service creation requires complex logic
        2. Services need runtime configuration
        3. Services have dependencies that need to be injected

        Args:
            name: Unique name to identify the factory
            factory: Function that creates service instances

        Example:
            >>> def create_database(config: SystemConfig) -> Database:
            ...     return Database(config.database_uri)
            >>>
            >>> container.register_factory("database", create_database)
        """
        self._factory_manager.register(name, factory)

    async def get(self, name: str) -> Any:
        """Get a service instance synchronously.

        This method attempts to retrieve a service in the following order:
        1. Check cache for existing singleton instance
        2. Try service manager for registered service
        3. Try factory manager for factory-created service

        Args:
            name: Name of the service to retrieve

        Returns:
            Service instance

        Raises:
            ServiceNotFoundError: If service is not found
            ServiceInitializationError: If service initialization fails

        Example:
            >>> config = await container.get("config")
            >>> assert isinstance(config, SystemConfig)
        """
        # Check cache first
        if name in self._cache:
            return self._cache[name]

        # Try service manager
        if self._service_manager.has(name):
            service = await self._service_manager.get_sync(name)
            if service is not None:
                self._cache[name] = service
                return service

        # Try factory manager
        if self._factory_manager.has(name):
            service = await self._factory_manager.get(name)
            if service is not None:
                self._cache[name] = service
                return service

        raise ServiceNotFoundError(f"Service not found: {name}")

    def has(self, name: str) -> bool:
        """Check if a service exists in the container.

        This method checks:
        1. Cache for existing singleton instances
        2. Service manager for registered services
        3. Factory manager for registered factories

        Args:
            name: Name of the service to check

        Returns:
            True if service exists, False otherwise

        Example:
            >>> assert container.has("config")
            >>> assert not container.has("unknown")
        """
        return (
            name in self._cache
            or self._service_manager.has(name)
            or self._factory_manager.has(name)
        )

    def unregister(self, name: str) -> None:
        """Unregister a service or factory from the container.

        This method:
        1. Removes service from cache
        2. Unregisters from service manager
        3. Unregisters from factory manager

        Args:
            name: Name of the service or factory to unregister

        Example:
            >>> container.unregister("config")
            >>> assert not container.has("config")
        """
        # Remove from cache
        if name in self._cache:
            del self._cache[name]

        # Remove from managers
        self._service_manager.unregister(name)
        self._factory_manager.unregister(name)
