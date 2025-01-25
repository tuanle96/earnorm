"""Model event handler implementation.

This module provides event handling for model events.
It handles model lifecycle events like created, updated, deleted.

Features:
- Model event handling
- Automatic event publishing
- Event validation
- Error handling
- Event tracking

Examples:
    ```python
    from earnorm.events.handlers.model import ModelEventHandler
    from earnorm.models import Model

    # Create model handler
    handler = ModelEventHandler[User](
        model_cls=User,
        pattern="user.*"
    )

    # Handle model events
    @handler.on_created
    async def handle_user_created(user: User) -> None:
        await send_welcome_email(user.email)

    @handler.on_updated
    async def handle_user_updated(user: User) -> None:
        await notify_profile_updated(user)

    @handler.on_deleted
    async def handle_user_deleted(user: User) -> None:
        await cleanup_user_data(user)
    ```
"""

import logging
from typing import Any, Callable, Dict, Optional, Type, TypeVar, cast

from earnorm.base import BaseModel
from earnorm.events.core.event import Event
from earnorm.events.handlers.base import EventHandler

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class ModelEventHandler(EventHandler):
    """Model event handler.

    This handler processes events for a specific model class.
    """

    def __init__(
        self,
        model_class: Type[T],
        event_type: str,
        method_name: Optional[str] = None,
    ) -> None:
        """Initialize handler.

        Args:
            model_class: Model class to handle events for
            event_type: Event type to handle
            method_name: Optional method name to call
        """
        self._model_class = model_class
        self._event_type = event_type
        self._method_name = method_name or f"on_{event_type}"
        self._id = f"{model_class.__name__}_{event_type}_handler"

    @property
    def id(self) -> str:
        """Get handler ID."""
        return self._id

    @property
    def data(self) -> Dict[str, Any]:
        """Get handler data."""
        return {
            "model": self._model_class.__name__,
            "event_type": self._event_type,
            "method": self._method_name,
        }

    async def handle(self, event: Event) -> None:
        """Handle event.

        This method:
        1. Gets model instance from event data
        2. Calls handler method on model instance
        """
        # Get model ID from event
        model_id = event.data.get("id")
        if not model_id:
            return

        # Get model instance
        env = cast(Environment, event.env)
        model = await self._model_class.get(env, model_id)
        if not model:
            return

        # Call handler method
        method = getattr(model, self._method_name)
        if method:
            await method(event)


def model_events(
    pattern: str,
    *,
    publish_created: bool = True,
    publish_updated: bool = True,
    publish_deleted: bool = True,
) -> Callable[[Type[T]], Type[T]]:
    """Decorator for enabling model events.

    This decorator adds event publishing to model lifecycle methods.

    Args:
        pattern: Event pattern prefix (e.g. "user")
        publish_created: Whether to publish created events
        publish_updated: Whether to publish updated events
        publish_deleted: Whether to publish deleted events

    Returns:
        Decorated model class

    Examples:
        ```python
        @model_events("user")
        class User(Model):
            name: str
            email: str

        # Events will be published automatically:
        user = await User.create(name="Test", email="test@example.com")
        # Publishes: user.created

        await user.update(name="Updated")
        # Publishes: user.updated

        await user.delete()
        # Publishes: user.deleted
        ```
    """

    def decorator(model_cls: Type[T]) -> Type[T]:
        # Store original methods
        original_save = getattr(model_cls, "save")
        original_delete = getattr(model_cls, "delete")

        # Add event publishing
        async def save(self: T, *args: Any, **kwargs: Any) -> None:
            is_new = not self.id
            await original_save(self, *args, **kwargs)

            # Publish event
            if is_new and publish_created:
                await self.publish_event(f"{pattern}.created")
            elif not is_new and publish_updated:
                await self.publish_event(f"{pattern}.updated")

        async def delete(self: T, *args: Any, **kwargs: Any) -> None:
            await original_delete(self, *args, **kwargs)
            if publish_deleted:
                await self.publish_event(f"{pattern}.deleted")

        # Add event publishing method
        async def publish_event(self: T, name: str) -> None:
            event = Event(
                name=name,
                data=self.to_dict(),
            )
            await self.env.events.publish(event)

        # Update model class
        model_cls.save = save  # type: ignore
        model_cls.delete = delete  # type: ignore
        model_cls.publish_event = publish_event  # type: ignore

        return model_cls

    return decorator


class UserHandler(EventHandler):
    """Handle user events."""

    @property
    def id(self) -> str:
        """Get handler ID."""
        return "user_handler"

    @property
    def data(self) -> Dict[str, Any]:
        """Get handler data."""
        return {"type": "user"}

    async def handle(self, event: Event) -> None:
        """Handle user event.

        Args:
            event: Event to handle
        """
        # Handle user event
        pass

    async def cleanup(self) -> None:
        """Cleanup handler resources."""
        # No resources to cleanup
        pass


class CreateUserHandler(EventHandler):
    """Handle user creation events."""

    @property
    def id(self) -> str:
        """Get handler ID."""
        return "create_user_handler"

    @property
    def data(self) -> Dict[str, Any]:
        """Get handler data."""
        return {"type": "user.create"}

    async def handle(self, event: Event) -> None:
        """Handle user creation event.

        Args:
            event: Event to handle
        """
        # Handle user creation
        pass

    async def cleanup(self) -> None:
        """Cleanup handler resources."""
        # No resources to cleanup
        pass


async def default_logger(event: Event) -> None:
    """Default event logger.

    Args:
        event: Event to log
    """
    # Log event
    pass


async def default_tracker(event: Event) -> None:
    """Default event tracker.

    Args:
        event: Event to track
    """
    # Track event
    pass


async def default_validator(event: Event) -> None:
    """Default event validator.

    Args:
        event: Event to validate
    """
    # Validate event
    pass


async def default_cleanup(event: Event) -> None:
    """Default event cleanup.

    Args:
        event: Event to cleanup
    """
    # Cleanup after event
    pass
