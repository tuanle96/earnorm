"""Pool health check implementation."""

import logging
from typing import Any, Dict, List, Set, cast

from earnorm.pool.protocols.connection import ConnectionProtocol
from earnorm.pool.protocols.pool import PoolProtocol
from earnorm.pool.utils.metrics import (
    ConnectionMetrics,
    calculate_connection_metrics,
    calculate_health_check,
    calculate_pool_metrics,
)

logger = logging.getLogger(__name__)


async def check_pool_health(pool: PoolProtocol[Any]) -> Dict[str, Any]:
    """Check pool health.

    Args:
        pool: Pool instance

    Returns:
        Health check data

    Examples:
        >>> from earnorm.pool.backends.mongo import MongoPool
        >>> pool = MongoPool(
        ...     uri="mongodb://localhost:27017",
        ...     database="test",
        ...     min_size=5,
        ...     max_size=20
        ... )
        >>> await pool.init()
        >>> health = await check_pool_health(pool)
        >>> health["status"]
        "healthy"
        >>> health["metrics"]["total_connections"]
        5
        >>> await pool.close()
    """
    # Get pool metrics
    metrics = calculate_pool_metrics(
        backend_type=pool.backend_type,
        total_connections=pool.size,
        active_connections=pool.size - pool.available,
        available_connections=pool.available,
        acquiring_connections=0,  # TODO: Add acquiring count to pool protocol
        min_size=getattr(pool, "_min_size", 0),
        max_size=getattr(pool, "_max_size", 0),
        timeout=getattr(pool, "_timeout", 0.0),
        max_lifetime=getattr(pool, "_max_lifetime", 0),
        idle_timeout=getattr(pool, "_idle_timeout", 0),
    )

    # Get connection metrics
    connections: List[ConnectionMetrics] = []
    empty_set: Set[ConnectionProtocol] = set()
    empty_list: List[ConnectionProtocol] = []
    pool_connections = cast(
        Set[ConnectionProtocol], getattr(pool, "_connections", empty_set)
    )
    pool_available = cast(
        List[ConnectionProtocol], getattr(pool, "_available", empty_list)
    )

    for conn in pool_connections:
        connections.append(
            calculate_connection_metrics(
                id=str(id(conn)),
                created_at=conn.created_at,
                last_used_at=conn.last_used_at,
                is_stale=conn.is_stale,
                is_available=conn in pool_available,
            )
        )

    # Calculate health check
    health = calculate_health_check(
        status="healthy" if not getattr(pool, "_closed", False) else "closed",
        metrics=metrics,
        connections=connections,
    )

    return health.to_dict()


async def cleanup_stale_connections(pool: PoolProtocol[Any]) -> int:
    """Cleanup stale connections.

    Args:
        pool: Pool instance

    Returns:
        Number of connections cleaned up

    Examples:
        >>> from earnorm.pool.backends.mongo import MongoPool
        >>> pool = MongoPool(
        ...     uri="mongodb://localhost:27017",
        ...     database="test",
        ...     min_size=5,
        ...     max_size=20
        ... )
        >>> await pool.init()
        >>> cleaned = await cleanup_stale_connections(pool)
        >>> print(f"Cleaned up {cleaned} connections")
        Cleaned up 0 connections
        >>> await pool.close()
    """
    cleaned = 0
    lock = getattr(pool, "_lock", None)

    if not lock:
        logger.warning("Pool does not have a lock, skipping cleanup")
        return cleaned

    async with lock:
        # Check available connections
        empty_set: Set[ConnectionProtocol] = set()
        empty_list: List[ConnectionProtocol] = []
        available = cast(
            List[ConnectionProtocol], getattr(pool, "_available", empty_list)
        )
        connections = cast(
            Set[ConnectionProtocol], getattr(pool, "_connections", empty_set)
        )

        for conn in list(available):
            if conn.is_stale:
                available.remove(conn)
                connections.remove(conn)
                await conn.close()
                cleaned += 1

        # Create new connections if needed
        min_size = getattr(pool, "_min_size", 0)
        create_connection = getattr(pool, "_create_connection", None)

        if create_connection and len(connections) < min_size:
            while len(connections) < min_size:
                conn = await create_connection()
                connections.add(conn)
                available.append(conn)

    return cleaned
