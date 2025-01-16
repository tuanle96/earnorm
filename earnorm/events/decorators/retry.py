"""Retry decorator implementation.

This module provides decorators for retry handling.
It adds retry logic to event handlers for handling transient failures.

Features:
- Configurable retry attempts
- Exponential backoff
- Retry conditions
- Error filtering
- Retry logging

Examples:
    ```python
    from earnorm.events.decorators.retry import retry
    from earnorm.events.core.event import Event

    @retry(max_attempts=3)
    async def handle_user_created(event: Event) -> None:
        # This handler will retry up to 3 times on failure
        await process_user(event.data)

    @retry(max_attempts=5, backoff=2.0)
    async def handle_with_backoff(event: Event) -> None:
        # This handler uses exponential backoff between retries
        await process_event(event)
    ```
"""

import asyncio
import functools
import logging
import random
from typing import Any, Awaitable, Callable, Optional, Type, TypeVar, Union

from earnorm.events.core.exceptions import HandlerError

logger = logging.getLogger(__name__)

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


def retry(
    func: Optional[F] = None,
    *,
    max_attempts: int = 3,
    backoff: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    exceptions: Optional[Union[Type[Exception], tuple[Type[Exception], ...]]] = None,
) -> Union[F, Callable[[F], F]]:
    """Retry decorator.

    This decorator adds retry logic to a function.
    It will retry the function on failure with configurable backoff.

    Args:
        func: Function to decorate
        max_attempts: Maximum number of retry attempts
        backoff: Backoff multiplier between retries
        max_delay: Maximum delay between retries in seconds
        jitter: Whether to add random jitter to delays
        exceptions: Exception types to retry on (default: all)

    Returns:
        Decorated function

    Examples:
        ```python
        @retry
        async def handle_event(event: Event) -> None:
            # Will retry 3 times by default
            await process_event(event)

        @retry(max_attempts=5, backoff=2.0, jitter=True)
        async def handle_with_backoff(event: Event) -> None:
            # Will retry up to 5 times with exponential backoff
            await process_event(event)
        ```
    """

    def decorator(handler_func: F) -> F:
        @functools.wraps(handler_func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 1
            last_exception = None

            while attempt <= max_attempts:
                try:
                    return await handler_func(*args, **kwargs)

                except Exception as e:
                    # Check if we should retry this exception
                    if exceptions and not isinstance(e, exceptions):
                        raise

                    last_exception = e
                    if attempt == max_attempts:
                        logger.error(
                            "Failed after %d attempts: %s", max_attempts, str(e)
                        )
                        raise HandlerError("Max retries exceeded: " + str(e))

                    # Calculate delay with exponential backoff
                    delay = min(backoff * (2 ** (attempt - 1)), max_delay)
                    if jitter:
                        delay *= 0.5 + random.random()

                    logger.warning(
                        "Attempt %d failed: %s. Retrying in %.2fs",
                        attempt,
                        str(e),
                        delay,
                    )

                    # Wait before retrying
                    await asyncio.sleep(delay)
                    attempt += 1

            # Should never reach here
            raise HandlerError(
                "Unexpected error after %d attempts: %s"
                % (max_attempts, str(last_exception))
            )

        return wrapper  # type: ignore

    if func is None:
        return decorator
    return decorator(func)
