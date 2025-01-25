"""Core functionality for connection pooling.

This module provides core functionality for connection pooling,
including retry mechanism, circuit breaker, and decorators.
"""

from .circuit import CircuitBreaker, CircuitState, CircuitStats
from .decorators import ResilienceError, with_resilience
from .retry import RetryContext, RetryError, RetryPolicy

__all__ = [
    # Circuit breaker
    "CircuitBreaker",
    "CircuitState",
    "CircuitStats",
    # Retry mechanism
    "RetryContext",
    "RetryError",
    "RetryPolicy",
    # Decorators
    "ResilienceError",
    "with_resilience",
]
