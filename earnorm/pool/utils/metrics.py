"""Pool utilities.

This module provides utility functions for connection pool management,
including health checks, metrics collection, and statistics.

Examples:
    ```python
    # Get pool metrics
    metrics = calculate_pool_metrics(
        backend_type="mongodb",
        total_connections=10,
        active_connections=5,
        available_connections=5,
        acquiring_connections=0,
        min_size=5,
        max_size=20,
        timeout=30.0,
        max_lifetime=3600,
        idle_timeout=300
    )

    # Get connection metrics
    conn_metrics = calculate_connection_metrics(
        id="123",
        created_at=1234567890.0,
        last_used_at=1234567890.0,
        is_stale=False,
        is_available=True
    )

    # Check pool health
    health = check_pool_health(pool)
    ```
"""

import time
from dataclasses import dataclass
from typing import Any, TypeVar

from earnorm.pool.protocols.pool import AsyncPoolProtocol

# Type variables for database and collection
DB = TypeVar("DB")
COLL = TypeVar("COLL")


@dataclass
class PoolMetrics:
    """Pool metrics data."""

    backend_type: str
    total_connections: int
    active_connections: int
    available_connections: int
    acquiring_connections: int
    min_size: int
    max_size: int
    timeout: float
    max_lifetime: int
    idle_timeout: int

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "backend_type": self.backend_type,
            "total_connections": self.total_connections,
            "active_connections": self.active_connections,
            "available_connections": self.available_connections,
            "acquiring_connections": self.acquiring_connections,
            "min_size": self.min_size,
            "max_size": self.max_size,
            "timeout": self.timeout,
            "max_lifetime": self.max_lifetime,
            "idle_timeout": self.idle_timeout,
        }


@dataclass
class ConnectionMetrics:
    """Connection metrics data."""

    id: str
    created_at: float
    last_used_at: float
    idle_time: float
    lifetime: float
    is_stale: bool
    is_available: bool

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "id": self.id,
            "created_at": self.created_at,
            "last_used_at": self.last_used_at,
            "idle_time": self.idle_time,
            "lifetime": self.lifetime,
            "is_stale": self.is_stale,
            "is_available": self.is_available,
        }


@dataclass
class PoolStatistics:
    """Pool statistics data."""

    average_idle_time: float
    average_lifetime: float
    stale_connections: int
    connection_usage: float

    def to_dict(self) -> dict[str, Any]:
        """Convert statistics to dictionary."""
        return {
            "average_idle_time": self.average_idle_time,
            "average_lifetime": self.average_lifetime,
            "stale_connections": self.stale_connections,
            "connection_usage": self.connection_usage,
        }


@dataclass
class HealthCheck:
    """Pool health check data."""

    status: str
    metrics: PoolMetrics
    statistics: PoolStatistics
    connections: list[ConnectionMetrics]

    def to_dict(self) -> dict[str, Any]:
        """Convert health check to dictionary."""
        return {
            "status": self.status,
            "metrics": self.metrics.to_dict(),
            "statistics": self.statistics.to_dict(),
            "connections": [conn.to_dict() for conn in self.connections],
        }


def calculate_pool_metrics(
    backend_type: str,
    total_connections: int,
    active_connections: int,
    available_connections: int,
    acquiring_connections: int,
    min_size: int,
    max_size: int,
    timeout: float,
    max_lifetime: int,
    idle_timeout: int,
) -> PoolMetrics:
    """Calculate pool metrics.

    Args:
        backend_type: Backend type identifier
        total_connections: Total number of connections
        active_connections: Number of active connections
        available_connections: Number of available connections
        acquiring_connections: Number of connections being acquired
        min_size: Minimum pool size
        max_size: Maximum pool size
        timeout: Connection acquire timeout
        max_lifetime: Maximum connection lifetime
        idle_timeout: Maximum idle time

    Returns:
        Pool metrics

    Examples:
        >>> metrics = calculate_pool_metrics(
        ...     backend_type="mongodb",
        ...     total_connections=10,
        ...     active_connections=5,
        ...     available_connections=5,
        ...     acquiring_connections=0,
        ...     min_size=5,
        ...     max_size=20,
        ...     timeout=30.0,
        ...     max_lifetime=3600,
        ...     idle_timeout=300
        ... )
        >>> metrics.to_dict()
        {
            "backend_type": "mongodb",
            "total_connections": 10,
            "active_connections": 5,
            "available_connections": 5,
            "acquiring_connections": 0,
            "min_size": 5,
            "max_size": 20,
            "timeout": 30.0,
            "max_lifetime": 3600,
            "idle_timeout": 300
        }
    """
    return PoolMetrics(
        backend_type=backend_type,
        total_connections=total_connections,
        active_connections=active_connections,
        available_connections=available_connections,
        acquiring_connections=acquiring_connections,
        min_size=min_size,
        max_size=max_size,
        timeout=timeout,
        max_lifetime=max_lifetime,
        idle_timeout=idle_timeout,
    )


