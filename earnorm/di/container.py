"""Dependency injection container."""

from typing import Any, Dict, Protocol, runtime_checkable


@runtime_checkable
class Container(Protocol):
    """Container protocol."""

    async def init_resources(
        self, *, mongo_uri: str, database: str, **kwargs: Any
    ) -> None:
        """Initialize container resources."""
        ...

    async def cleanup(self) -> None:
        """Cleanup container resources."""
        ...


class DIContainer:
    """Dependency injection container implementation."""

    def __init__(self) -> None:
        """Initialize container."""
        self._services: Dict[str, Any] = {}

    def register(self, key: str, service: Any) -> None:
        """Register service."""
        self._services[key] = service

    async def init_resources(
        self, *, mongo_uri: str, database: str, **kwargs: Any
    ) -> None:
        """Initialize container resources.

        Args:
            mongo_uri: MongoDB connection URI
            database: Database name
            **kwargs: Additional configuration
        """
        # Implementation here

    async def cleanup(self) -> None:
        """Cleanup container resources."""
        # Implementation here
