"""Service management."""

import logging
from typing import Any, Dict

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
        """Register service."""
        self._services[name] = {"service": service, "lifecycle": lifecycle}

    def has(self, name: str) -> bool:
        """Check if service exists."""
        return name in self._services

    async def get(self, name: str) -> Any:
        """Get service instance."""
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

    async def _create_instance(self, service: Any) -> Any:
        """Create service instance."""
        if isinstance(service, type):
            # Class-based service
            return service()
        elif callable(service):
            # Factory function
            return await service()
        else:
            # Value service
            return service

    async def init(self, **config: Any) -> None:
        """Initialize manager."""
        # Initialize lifecycle manager
        await self._lifecycle.init(**config)
