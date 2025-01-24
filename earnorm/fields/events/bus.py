"""Field event bus implementation.

This module provides the event bus for managing field events across the system.
It supports:
- Global event handling
- Event filtering and routing
- Event queuing and batching
- Asynchronous event processing
- Integration with core event system
- Event logging and monitoring

Examples:
    >>> bus = EventBus()
    >>> async def log_changes(event: FieldEvent) -> None:
    ...     if event.type == EventType.CHANGE:
    ...         print(f"Field {event.field.name} changed to {event.value}")
    ...
    >>> bus.subscribe(EventType.CHANGE, log_changes)
    >>> await bus.publish(change_event)  # Triggers log_changes
"""

from collections import defaultdict
from typing import Callable, DefaultDict, Dict, List, Optional, Set

from earnorm.di import container
from earnorm.events.core.bus import EventBus as CoreEventBus
from earnorm.fields.events.base import EventHandler, EventType, FieldEvent


class EventBus:
    """Event bus for managing field events.

    This class integrates with the core event system while maintaining
    backwards compatibility with the field event system.

    Attributes:
        _subscribers: Dictionary mapping event types to lists of handlers
        _filters: Dictionary mapping event types to filter functions
        _queue: List of queued events
        _batch_size: Maximum number of events to process in one batch
        _processing: Whether the bus is currently processing events
        _core_bus: Core event bus instance
    """

    def __init__(self, batch_size: int = 100) -> None:
        """Initialize event bus.

        Args:
            batch_size: Maximum number of events to process in one batch
        """
        self._subscribers: DefaultDict[EventType, List[EventHandler]] = defaultdict(
            list
        )
        self._filters: Dict[EventType, List[Callable[[FieldEvent], bool]]] = {}
        self._queue: List[FieldEvent] = []
        self._batch_size = batch_size
        self._processing = False
        self._core_bus: Optional[CoreEventBus] = None

    async def _get_core_bus(self) -> CoreEventBus:
        """Get core event bus instance.

        Returns:
            Core event bus instance

        Raises:
            RuntimeError: If core event bus is not available
        """
        if self._core_bus is None:
            bus = await container.get("events")
            if not isinstance(bus, CoreEventBus):
                raise RuntimeError("Core event bus not available")
            self._core_bus = bus
        return self._core_bus

    def subscribe(
        self,
        event_type: EventType,
        handler: EventHandler,
        filter_fn: Optional[Callable[[FieldEvent], bool]] = None,
    ) -> None:
        """Subscribe to event type.

        Args:
            event_type: Type of event to subscribe to
            handler: Event handler function
            filter_fn: Optional filter function for events
        """
        self._subscribers[event_type].append(handler)
        if filter_fn is not None:
            if event_type not in self._filters:
                self._filters[event_type] = []
            self._filters[event_type].append(filter_fn)

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Unsubscribe from event type.

        Args:
            event_type: Type of event to unsubscribe from
            handler: Event handler function
        """
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(handler)
            if not self._subscribers[event_type]:
                del self._subscribers[event_type]

    def clear_subscribers(self, event_type: Optional[EventType] = None) -> None:
        """Clear event subscribers.

        Args:
            event_type: Type of event to clear subscribers for, or None for all
        """
        if event_type is None:
            self._subscribers.clear()
            self._filters.clear()
        else:
            if event_type in self._subscribers:
                del self._subscribers[event_type]
            if event_type in self._filters:
                del self._filters[event_type]

    async def publish(self, event: FieldEvent) -> None:
        """Publish event to subscribers.

        This method handles both local subscribers and core event system.

        Args:
            event: Event to publish
        """
        # Add event to queue
        self._queue.append(event)

        # Process queue if not already processing
        if not self._processing:
            self._processing = True
            try:
                while self._queue:
                    # Process events in batches
                    batch = self._queue[: self._batch_size]
                    self._queue = self._queue[self._batch_size :]

                    # Process each event in batch
                    for event in batch:
                        # Process locally
                        await self._process_event(event)

                        # Publish to core event system
                        core_bus = await self._get_core_bus()
                        await core_bus.publish(event)
            finally:
                self._processing = False

    async def _process_event(self, event: FieldEvent) -> None:
        """Process single event.

        Args:
            event: Event to process
        """
        if event.type not in self._subscribers:
            return

        # Check if event passes filters
        if event.type in self._filters:
            for filter_fn in self._filters[event.type]:
                if not filter_fn(event):
                    return

        # Notify subscribers
        for handler in self._subscribers[event.type]:
            try:
                await handler(event)
            except Exception as e:
                # Create error event
                error_event = FieldEvent(
                    type=EventType.ERROR,
                    field=event.field,
                    error=e,
                    metadata={
                        "original_event": event,
                        "handler": handler.__name__,
                    },
                )
                await self.publish(error_event)

    def get_subscribers(
        self, event_type: Optional[EventType] = None
    ) -> Set[EventHandler]:
        """Get event subscribers.

        Args:
            event_type: Type of event to get subscribers for, or None for all

        Returns:
            Set of event handlers
        """
        subscribers: Set[EventHandler] = set()
        if event_type is None:
            # Get all subscribers
            for handler_list in self._subscribers.values():
                subscribers.update(handler_list)
        else:
            # Get subscribers for specific event type
            subscribers.update(self._subscribers.get(event_type, []))
        return subscribers

    def has_subscribers(self, event_type: EventType) -> bool:
        """Check if event type has subscribers.

        Args:
            event_type: Type of event to check

        Returns:
            True if event type has subscribers, False otherwise
        """
        return event_type in self._subscribers and bool(self._subscribers[event_type])

    def get_queue_size(self) -> int:
        """Get number of events in queue.

        Returns:
            Queue size
        """
        return len(self._queue)

    def clear_queue(self) -> None:
        """Clear event queue."""
        self._queue.clear()

    def is_processing(self) -> bool:
        """Check if bus is processing events.

        Returns:
            True if processing events, False otherwise
        """
        return self._processing
