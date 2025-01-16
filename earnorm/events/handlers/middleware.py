"""Handler middleware implementation.

This module provides middleware for event handlers.
It allows adding behavior before and after event handling.

Features:
- Pre-handle hooks
- Post-handle hooks
- Error handling
- Metrics collection
- Logging

Examples:
    ```python
    from earnorm.events.handlers.middleware import (
        HandlerMiddleware,
        LoggingMiddleware,
        MetricsMiddleware,
    )
    from earnorm.events.handlers.base import EventHandler
    from earnorm.events.core.event import Event

    # Create handler with middleware
    class UserHandler(EventHandler):
        async def handle(self, event: Event) -> None:
            print(f"Handling user event: {event.name}")

    handler = UserHandler()
    handler = LoggingMiddleware(handler)
    handler = MetricsMiddleware(handler)

    # Handle event with middleware
    event = Event(name="user.created", data={"id": "123"})
    await handler.handle(event)
    ```
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from earnorm.events.core.event import Event
from earnorm.events.handlers.base import EventHandler

logger = logging.getLogger(__name__)


class HandlerMiddleware(EventHandler, ABC):
    """Handler middleware base class.

    This class wraps an event handler and adds behavior.
    All middleware classes should inherit from this class.

    Features:
    - Pre-handle hooks
    - Post-handle hooks
    - Error handling
    - Metrics collection
    - Logging

    Attributes:
        handler: Wrapped event handler
    """

    def __init__(self, handler: EventHandler) -> None:
        """Initialize handler middleware.

        Args:
            handler: Event handler to wrap
        """
        self.handler = handler

    @property
    def id(self) -> Optional[str]:
        """Get handler ID.

        Returns:
            str: Handler ID from wrapped handler
        """
        return self.handler.id

    @property
    def data(self) -> Dict[str, Any]:
        """Get handler data.

        Returns:
            Dict containing handler state from wrapped handler
        """
        return self.handler.data

    async def handle(self, event: Event) -> None:
        """Handle event with middleware.

        This method wraps the handler's handle method with middleware.

        Args:
            event: Event to handle

        Examples:
            ```python
            await middleware.handle(event)
            ```
        """
        try:
            # Pre-handle hook
            await self.pre_handle(event)

            # Handle event
            await self.handler.handle(event)

            # Post-handle hook
            await self.post_handle(event)
        except Exception as e:
            # Error hook
            await self.on_error(event, e)
            raise

    @abstractmethod
    async def pre_handle(self, event: Event) -> None:
        """Pre-handle hook.

        This method is called before handling an event.
        Override this method to add behavior.

        Args:
            event: Event being handled

        Examples:
            ```python
            async def pre_handle(self, event: Event) -> None:
                print(f"Pre-handling event: {event.name}")
            ```
        """
        pass

    @abstractmethod
    async def post_handle(self, event: Event) -> None:
        """Post-handle hook.

        This method is called after handling an event.
        Override this method to add behavior.

        Args:
            event: Event that was handled

        Examples:
            ```python
            async def post_handle(self, event: Event) -> None:
                print(f"Post-handling event: {event.name}")
            ```
        """
        pass

    @abstractmethod
    async def on_error(self, event: Event, error: Exception) -> None:
        """Error hook.

        This method is called when handling fails.
        Override this method to add behavior.

        Args:
            event: Event that failed
            error: Exception that was raised

        Examples:
            ```python
            async def on_error(self, event: Event, error: Exception) -> None:
                print(f"Error handling event: {error}")
            ```
        """
        pass


class LoggingMiddleware(HandlerMiddleware):
    """Logging middleware.

    This middleware adds logging to event handling.
    It logs before and after handling, and any errors.

    Examples:
        ```python
        handler = UserHandler()
        handler = LoggingMiddleware(handler)
        await handler.handle(event)  # Will log handling
        ```
    """

    async def pre_handle(self, event: Event) -> None:
        """Log before handling."""
        logger.info(f"Handling event {event.name}")

    async def post_handle(self, event: Event) -> None:
        """Log after handling."""
        logger.info(f"Handled event {event.name}")

    async def on_error(self, event: Event, error: Exception) -> None:
        """Log error."""
        logger.error(f"Failed to handle event {event.name}: {str(error)}")


class MetricsMiddleware(HandlerMiddleware):
    """Metrics middleware.

    This middleware collects metrics about event handling.
    It tracks timing, success/failure rates, and counts.

    Examples:
        ```python
        handler = UserHandler()
        handler = MetricsMiddleware(handler)
        await handler.handle(event)  # Will collect metrics
        ```
    """

    def __init__(self, handler: EventHandler) -> None:
        """Initialize metrics middleware."""
        super().__init__(handler)
        self._total = 0
        self._success = 0
        self._errors = 0
        self._total_time = 0.0
        self._start_time = 0.0

    @property
    def data(self) -> Dict[str, Any]:
        """Get metrics data.

        Returns:
            Dict containing metrics:
            - total: Total events handled
            - success: Successful events
            - errors: Failed events
            - avg_time: Average handling time
            - success_rate: Success rate
            - error_rate: Error rate
        """
        metrics = super().data
        metrics.update(
            {
                "total": self._total,
                "success": self._success,
                "errors": self._errors,
                "avg_time": self._total_time / max(self._total, 1),
                "success_rate": self._success / max(self._total, 1),
                "error_rate": self._errors / max(self._total, 1),
            }
        )
        return metrics

    async def pre_handle(self, event: Event) -> None:
        """Start timing."""
        self._start_time = time.time()
        self._total += 1

    async def post_handle(self, event: Event) -> None:
        """Record success and time."""
        self._success += 1
        self._total_time += time.time() - self._start_time

    async def on_error(self, event: Event, error: Exception) -> None:
        """Record error and time."""
        self._errors += 1
        self._total_time += time.time() - self._start_time
