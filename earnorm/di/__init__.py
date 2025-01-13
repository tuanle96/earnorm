"""Dependency injection module for EarnORM."""

from typing import Any, Optional, Protocol, TypeVar, runtime_checkable

from earnorm.di.container import EarnORMContainer
from earnorm.di.lifecycle import LifecycleHooks, LifecycleManager

T = TypeVar("T")


@runtime_checkable
class Container(Protocol):
    """Protocol for dependency injection containers."""

    async def init(self, **kwargs: Any) -> None:
        """Initialize container."""
        ...

    async def cleanup(self) -> None:
        """Cleanup container resources."""
        ...

    def get(self, key: str) -> Any:
        """Get service by key."""
        ...

    def register(self, key: str, service: Any) -> None:
        """Register service."""
        ...


class DIContainer:
    """Global dependency injection container."""

    _instance: Optional[Container] = None
    _lifecycle: Optional[LifecycleManager] = None

    @classmethod
    def get_instance(cls) -> Container:
        """Get container instance."""
        if cls._instance is None:
            cls._instance = EarnORMContainer()
        return cls._instance

    @classmethod
    def get_lifecycle(cls) -> LifecycleManager:
        """Get lifecycle manager."""
        if cls._lifecycle is None:
            cls._lifecycle = LifecycleManager()
        return cls._lifecycle

    @classmethod
    async def init(cls, **kwargs: Any) -> None:
        """Initialize container."""
        container = cls.get_instance()
        await container.init(**kwargs)

    @classmethod
    async def cleanup(cls) -> None:
        """Cleanup container resources."""
        if cls._instance is not None:
            await cls._instance.cleanup()
            cls._instance = None

    @classmethod
    def get(cls, key: str) -> Any:
        """Get service by key."""
        return cls.get_instance().get(key)

    @classmethod
    def register(cls, key: str, service: Any) -> None:
        """Register service."""
        cls.get_instance().register(key, service)


# Global instances
container = DIContainer()
lifecycle = container.get_lifecycle()

__all__ = [
    "Container",
    "LifecycleHooks",
    "LifecycleManager",
    "container",
    "lifecycle",
]
