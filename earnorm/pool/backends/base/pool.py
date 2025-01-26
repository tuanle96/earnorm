"""Base connection pool implementation."""

import abc
import asyncio
from contextlib import AbstractAsyncContextManager
from typing import Any, Generic, TypeVar

# pylint: disable=redefined-builtin
from earnorm.exceptions import DatabaseConnectionError, PoolExhaustedError
from earnorm.pool.core.circuit import CircuitBreaker
from earnorm.pool.core.retry import RetryPolicy
from earnorm.pool.protocols.connection import AsyncConnectionProtocol

DB = TypeVar("DB")
COLL = TypeVar("COLL")


class BasePool(
    AbstractAsyncContextManager["BasePool[DB, COLL]"], Generic[DB, COLL], abc.ABC
):
    """Base connection pool implementation."""

    def __init__(
        self,
        pool_size: int = 10,
        min_size: int = 2,
        max_size: int = 20,
        max_idle_time: int = 300,
        max_lifetime: int = 3600,
        retry_policy: RetryPolicy | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        backend: str = "unknown",
    ) -> None:
        """Initialize base pool.

        Args:
            pool_size: Initial pool size
            min_size: Minimum pool size
            max_size: Maximum pool size
            max_idle_time: Maximum idle time in seconds
            max_lifetime: Maximum lifetime in seconds
            retry_policy: Retry policy
            circuit_breaker: Circuit breaker
            backend: Database backend name
        """
        self._pool_size = pool_size
        self._min_size = min_size
        self._max_size = max_size
        self._max_idle_time = max_idle_time
        self._max_lifetime = max_lifetime
        self._retry_policy = retry_policy
        self._circuit_breaker = circuit_breaker
        self._backend = backend

        self._available: list[AsyncConnectionProtocol[DB, COLL]] = []
        self._in_use: list[AsyncConnectionProtocol[DB, COLL]] = []
        self._lock = asyncio.Lock()

    @abc.abstractmethod
    def _create_connection(self) -> AsyncConnectionProtocol[DB, COLL]:
        """Create a new connection.

        Returns:
            AsyncConnectionProtocol: New connection

        Raises:
            ConnectionError: If connection creation fails
        """
        ...

    async def __aenter__(self) -> "BasePool[DB, COLL]":
        """Enter pool context.

        Returns:
            BasePool: Pool instance

        Raises:
            ConnectionError: If connection fails
        """
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        """Exit pool context.

        Args:
            exc_type: Exception type
            exc: Exception instance
            tb: Traceback
        """
        await self.disconnect()

    async def connect(self) -> None:
        """Connect to database.

        Raises:
            ConnectionError: If connection fails
        """
        async with self._lock:
            for _ in range(self._pool_size):
                try:
                    conn = self._create_connection()
                    self._available.append(conn)
                except Exception as e:
                    raise DatabaseConnectionError(
                        f"Failed to create connection: {e}",
                        backend=self._backend,
                    ) from e

    async def disconnect(self) -> None:
        """Disconnect from database."""
        async with self._lock:
            for conn in self._available + self._in_use:
                await conn.close()
            self._available.clear()
            self._in_use.clear()

    async def acquire(self) -> AsyncConnectionProtocol[DB, COLL]:
        """Acquire a connection.

        Returns:
            AsyncConnectionProtocol: Connection instance

        Raises:
            PoolExhaustedError: If no connections are available
        """
        async with self._lock:
            if self._available:
                conn = self._available.pop()
                self._in_use.append(conn)
                return conn

            if len(self._in_use) < self._max_size:
                try:
                    conn = self._create_connection()
                    self._in_use.append(conn)
                    return conn
                except Exception as e:
                    raise DatabaseConnectionError(
                        f"Failed to create connection: {e}",
                        backend=self._backend,
                    ) from e

            raise PoolExhaustedError(
                "Connection pool exhausted",
                backend=self._backend,
                pool_size=self._max_size,
                active_connections=len(self._in_use),
                waiting_requests=0,
            )

    async def release(self, conn: AsyncConnectionProtocol[DB, COLL]) -> None:
        """Release a connection.

        Args:
            conn: Connection to release
        """
        async with self._lock:
            try:
                self._in_use.remove(conn)
                if await conn.ping():
                    self._available.append(conn)
                else:
                    await conn.close()
            except ValueError:
                pass

    async def ping(self) -> bool:
        """Check pool health.

        Returns:
            bool: True if pool is healthy
        """
        try:
            conn = await self.acquire()
            try:
                return await conn.ping()
            finally:
                await self.release(conn)
        except Exception as e:
            raise DatabaseConnectionError(
                f"Failed to ping connection: {e}",
                backend=self._backend,
            ) from e

    def get_stats(self) -> dict[str, Any]:
        """Get pool statistics.

        Returns:
            dict[str, Any]: Pool statistics including connection counts
        """
        return {
            "pool_size": len(self._available) + len(self._in_use),
            "available": len(self._available),
            "in_use": len(self._in_use),
            "min_size": self._min_size,
            "max_size": self._max_size,
        }
