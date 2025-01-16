"""Model events implementation."""

import logging
from typing import Any, Callable, Coroutine, Dict, List, TypeVar

from earnorm.base.types import ModelProtocol

logger = logging.getLogger(__name__)

# Type aliases
M = TypeVar("M", bound=ModelProtocol)
Hook = Callable[[M], Coroutine[Any, Any, None]]


class ModelEvents:
    """Model events manager.

    This class manages model lifecycle events:
    - Before/after create
    - Before/after update
    - Before/after delete

    Events are emitted during model operations and can be handled
    by registering async functions using the @on decorator.

    Examples:
        ```python
        events = ModelEvents()

        @events.on("before_create")
        async def validate_email(model: User):
            if not await is_valid_email(model.email):
                raise ValidationError("Invalid email")

        @events.on("after_create")
        async def send_welcome_email(model: User):
            await send_email(model.email, "Welcome!")
        ```
    """

    def __init__(self) -> None:
        """Initialize events manager."""
        self._events: Dict[str, List[Hook[Any]]] = {
            "before_create": [],
            "after_create": [],
            "before_update": [],
            "after_update": [],
            "before_delete": [],
            "after_delete": [],
        }

    def on(self, event: str) -> Callable[[Hook[M]], Hook[M]]:
        """Register event handler.

        Args:
            event: Event name to handle

        Returns:
            Decorator function that registers the handler

        Raises:
            ValueError: If event name is invalid

        Examples:
            ```python
            @events.on("before_create")
            async def validate_email(model: User):
                if not await is_valid_email(model.email):
                    raise ValidationError("Invalid email")
            ```
        """

        def decorator(func: Hook[M]) -> Hook[M]:
            if event not in self._events:
                raise ValueError(f"Invalid event: {event}")
            self._events[event].append(func)  # type: ignore
            return func

        return decorator

    async def emit(self, event: str, model: ModelProtocol) -> None:
        """Emit event.

        Args:
            event: Event name to emit
            model: Model instance that triggered the event

        Raises:
            ValueError: If event name is invalid
            EventError: If any event handler fails
        """
        if event not in self._events:
            raise ValueError(f"Invalid event: {event}")

        for hook in self._events[event]:
            try:
                await hook(model)
            except Exception as e:
                logger.error("Event hook failed: %s", str(e))
                raise EventError(f"Event {event} hook failed: {str(e)}")

    async def before_create(self, model: ModelProtocol) -> None:
        """Emit before create event.

        Args:
            model: Model instance being created
        """
        await self.emit("before_create", model)

    async def after_create(self, model: ModelProtocol) -> None:
        """Emit after create event.

        Args:
            model: Model instance that was created
        """
        await self.emit("after_create", model)

    async def before_update(self, model: ModelProtocol) -> None:
        """Emit before update event.

        Args:
            model: Model instance being updated
        """
        await self.emit("before_update", model)

    async def after_update(self, model: ModelProtocol) -> None:
        """Emit after update event.

        Args:
            model: Model instance that was updated
        """
        await self.emit("after_update", model)

    async def before_delete(self, model: ModelProtocol) -> None:
        """Emit before delete event.

        Args:
            model: Model instance being deleted
        """
        await self.emit("before_delete", model)

    async def after_delete(self, model: ModelProtocol) -> None:
        """Emit after delete event.

        Args:
            model: Model instance that was deleted
        """
        await self.emit("after_delete", model)


class EventError(Exception):
    """Event error.

    This exception is raised when an event handler fails.
    It contains the original error message from the handler.

    Attributes:
        message: Error message from the handler
    """

    def __init__(self, message: str) -> None:
        """Initialize error.

        Args:
            message: Error message from the handler
        """
        self.message = message
        super().__init__(message)
