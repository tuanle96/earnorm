"""Retry policy implementation."""

import asyncio
import functools
import logging
from typing import Any, Callable, Optional, Type, TypeVar, cast

logger = logging.getLogger(__name__)

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


def retry_policy(
    max_retries: int = 3,
    delay: float = 1.0,
    max_delay: float = 30.0,
    backoff: float = 2.0,
    exceptions: Optional[tuple[Type[Exception], ...]] = None,
) -> Callable[[F], F]:
    """Retry policy decorator.

    Args:
        max_retries: Maximum number of retries
        delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff: Backoff multiplier for delay
        exceptions: Tuple of exceptions to catch

    Returns:
        Decorated function

    Examples:
        >>> @retry_policy(max_retries=3, delay=1.0)
        ... async def my_operation() -> None:
        ...     # Operation that may fail
        ...     ...
        >>>
        >>> @retry_policy(
        ...     max_retries=5,
        ...     delay=0.1,
        ...     max_delay=5.0,
        ...     backoff=2.0,
        ...     exceptions=(ConnectionError, TimeoutError)
        ... )
        ... async def my_service() -> None:
        ...     # Service that may fail
        ...     ...
    """
    if exceptions is None:
        exceptions = (Exception,)

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            current_delay = delay
            last_exception: Optional[Exception] = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    last_exception = exc

                    if attempt == max_retries:
                        break

                    logger.warning(
                        "Attempt %d/%d failed: %s",
                        attempt + 1,
                        max_retries,
                        str(exc),
                    )

                    # Wait before next attempt
                    await asyncio.sleep(current_delay)

                    # Update delay for next attempt
                    current_delay = min(current_delay * backoff, max_delay)

            if last_exception is not None:
                raise last_exception

            return None  # Make mypy happy

        return cast(F, wrapper)

    return decorator
