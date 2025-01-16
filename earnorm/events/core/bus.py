"""Event bus implementation.

This module provides the event bus that coordinates event publishing
and handling. It manages event backends, handlers, and retry policies.

Features:
- Event publishing
- Event handling
- Pattern-based subscriptions
- Retry policies
- Health checks
- Metrics collection

Examples:
    ```python
    from earnorm.events.core.bus import EventBus
    from earnorm.events.core.event import Event
    from earnorm.events.backends.redis import RedisBackend
    from earnorm.events.handlers.base import EventHandler

    # Create bus
    bus = EventBus(RedisBackend())

    # Register handler
    class UserHandler(EventHandler):
        async def handle(self, event: Event) -> None:
            print("Handling user event: %s" % event.name)

    await bus.subscribe("user.*", UserHandler())

    # Publish event
    event = Event(name="user.created", data={"id": "123"})
    await bus.publish(event)
    ```
"""

import asyncio
import logging
from typing import Dict, Optional, Set

from earnorm.events.backends.base import EventBackend
from earnorm.events.core.event import Event
from earnorm.events.core.exceptions import PublishError
from earnorm.events.core.registry import EventRegistry
from earnorm.events.handlers.base import EventHandler

logger = logging.getLogger(__name__)


class EventBus:
    """Event bus.

    This class coordinates event publishing and handling.
    It manages event backends, handlers, and retry policies.

    Features:
    - Event publishing
    - Event handling
    - Pattern-based subscriptions
    - Retry policies
    - Health checks
    - Metrics collection

    Attributes:
        backend (EventBackend): Event backend for publishing/subscribing
        registry (EventRegistry): Registry for event handlers
        retry_policy (Dict[str, int]): Retry policy configuration
        _running (bool): Whether bus is running
        _tasks (Set[asyncio.Task[None]]): Set of running tasks
    """

    def __init__(
        self,
        backend: EventBackend,
        retry_policy: Optional[Dict[str, int]] = None,
    ) -> None:
        """Initialize event bus.

        Args:
            backend: Event backend
            retry_policy: Optional retry policy configuration:
                - max_retries: Maximum number of retries
                - retry_delay: Delay between retries in seconds
                - max_delay: Maximum retry delay in seconds

        Examples:
            ```python
            # Create bus with Redis backend
            bus = EventBus(RedisBackend())

            # Create bus with retry policy
            bus = EventBus(
                RedisBackend(),
                retry_policy={
                    "max_retries": 3,
                    "retry_delay": 1,
                    "max_delay": 5,
                }
            )
            ```
        """
        self.backend = backend
        self.registry = EventRegistry()
        self.retry_policy = retry_policy or {
            "max_retries": 3,
            "retry_delay": 1,
            "max_delay": 5,
        }
        self._running = False
        self._tasks: Set[asyncio.Task[None]] = set()

    async def init(self) -> None:
        """Initialize event bus.

        This method initializes the backend and starts event processing.

        Examples:
            ```python
            await bus.init()
            ```
        """
        # Initialize backend
        await self.backend.connect()

        # Start processing
        self._running = True
        task = asyncio.create_task(self._process_events())
        self._tasks.add(task)
        logger.info("Started event bus")

    async def destroy(self) -> None:
        """Destroy event bus.

        This method stops event processing and cleans up resources.

        Examples:
            ```python
            await bus.destroy()
            ```
        """
        # Stop processing
        self._running = False

        # Cancel tasks
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

        # Disconnect backend
        await self.backend.disconnect()
        logger.info("Stopped event bus")

    async def publish(self, event: Event) -> None:
        """Publish event.

        This method publishes an event to the backend.
        It retries failed publishes according to the retry policy.

        Args:
            event: Event to publish

        Raises:
            PublishError: If publish fails after retries

        Examples:
            ```python
            event = Event(name="user.created", data={"id": "123"})
            await bus.publish(event)
            ```
        """
        # Get retry config
        max_retries = self.retry_policy["max_retries"]
        retry_delay = self.retry_policy["retry_delay"]
        max_delay = self.retry_policy["max_delay"]

        # Try publish with retries
        for attempt in range(max_retries + 1):
            try:
                await self.backend.publish(event)
                logger.debug("Published event %s", event.name)
                return
            except Exception as e:
                if attempt == max_retries:
                    logger.error("Failed to publish event %s: %s", event.name, str(e))
                    raise PublishError("Failed to publish event: %s" % str(e))

                # Calculate delay
                delay = min(retry_delay * (2**attempt), max_delay)
                logger.warning(
                    "Publish attempt %d failed, retrying in %ds: %s",
                    attempt + 1,
                    delay,
                    str(e),
                )
                await asyncio.sleep(delay)

    async def subscribe(self, pattern: str, handler: EventHandler) -> None:
        """Subscribe to events.

        This method subscribes a handler to events matching a pattern.

        Args:
            pattern: Event pattern to match
            handler: Event handler

        Examples:
            ```python
            # Subscribe to all user events
            await bus.subscribe("user.*", UserHandler())

            # Subscribe to specific event
            await bus.subscribe("user.created", CreateUserHandler())
            ```
        """
        # Register handler
        self.registry.register(pattern, handler)

        # Subscribe to backend
        await self.backend.subscribe(pattern)
        logger.info("Subscribed to pattern %s", pattern)

    async def unsubscribe(
        self, pattern: str, handler: Optional[EventHandler] = None
    ) -> None:
        """Unsubscribe from events.

        This method unsubscribes a handler or all handlers from events.

        Args:
            pattern: Event pattern
            handler: Optional handler to unsubscribe

        Examples:
            ```python
            # Unsubscribe specific handler
            await bus.unsubscribe("user.*", user_handler)

            # Unsubscribe all handlers
            await bus.unsubscribe("user.*")
            ```
        """
        # Unregister handler
        self.registry.unregister(pattern, handler)
        logger.info("Unsubscribed from pattern %s", pattern)

    async def _process_events(self) -> None:
        """Process events from backend.

        This method continuously processes events from the backend
        and dispatches them to registered handlers.
        """
        while self._running:
            try:
                # Get event from backend
                event = await self.backend.get()  # type: ignore
                if not event:
                    continue

                # Get handlers for event
                handlers = self.registry.get_handlers(event)  # type: ignore
                if not handlers:
                    continue

                # Handle event
                for handler in handlers:
                    try:
                        await handler.handle(event)  # type: ignore
                    except Exception as e:
                        logger.error(
                            "Handler %s failed to handle event %s: %s",
                            handler.__class__.__name__,
                            event.name,  # type: ignore
                            str(e),
                        )

            except Exception as e:
                logger.error("Failed to process events: %s", str(e))
                await asyncio.sleep(1)
