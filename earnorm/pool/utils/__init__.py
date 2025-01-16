"""Connection pooling utilities.

This module provides utility functions and classes for connection pooling in EarnORM.
It includes utilities for:
- Connection lifecycle management
- Health checks
- Metrics collection
- Error handling
- Retry policies
- Circuit breakers

Example:
    >>> from earnorm.pool.utils import retry_policy, circuit_breaker
    >>>
    >>> @retry_policy(max_retries=3, delay=1.0)
    ... async def my_operation() -> None:
    ...     # Operation that may fail
    ...     ...
    >>>
    >>> @circuit_breaker(failure_threshold=5, reset_timeout=60.0)
    ... async def my_service() -> None:
    ...     # Service that may fail
    ...     ...
"""

from earnorm.pool.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    circuit_breaker,
)
from earnorm.pool.utils.health import check_pool_health, cleanup_stale_connections
from earnorm.pool.utils.metrics import (
    ConnectionMetrics,
    HealthCheck,
    PoolMetrics,
    PoolStatistics,
    calculate_connection_metrics,
    calculate_health_check,
    calculate_pool_metrics,
    calculate_pool_statistics,
)
from earnorm.pool.utils.retry import retry_policy

__all__ = [
    # Circuit breaker
    "CircuitBreaker",
    "CircuitState",
    "circuit_breaker",
    # Health check
    "check_pool_health",
    "cleanup_stale_connections",
    # Metrics
    "ConnectionMetrics",
    "HealthCheck",
    "PoolMetrics",
    "PoolStatistics",
    "calculate_connection_metrics",
    "calculate_health_check",
    "calculate_pool_metrics",
    "calculate_pool_statistics",
    # Retry policy
    "retry_policy",
]
