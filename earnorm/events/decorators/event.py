"""Event decorators for EarnORM."""

import functools
from typing import Any, Callable, Optional, Type, TypeVar, cast

from earnorm.base import BaseModel
from earnorm.events.core.types import EventData

F = TypeVar("F", bound=Callable[..., Any])


def event(
    event_name: str, data_class: Optional[Type[EventData]] = None
) -> Callable[[F], F]:
    """Decorator for custom event handlers.

    Args:
        event_name: Name of event to handle (e.g. 'order_created', 'payment_failed')
        data_class: Optional Pydantic model class for event data validation

    Example:
        ```python
        class OrderCreatedEvent(EventData):
            order_id: str
            total: float
            items: list[dict]

        class User(BaseModel):
            @event('order_created', data_class=OrderCreatedEvent)
            async def send_order_email(self, data: OrderCreatedEvent):
                await self.mail_service.send_order_confirmation(
                    self.email,
                    order_id=data.order_id,
                    total=data.total
                )
        ```
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            # Validate data if data_class is provided
            if data_class and args:
                event_data = data_class(**args[0])
                return await func(self, event_data)
            return await func(self, *args, **kwargs)

        # Mark as event handler
        setattr(wrapper, "_is_event_handler", True)
        setattr(wrapper, "_event_name", event_name)
        setattr(wrapper, "_event_data_class", data_class)
        return cast(F, wrapper)

    return decorator


def event_handler(event_name: str) -> Callable[[F], F]:
    """Decorator to register event handler.

    Args:
        event_name: Name of event to handle

    Returns:
        Decorated function
    """

    def decorator(func: F) -> F:
        # Mark function as event handler
        setattr(func, "_is_event_handler", True)
        setattr(func, "_event_name", event_name)
        return func

    return decorator


def model_event_handler(
    model_cls: Type[BaseModel], event_name: str
) -> Callable[[F], F]:
    """Decorator to register model event handler.

    Args:
        model_cls: Model class to handle events for
        event_name: Name of event to handle

    Returns:
        Decorated function
    """
    full_event_name = f"{model_cls.__name__}.{event_name}"
    return event_handler(full_event_name)
