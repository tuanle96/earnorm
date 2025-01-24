"""Circuit breaker implementation.

This module provides circuit breaker functionality to prevent cascading failures.
It helps handle system overload and network partition scenarios.

Examples:
    ```python
    breaker = CircuitBreaker(
        failure_threshold=5,
        reset_timeout=30.0,
        half_open_timeout=5.0,
    )

    async with breaker as cb:
        await cb.execute(async_operation)
    ```
"""

import asyncio
import enum
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, List, Optional, Type, TypeVar

from earnorm.pool.protocols.errors import CircuitBreakerError

T = TypeVar("T")


class CircuitState(enum.Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation, requests allowed
    OPEN = "open"  # Requests blocked
    HALF_OPEN = "half_open"  # Testing if service is healthy


@dataclass
class CircuitStats:
    """Circuit breaker statistics."""

    total_requests: int = 0
    """Total number of requests."""

    successful_requests: int = 0
    """Number of successful requests."""

    failed_requests: int = 0
    """Number of failed requests."""

    consecutive_failures: int = 0
    """Number of consecutive failures."""

    last_failure_time: float = 0.0
    """Timestamp of last failure."""

    last_success_time: float = 0.0
    """Timestamp of last success."""

    state_change_time: float = 0.0
    """Timestamp of last state change."""


class CircuitBreaker:
    """Circuit breaker implementation."""

    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: float = 60.0,
        half_open_timeout: float = 5.0,
        excluded_exceptions: Optional[List[Type[Exception]]] = None,
    ) -> None:
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of consecutive failures before opening circuit
            reset_timeout: Time in seconds before attempting reset
            half_open_timeout: Time in seconds to wait in half-open state
            excluded_exceptions: Exceptions that don't count as failures
        """
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if reset_timeout < 0:
            raise ValueError("reset_timeout must be >= 0")
        if half_open_timeout < 0:
            raise ValueError("half_open_timeout must be >= 0")

        self._failure_threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._half_open_timeout = half_open_timeout
        self._excluded_exceptions = excluded_exceptions or []

        self._state = CircuitState.CLOSED
        self._stats = CircuitStats()
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def stats(self) -> CircuitStats:
        """Get circuit statistics."""
        return self._stats

    def _should_count_failure(self, exc: Exception) -> bool:
        """Check if exception should count as failure.

        Args:
            exc: Exception to check

        Returns:
            True if exception should count as failure
        """
        return not any(
            isinstance(exc, exc_type) for exc_type in self._excluded_exceptions
        )

    async def _update_state(self) -> None:
        """Update circuit state based on current conditions."""
        now = time.time()

        if self._state == CircuitState.OPEN:
            if now - self._stats.state_change_time >= self._reset_timeout:
                self._state = CircuitState.HALF_OPEN
                self._stats.state_change_time = now

        elif self._state == CircuitState.HALF_OPEN:
            if now - self._stats.state_change_time >= self._half_open_timeout:
                if self._stats.consecutive_failures == 0:
                    self._state = CircuitState.CLOSED
                else:
                    self._state = CircuitState.OPEN
                self._stats.state_change_time = now

        elif self._state == CircuitState.CLOSED:
            if self._stats.consecutive_failures >= self._failure_threshold:
                self._state = CircuitState.OPEN
                self._stats.state_change_time = now

    async def _on_success(self) -> None:
        """Handle successful operation."""
        async with self._lock:
            self._stats.total_requests += 1
            self._stats.successful_requests += 1
            self._stats.consecutive_failures = 0
            self._stats.last_success_time = time.time()
            await self._update_state()

    async def _on_failure(self, exc: Exception) -> None:
        """Handle failed operation.

        Args:
            exc: Exception that occurred
        """
        async with self._lock:
            self._stats.total_requests += 1
            self._stats.failed_requests += 1
            if self._should_count_failure(exc):
                self._stats.consecutive_failures += 1
            self._stats.last_failure_time = time.time()
            await self._update_state()

    async def _check_state(self) -> None:
        """Check if requests are allowed in current state.

        Raises:
            CircuitBreakerError: If circuit is open
        """
        if self._state == CircuitState.OPEN:
            raise CircuitBreakerError(
                "Circuit is open",
                {
                    "state": self._state.value,
                    "failures": self._stats.consecutive_failures,
                    "last_failure": self._stats.last_failure_time,
                    "reset_time": self._stats.state_change_time + self._reset_timeout,
                },
            )

    async def __aenter__(self) -> "CircuitBreaker":
        """Enter circuit breaker context.

        Returns:
            Circuit breaker instance

        Raises:
            CircuitBreakerError: If circuit is open
        """
        await self._check_state()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        """Exit circuit breaker context.

        Args:
            exc_type: Exception type
            exc: Exception instance
            tb: Traceback

        Returns:
            True if exception was handled
        """
        if exc is None:
            await self._on_success()
        else:
            await self._on_failure(exc)
        return False

    async def execute(
        self, operation: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any
    ) -> T:
        """Execute operation with circuit breaker.

        Args:
            operation: Async operation to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Operation result

        Raises:
            CircuitBreakerError: If circuit is open
        """
        async with self:
            return await operation(*args, **kwargs)