def calculate_connection_metrics(
    id: str,
    created_at: float,
    last_used_at: float,
    is_stale: bool,
    is_available: bool,
) -> ConnectionMetrics:
    """Calculate connection metrics.

    Args:
        id: Connection ID
        created_at: Creation timestamp
        last_used_at: Last used timestamp
        is_stale: Whether connection is stale
        is_available: Whether connection is available

    Returns:
        Connection metrics

    Examples:
        >>> metrics = calculate_connection_metrics(
        ...     id="123",
        ...     created_at=1234567890.0,
        ...     last_used_at=1234567890.0,
        ...     is_stale=False,
        ...     is_available=True
        ... )
        >>> metrics.to_dict()
        {
            "id": "123",
            "created_at": 1234567890.0,
            "last_used_at": 1234567890.0,
            "idle_time": 0.0,
            "lifetime": 0.0,
            "is_stale": False,
            "is_available": True
        }
    """
    now = time.time()
    return ConnectionMetrics(
        id=id,
        created_at=created_at,
        last_used_at=last_used_at,
        idle_time=now - last_used_at,
        lifetime=now - created_at,
        is_stale=is_stale,
        is_available=is_available,
    )


def calculate_pool_statistics(
    connections: list[ConnectionMetrics],
    total_connections: int,
    active_connections: int,
) -> PoolStatistics:
    """Calculate pool statistics.

    Args:
        connections: List of connection metrics
        total_connections: Total number of connections
        active_connections: Number of active connections

    Returns:
        Pool statistics

    Examples:
        >>> metrics = [
        ...     calculate_connection_metrics(
        ...         id="123",
        ...         created_at=1234567890.0,
        ...         last_used_at=1234567890.0,
        ...         is_stale=False,
        ...         is_available=True
        ...     )
        ... ]
        >>> stats = calculate_pool_statistics(
        ...     connections=metrics,
        ...     total_connections=1,
        ...     active_connections=0
        ... )
        >>> stats.to_dict()
        {
            "average_idle_time": 0.0,
            "average_lifetime": 0.0,
            "stale_connections": 0,
            "connection_usage": 0.0
        }
    """
    if not connections:
        return PoolStatistics(
            average_idle_time=0.0,
            average_lifetime=0.0,
            stale_connections=0,
            connection_usage=0.0,
        )

    total_idle_time = sum(conn.idle_time for conn in connections)
    total_lifetime = sum(conn.lifetime for conn in connections)
    stale_connections = sum(1 for conn in connections if conn.is_stale)

    return PoolStatistics(
        average_idle_time=total_idle_time / len(connections),
        average_lifetime=total_lifetime / len(connections),
        stale_connections=stale_connections,
        connection_usage=(active_connections / total_connections if total_connections > 0 else 0.0),
    )


async def check_pool_health(pool: AsyncPoolProtocol[DB, COLL]) -> HealthCheck:
    """Check pool health.

    Args:
        pool: Connection pool instance

    Returns:
        Health check data

    Examples:
        >>> health = await check_pool_health(pool)
        >>> health.to_dict()
        {
            "status": "healthy",
            "metrics": {...},
            "statistics": {...},
            "connections": [...]
        }
    """
    # Get pool metrics
    metrics = await pool.get_pool_stats()  # type: ignore # method exists in implementations

    # Get connection metrics
    connections: list[ConnectionMetrics] = []
    for conn in pool._pool.values():  # type: ignore # accessing internal state
        conn_metrics = calculate_connection_metrics(
            id=str(id(conn)),  # type: ignore # accessing connection attributes
            created_at=conn.created_at,  # type: ignore # accessing connection attributes
            last_used_at=conn.last_used_at,  # type: ignore
            is_stale=conn.is_stale,  # type: ignore
            is_available=not conn.in_use,  # type: ignore
        )
        connections.append(conn_metrics)

    # Calculate statistics
    statistics = calculate_pool_statistics(
        connections=connections,
        total_connections=metrics.total_connections,  # type: ignore # accessing metrics attributes
        active_connections=metrics.active_connections,  # type: ignore
    )

    # Determine status
    status = "healthy"
    if statistics.stale_connections > 0:
        status = "degraded"
    if metrics.available_connections == 0:  # type: ignore # accessing metrics attributes
        status = "critical"

    return HealthCheck(
        status=status,
        metrics=metrics,  # type: ignore # metrics type is compatible
        statistics=statistics,
        connections=connections,
    )


async def cleanup_stale_connections(pool: AsyncPoolProtocol[DB, COLL]) -> int:
    """Clean up stale connections in pool.

    Args:
        pool: Connection pool instance

    Returns:
        Number of connections cleaned

    Examples:
        >>> cleaned = await cleanup_stale_connections(pool)
        >>> print(f"Cleaned {cleaned} stale connections")
    """
    cleaned = 0
    for conn in pool._pool.values():  # type: ignore # accessing internal state
        if conn.is_stale and not conn.in_use:  # type: ignore # accessing connection attributes
            await pool.release(conn)  # type: ignore # method exists in implementations
            cleaned += 1
    return cleaned
