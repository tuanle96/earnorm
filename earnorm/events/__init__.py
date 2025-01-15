"""Event system for EarnORM.

This module provides an event system for EarnORM, using Celery as the message broker.
Events are processed asynchronously and can be delayed, retried, and monitored.

Basic usage:
    ```python
    from earnorm import init
    from earnorm.events import event_handler

    # Initialize EarnORM with event system
    await init(
        mongo_uri="mongodb://localhost:27017",
        database="earnbase",
        redis_uri="redis://localhost:6379/0",
        event_config={
            "queue_name": "my_app:events",
            "retry_policy": {
                "max_retries": 3,
                "interval_start": 0,
                "interval_step": 0.2,
                "interval_max": 0.5,
            }
        }
    )

    # Define event handler
    @event_handler("user.created")
    async def handle_user_created(event):
        print(f"User created: {event.data}")

    # Publish event
    from earnorm import event_bus
    from earnorm.events import Event
    await event_bus.publish(Event(name="user.created", data={"id": "123"}))
    ```

For model events:
    ```python
    from earnorm.events import model_event_handler

    @model_event_handler("User", "created")
    async def handle_user_created(event):
        print(f"User created: {event.data}")
    ```

Configuration options:
    - queue_name: Event queue name (default: "earnorm:events")
    - retry_policy: Retry policy for failed events
        - max_retries: Maximum number of retries (default: 3)
        - interval_start: Initial delay in seconds (default: 0)
        - interval_step: Delay increment in seconds (default: 0.2)
        - interval_max: Maximum delay in seconds (default: 0.5)
"""

from typing import Any, Dict, Optional

from earnorm.events.core.bus import EventBus
from earnorm.events.core.event import Event
from earnorm.events.decorators.event import event_handler, model_event_handler
from earnorm.events.utils.utils import (
    dispatch_batch_event,
    dispatch_event,
    dispatch_model_batch_event,
    dispatch_model_event,
)

# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get global event bus instance.

    Returns:
        EventBus: Global event bus instance

    Raises:
        RuntimeError: If event bus is not initialized
    """
    if _event_bus is None:
        raise RuntimeError(
            "Event bus is not initialized. Initialize EarnORM with redis_uri first."
        )
    return _event_bus


async def init_event_bus(
    redis_uri: str,
    queue_name: str = "earnorm:events",
    retry_policy: Optional[Dict[str, Any]] = None,
) -> EventBus:
    """Initialize global event bus.

    Note:
        This function is for internal use only.
        Use earnorm.init() with redis_uri and event_config instead.

    Args:
        redis_uri: Redis connection URI
        queue_name: Queue name for events (default: "earnorm:events")
        retry_policy: Retry policy for failed events. Example:
            {
                "max_retries": 3,
                "interval_start": 0,
                "interval_step": 0.2,
                "interval_max": 0.5,
            }

    Returns:
        EventBus: Initialized event bus instance

    Raises:
        RuntimeError: If failed to connect to Redis
    """
    global _event_bus

    if _event_bus is not None:
        await _event_bus.disconnect()

    _event_bus = EventBus(
        redis_uri=redis_uri,
        queue_name=queue_name,
        retry_policy=retry_policy,
    )
    await _event_bus.connect()
    return _event_bus


async def shutdown_event_bus() -> None:
    """Shutdown global event bus.

    Note:
        This function is for internal use only.
        The event bus will be automatically shutdown when EarnORM is shutdown.
    """
    global _event_bus

    if _event_bus is not None:
        await _event_bus.disconnect()
        _event_bus = None


__all__ = [
    # Core
    "Event",
    "EventBus",
    # Functions
    "get_event_bus",
    # Decorators
    "event_handler",
    "model_event_handler",
    # Utils
    "dispatch_event",
    "dispatch_model_event",
    "dispatch_batch_event",
    "dispatch_model_batch_event",
]
