"""Lifecycle manager implementation."""

from typing import Dict, List, Optional, Protocol, Type, TypeVar, runtime_checkable

from earnorm.di.lifecycle.events import LifecycleEvents


@runtime_checkable
class LifecycleAware(Protocol):
    """Protocol for lifecycle aware objects."""

    async def init(self) -> None:
        """Initialize object."""
        ...

    async def destroy(self) -> None:
        """Destroy object."""
        ...

    @property
    def id(self) -> Optional[str]:
        """Get object ID."""
        ...

    @property
    def data(self) -> Dict[str, str]:
        """Get object data."""
        ...


T = TypeVar("T", bound=LifecycleAware)


class LifecycleManager:
    """Lifecycle manager."""

    def __init__(self) -> None:
        """Initialize manager."""
        self._objects: Dict[str, LifecycleAware] = {}
        self._events = LifecycleEvents()

    async def init(self, obj: T, name: Optional[str] = None) -> T:
        """Initialize object."""
        if not name:
            name = obj.__class__.__name__

        if name in self._objects:
            raise ValueError(f"Object {name} already initialized")

        # Emit events
        await self._events.before_init(obj)

        # Initialize object
        await obj.init()

        # Store object
        self._objects[name] = obj

        # Emit events
        await self._events.after_init(obj)

        return obj

    async def destroy(self, name: str) -> None:
        """Destroy object."""
        obj = self._objects.get(name)
        if not obj:
            return

        # Emit events
        await self._events.before_destroy(obj)

        # Destroy object
        await obj.destroy()

        # Remove object
        del self._objects[name]

        # Emit events
        await self._events.after_destroy(obj)

    async def destroy_all(self) -> None:
        """Destroy all objects."""
        for name in list(self._objects.keys()):
            await self.destroy(name)

    def get(self, name: str) -> Optional[LifecycleAware]:
        """Get object by name."""
        return self._objects.get(name)

    def get_all(self) -> List[LifecycleAware]:
        """Get all objects."""
        return list(self._objects.values())

    def get_by_type(self, type_: Type[T]) -> List[T]:
        """Get objects by type."""
        return [obj for obj in self._objects.values() if isinstance(obj, type_)]
