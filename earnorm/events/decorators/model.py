"""Model event decorators."""

import functools
from typing import Any, Callable, Optional, TypeVar, cast

from ..core import Event

T = TypeVar("T", bound=Callable[..., Any])


def before_save(event_name: Optional[str] = None) -> Callable[[T], T]:
    """Decorator for triggering events before saving a model.

    Args:
        event_name: Optional custom event name

    Returns:
        Decorator function
    """

    def decorator(func: T) -> T:
        @functools.wraps(func)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            # Generate event name if not provided
            name = event_name or f"{self.__class__.__name__}.before_save"

            # Create event with model data
            event = Event(
                name=name,
                data=self.to_dict(),
                metadata={
                    "model": self.__class__.__name__,
                    "model_id": str(self.id) if hasattr(self, "id") else None,
                },
            )

            # Publish event if event bus is configured
            if hasattr(self, "_env") and hasattr(self._env, "event_bus"):
                await self._env.event_bus.publish(event)

            # Call original method
            return await func(self, *args, **kwargs)

        return cast(T, wrapper)

    return decorator


def after_save(event_name: Optional[str] = None) -> Callable[[T], T]:
    """Decorator for triggering events after saving a model.

    Args:
        event_name: Optional custom event name

    Returns:
        Decorator function
    """

    def decorator(func: T) -> T:
        @functools.wraps(func)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            # Call original method first
            result = await func(self, *args, **kwargs)

            # Generate event name if not provided
            name = event_name or f"{self.__class__.__name__}.after_save"

            # Create event with model data
            event = Event(
                name=name,
                data=self.to_dict(),
                metadata={
                    "model": self.__class__.__name__,
                    "model_id": str(self.id) if hasattr(self, "id") else None,
                },
            )

            # Publish event if event bus is configured
            if hasattr(self, "_env") and hasattr(self._env, "event_bus"):
                await self._env.event_bus.publish(event)

            return result

        return cast(T, wrapper)

    return decorator


def before_delete(event_name: Optional[str] = None) -> Callable[[T], T]:
    """Decorator for triggering events before deleting a model.

    Args:
        event_name: Optional custom event name

    Returns:
        Decorator function
    """

    def decorator(func: T) -> T:
        @functools.wraps(func)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            # Generate event name if not provided
            name = event_name or f"{self.__class__.__name__}.before_delete"

            # Create event with model data
            event = Event(
                name=name,
                data=self.to_dict(),
                metadata={
                    "model": self.__class__.__name__,
                    "model_id": str(self.id) if hasattr(self, "id") else None,
                },
            )

            # Publish event if event bus is configured
            if hasattr(self, "_env") and hasattr(self._env, "event_bus"):
                await self._env.event_bus.publish(event)

            # Call original method
            return await func(self, *args, **kwargs)

        return cast(T, wrapper)

    return decorator


def after_delete(event_name: Optional[str] = None) -> Callable[[T], T]:
    """Decorator for triggering events after deleting a model.

    Args:
        event_name: Optional custom event name

    Returns:
        Decorator function
    """

    def decorator(func: T) -> T:
        @functools.wraps(func)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            # Store model data before deletion
            model_data = self.to_dict()
            model_id = str(self.id) if hasattr(self, "id") else None

            # Call original method
            result = await func(self, *args, **kwargs)

            # Generate event name if not provided
            name = event_name or f"{self.__class__.__name__}.after_delete"

            # Create event with stored model data
            event = Event(
                name=name,
                data=model_data,
                metadata={"model": self.__class__.__name__, "model_id": model_id},
            )

            # Publish event if event bus is configured
            if hasattr(self, "_env") and hasattr(self._env, "event_bus"):
                await self._env.event_bus.publish(event)

            return result

        return cast(T, wrapper)

    return decorator
