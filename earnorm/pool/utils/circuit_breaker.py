"""Circuit breaker implementation."""

import asyncio
import functools
import logging
import time
from enum import Enum
from typing import Any, Callable, Optional, Type, TypeVar, cast

logger = logging.getLogger(__name__)

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Service is down
    HALF_OPEN = "half_open"  # Testing if service is back


class CircuitBreaker:
    """Circuit breaker implementation."""

    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: float = 60.0,
        exceptions: Optional[tuple[Type[Exception], ...]] = None,
    ) -> None:
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            reset_timeout: Time to wait before attempting reset
            exceptions: Tuple of exceptions to catch
        """
        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._exceptions = exceptions or (Exception,)

        # Internal state
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._failure_count

    async def _update_state(self) -> None:
        """Update circuit state based on current conditions."""
        now = time.time()

        if self._state == CircuitState.OPEN:
            if now - self._last_failure_time >= self._reset_timeout:
                self._state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker state changed to HALF_OPEN")

        elif self._state == CircuitState.HALF_OPEN:
            if self._failure_count >= self._failure_threshold:
                self._state = CircuitState.OPEN
                self._last_failure_time = now
                logger.warning("Circuit breaker state changed to OPEN")
            elif self._failure_count == 0:
                self._state = CircuitState.CLOSED
                logger.info("Circuit breaker state changed to CLOSED")

        elif self._state == CircuitState.CLOSED:
            if self._failure_count >= self._failure_threshold:
                self._state = CircuitState.OPEN
                self._last_failure_time = now
                logger.warning("Circuit breaker state changed to OPEN")

    async def _on_success(self) -> None:
        """Handle successful operation."""
        async with self._lock:
            self._failure_count = 0
            await self._update_state()

    async def _on_failure(self) -> None:
        """Handle failed operation."""
        async with self._lock:
            self._failure_count += 1
            await self._update_state()

    def __call__(self, func: F) -> F:
        """Decorate function with circuit breaker.

        Args:
            func: Function to decorate

        Returns:
            Decorated function

        Examples:
            >>> @circuit_breaker(failure_threshold=5, reset_timeout=60.0)
            ... async def my_service() -> None:
            ...     # Service that may fail
            ...     ...
            >>>
            >>> breaker = CircuitBreaker(
            ...     failure_threshold=3,
            ...     reset_timeout=30.0,
            ...     exceptions=(ConnectionError, TimeoutError)
            ... )
            >>>
            >>> @breaker
            ... async def my_operation() -> None:
            ...     # Operation that may fail
            ...     ...
        """

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if self._state == CircuitState.OPEN:
                raise RuntimeError("Circuit breaker is OPEN")

            try:
                result = await func(*args, **kwargs)
                await self._on_success()
                return result
            except self._exceptions as exc:
                await self._on_failure()
                raise exc

        return cast(F, wrapper)


def circuit_breaker(
    failure_threshold: int = 5,
    reset_timeout: float = 60.0,
    exceptions: Optional[tuple[Type[Exception], ...]] = None,
) -> Callable[[F], F]:
    """Circuit breaker decorator.

    Args:
        failure_threshold: Number of failures before opening circuit
        reset_timeout: Time to wait before attempting reset
        exceptions: Tuple of exceptions to catch

    Returns:
        Decorated function

    Examples:
        >>> @circuit_breaker(failure_threshold=5, reset_timeout=60.0)
        ... async def my_service() -> None:
        ...     # Service that may fail
        ...     ...
        >>>
        >>> @circuit_breaker(
        ...     failure_threshold=3,
        ...     reset_timeout=30.0,
        ...     exceptions=(ConnectionError, TimeoutError)
        ... )
        ... async def my_operation() -> None:
        ...     # Operation that may fail
        ...     ...
    """
    breaker = CircuitBreaker(
        failure_threshold=failure_threshold,
        reset_timeout=reset_timeout,
        exceptions=exceptions,
    )
    return breaker
