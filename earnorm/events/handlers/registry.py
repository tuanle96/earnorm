"""Handler registry implementation.

This module provides a registry for event handlers.
It manages registration and lookup of event handlers.

Features:
- Handler registration
- Handler lookup
- Handler validation
- Handler lifecycle management
- Thread-safe operations

Examples:
    ```python
    from earnorm.events.handlers.registry import HandlerRegistry
    from earnorm.events.handlers.base import EventHandler
    from earnorm.events.core.event import Event

    # Create registry
    registry = HandlerRegistry()

    # Register handler
    class UserHandler(EventHandler):
        async def handle(self, event: Event) -> None:
            print(f"Handling user event: {event.name}")

    handler = UserHandler()
    registry.register(handler)

    # Get handlers for event
    event = Event(name="user.created", data={"id": "123"})
    handlers = registry.get_handlers(event)
    ```
"""

import logging
import threading
from typing import Dict, List, Optional, Set
from uuid import uuid4

from earnorm.events.core.event import Event
from earnorm.events.handlers.base import EventHandler

logger = logging.getLogger(__name__)


class HandlerRegistry:
    """Handler registry.

    This class manages registration and lookup of event handlers.
    It provides thread-safe operations for registering and retrieving handlers.

    Features:
    - Handler registration
    - Handler lookup
    - Handler validation
    - Handler lifecycle management
    - Thread-safe operations

    Attributes:
        _handlers: Dict mapping handler IDs to handlers
        _patterns: Dict mapping handler IDs to patterns
        _lock: Thread lock for synchronization
    """

    def __init__(self) -> None:
        """Initialize handler registry."""
        self._handlers: Dict[str, EventHandler] = {}
        self._patterns: Dict[str, Set[str]] = {}
        self._lock = threading.Lock()

    def register(
        self, handler: EventHandler, patterns: Optional[List[str]] = None
    ) -> None:
        """Register event handler.

        This method registers a handler for events matching patterns.
        If no patterns are provided, uses handler's default patterns.

        Args:
            handler: Event handler instance
            patterns: Optional list of event patterns to match

        Examples:
            ```python
            # Register handler with default patterns
            registry.register(UserHandler())

            # Register handler with specific patterns
            registry.register(
                UserHandler(),
                patterns=["user.created", "user.updated"]
            )
            ```
        """
        with self._lock:
            # Get or generate handler ID
            handler_id = handler.id or str(uuid4())

            # Store handler
            self._handlers[handler_id] = handler

            # Store patterns
            if patterns:
                self._patterns[handler_id] = set(patterns)
            else:
                self._patterns[handler_id] = set()

            logger.info(
                f"Registered handler {handler.__class__.__name__} "
                f"with patterns {self._patterns[handler_id]}"
            )

    def unregister(self, handler: EventHandler) -> None:
        """Unregister event handler.

        This method unregisters a handler and removes its patterns.

        Args:
            handler: Event handler instance

        Examples:
            ```python
            registry.unregister(user_handler)
            ```
        """
        with self._lock:
            # Get handler ID
            handler_id = handler.id
            if not handler_id:
                return

            # Remove handler
            if handler_id in self._handlers:
                self._handlers.pop(handler_id)
                self._patterns.pop(handler_id, None)
                logger.info(f"Unregistered handler {handler.__class__.__name__}")

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
            for handler_id, handler in self._handlers.items():
                # Check if handler matches event
                patterns = self._patterns[handler_id]
                if not patterns or event.name in patterns:
                    handlers.append(handler)
            return handlers

    def clear(self) -> None:
        """Clear registry.

        This method removes all registered handlers and patterns.

        Examples:
            ```python
            registry.clear()
            ```
        """
        with self._lock:
            self._handlers.clear()
            self._patterns.clear()
            logger.info("Cleared handler registry")
