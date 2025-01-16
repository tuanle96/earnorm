"""Pool metrics implementation."""

import time
from dataclasses import dataclass
from typing import Any, Dict, List


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

    def to_dict(self) -> Dict[str, Any]:
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

    def to_dict(self) -> Dict[str, Any]:
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

    def to_dict(self) -> Dict[str, Any]:
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
    connections: List[ConnectionMetrics]

    def to_dict(self) -> Dict[str, Any]:
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
    connections: List[ConnectionMetrics],
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
        connection_usage=(
            active_connections / total_connections if total_connections else 0.0
        ),
    )


def calculate_health_check(
    status: str,
    metrics: PoolMetrics,
    connections: List[ConnectionMetrics],
) -> HealthCheck:
    """Calculate pool health check.

    Args:
        status: Pool status
        metrics: Pool metrics
        connections: List of connection metrics

    Returns:
        Health check data

    Examples:
        >>> pool_metrics = calculate_pool_metrics(
        ...     backend_type="mongodb",
        ...     total_connections=1,
        ...     active_connections=0,
        ...     available_connections=1,
        ...     acquiring_connections=0,
        ...     min_size=1,
        ...     max_size=10,
        ...     timeout=30.0,
        ...     max_lifetime=3600,
        ...     idle_timeout=300
        ... )
        >>> conn_metrics = [
        ...     calculate_connection_metrics(
        ...         id="123",
        ...         created_at=1234567890.0,
        ...         last_used_at=1234567890.0,
        ...         is_stale=False,
        ...         is_available=True
        ...     )
        ... ]
        >>> health = calculate_health_check(
        ...     status="healthy",
        ...     metrics=pool_metrics,
        ...     connections=conn_metrics
        ... )
        >>> health.to_dict()
        {
            "status": "healthy",
            "metrics": {...},
            "statistics": {...},
            "connections": [...]
        }
    """
    statistics = calculate_pool_statistics(
        connections=connections,
        total_connections=metrics.total_connections,
        active_connections=metrics.active_connections,
    )
    return HealthCheck(
        status=status,
        metrics=metrics,
        statistics=statistics,
        connections=connections,
    )
