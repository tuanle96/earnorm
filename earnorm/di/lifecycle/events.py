"""Lifecycle events implementation."""

import logging
from typing import Any, Callable, Coroutine, Dict, List, TypeVar

from earnorm.di.lifecycle.manager import LifecycleAware

logger = logging.getLogger(__name__)

# Type aliases
T = TypeVar("T", bound=LifecycleAware)
Hook = Callable[[T], Coroutine[Any, Any, None]]


class LifecycleEvents:
    """Lifecycle events manager."""

    def __init__(self) -> None:
        """Initialize events."""
        self._events: Dict[str, List[Hook[Any]]] = {
            "before_init": [],
            "after_init": [],
            "before_destroy": [],
            "after_destroy": [],
        }

    def on(self, event: str) -> Callable[[Hook[T]], Hook[T]]:
        """Register event handler."""

        def decorator(func: Hook[T]) -> Hook[T]:
            if event not in self._events:
                raise ValueError(f"Invalid event: {event}")
            self._events[event].append(func)  # type: ignore
            return func

        return decorator

    async def emit(self, event: str, obj: LifecycleAware) -> None:
        """Emit event."""
        if event not in self._events:
            raise ValueError(f"Invalid event: {event}")

        for hook in self._events[event]:
            try:
                await hook(obj)
            except Exception as e:
                logger.error("Event hook failed: %s", str(e))
                raise EventError(f"Event {event} hook failed: {str(e)}")

    async def before_init(self, obj: LifecycleAware) -> None:
        """Emit before init event."""
        await self.emit("before_init", obj)

    async def after_init(self, obj: LifecycleAware) -> None:
        """Emit after init event."""
        await self.emit("after_init", obj)

    async def before_destroy(self, obj: LifecycleAware) -> None:
        """Emit before destroy event."""
        await self.emit("before_destroy", obj)

    async def after_destroy(self, obj: LifecycleAware) -> None:
        """Emit after destroy event."""
        await self.emit("after_destroy", obj)


class EventError(Exception):
    """Event error."""

    def __init__(self, message: str) -> None:
        """Initialize error."""
        self.message = message
        super().__init__(message)
