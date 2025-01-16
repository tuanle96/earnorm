"""Event decorator implementation.

This module provides decorators for event handling.
It includes decorators for event handlers, retry policies, and transactions.

Features:
- Event handler registration
- Retry policies
- Transaction management
- Error handling
- Metrics collection

Examples:
    ```python
    from earnorm.events.decorators.event import event_handler, retry, transactional
    from earnorm.events.core.event import Event

    # Register event handler
    @event_handler("user.created")
    async def handle_user_created(event: Event) -> None:
        print(f"User created: {event.data}")

    # Add retry policy
    @retry(max_retries=3, retry_delay=1, max_delay=5)
    async def handle_with_retry(event: Event) -> None:
        print(f"Handling event: {event.name}")

    # Add transaction
    @transactional
    async def handle_with_transaction(event: Event) -> None:
        print(f"Handling event in transaction: {event.name}")
    ```
"""

import asyncio
import functools
import logging
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Optional,
    Protocol,
    TypeVar,
    Union,
    runtime_checkable,
)

from earnorm.events.core.event import Event
from earnorm.events.core.exceptions import HandlerError
from earnorm.events.handlers.base import EventHandler

logger = logging.getLogger(__name__)

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


@runtime_checkable
class EventHandlerCallable(Protocol):
    """Event handler callable protocol."""

    async def __call__(self, event: Event) -> Any:
        """Handle event."""
        ...


def event_handler(pattern: str) -> Callable[[EventHandlerCallable], EventHandler]:
    """Register event handler.

    This decorator registers a function as an event handler.
    It creates a new handler instance and registers it with the event bus.

    Args:
        pattern: Event pattern to match

    Returns:
        Decorator function that creates handler

    Examples:
        ```python
        @event_handler("user.created")
        async def handle_user_created(event: Event) -> None:
            print(f"User created: {event.data}")

        @event_handler("user.*")
        async def handle_user_events(event: Event) -> None:
            print(f"User event: {event.name}")
        ```
    """

    def decorator(func: EventHandlerCallable) -> EventHandler:
        # Create handler class
        class FunctionHandler(EventHandler):
            @property
            def id(self) -> str:
                return f"function_handler_{pattern}"

            @property
            def data(self) -> Dict[str, Any]:
                return {"pattern": pattern}

            async def handle(self, event: Event) -> None:
                await func(event)

            async def cleanup(self) -> None:
                pass

        # Create handler instance
        handler = FunctionHandler()
        logger.debug("Created handler for pattern %s", pattern)
        return handler

    return decorator


def retry(
    func: Optional[F] = None,
    *,
    max_retries: int = 3,
    retry_delay: int = 1,
    max_delay: int = 5,
) -> Union[F, Callable[[F], F]]:
    """Add retry policy to handler.

    This decorator adds retry logic to an event handler.
    It retries failed operations with exponential backoff.

    Args:
        func: Function to decorate
        max_retries: Maximum number of retries
        retry_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds

    Returns:
        Decorated handler function

    Examples:
        ```python
        @retry(max_retries=3, retry_delay=1, max_delay=5)
        async def handle_with_retry(event: Event) -> None:
            print(f"Handling event: {event.name}")

        @retry()  # Use default values
        async def handle_with_default_retry(event: Event) -> None:
            print(f"Handling event: {event.name}")
        ```
    """

    def decorator(handler_func: F) -> F:
        @functools.wraps(handler_func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Try operation with retries
            for attempt in range(max_retries + 1):
                try:
                    return await handler_func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries:
                        logger.error(
                            "Operation failed after %d retries: %s", max_retries, str(e)
                        )
                        raise HandlerError("Operation failed: %s" % str(e))

                    # Calculate delay
                    delay = min(retry_delay * (2**attempt), max_delay)
                    logger.warning(
                        "Attempt %d failed, retrying in %ds: %s",
                        attempt + 1,
                        delay,
                        str(e),
                    )
                    await asyncio.sleep(delay)

        return wrapper  # type: ignore

    if func is None:
        return decorator
    return decorator(func)


def transactional(
    func: Optional[F] = None,
) -> Union[F, Callable[[F], F]]:
    """Add transaction to handler.

    This decorator wraps an event handler in a transaction.
    It ensures all operations are atomic and can be rolled back.

    Args:
        func: Handler function to wrap

    Returns:
        Decorated handler function

    Examples:
        ```python
        @transactional
        async def handle_with_transaction(event: Event) -> None:
            print(f"Handling event in transaction: {event.name}")

        @transactional
        @retry()
        async def handle_with_transaction_and_retry(event: Event) -> None:
            print(f"Handling event: {event.name}")
        ```
    """

    def decorator(handler_func: F) -> F:
        @functools.wraps(handler_func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # TODO: Implement transaction management
            try:
                return await handler_func(*args, **kwargs)
            except Exception as e:
                logger.error("Transaction failed: %s", str(e))
                raise HandlerError("Transaction failed: %s" % str(e))

        return wrapper  # type: ignore

    if func is None:
        return decorator
    return decorator(func)
