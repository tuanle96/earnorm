"""Event handler interface.

This module defines the interface that all event handlers must implement.
It provides the contract for handling events and managing handler state.

Examples:
    ```python
    from earnorm.events.handlers.base import EventHandler
    from earnorm.events.core.event import Event

    class MyHandler(EventHandler):
        async def handle(self, event: Event) -> None:
            # Handle event
            print(f"Handling event {event.name}")

        async def cleanup(self) -> None:
            # Clean up resources
            await self.db.close()
    ```
"""

import abc
import logging
from typing import Any, Dict, Optional, Protocol

from earnorm.di.lifecycle import LifecycleAware
from earnorm.events.core.event import Event
from earnorm.events.core.exceptions import HandlerError

logger = logging.getLogger(__name__)


class EventHandlerProtocol(Protocol):
    """Event handler protocol.

    This protocol defines the interface that all event handlers must implement.
    It provides methods for handling events and managing handler state.
    """

    @property
    def id(self) -> Optional[str]:
        """Get handler ID.

        Returns:
            str: Handler identifier
        """
        ...

    @property
    def data(self) -> Dict[str, Any]:
        """Get handler data.

        Returns:
            Dict containing handler state and configuration
        """
        ...

    async def handle(self, event: Event) -> None:
        """Handle event.

        Args:
            event: Event to handle

        Raises:
            HandlerError: If handling fails
        """
        ...

    async def cleanup(self) -> None:
        """Clean up handler resources."""
        ...


class EventHandler(LifecycleAware, EventHandlerProtocol):
    """Base event handler implementation.

    This class provides a base implementation of the EventHandlerProtocol.
    Concrete handlers should inherit from this class and implement the
    required methods.

    Examples:
        ```python
        class UserCreatedHandler(EventHandler):
            def __init__(self, db):
                self._db = db

            async def handle(self, event: Event) -> None:
                user_id = event.data["id"]
                await self._db.users.update_one(
                    {"_id": user_id},
                    {"$set": {"email_verified": True}}
                )

            async def cleanup(self) -> None:
                await self._db.close()
        ```
    """

    @property
    @abc.abstractmethod
    def id(self) -> Optional[str]:
        """Get handler ID."""
        ...

    @property
    @abc.abstractmethod
    def data(self) -> Dict[str, Any]:
        """Get handler data."""
        ...

    async def init(self, **config: Any) -> None:
        """Initialize handler.

        This method should be called to initialize the handler with
        configuration options.

        Args:
            **config: Handler-specific configuration options

        Raises:
            HandlerError: If initialization fails
        """
        try:
            await self.setup(**config)
            logger.info(f"Event handler {self.id} initialized")
        except Exception as e:
            logger.error(f"Failed to initialize event handler: {str(e)}")
            raise HandlerError(f"Failed to initialize event handler: {str(e)}")

    async def destroy(self) -> None:
        """Destroy handler.

        This method should be called to clean up resources when shutting down.
        """
        await self.cleanup()
        logger.info(f"Event handler {self.id} destroyed")

    async def setup(self, **config: Any) -> None:
        """Set up handler.

        This method can be overridden to perform additional setup.

        Args:
            **config: Handler-specific configuration options
        """
        pass

    @abc.abstractmethod
    async def handle(self, event: Event) -> None:
        """Handle event.

        This method must be implemented by concrete handlers.

        Args:
            event: Event to handle

        Raises:
            HandlerError: If handling fails
        """
        ...
