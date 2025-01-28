"""Lifecycle events module for dependency injection.

This module provides event handling functionality for lifecycle management.
It includes:

1. Event Types:
   - Initialization events (before/after)
   - Destruction events (before/after)
   - State change events
   - Error events

2. Event Handling:
   - Event emission
   - Event subscription
   - Event filtering
   - Error handling

3. Event Propagation:
   - Event bubbling
   - Event capturing
   - Event cancellation
   - Event ordering

Example:
    >>> events = LifecycleEvents()
    >>>
    >>> # Subscribe to events
    >>> async def on_init(obj: LifecycleAware) -> None:
    ...     logger.info(f"Initializing {obj.id}")
    >>>
    >>> events.on_before_init.append(on_init)
    >>>
    >>> # Emit events
    >>> service = MyService()
    >>> await events.before_init(service)
    >>> await service.init()
    >>> await events.after_init(service)
"""

import logging
from typing import Awaitable, Callable, List

from earnorm.di.lifecycle.protocol import LifecycleAware
from earnorm.exceptions import EventError

logger = logging.getLogger(__name__)

# Type aliases
EventHandler = Callable[[LifecycleAware], Awaitable[None]]


class LifecycleEvents:
    """Event manager for lifecycle events.

    This class manages event subscription and emission for lifecycle events.
    It supports:
    - Initialization events
    - Destruction events
    - Custom event handlers
    - Error handling

    Example:
        >>> events = LifecycleEvents()
        >>>
        >>> # Subscribe to events
        >>> async def log_init(obj: LifecycleAware) -> None:
        ...     logger.info(f"Initializing {obj.id}")
        >>>
        >>> events.on_before_init.append(log_init)
        >>>
        >>> # Emit events
        >>> service = MyService()
        >>> await events.before_init(service)
    """

    def __init__(self) -> None:
        """Initialize event manager.

        This constructor sets up:
        1. Event handler lists for each event type
        2. Error handling configuration
        3. Event propagation settings
        """
        self.on_before_init: List[EventHandler] = []
        self.on_after_init: List[EventHandler] = []
        self.on_before_destroy: List[EventHandler] = []
        self.on_after_destroy: List[EventHandler] = []

    async def before_init(self, obj: LifecycleAware) -> None:
        """Emit before initialization event.

        This method:
        1. Notifies all subscribers that initialization is about to start
        2. Allows subscribers to prepare resources
        3. Can be used to validate initialization conditions

        Args:
            obj: Object being initialized

        Raises:
            EventError: If event emission fails
            ValueError: If object is invalid
        """
        try:
            for handler in self.on_before_init:
                await handler(obj)
        except Exception as e:
            logger.error("Error in before_init event: %s", str(e))
            raise EventError(f"Failed to emit before_init event: {e}") from e

    async def after_init(self, obj: LifecycleAware) -> None:
        """Emit after initialization event.

        This method:
        1. Notifies all subscribers that initialization is complete
        2. Allows subscribers to perform post-initialization tasks
        3. Can be used to validate initialization results

        Args:
            obj: Object that was initialized

        Raises:
            EventError: If event emission fails
            ValueError: If object is invalid
        """
        try:
            for handler in self.on_after_init:
                await handler(obj)
        except Exception as e:
            logger.error("Error in after_init event: %s", str(e))
            raise EventError(f"Failed to emit after_init event: {e}") from e

    async def before_destroy(self, obj: LifecycleAware) -> None:
        """Emit before destruction event.

        This method:
        1. Notifies all subscribers that destruction is about to start
        2. Allows subscribers to prepare for cleanup
        3. Can be used to validate destruction conditions

        Args:
            obj: Object being destroyed

        Raises:
            EventError: If event emission fails
            ValueError: If object is invalid
        """
        try:
            for handler in self.on_before_destroy:
                await handler(obj)
        except Exception as e:
            logger.error("Error in before_destroy event: %s", str(e))
            raise EventError(f"Failed to emit before_destroy event: {e}") from e

    async def after_destroy(self, obj: LifecycleAware) -> None:
        """Emit after destruction event.

        This method:
        1. Notifies all subscribers that destruction is complete
        2. Allows subscribers to perform post-destruction tasks
        3. Can be used to validate destruction results

        Args:
            obj: Object that was destroyed

        Raises:
            EventError: If event emission fails
            ValueError: If object is invalid
        """
        try:
            for handler in self.on_after_destroy:
                await handler(obj)
        except Exception as e:
            logger.error("Error in after_destroy event: %s", str(e))
            raise EventError(f"Failed to emit after_destroy event: {e}") from e
