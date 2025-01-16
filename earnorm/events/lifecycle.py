"""Event lifecycle management.

This module provides lifecycle management for the event system, including:
- Initialization and cleanup of event bus
- Configuration management
- Health checks
- Metrics collection

The lifecycle manager ensures proper initialization and cleanup of event
resources, and provides a central point for managing event configuration
and state.

Examples:
    ```python
    from earnorm.events.lifecycle import EventLifecycleManager

    # Create lifecycle manager
    lifecycle = EventLifecycleManager()

    # Initialize with configuration
    await lifecycle.init(
        backend=RedisBackend(
            host="localhost",
            port=6379,
            db=0
        ),
        retry_policy={
            "max_retries": 3,
            "interval_start": 0,
            "interval_step": 0.2,
            "interval_max": 0.5,
        }
    )

    # Get event bus
    bus = lifecycle.bus
    if bus:
        await bus.publish(event)

    # Cleanup on shutdown
    await lifecycle.destroy()
    ```
"""

import logging
from typing import Any, Dict, Optional

from earnorm.di.lifecycle import LifecycleAware
from earnorm.events.core.bus import EventBus
from earnorm.events.core.exceptions import EventError

logger = logging.getLogger(__name__)


class EventLifecycleManager(LifecycleAware):
    """Event lifecycle manager.

    This class manages the lifecycle of the event system, including:
    - Initialization with configuration
    - Event bus creation and setup
    - Cleanup and resource release
    - Health checks and metrics

    Attributes:
        _bus: Optional[EventBus] - The managed event bus instance
    """

    def __init__(self) -> None:
        """Initialize manager with no event bus instance."""
        self._bus: Optional[EventBus] = None

    @property
    def id(self) -> Optional[str]:
        """Get manager ID.

        Returns:
            str: Always returns "event_lifecycle_manager"
        """
        return "event_lifecycle_manager"

    @property
    def data(self) -> Dict[str, Any]:
        """Get manager data.

        Returns:
            Dict containing manager state and configuration:
            - bus: Event bus configuration if initialized
        """
        return {
            "bus": {
                "initialized": self._bus is not None,
                "backend": self._bus.backend.id if self._bus else None,
            }
        }

    async def init(self, **config: Any) -> None:
        """Initialize event bus.

        This method creates and initializes a new event bus with the
        provided configuration.

        Args:
            **config: Configuration options
                - backend: Event backend instance
                - retry_policy: Optional retry policy for failed events

        Examples:
            ```python
            await manager.init(
                backend=RedisBackend(
                    host="localhost",
                    port=6379,
                    db=0
                ),
                retry_policy={
                    "max_retries": 3,
                    "interval_start": 0,
                    "interval_step": 0.2,
                    "interval_max": 0.5,
                }
            )
            ```
        """
        try:
            # Create event bus
            self._bus = EventBus(
                backend=config["backend"],
                retry_policy=config.get("retry_policy"),
            )

            # Initialize bus
            await self._bus.init()
            logger.info("Event lifecycle manager initialized")
        except Exception as e:
            logger.error("Failed to initialize event manager: %s", str(e))
            raise EventError(f"Failed to initialize event manager: {str(e)}")

    async def destroy(self) -> None:
        """Destroy event bus.

        This method cleans up event resources and releases connections.
        It should be called when shutting down the application.

        Examples:
            ```python
            await manager.destroy()
            ```
        """
        if self._bus:
            await self._bus.destroy()
            self._bus = None
            logger.info("Event lifecycle manager destroyed")

    @property
    def bus(self) -> Optional[EventBus]:
        """Get event bus.

        Returns:
            Optional[EventBus]: The managed event bus instance, if initialized
        """
        return self._bus
