"""Connection pooling module for EarnORM.

This module provides connection pooling functionality for various database backends.
It supports multiple backend types (MongoDB, Redis) and includes features such as
connection lifecycle management, health checks, metrics collection, and more.

Example:
    >>> from earnorm.pool.factory import PoolFactory
    >>> from earnorm.pool.context import PoolContext, ConnectionContext

    >>> # Create MongoDB pool
    >>> mongo_pool = await PoolFactory.create_mongo_pool(
    ...     uri="mongodb://localhost:27017",
    ...     database="test",
    ...     min_size=5,
    ...     max_size=20
    ... )
    >>> async with ConnectionContext(mongo_pool) as conn:
    ...     await conn.execute("find_one", "users", {"name": "John"})
    {"_id": "...", "name": "John", "age": 30}

    >>> # Create Redis pool
    >>> redis_pool = await PoolFactory.create_redis_pool(
    ...     host="localhost",
    ...     port=6379,
    ...     db=0,
    ...     min_size=5,
    ...     max_size=20
    ... )
    >>> async with ConnectionContext(redis_pool) as conn:
    ...     await conn.execute("set", "key", "value")
    ...     await conn.execute("get", "key")
    True
    "value"
"""

from earnorm.pool.backends.mongo.connection import MongoConnection
from earnorm.pool.backends.mongo.pool import MongoPool
from earnorm.pool.backends.redis.connection import RedisConnection
from earnorm.pool.backends.redis.pool import RedisPool
from earnorm.pool.context import ConnectionContext, PoolContext
from earnorm.pool.factory import PoolFactory
from earnorm.pool.protocols.aware import PoolAware
from earnorm.pool.registry import PoolRegistry
from earnorm.pool.utils import (
    CircuitBreaker,
    CircuitState,
    ConnectionMetrics,
    HealthCheck,
    PoolMetrics,
    PoolStatistics,
    calculate_connection_metrics,
    calculate_health_check,
    calculate_pool_metrics,
    calculate_pool_statistics,
    check_pool_health,
    circuit_breaker,
    cleanup_stale_connections,
    retry_policy,
)

# Create global instances
pool_registry = PoolRegistry()
pool_factory = PoolFactory()

__all__ = [
    # Global instances
    "pool_registry",
    "pool_factory",
    # Backends
    "MongoPool",
    "MongoConnection",
    "RedisPool",
    "RedisConnection",
    # Factory
    "PoolFactory",
    # Registry
    "PoolRegistry",
    # Context
    "PoolContext",
    "ConnectionContext",
    # Protocol
    "PoolAware",
    # Utils
    "CircuitBreaker",
    "CircuitState",
    "ConnectionMetrics",
    "HealthCheck",
    "PoolMetrics",
    "PoolStatistics",
    "calculate_connection_metrics",
    "calculate_health_check",
    "calculate_pool_metrics",
    "calculate_pool_statistics",
    "check_pool_health",
    "circuit_breaker",
    "cleanup_stale_connections",
    "retry_policy",
]
