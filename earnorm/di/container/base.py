"""DI container implementation."""

import logging
from typing import Any, Callable

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

    def register(self, name: str, service: Any, lifecycle: str = "singleton") -> None:
        """Register service."""
        self._service_manager.register(name, service, lifecycle)

    def register_factory(self, name: str, factory: Callable[..., Any]) -> None:
        """Register factory."""
        self._factory_manager.register(name, factory)

    async def get(self, name: str) -> Any:
        """Get service."""
        # Try factory first
        if self._factory_manager.has(name):
            return await self._factory_manager.create(name, self)

        # Then try service
        if self._service_manager.has(name):
            return await self._service_manager.get(name)

        raise KeyError(f"Service not found: {name}")

    def has(self, name: str) -> bool:
        """Check if service exists."""
        return self._service_manager.has(name) or self._factory_manager.has(name)

    async def init(self, **config: Any) -> None:
        """Initialize container."""
        # Initialize service manager
        await self._service_manager.init(**config)

        # Initialize factory manager
        await self._factory_manager.init(**config)

        # Initialize resolver
        await self._resolver.init(**config)
