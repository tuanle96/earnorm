"""Connection pool implementation."""

import asyncio
import logging
import time
from typing import Any, Dict, List, NamedTuple, Set

from motor.motor_asyncio import AsyncIOMotorClient

from earnorm.pool.core.connection import Connection

logger = logging.getLogger(__name__)


class PoolMetrics(NamedTuple):
    """Connection pool metrics."""

    total_connections: int
    active_connections: int
    available_connections: int
    acquiring_connections: int
    min_size: int
    max_size: int
    timeout: float
    max_lifetime: int
    idle_timeout: int


class ConnectionInfo(NamedTuple):
    """Connection information."""

    id: str
    created_at: float
    last_used_at: float
    idle_time: float
    lifetime: float
    is_stale: bool
    is_available: bool


class ConnectionPool:
    """MongoDB connection pool."""

    def __init__(
        self,
        uri: str,
        database: str,
        min_size: int = 5,
        max_size: int = 20,
        timeout: float = 30.0,
        max_lifetime: int = 3600,
        idle_timeout: int = 300,
        validate_on_borrow: bool = True,
        test_on_return: bool = True,
        fifo: bool = True,
    ) -> None:
        """Initialize pool.

        Args:
            uri: MongoDB connection URI
            database: Database name
            min_size: Minimum pool size
            max_size: Maximum pool size
            timeout: Connection acquire timeout
            max_lifetime: Maximum connection lifetime
            idle_timeout: Maximum idle time
            validate_on_borrow: Validate connection on borrow
            test_on_return: Test connection on return
            fifo: Use FIFO order for connections
        """
        self.uri = uri
        self.database = database
        self.min_size = min_size
        self.max_size = max_size
        self.timeout = timeout
        self.max_lifetime = max_lifetime
        self.idle_timeout = idle_timeout
        self.validate_on_borrow = validate_on_borrow
        self.test_on_return = test_on_return
        self.fifo = fifo

        # Internal state
        self._connections: Set[Connection] = set()
        self._available: List[Connection] = []
        self._acquiring = 0
        self._initialized = False
        self._closed = False
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Condition(self._lock)

    @property
    def size(self) -> int:
        """Get current pool size."""
        return len(self._connections)

    @property
    def available(self) -> int:
        """Get number of available connections."""
        return len(self._available)

    @property
    def active(self) -> int:
        """Get number of active connections."""
        return self.size - self.available

    async def init(self) -> None:
        """Initialize pool with minimum connections."""
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            # Create minimum connections
            for _ in range(self.min_size):
                conn = await self._create_connection()
                self._connections.add(conn)
                self._available.append(conn)

            self._initialized = True
            logger.info(
                "Initialized pool with %d connections (min_size=%d, max_size=%d)",
                self.size,
                self.min_size,
                self.max_size,
            )

    async def acquire(self) -> Connection:
        """Acquire connection from pool.

        Returns:
            Connection instance

        Raises:
            TimeoutError: If timeout exceeded
            RuntimeError: If pool is closed
        """
        if not self._initialized:
            await self.init()

        if self._closed:
            raise RuntimeError("Pool is closed")

        async with self._lock:
            while True:
                # Check available connections
                while self._available:
                    conn = (
                        self._available.pop(0) if self.fifo else self._available.pop()
                    )

                    # Validate if needed
                    if self.validate_on_borrow and not await self._validate_connection(
                        conn
                    ):
                        self._connections.remove(conn)
                        await conn.close()
                        continue

                    conn.touch()
                    return conn

                # Create new connection if possible
                if self.size + self._acquiring < self.max_size:
                    self._acquiring += 1
                    try:
                        conn = await self._create_connection()
                        self._connections.add(conn)
                        conn.touch()
                        return conn
                    finally:
                        self._acquiring -= 1

                # Wait for available connection
                try:
                    await asyncio.wait_for(self._not_empty.wait(), timeout=self.timeout)
                except asyncio.TimeoutError:
                    raise TimeoutError(
                        f"Timeout waiting for connection (timeout={self.timeout}s)"
                    )

    async def release(self, conn: Connection) -> None:
        """Release connection back to pool.

        Args:
            conn: Connection to release
        """
        if conn not in self._connections:
            return

        # Test connection if needed
        if self.test_on_return and not await self._validate_connection(conn):
            self._connections.remove(conn)
            await conn.close()
            return

        # Check if connection should be closed
        if self._should_close_connection(conn):
            self._connections.remove(conn)
            await conn.close()
            return

        # Add back to available connections
        async with self._lock:
            self._available.append(conn)
            self._not_empty.notify()

    async def close(self) -> None:
        """Close all connections and shutdown pool."""
        if self._closed:
            return

        self._closed = True
        async with self._lock:
            for conn in self._connections:
                await conn.close()
            self._connections.clear()
            self._available.clear()

    async def _create_connection(self) -> Connection:
        """Create new connection.

        Returns:
            Connection instance
        """
        client: AsyncIOMotorClient[Dict[str, Any]] = AsyncIOMotorClient(self.uri)
        return Connection(client)

    async def _validate_connection(self, conn: Connection) -> bool:
        """Validate connection health.

        Args:
            conn: Connection to validate

        Returns:
            True if connection is valid
        """
        if conn.is_stale:
            return False
        return await conn.ping()

    def _should_close_connection(self, conn: Connection) -> bool:
        """Check if connection should be closed.

        Args:
            conn: Connection to check

        Returns:
            True if connection should be closed
        """
        return (
            conn.lifetime > self.max_lifetime
            or conn.idle_time > self.idle_timeout
            or self.size > self.min_size
        )

    def get_metrics(self) -> PoolMetrics:
        """Get pool metrics.

        Returns:
            PoolMetrics instance with current pool metrics
        """
        return PoolMetrics(
            total_connections=self.size,
            active_connections=self.active,
            available_connections=self.available,
            acquiring_connections=self._acquiring,
            min_size=self.min_size,
            max_size=self.max_size,
            timeout=self.timeout,
            max_lifetime=self.max_lifetime,
            idle_timeout=self.idle_timeout,
        )

    def get_connection_info(self) -> List[ConnectionInfo]:
        """Get information about all connections.

        Returns:
            List of ConnectionInfo instances
        """
        now = time.time()
        info: List[ConnectionInfo] = []

        for conn in self._connections:
            info.append(
                ConnectionInfo(
                    id=str(id(conn)),
                    created_at=conn.created_at,
                    last_used_at=conn.last_used_at,
                    idle_time=now - conn.last_used_at,
                    lifetime=now - conn.created_at,
                    is_stale=conn.is_stale,
                    is_available=conn in self._available,
                )
            )
        return info

    async def get_health_check(self) -> Dict[str, Any]:
        """Get pool health check information.

        Returns:
            Dict with health check information
        """
        metrics = self.get_metrics()
        connections = self.get_connection_info()

        # Calculate statistics
        total_idle_time = sum(c.idle_time for c in connections)
        avg_idle_time = total_idle_time / len(connections) if connections else 0

        total_lifetime = sum(c.lifetime for c in connections)
        avg_lifetime = total_lifetime / len(connections) if connections else 0

        stale_connections = sum(1 for c in connections if c.is_stale)

        return {
            "status": "healthy" if not self._closed else "closed",
            "metrics": metrics._asdict(),
            "statistics": {
                "average_idle_time": avg_idle_time,
                "average_lifetime": avg_lifetime,
                "stale_connections": stale_connections,
                "connection_usage": (
                    metrics.active_connections / metrics.total_connections
                    if metrics.total_connections
                    else 0
                ),
            },
            "connections": [c._asdict() for c in connections],
        }

    async def cleanup_stale(self) -> int:
        """Cleanup stale connections.

        Returns:
            Number of connections cleaned up
        """
        cleaned = 0
        async with self._lock:
            # Check available connections
            for conn in list(self._available):
                if self._should_close_connection(conn):
                    self._available.remove(conn)
                    self._connections.remove(conn)
                    await conn.close()
                    cleaned += 1

            # Create new connections if needed
            while len(self._connections) < self.min_size:
                conn = await self._create_connection()
                self._connections.add(conn)
                self._available.append(conn)

        return cleaned
