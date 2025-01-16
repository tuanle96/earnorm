"""Base model implementation.

This module provides the base model class that all models inherit from.
It includes core functionality like:
- CRUD operations
- Event handling
- Validation
- Serialization

Examples:
    ```python
    from earnorm.base.models import Model
    from earnorm.fields import Char

    class User(Model):
        name = Char()
        email = Char()

        @event_handler("user.registered")
        async def handle_register(self, event: Event):
            print(f"User {self.name} registered")
    ```
"""

import inspect
import logging
from typing import Any, Callable, Coroutine, Dict, List, Optional, Type, TypeVar, cast

from typing_extensions import Self

from earnorm.base.recordset.recordset import RecordSet
from earnorm.base.types import ModelProtocol
from earnorm.events.core.event import Event

logger = logging.getLogger(__name__)

T = TypeVar("T", bound="Model")


class Model(ModelProtocol):
    """Base model class.

    All models should inherit from this class. It provides:
    - CRUD operations (find, save, delete)
    - Event handling via decorators
    - Validation
    - Serialization

    Attributes:
        _name: Model name
        _collection: MongoDB collection name
        _abstract: Whether model is abstract
        _data: Model data dictionary
        _event_handlers: Dictionary of event handlers
    """

    _name: str = ""
    _collection: str = ""
    _abstract: bool = False
    _data: Dict[str, Any] = {}
    _event_handlers: Dict[str, List[Callable[[Event], Coroutine[Any, Any, None]]]] = {}

    def __new__(cls: Type[Self], **kwargs: Any) -> RecordSet[Self]:
        """Create new instance.

        This method is called before __init__ when creating a new instance.
        It returns a RecordSet containing a single record instead of the instance itself.

        Args:
            **kwargs: Model data

        Returns:
            RecordSet containing the new instance
        """
        instance = super().__new__(cls)
        instance.__init__(**kwargs)  # type: ignore
        return RecordSet(cls, [cast(Self, instance)])

    def __init__(self, **kwargs: Any) -> None:
        """Initialize model.

        Args:
            **kwargs: Model data
        """
        super().__init__()
        self._data = kwargs
        self._register_event_handlers()

    def _register_event_handlers(self) -> None:
        """Register event handlers from methods."""
        # Get all methods
        for _, method in inspect.getmembers(self, inspect.ismethod):
            # Check if method is event handler
            if hasattr(method, "__is_event_handler__"):
                pattern = getattr(method, "__event_pattern__")

                # Register with event manager
                if self.env and self.env.events:
                    self.env.events.on(pattern)(method)

                # Store in handlers dict
                if pattern not in self._event_handlers:
                    self._event_handlers[pattern] = []
                self._event_handlers[pattern].append(method)

    @classmethod
    async def handle_event(cls, event: Event) -> None:
        """Handle event for this model class.

        This method is called by the event system when an event is received.
        It finds the appropriate handler method and calls it.

        Args:
            event: Event to handle
        """
        # Get handlers for this event
        pattern = event.name
        handlers = cls._event_handlers.get(pattern, [])

        # Call each handler
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(
                    "Event handler %s failed: %s",
                    handler.__name__,
                    str(e),
                    exc_info=True,
                )
                raise

    @property
    def id(self) -> Optional[str]:
        """Get document ID."""
        return str(self._data.get("_id")) if self._data.get("_id") else None

    @property
    def data(self) -> Dict[str, Any]:
        """Get model data."""
        return self._data

    async def validate(self) -> None:
        """Validate model data."""
        await self._validator.validate(self)

    async def save(self) -> None:
        """Save model to database."""
        await self._lifecycle.before_save(self)
        await self.validate()
        await self._persistence.save(self)
        await self._lifecycle.after_save(self)

    async def delete(self) -> None:
        """Delete model from database."""
        await self._lifecycle.before_delete(self)
        await self._persistence.delete(self)
        await self._lifecycle.after_delete(self)

    def __getattr__(self, name: str) -> Any:
        """Get dynamic attribute."""
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"'{self.__class__.__name__}' has no attribute '{name}'")
