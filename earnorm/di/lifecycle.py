"""Service lifecycle management."""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LifecycleHooks(Protocol):
    """Service lifecycle hooks protocol.

    Services can implement this protocol to handle lifecycle events.
    """

    async def on_init(self) -> None:
        """Called when service is initialized."""
        ...

    async def on_start(self) -> None:
        """Called when service is started."""
        ...

    async def on_stop(self) -> None:
        """Called when service is stopped."""
        ...

    async def on_cleanup(self) -> None:
        """Called when service is cleaned up."""
        ...


class LifecycleManager:
    """Manages service lifecycle.

    Handles initialization, startup, shutdown and cleanup of services.
    """

    def __init__(self) -> None:
        """Initialize lifecycle manager."""
        self._services: dict[str, Any] = {}

    async def init_service(self, service: Any) -> None:
        """Initialize service.

        Args:
            service: Service instance
        """
        if isinstance(service, LifecycleHooks):
            await service.on_init()

    async def start_service(self, service: Any) -> None:
        """Start service.

        Args:
            service: Service instance
        """
        if isinstance(service, LifecycleHooks):
            await service.on_start()

    async def stop_service(self, service: Any) -> None:
        """Stop service.

        Args:
            service: Service instance
        """
        if isinstance(service, LifecycleHooks):
            await service.on_stop()

    async def cleanup_service(self, service: Any) -> None:
        """Clean up service.

        Args:
            service: Service instance
        """
        if isinstance(service, LifecycleHooks):
            await service.on_cleanup()

    def register(self, key: str, service: Any) -> None:
        """Register service.

        Args:
            key: Service key
            service: Service instance
        """
        self._services[key] = service

    def get(self, key: str) -> Any:
        """Get service by key.

        Args:
            key: Service key

        Returns:
            Service instance
        """
        return self._services[key]


# Global lifecycle manager instance
lifecycle_manager = LifecycleManager()
