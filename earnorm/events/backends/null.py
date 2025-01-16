"""Null event backend implementation.

This module provides a null event backend that does nothing.
It implements the EventBackend protocol but discards all events.

Features:
- No event storage
- No subscriptions
- No persistence
- Useful for testing and development

Examples:
    ```python
    from earnorm.events.backends.null import NullBackend
    from earnorm.events.core.event import Event

    # Create backend
    backend = NullBackend()

    # Initialize and connect
    await backend.connect()

    # Publish event (will be discarded)
    event = Event(name="user.created", data={"id": "123"})
    await backend.publish(event)

    # Subscribe to events (no effect)
    await backend.subscribe("user.*")
    ```
"""

import logging
from typing import Any, Dict, Optional

from earnorm.events.backends.base import EventBackend
from earnorm.events.core.event import Event

logger = logging.getLogger(__name__)


class NullBackend(EventBackend):
    """Null event backend.

    This class implements the EventBackend protocol but does nothing.
    It is useful for testing and development when events should be discarded.

    Features:
    - No event storage
    - No subscriptions
    - No persistence
    - Useful for testing and development

    Attributes:
        _connected: Whether backend is connected
    """

    def __init__(self) -> None:
        """Initialize null backend."""
        self._connected = False

    @property
    def id(self) -> Optional[str]:
        """Get backend ID.

        Returns:
            str: Always returns "null"
        """
        return "null"

    @property
    def data(self) -> Dict[str, Any]:
        """Get backend data.

        Returns:
            Dict containing backend state:
            - connected: Whether backend is connected
        """
        return {"connected": self.is_connected}

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
        logger.info("Connected to null backend")

    async def disconnect(self) -> None:
        """Disconnect from backend.

        This method simulates disconnecting from a backend.

        Examples:
            ```python
            await backend.disconnect()
            ```
        """
        self._connected = False
        logger.info("Disconnected from null backend")

    async def publish(self, event: Event) -> None:
        """Publish event.

        This method discards the event.

        Args:
            event: Event to publish (will be discarded)

        Examples:
            ```python
            event = Event(name="user.created", data={"id": "123"})
            await backend.publish(event)  # Event will be discarded
            ```
        """
        logger.debug("Discarded event %s", event.name)

    async def subscribe(self, pattern: str) -> None:
        """Subscribe to events.

        This method does nothing.

        Args:
            pattern: Event pattern to match (ignored)

        Examples:
            ```python
            await backend.subscribe("user.*")  # No effect
            ```
        """
        logger.debug("Ignored subscription to pattern %s", pattern)

    async def get(self) -> Optional[Event]:
        """Get next event.

        This method always returns None.

        Returns:
            Optional[Event]: Always returns None

        Examples:
            ```python
            event = await backend.get()  # Always returns None
            ```
        """
        return None
