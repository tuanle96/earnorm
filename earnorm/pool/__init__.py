"""Connection pooling module for EarnORM.

This module provides connection pooling functionality for various database backends.
It supports multiple backend types (MongoDB, Redis) and includes features such as
connection lifecycle management, health checks, metrics collection, and more.

Example:
    >>> from earnorm.pool import PoolFactory, PoolConfig
    >>>
    >>> # Create MongoDB pool
    >>> pool = PoolFactory.create(
    ...     "mongodb",
    ...     uri="mongodb://localhost:27017",
    ...     database="test",
    ...     min_size=5,
    ...     max_size=20
    ... )
    >>>
    >>> # Create Redis pool
    >>> pool = PoolFactory.create(
    ...     "redis",
    ...     uri="redis://localhost:6379",
    ...     min_size=5,
    ...     max_size=20
    ... )
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .backends.base import BasePool
from .backends.mongo import MongoPool
from .backends.redis import RedisPool
from .constants import (
    DEFAULT_CONNECTION_TIMEOUT,
    DEFAULT_MAX_IDLE_TIME,
    DEFAULT_MAX_LIFETIME,
    DEFAULT_MAX_POOL_SIZE,
    DEFAULT_MIN_POOL_SIZE,
)
from .core import CircuitBreaker, CircuitState, RetryPolicy, with_resilience
from .factory import PoolFactory, create_mongo_pool, create_redis_pool
from .protocols import AsyncPoolProtocol
from .registry import PoolRegistry
from .utils import (
    ConnectionMetrics,
    HealthCheck,
    PoolMetrics,
    PoolStatistics,
    calculate_connection_metrics,
    calculate_pool_metrics,
    calculate_pool_statistics,
    check_pool_health,
    cleanup_stale_connections,
)


@dataclass
class PoolConfig:
    """Pool configuration.

    Examples:
        >>> config = PoolConfig(
        ...     min_size=5,
        ...     max_size=20,
        ...     max_idle_time=60,
        ...     connection_timeout=5
        ... )
        >>> pool = PoolFactory.create("mongodb", config=config)
    """

    min_size: int = DEFAULT_MIN_POOL_SIZE
    max_size: int = DEFAULT_MAX_POOL_SIZE
    max_idle_time: int = DEFAULT_MAX_IDLE_TIME
    connection_timeout: float = DEFAULT_CONNECTION_TIMEOUT
    max_lifetime: int = DEFAULT_MAX_LIFETIME
    validate_on_borrow: bool = True
    test_on_return: bool = True
    extra_config: dict[str, Any] | None = None


__all__ = [
    # Base
    "BasePool",
    "AsyncPoolProtocol",
    "PoolConfig",
    # Backends
    "MongoPool",
    "RedisPool",
    # Factory & Registry
    "PoolFactory",
    "PoolRegistry",
    # Core
    "CircuitBreaker",
    "CircuitState",
    "RetryPolicy",
    "with_resilience",
    # Utils
    "ConnectionMetrics",
    "HealthCheck",
    "PoolMetrics",
    "PoolStatistics",
    "calculate_connection_metrics",
    "calculate_pool_metrics",
    "calculate_pool_statistics",
    "check_pool_health",
    "cleanup_stale_connections",
    # Factory functions
    "create_mongo_pool",
    "create_redis_pool",
]
