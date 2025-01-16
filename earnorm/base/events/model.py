"""Model events implementation."""

import logging
from typing import Any, Callable, Coroutine, Dict, List, TypeVar

from earnorm.base.models.interfaces import ModelInterface

logger = logging.getLogger(__name__)

# Type aliases
M = TypeVar("M", bound=ModelInterface)
Hook = Callable[[M], Coroutine[Any, Any, None]]


class ModelEvents:
    """Model events manager."""

    def __init__(self) -> None:
        """Initialize events."""
        self._events: Dict[str, List[Hook[Any]]] = {
            "before_create": [],
            "after_create": [],
            "before_update": [],
            "after_update": [],
            "before_delete": [],
            "after_delete": [],
        }

    def on(self, event: str) -> Callable[[Hook[M]], Hook[M]]:
        """Register event handler."""

        def decorator(func: Hook[M]) -> Hook[M]:
            if event not in self._events:
                raise ValueError(f"Invalid event: {event}")
            self._events[event].append(func)  # type: ignore
            return func

        return decorator

    async def emit(self, event: str, model: ModelInterface) -> None:
        """Emit event."""
        if event not in self._events:
            raise ValueError(f"Invalid event: {event}")

        for hook in self._events[event]:
            try:
                await hook(model)
            except Exception as e:
                logger.error("Event hook failed: %s", str(e))
                raise EventError(f"Event {event} hook failed: {str(e)}")

    async def before_create(self, model: ModelInterface) -> None:
        """Emit before create event."""
        await self.emit("before_create", model)

    async def after_create(self, model: ModelInterface) -> None:
        """Emit after create event."""
        await self.emit("after_create", model)

    async def before_update(self, model: ModelInterface) -> None:
        """Emit before update event."""
        await self.emit("before_update", model)

    async def after_update(self, model: ModelInterface) -> None:
        """Emit after update event."""
        await self.emit("after_update", model)

    async def before_delete(self, model: ModelInterface) -> None:
        """Emit before delete event."""
        await self.emit("before_delete", model)

    async def after_delete(self, model: ModelInterface) -> None:
        """Emit after delete event."""
        await self.emit("after_delete", model)


class EventError(Exception):
    """Event error."""

    def __init__(self, message: str) -> None:
        """Initialize error."""
        self.message = message
        super().__init__(message)
