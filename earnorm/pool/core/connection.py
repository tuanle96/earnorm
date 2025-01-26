"""Connection management functionality.

This module provides advanced connection management features including:
- Connection pre-warming
- Connection recycling
- Connection multiplexing
- Connection validation
- Connection cleanup
- Error classification and recovery

Examples:
    ```python
    # Create connection manager
    manager = ConnectionManager(
        factory=MongoConnectionFactory(),
        pool_size=10,
        min_size=2,
        max_size=20,
    )

    # Pre-warm connections
    await manager.pre_warm()

    # Get connection
    async with manager.acquire() as conn:
        result = await conn.execute(MongoOperation.FIND_ONE, {"_id": "123"})
    ```
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    AsyncContextManager,
    Dict,
    List,
    Optional,
    Protocol,
    Set,
    TypeVar,
)

from earnorm.exceptions import ConnectionError, PoolExhaustedError

logger = logging.getLogger(__name__)

T = TypeVar("T")
DBType = TypeVar("DBType", covariant=True)
CollType = TypeVar("CollType", covariant=True)


class ConnectionState(Enum):
    """Connection states."""

    IDLE = "idle"  # Connection is idle and available
    BUSY = "busy"  # Connection is in use
    STALE = "stale"  # Connection is stale and needs cleanup
    CLOSED = "closed"  # Connection is closed
    ERROR = "error"  # Connection is in error state


class ErrorSeverity(Enum):
    """Error severity levels."""

    LOW = "low"  # Transient error, can retry
    MEDIUM = "medium"  # Needs connection reset
    HIGH = "high"  # Needs connection replacement
    CRITICAL = "critical"  # Needs pool reset


@dataclass
class ConnectionMetrics:
    """Connection metrics."""

    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    total_errors: int = 0
    error_types: Dict[str, int] = field(default_factory=dict)
    validation_failures: int = 0
    recovery_attempts: int = 0
    successful_recoveries: int = 0


class ConnectionFactory(Protocol[DBType, CollType]):
    """Protocol for connection factory."""

    async def create_connection(self) -> AsyncContextManager[Any]:
        """Create a new connection.

        Returns:
            AsyncContextManager: Connection context manager
        """
        ...

    async def validate_connection(self, connection: Any) -> bool:
        """Validate connection health.

        Args:
            connection: Connection to validate

        Returns:
            bool: True if connection is healthy
        """
        ...

    async def cleanup_connection(self, connection: Any) -> None:
        """Clean up connection.

        Args:
            connection: Connection to clean up
        """
        ...

    def classify_error(self, error: Exception) -> ErrorSeverity:
        """Classify error severity.

        Args:
            error: Error to classify

        Returns:
            ErrorSeverity: Error severity level
        """
        ...

    @property
    def backend(self) -> str:
        """Get backend name.

        Returns:
            str: Backend name
        """
        ...


@dataclass
class ConnectionWrapper:
    """Connection wrapper with metadata."""

    connection: Any
    state: ConnectionState = ConnectionState.IDLE
    metrics: ConnectionMetrics = field(default_factory=ConnectionMetrics)
    last_error: Optional[Exception] = None
    error_severity: Optional[ErrorSeverity] = None


class ConnectionManager:
    """Connection manager implementation."""

    def __init__(
        self,
        factory: ConnectionFactory[DBType, CollType],
        pool_size: int = 10,
        min_size: int = 2,
        max_size: int = 20,
        max_idle_time: int = 300,
        max_lifetime: int = 3600,
        validation_interval: int = 60,
        cleanup_interval: int = 300,
        pre_warm: bool = True,
    ) -> None:
        """Initialize connection manager.

        Args:
            factory: Connection factory
            pool_size: Initial pool size
            min_size: Minimum pool size
            max_size: Maximum pool size
            max_idle_time: Maximum idle time in seconds
            max_lifetime: Maximum lifetime in seconds
            validation_interval: Connection validation interval in seconds
            cleanup_interval: Connection cleanup interval in seconds
            pre_warm: Whether to pre-warm connections
        """
        self._factory = factory
        self._pool_size = pool_size
        self._min_size = min_size
        self._max_size = max_size
        self._max_idle_time = max_idle_time
        self._max_lifetime = max_lifetime
        self._validation_interval = validation_interval
        self._cleanup_interval = cleanup_interval
        self._pre_warm = pre_warm

        self._connections: List[ConnectionWrapper] = []
        self._idle_connections: Set[ConnectionWrapper] = set()
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task[None]] = None

    async def start(self) -> None:
        """Start connection manager."""
        if self._pre_warm:
            await self.pre_warm()
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        """Stop connection manager."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        await self._cleanup_all()

    async def pre_warm(self) -> None:
        """Pre-warm connections."""
        async with self._lock:
            while len(self._connections) < self._pool_size:
                try:
                    conn = await self._create_connection()
                    self._connections.append(conn)
                    self._idle_connections.add(conn)
                except Exception as e:
                    logger.error(f"Failed to pre-warm connection: {e}")
                    break

    async def _create_connection(self) -> ConnectionWrapper:
        """Create a new connection.

        Returns:
            ConnectionWrapper: New connection wrapper

        Raises:
            ConnectionError: If connection creation fails
        """
        try:
            conn = await self._factory.create_connection()
            return ConnectionWrapper(connection=conn)
        except Exception as e:
            raise ConnectionError(
                f"Failed to create connection: {e}",
                backend=self._factory.backend,
            ) from e

    async def _validate_connection(self, wrapper: ConnectionWrapper) -> bool:
        """Validate connection health.

        Args:
            wrapper: Connection wrapper to validate

        Returns:
            bool: True if connection is healthy
        """
        try:
            is_valid = await self._factory.validate_connection(wrapper.connection)
            if not is_valid:
                wrapper.metrics.validation_failures += 1
            return is_valid
        except Exception as e:
            wrapper.metrics.validation_failures += 1
            wrapper.last_error = e
            wrapper.error_severity = self._factory.classify_error(e)
            return False

    async def _cleanup_connection(self, wrapper: ConnectionWrapper) -> None:
        """Clean up connection.

        Args:
            wrapper: Connection wrapper to clean up
        """
        try:
            await self._factory.cleanup_connection(wrapper.connection)
            wrapper.state = ConnectionState.CLOSED
        except Exception as e:
            logger.error(f"Failed to cleanup connection: {e}", exc_info=True)
            wrapper.last_error = e
            wrapper.error_severity = self._factory.classify_error(e)
            wrapper.state = ConnectionState.ERROR

    async def _cleanup_loop(self) -> None:
        """Background task for connection cleanup."""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self._cleanup_idle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}", exc_info=True)

    async def _cleanup_idle(self) -> None:
        """Clean up idle connections."""
        now = time.time()
        async with self._lock:
            for wrapper in list(self._idle_connections):
                if (
                    now - wrapper.metrics.last_used_at > self._max_idle_time
                    or now - wrapper.metrics.created_at > self._max_lifetime
                ):
                    await self._cleanup_connection(wrapper)
                    self._idle_connections.remove(wrapper)
                    self._connections.remove(wrapper)

    async def _cleanup_all(self) -> None:
        """Clean up all connections."""
        async with self._lock:
            for wrapper in self._connections:
                await self._cleanup_connection(wrapper)
            self._connections.clear()
            self._idle_connections.clear()

    async def acquire(self) -> AsyncContextManager[Any]:
        """Acquire a connection from the pool.

        Returns:
            AsyncContextManager: Connection context manager

        Raises:
            PoolExhaustedError: If pool is exhausted
        """
        async with self._lock:
            if not self._idle_connections:
                if len(self._connections) >= self._max_size:
                    raise PoolExhaustedError(
                        "Connection pool exhausted",
                        backend=self._factory.backend,
                        pool_size=self._max_size,
                        active_connections=len(self._connections),
                        waiting_requests=0,
                    )
                wrapper = await self._create_connection()
                self._connections.append(wrapper)
            else:
                wrapper = self._idle_connections.pop()

            wrapper.state = ConnectionState.BUSY
            wrapper.metrics.last_used_at = time.time()
            return wrapper.connection

    async def release(self, connection: Any) -> None:
        """Release a connection back to the pool.

        Args:
            connection: Connection to release
        """
        async with self._lock:
            for wrapper in self._connections:
                if wrapper.connection == connection:
                    if not await self._validate_connection(wrapper):
                        await self._cleanup_connection(wrapper)
                        self._connections.remove(wrapper)
                    else:
                        wrapper.state = ConnectionState.IDLE
                        self._idle_connections.add(wrapper)
                    break
