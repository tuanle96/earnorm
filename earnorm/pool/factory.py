"""Pool factory implementation.

This module provides a factory for creating database connection pools.
It supports MongoDB, Redis, MySQL, and PostgreSQL backends.

Examples:
    ```python
    # Create MongoDB pool
    mongo_pool = PoolFactory.create(
        "mongodb",
        uri="mongodb://localhost:27017",
        database="test",
    )

    # Create Redis pool
    redis_pool = PoolFactory.create(
        "redis",
        host="localhost",
        port=6379,
    )
    ```
"""

from typing import Any, Dict, Type, TypeVar, cast

from earnorm.pool.backends.mongo.pool import MongoPool
from earnorm.pool.backends.redis.pool import RedisPool
from earnorm.pool.protocols.pool import AsyncPoolProtocol

# Define type variables for database and collection types
DB = TypeVar("DB")
COLL = TypeVar("COLL")


class PoolFactory:
    """Pool factory for creating database connection pools."""

    _pools: Dict[str, Type[AsyncPoolProtocol[Any, Any]]] = {
        "mongodb": cast(Type[AsyncPoolProtocol[Any, Any]], MongoPool),
        "redis": cast(Type[AsyncPoolProtocol[Any, Any]], RedisPool),
    }

    @classmethod
    def register(cls, name: str, pool_class: Type[AsyncPoolProtocol[DB, COLL]]) -> None:
        """Register pool implementation.

        Args:
            name: Pool name
            pool_class: Pool class

        Examples:
            ```python
            # Register custom pool
            PoolFactory.register("custom", CustomPool)
            ```
        """
        cls._pools[name] = pool_class  # type: ignore

    @classmethod
    def create(cls, backend: str, **config: Any) -> AsyncPoolProtocol[Any, Any]:
        """Create pool instance.

        Args:
            backend: Backend type (mongodb, redis, mysql, postgresql)
            **config: Pool configuration

        Returns:
            Pool instance

        Raises:
            ValueError: If backend type is unknown

        Examples:
            ```python
            # Create MongoDB pool
            pool = PoolFactory.create(
                "mongodb",
                uri="mongodb://localhost:27017",
                database="test",
            )
            ```
        """
        if backend not in cls._pools:
            raise ValueError(f"Unknown backend: {backend}")

        pool_class = cls._pools[backend]
        return pool_class(**config)


async def create_mongo_pool(
    *,
    uri: str,
    database: str,
    min_size: int = 1,
    max_size: int = 10,
    retry_policy: Any | None = None,
    circuit_breaker: Any | None = None,
    **kwargs: Any,
) -> MongoPool[Any, Any]:
    """Create MongoDB connection pool.

    Args:
        uri: MongoDB URI
        database: Database name
        min_size: Minimum pool size
        max_size: Maximum pool size
        retry_policy: Optional retry policy
        circuit_breaker: Optional circuit breaker
        **kwargs: Additional pool options

    Returns:
        MongoDB connection pool

    Examples:
        ```python
        pool = await create_mongo_pool(
            uri="mongodb://localhost:27017",
            database="test",
            min_size=1,
            max_size=5
        )
        ```
    """
    pool = MongoPool[Any, Any](
        uri=uri,
        database=database,
        min_size=min_size,
        max_size=max_size,
        retry_policy=retry_policy,
        circuit_breaker=circuit_breaker,
        **kwargs,
    )

    await pool.init()
    return pool


async def create_redis_pool(
    *,
    host: str = "localhost",
    port: int = 6379,
    db: int = 0,
    username: str | None = None,
    password: str | None = None,
    min_size: int = 1,
    max_size: int = 10,
    socket_timeout: float | None = None,
    socket_connect_timeout: float | None = None,
    socket_keepalive: bool = True,
    retry_policy: Any | None = None,
    circuit_breaker: Any | None = None,
    **kwargs: Any,
) -> RedisPool[Any, None]:
    """Create Redis connection pool.

    Args:
        host: Redis host
        port: Redis port
        db: Redis database number
        username: Redis username
        password: Redis password
        min_size: Minimum pool size
        max_size: Maximum pool size
        socket_timeout: Socket timeout in seconds
        socket_connect_timeout: Socket connect timeout in seconds
        socket_keepalive: Whether to enable socket keepalive
        retry_policy: Optional retry policy
        circuit_breaker: Optional circuit breaker
        **kwargs: Additional pool options

    Returns:
        Redis connection pool

    Examples:
        ```python
        pool = await create_redis_pool(
            host="localhost",
            port=6379,
            db=0,
            min_size=1,
            max_size=5,
            socket_timeout=30,
            socket_connect_timeout=10,
            socket_keepalive=True
        )
        ```
    """
    pool = RedisPool[Any, None](
        host=host,
        port=port,
        db=db,
        username=username,
        password=password,
        min_size=min_size,
        max_size=max_size,
        socket_timeout=socket_timeout,
        socket_connect_timeout=socket_connect_timeout,
        socket_keepalive=socket_keepalive,
        retry_policy=retry_policy,
        circuit_breaker=circuit_breaker,
        **kwargs,
    )

    await pool.init()
    return pool
