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
from typing import Any, Awaitable, Callable, Generic, Optional, Type, TypeVar

from earnorm.base.models.base import Model
from earnorm.events.core.event import Event
from earnorm.events.core.exceptions import HandlerError
from earnorm.events.handlers.base import EventHandler

logger = logging.getLogger(__name__)

M = TypeVar("M", bound=Model)


class ModelEventHandler(EventHandler, Generic[M]):
    """Model event handler.

    This class handles events for a specific model type.
    It provides decorators for handling model lifecycle events.

    Attributes:
        model_cls: Model class to handle events for
        pattern: Event pattern to match (e.g. "user.*")
        created_handler: Handler for created events
        updated_handler: Handler for updated events
        deleted_handler: Handler for deleted events

    Examples:
        ```python
        # Create handler for User model
        handler = ModelEventHandler[User](
            model_cls=User,
            pattern="user.*"
        )

        # Register event handlers
        @handler.on_created
        async def handle_created(user: User) -> None:
            await send_welcome_email(user)

        @handler.on_updated
        async def handle_updated(user: User) -> None:
            await notify_profile_updated(user)

        @handler.on_deleted
        async def handle_deleted(user: User) -> None:
            await cleanup_user_data(user)
        ```
    """

    def __init__(
        self,
        model_cls: Type[M],
        pattern: str,
    ) -> None:
        """Initialize model event handler.

        Args:
            model_cls: Model class to handle events for
            pattern: Event pattern to match
        """
        super().__init__()
        self._pattern = pattern
        self.model_cls = model_cls
        self.created_handler: Optional[Callable[[M], Awaitable[None]]] = None
        self.updated_handler: Optional[Callable[[M], Awaitable[None]]] = None
        self.deleted_handler: Optional[Callable[[M], Awaitable[None]]] = None

    @property
    def id(self) -> str:
        """Get handler ID."""
        return f"model_handler_{self.model_cls.__name__}_{self._pattern}"

    @property
    def data(self) -> dict[str, Any]:
        """Get handler data."""
        return {
            "model": self.model_cls.__name__,
            "pattern": self._pattern,
        }

    def on_created(
        self, func: Callable[[M], Awaitable[None]]
    ) -> Callable[[M], Awaitable[None]]:
        """Decorator for handling created events.

        Args:
            func: Handler function

        Returns:
            Decorated function

        Examples:
            ```python
            @handler.on_created
            async def handle_created(user: User) -> None:
                await send_welcome_email(user)
            ```
        """
        self.created_handler = func
        return func

    def on_updated(
        self, func: Callable[[M], Awaitable[None]]
    ) -> Callable[[M], Awaitable[None]]:
        """Decorator for handling updated events.

        Args:
            func: Handler function

        Returns:
            Decorated function

        Examples:
            ```python
            @handler.on_updated
            async def handle_updated(user: User) -> None:
                await notify_profile_updated(user)
            ```
        """
        self.updated_handler = func
        return func

    def on_deleted(
        self, func: Callable[[M], Awaitable[None]]
    ) -> Callable[[M], Awaitable[None]]:
        """Decorator for handling deleted events.

        Args:
            func: Handler function

        Returns:
            Decorated function

        Examples:
            ```python
            @handler.on_deleted
            async def handle_deleted(user: User) -> None:
                await cleanup_user_data(user)
            ```
        """
        self.deleted_handler = func
        return func

    async def handle(self, event: Event) -> None:
        """Handle model event.

        This method routes events to the appropriate handler based on
        the event name.

        Args:
            event: Event to handle

        Raises:
            HandlerError: If event handling fails
        """
        try:
            # Get model instance from event data
            model = self.model_cls(**event.data)

            # Route to appropriate handler
            if event.name.endswith(".created") and self.created_handler:
                await self.created_handler(model)
            elif event.name.endswith(".updated") and self.updated_handler:
                await self.updated_handler(model)
            elif event.name.endswith(".deleted") and self.deleted_handler:
                await self.deleted_handler(model)
            else:
                logger.warning(f"No handler for event: {event.name}")

        except Exception as e:
            raise HandlerError(f"Failed to handle model event: {str(e)}")


def model_events(
    pattern: str,
    *,
    publish_created: bool = True,
    publish_updated: bool = True,
    publish_deleted: bool = True,
) -> Callable[[Type[M]], Type[M]]:
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

    def decorator(model_cls: Type[M]) -> Type[M]:
        # Store original methods
        original_save = getattr(model_cls, "save")
        original_delete = getattr(model_cls, "delete")

        # Add event publishing
        async def save(self: M, *args: Any, **kwargs: Any) -> None:
            is_new = not self.id
            await original_save(self, *args, **kwargs)

            # Publish event
            if is_new and publish_created:
                await self.publish_event(f"{pattern}.created")
            elif not is_new and publish_updated:
                await self.publish_event(f"{pattern}.updated")

        async def delete(self: M, *args: Any, **kwargs: Any) -> None:
            await original_delete(self, *args, **kwargs)
            if publish_deleted:
                await self.publish_event(f"{pattern}.deleted")

        # Add event publishing method
        async def publish_event(self: M, name: str) -> None:
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
