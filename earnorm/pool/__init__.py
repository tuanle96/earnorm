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
from typing import Any, Dict, Optional, Type

from earnorm.pool.factory import create_mongo_pool

from .backends.base import BasePool
from .backends.mongo import MongoPool
from .backends.redis import RedisPool
from .circuit import CircuitBreaker, CircuitState
from .factory import PoolFactory
from .protocols.pool import PoolProtocol
from .registry import PoolRegistry
from .retry import RetryPolicy
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

    min_size: int = 5
    max_size: int = 20
    max_idle_time: int = 300
    connection_timeout: float = 30.0
    max_lifetime: int = 3600
    validate_on_borrow: bool = True
    test_on_return: bool = True
    extra_config: Optional[Dict[str, Any]] = None


def register_pool_class(
    backend_type: str, pool_class: Type[PoolProtocol[Any, Any]]
) -> None:
    """Register pool class for backend type.

    Args:
        backend_type: Backend type identifier
        pool_class: Pool class to register

    Examples:
        >>> from earnorm.pool.backends.mongo import MongoPool
        >>> register_pool_class("mongodb", MongoPool)
    """
    PoolRegistry.register(backend_type, pool_class)


__all__ = [
    # Base
    "BasePool",
    "PoolProtocol",
    "PoolConfig",
    # Backends
    "MongoPool",
    "RedisPool",
    # Factory & Registry
    "PoolFactory",
    "PoolRegistry",
    "register_pool_class",
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitState",
    # Retry
    "RetryPolicy",
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
    "create_mongo_pool",
    "retry",
]
