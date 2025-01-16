"""Event system for EarnORM.

This module provides an event system for EarnORM, using Redis Pub/Sub as
the message broker. Events are processed asynchronously and can be delayed,
retried, and monitored.

Features:
- Asynchronous event processing
- Redis Pub/Sub backend
- Event handlers and decorators
- Retry policies
- Health checks
- Metrics collection

Basic usage:
    ```python
    from earnorm import init
    from earnorm.events import Event, event_handler

    # Initialize EarnORM with event system
    await init(
        mongo_uri="mongodb://localhost:27017",
        database="earnbase",
        redis_uri="redis://localhost:6379/0",
        event_config={
            "backend": {
                "host": "localhost",
                "port": 6379,
                "db": 0
            },
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
    from earnorm.base import BaseModel
    from earnorm.events import Event

    class User(BaseModel):
        async def create(self, **data):
            await super().create(**data)
            await self.env.events.publish(
                Event(name="user.created", data={"id": str(self.id)})
            )
    ```

For model events:
    ```python
    from earnorm.events import model_event_handler

    @model_event_handler("User", "created")
    async def handle_user_created(event):
        print(f"User created: {event.data}")
    ```

Configuration options:
    - backend: Event backend configuration
        - host: Redis host (default: "localhost")
        - port: Redis port (default: 6379)
        - db: Redis database (default: 0)
    - retry_policy: Retry policy for failed events
        - max_retries: Maximum number of retries (default: 3)
        - interval_start: Initial delay in seconds (default: 0)
        - interval_step: Delay increment in seconds (default: 0.2)
        - interval_max: Maximum delay in seconds (default: 0.5)
"""

from earnorm.events.backends.base import EventBackend
from earnorm.events.backends.redis import RedisBackend
from earnorm.events.core.event import Event
from earnorm.events.core.exceptions import (
    ConnectionError,
    EventError,
    HandlerError,
    PublishError,
    ValidationError,
)
from earnorm.events.decorators.event import event_handler
from earnorm.events.handlers.base import EventHandler
from earnorm.events.handlers.model import ModelEventHandler, model_events
from earnorm.events.lifecycle import EventLifecycleManager

__all__ = [
    # Core
    "Event",
    "EventError",
    "ConnectionError",
    "PublishError",
    "HandlerError",
    "ValidationError",
    # Backends
    "EventBackend",
    "RedisBackend",
    # Handlers
    "EventHandler",
    "ModelEventHandler",
    # Decorators
    "event_handler",
    "model_events",
    # Lifecycle
    "EventLifecycleManager",
]
