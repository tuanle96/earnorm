"""Container interfaces."""

from typing import Any, Callable, Protocol


class ContainerInterface(Protocol):
    """Container interface."""

    def register(self, name: str, service: Any, lifecycle: str = "singleton") -> None:
        """Register service."""
        ...

    def register_factory(self, name: str, factory: Callable[..., Any]) -> None:
        """Register factory."""
        ...

    async def get(self, name: str) -> Any:
        """Get service."""
        ...

    def has(self, name: str) -> bool:
        """Check if service exists."""
        ...

    async def init(self, **config: Any) -> None:
        """Initialize container."""
        ...
