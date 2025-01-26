"""Container interfaces."""

from typing import Any, Callable, Protocol, runtime_checkable


@runtime_checkable
class ContainerInterface(Protocol):
    """Container interface."""

    def register(self, name: str, service: Any, lifecycle: str = "singleton") -> None:
        """Register service.

        Args:
            name: Service name
            service: Service instance or class
            lifecycle: Service lifecycle ("singleton" or "transient")
        """
        ...

    def register_factory(self, name: str, factory: Callable[..., Any]) -> None:
        """Register factory.

        Args:
            name: Factory name
            factory: Factory function
        """
        ...

    def unregister(self, name: str) -> None:
        """Unregister service or factory.

        Args:
            name: Service or factory name

        Examples:
            ```python
            container.unregister("my_service")
            ```
        """
        ...

    async def get(self, name: str) -> Any:
        """Get service.

        Args:
            name: Service name

        Returns:
            Service instance

        Raises:
            KeyError: If service not found
        """
        ...

    def has(self, name: str) -> bool:
        """Check if service exists.

        Args:
            name: Service name

        Returns:
            True if service exists
        """
        ...

    async def init(self, **config: Any) -> None:
        """Initialize container.

        Args:
            **config: Configuration options
        """
        ...
