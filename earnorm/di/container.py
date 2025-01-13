"""Container for EarnORM."""

from typing import Any, Dict, Generic, Optional, Type, TypeVar

from .types import BaseManager

T = TypeVar("T", bound=BaseManager)


class Container(Generic[T]):
    """Container for managing dependencies."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize container with config."""
        self._instances: Dict[Type[T], T] = {}
        self._config = config or {}

    def register(self, protocol: Type[T], implementation: Type[T]) -> None:
        """Register a service implementation for a protocol.

        Args:
            protocol: The protocol/interface type
            implementation: The concrete implementation class
        """
        if protocol not in self._instances:
            self._instances[protocol] = implementation()

    def get(self, protocol: Type[T]) -> T:
        """Get an instance of a registered service.

        Args:
            protocol: The protocol/interface type to retrieve

        Returns:
            The registered service instance

        Raises:
            KeyError: If no implementation is registered for the protocol
        """
        if protocol not in self._instances:
            raise KeyError(f"No implementation registered for {protocol.__name__}")
        return self._instances[protocol]

    async def init(self) -> None:
        """Initialize all registered services."""
        for service in self._instances.values():
            service: BaseManager
            await service.init()

    async def cleanup(self) -> None:
        """Clean up all registered services."""
        for service in reversed(list(self._instances.values())):
            service: BaseManager
            await service.cleanup()


# Global container instance
container = Container[BaseManager]({})
