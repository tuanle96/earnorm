"""Memory event backend implementation.

This module provides an in-memory event backend for testing and development.
It implements the EventBackend protocol using an in-memory queue.

Features:
- In-memory event queue
- Pattern-based subscriptions
- No persistence
- Fast and simple

Examples:
    ```python
    from earnorm.events.backends.memory import MemoryBackend
    from earnorm.events.core.event import Event

    # Create backend
    backend = MemoryBackend()

    # Initialize and connect
    await backend.init()

    # Publish event
    event = Event(name="user.created", data={"id": "123"})
    await backend.publish(event)

    # Subscribe to events
    await backend.subscribe("user.*")
    ```
"""

import asyncio
import fnmatch
import logging
from typing import Any, Dict, Optional, Set

from earnorm.events.backends.base import EventBackend
from earnorm.events.core.event import Event
from earnorm.events.core.exceptions import ConnectionError, PublishError

logger = logging.getLogger(__name__)


class MemoryBackend(EventBackend):
    """Memory event backend.

    This class implements the EventBackend protocol using an in-memory
    queue. It is intended for testing and development.

    Features:
    - In-memory event queue
    - Pattern-based subscriptions
    - No persistence
    - Fast and simple

    Attributes:
        _queue: Event queue
        _subscriptions: Set of subscription patterns
        _connected: Whether backend is connected
    """

    def __init__(self) -> None:
        """Initialize memory backend."""
        self._queue: asyncio.Queue[Event] = asyncio.Queue()
        self._subscriptions: Set[str] = set()
        self._connected = False

    @property
    def id(self) -> Optional[str]:
        """Get backend ID.

        Returns:
            str: Always returns "memory"
        """
        return "memory"

    @property
    def data(self) -> Dict[str, Any]:
        """Get backend data.

        Returns:
            Dict containing backend state:
            - queue_size: Current queue size
            - subscriptions: Number of subscriptions
        """
        return {
            "queue_size": self._queue.qsize(),
            "subscriptions": len(self._subscriptions),
        }

    @property
    def is_connected(self) -> bool:
        """Check if connected.

        Returns:
            bool: True if backend is connected
        """
        return self._connected

    async def connect(self) -> None:
        """Connect to backend.

        This method simulates connecting to a backend.

        Examples:
            ```python
            await backend.connect()
            ```
        """
        self._connected = True
        logger.info("Connected to memory backend")

    async def disconnect(self) -> None:
        """Disconnect from backend.

        This method simulates disconnecting from a backend.

        Examples:
            ```python
            await backend.disconnect()
            ```
        """
        self._connected = False
        self._queue = asyncio.Queue()
        self._subscriptions.clear()
        logger.info("Disconnected from memory backend")

    async def publish(self, event: Event) -> None:
        """Publish event.

        This method adds an event to the in-memory queue.

        Args:
            event: Event to publish

        Raises:
            PublishError: If publish fails
            ConnectionError: If not connected

        Examples:
            ```python
            event = Event(name="user.created", data={"id": "123"})
            await backend.publish(event)
            ```
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to backend")

        try:
            # Check subscriptions
            if not any(
                fnmatch.fnmatch(event.name, pattern) for pattern in self._subscriptions
            ):
                return

            # Add to queue
            await self._queue.put(event)
            logger.debug("Published event %s", event.name)
        except Exception as e:
            logger.error("Failed to publish event %s: %s", event.name, str(e))
            raise PublishError(f"Failed to publish event: {str(e)}")

    async def subscribe(self, pattern: str) -> None:
        """Subscribe to events matching pattern.

        This method adds a subscription pattern.

        Args:
            pattern: Event pattern to match

        Raises:
            ConnectionError: If not connected

        Examples:
            ```python
            # Subscribe to all user events
            await backend.subscribe("user.*")

            # Subscribe to specific event type
            await backend.subscribe("user.created")
            ```
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to backend")

        self._subscriptions.add(pattern)
        logger.info("Subscribed to pattern %s", pattern)

    async def get(self) -> Optional[Event]:
        """Get next event.

        This method gets the next event from the queue.

        Returns:
            Optional[Event]: Next event if available

        Raises:
            ConnectionError: If not connected

        Examples:
            ```python
            event = await backend.get()
            if event:
                print(f"Got event: {event.name}")
            ```
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to backend")

        try:
            return await self._queue.get()
        except Exception as e:
            logger.error("Failed to get event: %s", str(e))
            return None
