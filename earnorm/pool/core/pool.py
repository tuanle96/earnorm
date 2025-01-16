"""Base pool implementation."""

import asyncio
import logging
from typing import Any, Dict, Generic, List, Set, TypeVar

from earnorm.pool.protocols.connection import ConnectionProtocol
from earnorm.pool.protocols.pool import PoolProtocol

logger = logging.getLogger(__name__)

C = TypeVar("C", bound=ConnectionProtocol)


class BasePool(PoolProtocol[C], Generic[C]):
    """Base pool implementation."""

    def __init__(
        self,
        backend_type: str,
        min_size: int = 5,
        max_size: int = 20,
        timeout: float = 30.0,
        max_lifetime: int = 3600,
        idle_timeout: int = 300,
        validate_on_borrow: bool = True,
        test_on_return: bool = True,
        **config: Any,
    ) -> None:
        """Initialize pool.

        Args:
            backend_type: Backend type identifier
            min_size: Minimum pool size
            max_size: Maximum pool size
            timeout: Connection acquire timeout
            max_lifetime: Maximum connection lifetime
            idle_timeout: Maximum idle time
            validate_on_borrow: Validate connection on borrow
            test_on_return: Test connection on return
            **config: Additional configuration
        """
        self._backend_type = backend_type
        self._min_size = min_size
        self._max_size = max_size
        self._timeout = timeout
        self._max_lifetime = max_lifetime
        self._idle_timeout = idle_timeout
        self._validate_on_borrow = validate_on_borrow
        self._test_on_return = test_on_return
        self._config = config

        # Internal state
        self._connections: Set[C] = set()
        self._available: List[C] = []
        self._acquiring = 0
        self._initialized = False
        self._closed = False
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Condition(self._lock)

    @property
    def backend_type(self) -> str:
        return self._backend_type

    @property
    def size(self) -> int:
        return len(self._connections)

    @property
    def available(self) -> int:
        return len(self._available)

    async def init(self, **config: Dict[str, Any]) -> None:
        """Initialize pool with minimum connections."""
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            # Create minimum connections
            for _ in range(self._min_size):
                conn = await self._create_connection()
                self._connections.add(conn)
                self._available.append(conn)

            self._initialized = True
            logger.info(
                "Initialized %s pool with %d connections (min=%d, max=%d)",
                self._backend_type,
                self.size,
                self._min_size,
                self._max_size,
            )

    async def acquire(self) -> C:
        """Acquire connection from pool."""
        if not self._initialized:
            await self.init()

        if self._closed:
            raise RuntimeError("Pool is closed")

        async with self._lock:
            while True:
                # Check available connections
                while self._available:
                    conn = self._available.pop(0)

                    # Validate if needed
                    if (
                        self._validate_on_borrow
                        and not await self._validate_connection(conn)
                    ):
                        self._connections.remove(conn)
                        await conn.close()
                        continue

                    conn.touch()
                    return conn

                # Create new connection if possible
                if self.size + self._acquiring < self._max_size:
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
                    await asyncio.wait_for(
                        self._not_empty.wait(), timeout=self._timeout
                    )
                except asyncio.TimeoutError:
                    raise TimeoutError(
                        f"Timeout waiting for connection (timeout={self._timeout}s)"
                    )

    async def release(self, conn: C) -> None:
        """Release connection back to pool."""
        if conn not in self._connections:
            return

        # Test connection if needed
        if self._test_on_return and not await self._validate_connection(conn):
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

    async def _create_connection(self) -> C:
        """Create new connection.

        This method should be overridden by subclasses.
        """
        raise NotImplementedError

    async def _validate_connection(self, conn: C) -> bool:
        """Validate connection health.

        This method should be overridden by subclasses.
        """
        raise NotImplementedError
