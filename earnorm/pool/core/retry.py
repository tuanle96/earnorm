"""Retry mechanism implementation.

This module provides retry functionality with exponential backoff.
It helps handle transient failures in database operations.

Examples:
    ```python
    retry = RetryPolicy(
        max_retries=3,
        base_delay=1.0,
        max_delay=5.0,
        exponential_base=2.0,
        jitter=0.1,
    )

    async with retry as r:
        await r.execute(async_operation)
    ```
"""

import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from earnorm.exceptions import RetryError

T = TypeVar("T")


@dataclass
class RetryPolicy:
    """Retry policy configuration."""

    max_retries: int = 3
    """Maximum number of retry attempts."""

    base_delay: float = 1.0
    """Base delay between retries in seconds."""

    max_delay: float = 5.0
    """Maximum delay between retries in seconds."""

    exponential_base: float = 2.0
    """Base for exponential backoff calculation."""

    jitter: float = 0.1
    """Random jitter factor to add to delay."""

    retry_exceptions: list[type[Exception]] | None = None
    """List of exceptions to retry on. If None, retry on all exceptions."""

    def __post_init__(self) -> None:
        """Validate retry policy configuration."""
        if self.max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if self.base_delay < 0:
            raise ValueError("base_delay must be >= 0")
        if self.max_delay < self.base_delay:
            raise ValueError("max_delay must be >= base_delay")
        if self.exponential_base <= 1:
            raise ValueError("exponential_base must be > 1")
        if self.jitter < 0 or self.jitter > 1:
            raise ValueError("jitter must be between 0 and 1")

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt.

        Args:
            attempt: Current retry attempt number (0-based)

        Returns:
            Delay in seconds
        """
        delay = min(
            self.base_delay * (self.exponential_base**attempt),
            self.max_delay,
        )
        if self.jitter > 0:
            delay *= 1 + random.uniform(-self.jitter, self.jitter)
        return delay

    def should_retry(self, attempt: int, exc: Exception) -> bool:
        """Check if operation should be retried.

        Args:
            attempt: Current retry attempt number (0-based)
            exc: Exception that occurred

        Returns:
            True if operation should be retried
        """
        if attempt >= self.max_retries:
            return False

        if self.retry_exceptions is None:
            return True

        return any(isinstance(exc, exc_type) for exc_type in self.retry_exceptions)


class RetryContext:
    """Context manager for retrying operations."""

    def __init__(self, policy: RetryPolicy, backend: str = "unknown") -> None:
        """Initialize retry context.

        Args:
            policy: Retry policy configuration
            backend: Database backend name
        """
        self._policy = policy
        self._backend = backend
        self._attempt = 0
        self._start_time = 0.0
        self._last_error: Exception | None = None

    async def __aenter__(self) -> "RetryContext":
        """Enter retry context.

        Returns:
            Retry context instance
        """
        self._start_time = time.time()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        """Exit retry context.

        Args:
            exc_type: Exception type
            exc: Exception instance
            tb: Traceback

        Returns:
            True if exception was handled
        """
        if exc is None:
            return False

        if not self._policy.should_retry(self._attempt, exc):
            elapsed = time.time() - self._start_time
            raise RetryError(
                "Operation failed after maximum retries",
                backend=self._backend,
                attempts=self._attempt,
                elapsed=elapsed,
                last_error=self._last_error,
            )

        self._last_error = exc
        delay = self._policy.calculate_delay(self._attempt)
        self._attempt += 1

        await asyncio.sleep(delay)
        return True

    async def execute(self, operation: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any) -> T:
        """Execute operation with retries.

        Args:
            operation: Async operation to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Operation result

        Raises:
            RetryError: If all retry attempts failed
        """
        async with self:
            while True:
                try:
                    return await operation(*args, **kwargs)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    if not await self.__aexit__(type(e), e, None):
                        raise
