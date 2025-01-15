"""Utility functions for event system."""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union

from earnorm.base import BaseModel
from earnorm.events.core import Event, EventBus

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)
F = TypeVar("F", bound=Callable[..., Any])


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


def model_event_handler(model_cls: Type[T], event_name: str) -> Callable[[F], F]:
    """Decorator to register model event handler.

    Args:
        model_cls: Model class to handle events for
        event_name: Name of event to handle

    Returns:
        Decorated function
    """
    full_event_name = f"{model_cls.__name__}.{event_name}"
    return event_handler(full_event_name)


async def dispatch_event(
    event_bus: EventBus,
    event_name: str,
    data: Optional[Union[Dict[str, Any], T]] = None,
    delay: Optional[float] = None,
) -> None:
    """Dispatch event to event bus.

    Args:
        event_bus: Event bus instance
        event_name: Event name
        data: Event data
        delay: Optional delay in seconds
    """
    event_data = data.dict() if isinstance(data, BaseModel) else (data or {})
    event = Event(name=event_name, data=event_data)
    await event_bus.publish(event, delay=delay)


async def dispatch_model_event(
    event_bus: EventBus,
    model_cls: Type[T],
    event_name: str,
    model_id: Optional[str] = None,
    data: Optional[T] = None,
    delay: Optional[float] = None,
) -> None:
    """Dispatch model event to event bus.

    Args:
        event_bus: Event bus instance
        model_cls: Model class
        event_name: Event name
        model_id: Optional model ID
        data: Optional event data
        delay: Optional delay in seconds
    """
    full_event_name = f"{model_cls.__name__}.{event_name}"
    event_data: Dict[str, Any] = {"id": model_id} if model_id else {}
    if data:
        event_data["data"] = data.dict()
    await dispatch_event(event_bus, full_event_name, event_data, delay)


async def dispatch_batch_event(
    event_bus: EventBus,
    event_name: str,
    items: List[T],
    batch_size: int = 100,
    delay: Optional[float] = None,
) -> None:
    """Dispatch batch of events to event bus.

    Args:
        event_bus: Event bus instance
        event_name: Event name
        items: List of event data items
        batch_size: Batch size for processing
        delay: Optional delay in seconds
    """
    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        tasks = [dispatch_event(event_bus, event_name, item, delay) for item in batch]
        await asyncio.gather(*tasks)


async def dispatch_model_batch_event(
    event_bus: EventBus,
    model_cls: Type[T],
    event_name: str,
    items: List[T],
    batch_size: int = 100,
    delay: Optional[float] = None,
) -> None:
    """Dispatch batch of model events to event bus.

    Args:
        event_bus: Event bus instance
        model_cls: Model class
        event_name: Event name
        items: List of event data items
        batch_size: Batch size for processing
        delay: Optional delay in seconds
    """
    full_event_name = f"{model_cls.__name__}.{event_name}"
    await dispatch_batch_event(event_bus, full_event_name, items, batch_size, delay)
