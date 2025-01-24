"""Field event base implementation.

This module provides the base event system for handling field events.
It supports:
- Event types and data
- Event handlers
- Event propagation
- Event filtering
- Asynchronous event handling
- Integration with core event system

Examples:
    >>> async def on_change(event: FieldEvent) -> None:
    ...     print(f"Field {event.field.name} changed from {event.old_value} to {event.new_value}")
    ...
    >>> field = StringField()
    >>> field.on("change", on_change)
    >>> await field.set_value("new value")  # Triggers change event
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set, TypeVar

from earnorm.events.core.event import Event
from earnorm.events.handlers.base import EventHandler as CoreEventHandler
from earnorm.fields.base import Field

T = TypeVar("T")  # Type of field value


class EventType(Enum):
    """Types of field events."""

    INIT = auto()  # Field initialized
    SETUP = auto()  # Field set up
    VALIDATE = auto()  # Field validation
    CONVERT = auto()  # Field conversion
    CHANGE = auto()  # Field value changed
    ERROR = auto()  # Field error occurred
    CLEANUP = auto()  # Field cleaned up


@dataclass
class FieldEvent(Event):
    """Event data for field events.

    This class extends the core Event class to add field-specific data.

    Attributes:
        type: Type of event (from EventType enum)
        field: Field that triggered event
        value: Current field value
        old_value: Previous field value
        error: Error that occurred (for error events)
        metadata: Additional event metadata
    """

    type: EventType
    field: Field[Any]
    value: Any = None
    old_value: Any = None
    error: Optional[Exception] = None
    metadata: Dict[str, Any] = dict()

    def __post_init__(self) -> None:
        """Initialize core event attributes."""
        super().__init__(
            name=f"field.{self.type.name.lower()}",
            data={
                "field_name": self.field.name,
                "field_type": self.field.__class__.__name__,
                "value": self.value,
                "old_value": self.old_value,
                "error": str(self.error) if self.error else None,
            },
            metadata=self.metadata,
        )


class FieldEventHandler(CoreEventHandler):
    """Base class for field event handlers.

    This class extends the core EventHandler to handle field events.
    It provides type safety and field-specific functionality.

    Examples:
        >>> class ChangeLogger(FieldEventHandler):
        ...     async def handle(self, event: FieldEvent) -> None:
        ...         if event.type == EventType.CHANGE:
        ...             print(f"Field {event.field.name} changed to {event.value}")
    """

    async def handle(self, event: Event) -> None:
        """Handle field event.

        Args:
            event: Event to handle (must be FieldEvent)

        Raises:
            TypeError: If event is not a FieldEvent
        """
        if not isinstance(event, FieldEvent):
            raise TypeError(f"Expected FieldEvent, got {type(event).__name__}")
        await self.handle_field_event(event)

    async def handle_field_event(self, event: FieldEvent) -> None:
        """Handle field-specific event.

        Override this method to implement field event handling.

        Args:
            event: Field event to handle
        """
        raise NotImplementedError


# Type alias for simple event handlers
EventHandler = Callable[[FieldEvent], Awaitable[None]]


class EventEmitter:
    """Base class for objects that can emit events.

    This class integrates with the core event system while maintaining
    backwards compatibility with the field event system.

    Attributes:
        _handlers: Dictionary mapping event types to lists of handlers
        _propagate: Whether to propagate events to parent emitters
        _parent: Parent event emitter
    """

    def __init__(self) -> None:
        """Initialize event emitter."""
        self._handlers: Dict[EventType, List[EventHandler]] = {}
        self._propagate: bool = True
        self._parent: Optional[EventEmitter] = None

    def on(self, event_type: EventType, handler: EventHandler) -> None:
        """Register event handler.

        Args:
            event_type: Type of event to handle
            handler: Event handler function
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def off(self, event_type: EventType, handler: EventHandler) -> None:
        """Unregister event handler.

        Args:
            event_type: Type of event to unhandle
            handler: Event handler function
        """
        if event_type in self._handlers:
            self._handlers[event_type].remove(handler)
            if not self._handlers[event_type]:
                del self._handlers[event_type]

    async def emit(self, event: FieldEvent) -> None:
        """Emit event.

        This method handles both local handlers and core event system.

        Args:
            event: Event to emit
        """
        # Handle event locally
        if event.type in self._handlers:
            for handler in self._handlers[event.type]:
                await handler(event)

        # Propagate event to parent
        if self._propagate and self._parent is not None:
            await self._parent.emit(event)

        # Publish to core event system
        from earnorm.di import container

        event_bus = await container.get("events")
        await event_bus.publish(event)

    def clear_handlers(self, event_type: Optional[EventType] = None) -> None:
        """Clear event handlers.

        Args:
            event_type: Type of event to clear handlers for, or None for all
        """
        if event_type is None:
            self._handlers.clear()
        elif event_type in self._handlers:
            del self._handlers[event_type]

    def set_parent(self, parent: Optional["EventEmitter"]) -> None:
        """Set parent event emitter.

        Args:
            parent: Parent event emitter
        """
        self._parent = parent

    def set_propagate(self, propagate: bool) -> None:
        """Set event propagation.

        Args:
            propagate: Whether to propagate events to parent emitters
        """
        self._propagate = propagate

    def get_handlers(self, event_type: Optional[EventType] = None) -> Set[EventHandler]:
        """Get event handlers.

        Args:
            event_type: Type of event to get handlers for, or None for all

        Returns:
            Set of event handlers
        """
        handlers: Set[EventHandler] = set()
        if event_type is None:
            # Get all handlers
            for handler_list in self._handlers.values():
                handlers.update(handler_list)
        else:
            # Get handlers for specific event type
            handlers.update(self._handlers.get(event_type, []))
        return handlers

    def has_handlers(self, event_type: EventType) -> bool:
        """Check if event type has handlers.

        Args:
            event_type: Type of event to check

        Returns:
            True if event type has handlers, False otherwise
        """
        return event_type in self._handlers and bool(self._handlers[event_type])
