"""Factory management."""

import logging
from typing import Any, Callable, Dict

logger = logging.getLogger(__name__)


class FactoryManager:
    """Factory manager."""

    def __init__(self) -> None:
        """Initialize manager."""
        self._factories: Dict[str, Callable[..., Any]] = {}

    def register(self, name: str, factory: Callable[..., Any]) -> None:
        """Register factory."""
        self._factories[name] = factory

    def has(self, name: str) -> bool:
        """Check if factory exists."""
        return name in self._factories

    async def create(self, name: str, container: Any) -> Any:
        """Create service using factory."""
        if name not in self._factories:
            raise KeyError(f"Factory not found: {name}")

        factory = self._factories[name]
        return await factory(container)

    async def init(self, **config: Any) -> None:
        """Initialize manager."""
        # No initialization needed for now
        pass

    def unregister(self, name: str) -> None:
        """Unregister factory.

        Args:
            name: Factory name
        """
        if name in self._factories:
            del self._factories[name]
