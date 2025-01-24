"""Base pool implementation."""

from typing import (
    Any,
    AsyncContextManager,
    Coroutine,
    Dict,
    Generic,
    Optional,
    TypeVar,
    cast,
)

from earnorm.pool.protocols.connection import ConnectionProtocol
from earnorm.pool.protocols.errors import ConnectionError, PoolError, PoolExhaustedError
from earnorm.pool.protocols.pool import PoolProtocol

# Type variables for database and collection
DB = TypeVar("DB")
COLL = TypeVar("COLL")


class PoolContextManager(AsyncContextManager[ConnectionProtocol[DB, COLL]]):
    """Pool connection context manager."""

    def __init__(self, pool: "BasePool[DB, COLL]") -> None:
        """Initialize context manager.

        Args:
            pool: Connection pool
        """
        self._pool = pool
        self._conn: Optional[ConnectionProtocol[DB, COLL]] = None

    async def __aenter__(self) -> ConnectionProtocol[DB, COLL]:
        """Enter context.

        Returns:
            Connection from pool
        """
        conn = await self._pool.acquire()
        self._conn = cast(ConnectionProtocol[DB, COLL], conn)
        return self._conn

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context.

        Args:
            exc_type: Exception type
            exc_val: Exception value
            exc_tb: Exception traceback
        """
        if self._conn is not None:
            await self._pool.release(self._conn)


class BasePool(PoolProtocol[DB, COLL], Generic[DB, COLL]):
    """Base pool implementation.

    This class provides a basic pool protocol implementation that can be
    extended by specific database backends.

    Args:
        uri: Database URI
        database: Database name
        min_size: Minimum pool size
        max_size: Maximum pool size
        max_idle_time: Maximum idle time in seconds
        connection_timeout: Connection timeout in seconds
        max_lifetime: Maximum connection lifetime in seconds
        validate_on_borrow: Whether to validate connections on borrow
        test_on_return: Whether to test connections on return
        extra_config: Extra configuration options
    """

    def __init__(
        self,
        uri: str,
        database: Optional[str] = None,
        min_size: int = 5,
        max_size: int = 20,
        max_idle_time: int = 300,
        connection_timeout: float = 30.0,
        max_lifetime: int = 3600,
        validate_on_borrow: bool = True,
        test_on_return: bool = True,
        extra_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._uri = uri
        self._database = database
        self._min_size = min_size
        self._max_size = max_size
        self._max_idle_time = max_idle_time
        self._connection_timeout = connection_timeout
        self._max_lifetime = max_lifetime
        self._validate_on_borrow = validate_on_borrow
        self._test_on_return = test_on_return
        self._extra_config = extra_config or {}

        self._pool: Dict[int, ConnectionProtocol[DB, COLL]] = {}
        self._acquiring = 0

    @property
    def size(self) -> int:
        """Get current pool size."""
        return len(self._pool)

    @property
    def max_size(self) -> int:
        """Get maximum pool size."""
        return self._max_size

    @property
    def min_size(self) -> int:
        """Get minimum pool size."""
        return self._min_size

    @property
    def available(self) -> int:
        """Get number of available connections."""
        return self.max_size - self.in_use

    @property
    def in_use(self) -> int:
        """Get number of connections in use."""
        return self._acquiring

    def _create_connection(self) -> ConnectionProtocol[DB, COLL]:
        """Create new connection.

        Returns:
            New connection instance

        Raises:
            NotImplementedError: Must be implemented by subclass
        """
        raise NotImplementedError("Must be implemented by subclass")

    async def _validate_connection(self, conn: ConnectionProtocol[DB, COLL]) -> bool:
        """Validate connection.

        Args:
            conn: Connection to validate

        Returns:
            True if connection is valid
        """
        try:
            await conn.ping()
            return True
        except Exception:
            return False

    async def acquire(self) -> Coroutine[Any, Any, ConnectionProtocol[DB, COLL]]:
        """Acquire connection from pool.

        Returns:
            Connection from pool

        Raises:
            PoolExhaustedError: If pool is exhausted
            ConnectionError: If connection cannot be created
        """
        if len(self._pool) >= self._max_size and self._acquiring >= self._max_size:
            raise PoolExhaustedError("Pool exhausted")

        self._acquiring += 1
        try:
            conn = self._create_connection()
            if self._validate_on_borrow and not await self._validate_connection(conn):
                raise ConnectionError("Connection validation failed")
            self._pool[id(conn)] = conn

            async def _acquire() -> ConnectionProtocol[DB, COLL]:
                return conn

            return _acquire()  # type: ignore
        except Exception as e:
            self._acquiring -= 1
            raise ConnectionError("Failed to acquire connection") from e

    async def release(
        self, connection: ConnectionProtocol[DB, COLL]
    ) -> Coroutine[Any, Any, None]:
        """Release connection back to pool.

        Args:
            connection: Connection to release

        Raises:
            ConnectionError: If connection cannot be released
        """
        conn_id = id(connection)
        if conn_id not in self._pool:
            raise ConnectionError("Connection not from this pool")

        try:
            if self._test_on_return and not await self._validate_connection(connection):
                await self.remove(connection)

                async def _release() -> None:
                    return None

                return _release()  # type: ignore

            self._pool[conn_id] = connection
            self._acquiring -= 1

            async def _release() -> None:
                return None

            return _release()  # type: ignore
        except Exception as e:
            raise ConnectionError("Failed to release connection") from e

    async def remove(self, conn: ConnectionProtocol[DB, COLL]) -> None:
        """Remove connection from pool.

        Args:
            conn: Connection to remove

        Raises:
            ConnectionError: If connection cannot be removed
        """
        conn_id = id(conn)
        if conn_id not in self._pool:
            return

        try:
            await conn.close()
            del self._pool[conn_id]
            self._acquiring -= 1
        except Exception as e:
            raise ConnectionError("Failed to remove connection") from e

    async def clear(self) -> Coroutine[Any, Any, None]:
        """Clear all connections in pool.

        Raises:
            PoolError: If pool cannot be cleared
        """
        try:
            for conn in list(self._pool.values()):
                await self.remove(conn)

            async def _clear() -> None:
                return None

            return _clear()  # type: ignore
        except Exception as e:
            raise PoolError("Failed to clear pool") from e

    async def close(self) -> Coroutine[Any, Any, None]:
        """Close pool.

        Raises:
            PoolError: If pool cannot be closed
        """
        try:
            await self.clear()

            async def _close() -> None:
                return None

            return _close()  # type: ignore
        except Exception as e:
            raise PoolError("Failed to close pool") from e

    async def connection(self) -> AsyncContextManager[ConnectionProtocol[DB, COLL]]:
        """Get connection context manager.

        Returns:
            Connection context manager

        Raises:
            ConnectionError: If connection cannot be acquired or released
        """
        return PoolContextManager(self)

    async def execute_typed(self, operation: str, *args: Any, **kwargs: Any) -> Any:
        """Execute operation with connection from pool.

        Args:
            operation: Operation name
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Operation result

        Raises:
            ConnectionError: If connection is unhealthy
        """
        ctx = await self.connection()
        async with ctx as conn:
            return await conn.execute_typed(operation, *args, **kwargs)

    async def health_check(self) -> Coroutine[Any, Any, bool]:
        """Check pool health.

        Returns:
            True if pool is healthy
        """
        try:
            ctx = await self.connection()
            async with ctx as conn:
                result = bool(await conn.ping())

                async def _health_check() -> bool:
                    return result

                return _health_check()  # type: ignore
        except Exception:

            async def _health_check() -> bool:
                return False

            return _health_check()  # type: ignore

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics.

        Returns:
            Dictionary containing pool statistics:
            - size: Current pool size
            - max_size: Maximum pool size
            - min_size: Minimum pool size
            - available: Number of available connections
            - in_use: Number of connections in use
            - acquiring: Number of connections being acquired
            - uri: Database URI
            - database: Database name
            - max_idle_time: Maximum idle time in seconds
            - max_lifetime: Maximum lifetime in seconds
            - validate_on_borrow: Whether to validate connections on borrow
            - test_on_return: Whether to test connections on return
        """
        return {
            "size": self.size,
            "max_size": self.max_size,
            "min_size": self.min_size,
            "available": self.available,
            "in_use": self.in_use,
            "acquiring": self._acquiring,
            "uri": self._uri,
            "database": self._database,
            "max_idle_time": self._max_idle_time,
            "max_lifetime": self._max_lifetime,
            "validate_on_borrow": self._validate_on_borrow,
            "test_on_return": self._test_on_return,
        }

    @property
    def database_name(self) -> str:
        """Get database name."""
        if self._database is None:
            raise ValueError("Database name not set")
        return self._database
