"""Event backend interface.

This module defines the interface that all event backends must implement.
It provides the contract for event publishing and subscription.

Examples:
    ```python
    from earnorm.events.backends.base import EventBackend
    from earnorm.events.core.event import Event

    class MyBackend(EventBackend):
        async def connect(self) -> None:
            # Connect to message broker
            ...

        async def disconnect(self) -> None:
            # Disconnect from message broker
            ...

        async def publish(self, event: Event) -> None:
            # Publish event
            ...

        async def subscribe(self, pattern: str) -> None:
            # Subscribe to events matching pattern
            ...
    ```
"""

import abc
import logging
from typing import Any, Dict, Optional, Protocol

from earnorm.di.lifecycle import LifecycleAware
from earnorm.events.core.event import Event
from earnorm.events.core.exceptions import EventConnectionError


logger = logging.getLogger(__name__)


class EventBackendProtocol(Protocol):
    """Event backend protocol.

    This protocol defines the interface that all event backends must implement.
    It provides methods for connecting to the message broker, publishing events,
    and subscribing to event patterns.
    """

    @property
    def id(self) -> Optional[str]:
        """Get backend ID.

        Returns:
            str: Backend identifier
        """
        ...

    @property
    def data(self) -> Dict[str, Any]:
        """Get backend data.

        Returns:
            Dict containing backend state and configuration
        """
        ...

    @property
    def is_connected(self) -> bool:
        """Check if connected to message broker.

        Returns:
            bool: True if connected
        """
        ...

    async def connect(self) -> None:
        """Connect to message broker.

        Raises:
            ConnectionError: If connection fails
        """
        ...

    async def disconnect(self) -> None:
        """Disconnect from message broker."""
        ...

    async def publish(self, event: Event) -> None:
        """Publish event.

        Args:
            event: Event to publish

        Raises:
            PublishError: If publish fails
        """
        ...

    async def subscribe(self, pattern: str) -> None:
        """Subscribe to events matching pattern.

        Args:
            pattern: Event pattern to match

        Raises:
            ConnectionError: If subscription fails
        """
        ...


class EventBackend(LifecycleAware, EventBackendProtocol):
    """Base event backend implementation.

    This class provides a base implementation of the EventBackendProtocol.
    Concrete backends should inherit from this class and implement the
    required methods.

    Examples:
        ```python
        class RedisBackend(EventBackend):
            def __init__(self, redis_uri: str):
                self._redis_uri = redis_uri
                self._client = None

            async def connect(self) -> None:
                self._client = await redis.from_url(self._redis_uri)
                await self._client.ping()

            async def publish(self, event: Event) -> None:
                await self._client.publish(event.name, event.data)
        ```
    """

    @property
    @abc.abstractmethod
    def id(self) -> Optional[str]:
        """Get backend ID."""
        ...

    @property
    @abc.abstractmethod
    def data(self) -> Dict[str, Any]:
        """Get backend data."""
        ...

    @property
    @abc.abstractmethod
    def is_connected(self) -> bool:
        """Check if connected."""
        ...

    async def init(self, **config: Any) -> None:
        """Initialize backend.

        This method should be called to initialize the backend with
        configuration options.

        Args:
            **config: Backend-specific configuration options

        Raises:
            ConnectionError: If initialization fails
        """
        try:
            await self.connect()
            if self.id:
                logger.info("Event backend %s initialized", self.id)
            else:
                logger.info("Event backend initialized")
        except Exception as e:
            logger.error("Failed to initialize event backend: %s", str(e))
            raise EventConnectionError(f"Failed to initialize event backend: {str(e)}") from e

    async def destroy(self) -> None:
        """Destroy backend.

        This method should be called to clean up resources when shutting down.
        """
        await self.disconnect()
        if self.id:
            logger.info("Event backend %s destroyed", self.id)
        else:
            logger.info("Event backend destroyed")
