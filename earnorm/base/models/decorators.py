"""Model decorators.

This module provides decorators for model methods:
- event_handler: Register method as event handler

Examples:
    ```python
    from earnorm.base.models import Model
    from earnorm.base.models.decorators import event_handler

    class User(Model):
        name = fields.Char()

        @event_handler("user.registered")
        async def handle_user_register(self, event: Event):
            # Handle user registration event
            print(f"User {self.name} registered")

        @event_handler("user.profile_updated")
        async def handle_profile_update(self, event: Event):
            # Handle profile update event
            print(f"User {self.name} updated profile")
    ```
"""

import functools
import logging
from typing import Any, Callable, Protocol, TypeVar

from earnorm.events.core.event import Event

logger = logging.getLogger(__name__)


class ModelProtocol(Protocol):
    """Protocol for model type."""

    @property
    def name(self) -> str:
        """Get model name."""
        ...


M = TypeVar("M", bound=ModelProtocol)


def event_handler(
    pattern: str,
) -> Callable[[Callable[[M, Event], Any]], Callable[[M, Event], Any]]:
    """Register method as event handler.

    This decorator registers a model method as an event handler.
    The method will be called when an event matching the pattern is received.

    Args:
        pattern: Event pattern to match (e.g. "user.registered")

    Returns:
        Decorator function

    Examples:
        ```python
        class User(Model):
            name = fields.Char()

            @event_handler("user.registered")
            async def handle_register(self, event: Event):
                print(f"User {self.name} registered")

            @event_handler("user.*.updated")
            async def handle_update(self, event: Event):
                print(f"User {self.name} updated {event.name}")
        ```
    """

    def decorator(func: Callable[[M, Event], Any]) -> Callable[[M, Event], Any]:
        @functools.wraps(func)
        async def wrapper(self: M, event: Event) -> Any:
            try:
                # Call handler
                return await func(self, event)
            except Exception as e:
                logger.error(
                    "Event handler %s failed: %s", func.__name__, str(e), exc_info=True
                )
                raise

        # Mark as event handler
        setattr(wrapper, "__event_pattern__", pattern)
        setattr(wrapper, "__is_event_handler__", True)

        return wrapper

    return decorator
