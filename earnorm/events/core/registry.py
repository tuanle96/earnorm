"""Event registry implementation.

This module provides a registry for event handlers and event types.
It manages registration and lookup of event handlers and event types.

Features:
- Event handler registration
- Event type registration
- Pattern-based handler lookup
- Handler validation
- Thread-safe operations

Examples:
    ```python
    from earnorm.events.core.registry import EventRegistry
    from earnorm.events.core.event import Event
    from earnorm.events.handlers.base import EventHandler

    # Create registry
    registry = EventRegistry()

    # Register handler
    class UserHandler(EventHandler):
        async def handle(self, event: Event) -> None:
            print(f"Handling user event: {event.name}")

    registry.register("user.*", UserHandler())

    # Get handlers for event
    event = Event(name="user.created", data={"id": "123"})
    handlers = registry.get_handlers(event)
    ```
"""

import fnmatch
import logging
import threading
from typing import Dict, List, Optional, Set

from earnorm.events.core.event import Event
from earnorm.events.handlers.base import EventHandler

logger = logging.getLogger(__name__)


class EventRegistry:
    """Event registry.

    This class manages registration and lookup of event handlers and event types.
    It provides thread-safe operations for registering and retrieving handlers.

    Features:
    - Event handler registration
    - Event type registration
    - Pattern-based handler lookup
    - Handler validation
    - Thread-safe operations

    Attributes:
        _handlers: Dict mapping patterns to handlers
        _types: Set of registered event types
        _lock: Thread lock for synchronization
    """

    def __init__(self) -> None:
        """Initialize event registry."""
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._types: Set[str] = set()
        self._lock = threading.Lock()

    def register(self, pattern: str, handler: EventHandler) -> None:
        """Register event handler.

        This method registers a handler for events matching a pattern.
        The pattern can include wildcards (*) for matching multiple event types.

        Args:
            pattern: Event pattern to match
            handler: Event handler instance

        Examples:
            ```python
            # Register handler for all user events
            registry.register("user.*", UserHandler())

            # Register handler for specific event
            registry.register("user.created", CreateUserHandler())
            ```
        """
        with self._lock:
            if pattern not in self._handlers:
                self._handlers[pattern] = []
            self._handlers[pattern].append(handler)
            logger.info(
                "Registered handler %s for pattern %s",
                handler.__class__.__name__,
                pattern,
            )

    def unregister(self, pattern: str, handler: Optional[EventHandler] = None) -> None:
        """Unregister event handler.

        This method unregisters a handler or all handlers for a pattern.

        Args:
            pattern: Event pattern to unregister
            handler: Optional handler to unregister. If None, unregisters all handlers.

        Examples:
            ```python
            # Unregister specific handler
            registry.unregister("user.*", user_handler)

            # Unregister all handlers for pattern
            registry.unregister("user.*")
            ```
        """
        with self._lock:
            if pattern not in self._handlers:
                return

            if handler is None:
                # Remove all handlers
                self._handlers.pop(pattern)
                logger.info("Unregistered all handlers for pattern %s", pattern)
            else:
                # Remove specific handler
                handlers = self._handlers[pattern]
                handlers = [h for h in handlers if h != handler]
                if handlers:
                    self._handlers[pattern] = handlers
                else:
                    self._handlers.pop(pattern)
                logger.info(
                    "Unregistered handler %s for pattern %s",
                    handler.__class__.__name__,
                    pattern,
                )

    def register_type(self, event_type: str) -> None:
        """Register event type.

        This method registers a valid event type.
        Registered types can be used for validation.

        Args:
            event_type: Event type to register

        Examples:
            ```python
            # Register event types
            registry.register_type("user.created")
            registry.register_type("user.updated")
            ```
        """
        with self._lock:
            self._types.add(event_type)
            logger.info("Registered event type %s", event_type)

    def unregister_type(self, event_type: str) -> None:
        """Unregister event type.

        This method unregisters an event type.

        Args:
            event_type: Event type to unregister

        Examples:
            ```python
            registry.unregister_type("user.created")
            ```
        """
        with self._lock:
            self._types.discard(event_type)
            logger.info("Unregistered event type %s", event_type)

    def get_handlers(self, event: Event) -> List[EventHandler]:
        """Get handlers for event.

        This method returns all handlers matching the event name.
        Handlers are returned in registration order.

        Args:
            event: Event to get handlers for

        Returns:
            List of matching handlers

        Examples:
            ```python
            event = Event(name="user.created", data={"id": "123"})
            handlers = registry.get_handlers(event)
            for handler in handlers:
                await handler.handle(event)
            ```
        """
        with self._lock:
            handlers: List[EventHandler] = []
            for pattern, pattern_handlers in self._handlers.items():
                if fnmatch.fnmatch(event.name, pattern):
                    handlers.extend(pattern_handlers)
            return handlers

    def is_valid_type(self, event_type: str) -> bool:
        """Check if event type is valid.

        This method checks if an event type has been registered.

        Args:
            event_type: Event type to check

        Returns:
            bool: True if type is valid

        Examples:
            ```python
            if registry.is_valid_type("user.created"):
                print("Valid event type")
            ```
        """
        with self._lock:
            return event_type in self._types

    def clear(self) -> None:
        """Clear registry.

        This method removes all registered handlers and types.

        Examples:
            ```python
            registry.clear()
            ```
        """
        with self._lock:
            self._handlers.clear()
            self._types.clear()
            logger.info("Cleared event registry")
