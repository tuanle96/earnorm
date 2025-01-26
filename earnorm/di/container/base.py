"""DI container implementation."""

import logging
from typing import Any, Callable, Dict

from earnorm.di.container.factory import FactoryManager
from earnorm.di.container.interfaces import ContainerInterface
from earnorm.di.container.service import ServiceManager
from earnorm.di.resolver.dependency import DependencyResolver

logger = logging.getLogger(__name__)


class Container(ContainerInterface):
    """DI container implementation."""

    def __init__(self) -> None:
        """Initialize container."""
        self._service_manager = ServiceManager()
        self._factory_manager = FactoryManager()
        self._resolver = DependencyResolver()
        self._cache: Dict[str, Any] = {}

    def register(self, name: str, service: Any, lifecycle: str = "singleton") -> None:
        """Register service.

        Args:
            name: Service name
            service: Service instance or class
            lifecycle: Service lifecycle ('singleton' or 'transient')
        """
        self._service_manager.register(name, service, lifecycle)
        # Cache singleton services
        if lifecycle == "singleton":
            self._cache[name] = service

    def register_factory(self, name: str, factory: Callable[..., Any]) -> None:
        """Register factory.

        Args:
            name: Factory name
            factory: Factory function
        """
        self._factory_manager.register(name, factory)

    def get(self, name: str) -> Any:
        """Get service synchronously.

        This method only works for services that:
        1. Are already registered and initialized
        2. Don't require async initialization

        Args:
            name: Service name

        Returns:
            Service instance

        Raises:
            KeyError: If service not found
            RuntimeError: If service requires async initialization
        """
        # Check cache first
        if name in self._cache:
            return self._cache[name]

        # Then try service manager
        if self._service_manager.has(name):
            service = self._service_manager.get_sync(name)
            if service is not None:
                self._cache[name] = service
                return service
            raise RuntimeError(f"Service {name} requires async initialization")

        raise KeyError(f"Service not found: {name}")

    async def get_async(self, name: str) -> Any:
        """Get service asynchronously.

        This method works for all services, including those that:
        1. Need to be created on demand
        2. Require async initialization

        Args:
            name: Service name

        Returns:
            Service instance

        Raises:
            KeyError: If service not found
        """
        # Try factory first
        if self._factory_manager.has(name):
            service = await self._factory_manager.create(name, self)
            if isinstance(service, ContainerInterface):
                self._cache[name] = service
            return service

        # Then try service manager
        if self._service_manager.has(name):
            service = await self._service_manager.get(name)
            if isinstance(service, ContainerInterface):
                self._cache[name] = service
            return service

        raise KeyError(f"Service not found: {name}")

    def has(self, name: str) -> bool:
        """Check if service exists.

        Args:
            name: Service name

        Returns:
            True if service exists, False otherwise
        """
        return (
            name in self._cache
            or self._service_manager.has(name)
            or self._factory_manager.has(name)
        )

    async def init(self, **config: Any) -> None:
        """Initialize container.

        Args:
            **config: Configuration options
        """
        # Initialize service manager
        await self._service_manager.init(**config)

        # Initialize factory manager
        await self._factory_manager.init(**config)

        # Initialize resolver
        await self._resolver.init(**config)

    def unregister(self, name: str) -> None:
        """Unregister service or factory.

        Args:
            name: Service or factory name
        """
        # Remove from cache
        if name in self._cache:
            del self._cache[name]

        # Remove from managers
        if self._service_manager.has(name):
            self._service_manager.unregister(name)
        elif self._factory_manager.has(name):
            self._factory_manager.unregister(name)
