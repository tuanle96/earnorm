"""Service management."""

import inspect
import logging
from typing import Any, Dict, Optional

from earnorm.di.lifecycle.manager import LifecycleManager

logger = logging.getLogger(__name__)


class ServiceManager:
    """Service manager."""

    def __init__(self) -> None:
        """Initialize manager."""
        self._services: Dict[str, Dict[str, Any]] = {}
        self._instances: Dict[str, Any] = {}
        self._lifecycle = LifecycleManager()

    def register(self, name: str, service: Any, lifecycle: str = "singleton") -> None:
        """Register service.

        Args:
            name: Service name
            service: Service instance or class
            lifecycle: Service lifecycle ('singleton' or 'transient')
        """
        self._services[name] = {"service": service, "lifecycle": lifecycle}

    def has(self, name: str) -> bool:
        """Check if service exists.

        Args:
            name: Service name

        Returns:
            True if service exists, False otherwise
        """
        return name in self._services

    def get_sync(self, name: str) -> Optional[Any]:
        """Get service instance synchronously.

        This method only works for services that:
        1. Are already registered and initialized
        2. Don't require async initialization

        Args:
            name: Service name

        Returns:
            Service instance or None if service requires async initialization

        Raises:
            KeyError: If service not found
        """
        if name not in self._services:
            raise KeyError(f"Service not found: {name}")

        # Return cached instance for singleton
        if self._services[name]["lifecycle"] == "singleton" and name in self._instances:
            return self._instances[name]

        # Create new instance if possible
        service = self._services[name]["service"]

        # Check if service requires async initialization
        if inspect.iscoroutinefunction(service) or (
            isinstance(service, type) and hasattr(service, "__await__")
        ):
            return None

        instance = self._create_instance_sync(service)

        # Cache singleton instance
        if self._services[name]["lifecycle"] == "singleton":
            self._instances[name] = instance

        return instance

    async def get(self, name: str) -> Any:
        """Get service instance asynchronously.

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
        if name not in self._services:
            raise KeyError(f"Service not found: {name}")

        # Return cached instance for singleton
        if self._services[name]["lifecycle"] == "singleton" and name in self._instances:
            return self._instances[name]

        # Create new instance
        service = self._services[name]["service"]
        instance = await self._create_instance(service)

        # Cache singleton instance
        if self._services[name]["lifecycle"] == "singleton":
            self._instances[name] = instance

        return instance

    def _create_instance_sync(self, service: Any) -> Any:
        """Create service instance synchronously.

        Args:
            service: Service class or factory

        Returns:
            Service instance
        """
        if isinstance(service, type):
            # Class-based service
            return service()
        elif callable(service):
            # Factory function
            return service()
        else:
            # Value service
            return service

    async def _create_instance(self, service: Any) -> Any:
        """Create service instance asynchronously.

        Args:
            service: Service class or factory

        Returns:
            Service instance
        """
        if isinstance(service, type):
            # Class-based service
            instance = service()
            if hasattr(instance, "__await__"):
                instance = await instance
            return instance
        elif callable(service):
            # Factory function
            result = service()
            if inspect.iscoroutine(result):
                result = await result
            return result
        else:
            # Value service
            return service

    async def init(self, **config: Any) -> None:
        """Initialize manager.

        Args:
            **config: Configuration options
        """
        # Initialize lifecycle manager
        await self._lifecycle.init(**config)

    def unregister(self, name: str) -> None:
        """Unregister service.

        Args:
            name: Service name
        """
        if name in self._instances:
            del self._instances[name]
        if name in self._services:
            del self._services[name]
