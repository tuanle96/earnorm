"""Event manager implementation.

This module provides event management through env.
It enables event publishing and handling via env.events.

Features:
- Event publishing via env
- Event handling registration
- Event bus management
- Event tracking
- Error handling

Examples:
    ```python
    # Access via env
    await env.events.publish("user.created", {"id": "123"})

    # Register handler
    @env.events.on("user.*")
    async def handle_user_events(event):
        print(f"Got event: {event.name}")

    # In model
    class User(Model):
        name = fields.Char()

        async def send_welcome_email(self):
            await self.env.events.publish(
                "user.welcome_email",
                {"user_id": self.id}
            )
    ```
"""

import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, List, Optional, Protocol, Union

from earnorm.events.core.bus import EventBus
from earnorm.events.core.event import Event
from earnorm.events.core.exceptions import EventError
from earnorm.events.handlers.base import EventHandler

logger = logging.getLogger(__name__)


class EventHandlerCallable(Protocol):
    """Protocol for event handler callable."""

    async def __call__(self, event: Event) -> Any:
        """Handle event."""
        ...


class FunctionHandler(EventHandler):
    """Function handler.

    This class wraps a function as an event handler.
    """

    def __init__(self, func: EventHandlerCallable, pattern: str) -> None:
        """Initialize handler.

        Args:
            func: Handler function
            pattern: Event pattern
        """
        self._func = func
        self._pattern = pattern
        module = inspect.getmodule(func)
        module_name = module.__name__ if module else "unknown"
        self._id = f"{module_name}.{func.__qualname__}_{pattern}"

    @property
    def id(self) -> str:
        """Get handler ID."""
        return self._id

    @property
    def data(self) -> Dict[str, Any]:
        """Get handler data."""
        module = inspect.getmodule(self._func)
        module_name = module.__name__ if module else "unknown"
        return {
            "pattern": self._pattern,
            "function": f"{module_name}.{self._func.__qualname__}",
        }

    async def handle(self, event: Event) -> None:
        """Handle event."""
        await self._func(event)

    async def cleanup(self) -> None:
        """Clean up handler resources."""
        pass


class EventManager:
    """Event manager.

    This class provides event management through env.
    It enables event publishing and handling via env.events.

    Attributes:
        env: Environment instance
        event_bus: Event bus instance
        handlers: Dictionary of event handlers
    """

    def __init__(self, env: Any) -> None:
        """Initialize event manager.

        Args:
            env: Environment instance
        """
        self.env = env
        self.event_bus: Optional[EventBus] = None
        self.handlers: Dict[str, List[Union[EventHandlerCallable, EventHandler]]] = {}

    async def init(self, **config: Any) -> None:
        """Initialize event manager.

        This method initializes the event bus and registers handlers.

        Args:
            **config: Event bus configuration
        """
        try:
            # Create event bus
            self.event_bus = EventBus(**config)
            await self.event_bus.init()

            # Register handlers
            for pattern, handlers in self.handlers.items():
                for handler in handlers:
                    if isinstance(handler, EventHandler):
                        await self.event_bus.subscribe(pattern, handler)
                    else:
                        await self.event_bus.subscribe(
                            pattern, FunctionHandler(handler, pattern)
                        )

            logger.info("Event manager initialized")
        except Exception as e:
            logger.error("Failed to initialize event manager: %s", str(e))
            raise EventError(f"Failed to initialize event manager: {str(e)}")

    async def destroy(self) -> None:
        """Destroy event manager.

        This method stops the event bus and cleans up resources.
        """
        if self.event_bus:
            await self.event_bus.destroy()
            self.event_bus = None
            logger.info("Event manager destroyed")

    def on(
        self, pattern: str
    ) -> Callable[[EventHandlerCallable], EventHandlerCallable]:
        """Register event handler.

        This decorator registers a function as an event handler.
        The function will be called when an event matching the pattern is received.

        Args:
            pattern: Event pattern to match (e.g. "user.created")

        Returns:
            Decorator function

        Examples:
            ```python
            @env.events.on("user.created")
            async def handle_user_created(event):
                print(f"User created: {event.data}")
            ```
        """

        def decorator(func: EventHandlerCallable) -> EventHandlerCallable:
            # Store handler
            if pattern not in self.handlers:
                self.handlers[pattern] = []
            self.handlers[pattern].append(func)

            # Register with bus if initialized
            if self.event_bus:
                handler = FunctionHandler(func, pattern)
                asyncio.create_task(self.event_bus.subscribe(pattern, handler))

            return func

        return decorator

    async def publish(self, name: str, data: Dict[str, Any]) -> None:
        """Publish event.

        This method publishes an event to the event bus.
        The event will be delivered to all matching handlers.

        Args:
            name: Event name
            data: Event data

        Examples:
            ```python
            await env.events.publish(
                "user.created",
                {"id": "123", "name": "John"}
            )
            ```
        """
        if not self.event_bus:
            raise EventError("Event manager not initialized")

        try:
            event = Event(name=name, data=data)
            await self.event_bus.publish(event)
            logger.debug("Published event %s: %s", name, data)
        except Exception as e:
            logger.error("Failed to publish event %s: %s", name, str(e))
            raise EventError(f"Failed to publish event: {str(e)}")

    async def emit(self, name: str, data: Dict[str, Any]) -> None:
        """Emit event.

        This is an alias for publish().
        """
        await self.publish(name, data)
