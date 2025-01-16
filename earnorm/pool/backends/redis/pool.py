"""Redis pool implementation."""

from typing import Any, Optional

from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool as RedisConnectionPool

from earnorm.pool.backends.redis.connection import RedisConnection
from earnorm.pool.core.pool import BasePool


class RedisPool(BasePool[RedisConnection]):
    """Redis connection pool implementation."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        username: Optional[str] = None,
        ssl: bool = False,
        encoding: str = "utf-8",
        decode_responses: bool = True,
        min_size: int = 5,
        max_size: int = 20,
        timeout: float = 30.0,
        max_lifetime: int = 3600,
        idle_timeout: int = 300,
        validate_on_borrow: bool = True,
        test_on_return: bool = True,
        **config: Any,
    ) -> None:
        """Initialize Redis connection pool.

        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password
            username: Redis username
            ssl: Use SSL/TLS
            encoding: Response encoding
            decode_responses: Decode responses to strings
            min_size: Minimum pool size
            max_size: Maximum pool size
            timeout: Connection acquire timeout
            max_lifetime: Maximum connection lifetime
            idle_timeout: Maximum idle time
            validate_on_borrow: Validate connection on borrow
            test_on_return: Test connection on return
            **config: Additional configuration

        Examples:
            >>> pool = RedisPool(
            ...     host="localhost",
            ...     port=6379,
            ...     db=0,
            ...     min_size=5,
            ...     max_size=20
            ... )
            >>> await pool.init()
            >>> conn = await pool.acquire()
            >>> await conn.execute("set", "key", "value")
            True
            >>> await conn.execute("get", "key")
            "value"
            >>> await pool.release(conn)
            >>> await pool.close()
        """
        super().__init__(
            backend_type="redis",
            min_size=min_size,
            max_size=max_size,
            timeout=timeout,
            max_lifetime=max_lifetime,
            idle_timeout=idle_timeout,
            validate_on_borrow=validate_on_borrow,
            test_on_return=test_on_return,
            **config,
        )
        self._host = host
        self._port = port
        self._db = db
        self._password = password
        self._username = username
        self._ssl = ssl
        self._encoding = encoding
        self._decode_responses = decode_responses
        self._redis_pool = RedisConnectionPool(
            host=host,
            port=port,
            db=db,
            password=password,
            username=username,
            ssl=ssl,
            encoding=encoding,
            decode_responses=decode_responses,
            max_connections=max_size,
        )

    @property
    def host(self) -> str:
        """Get Redis host."""
        return self._host

    @property
    def port(self) -> int:
        """Get Redis port."""
        return self._port

    @property
    def db(self) -> int:
        """Get Redis database number."""
        return self._db

    @property
    def min_size(self) -> int:
        """Get minimum pool size."""
        return self._min_size

    @property
    def max_size(self) -> int:
        """Get maximum pool size."""
        return self._max_size

    @property
    def timeout(self) -> float:
        """Get connection acquire timeout."""
        return self._timeout

    @property
    def max_lifetime(self) -> int:
        """Get maximum connection lifetime."""
        return self._max_lifetime

    @property
    def idle_timeout(self) -> int:
        """Get maximum idle time."""
        return self._idle_timeout

    async def _create_connection(self) -> RedisConnection:
        """Create new Redis connection.

        Returns:
            RedisConnection instance
        """
        client = Redis(connection_pool=self._redis_pool)
        return RedisConnection(client)

    async def _validate_connection(self, conn: RedisConnection) -> bool:
        """Validate Redis connection health.

        Args:
            conn: Connection to validate

        Returns:
            True if connection is healthy
        """
        return await conn.ping()

    async def close(self) -> None:
        """Close all connections and shutdown pool."""
        await super().close()
        await self._redis_pool.disconnect()
