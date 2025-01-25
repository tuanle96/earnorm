"""Pool factory implementation.

This module provides a factory for creating database connection pools.
It supports MongoDB, Redis, MySQL, and PostgreSQL backends.

Examples:
    ```python
    # Create MongoDB pool
    mongo_pool = PoolFactory.create(
        "mongodb",
        host="localhost",
        port=27017,
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
                host="localhost",
                port=27017,
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
    host: str = "localhost",
    port: int = 27017,
    database: str = "test",
    collection: str = "test",
    username: str | None = None,
    password: str | None = None,
    auth_source: str | None = None,
    auth_mechanism: str | None = None,
    min_size: int = 1,
    max_size: int = 10,
    max_lifetime: int = 3600,
    **kwargs: Any,
) -> MongoPool[Any, Any]:
    """Create MongoDB connection pool.

    Args:
        host: MongoDB host
        port: MongoDB port
        database: Database name
        collection: Collection name
        username: MongoDB username
        password: MongoDB password
        auth_source: Authentication database
        auth_mechanism: Authentication mechanism
        min_size: Minimum pool size
        max_size: Maximum pool size
        max_lifetime: Maximum connection lifetime
        **kwargs: Additional pool options

    Returns:
        MongoDB connection pool

    Examples:
        ```python
        pool = await create_mongo_pool(
            host="localhost",
            port=27017,
            database="test",
            min_size=1,
            max_size=5
        )
        ```
    """
    pool = MongoPool[Any, Any](
        host=host,
        port=port,
        database=database,
        collection=collection,
        username=username,
        password=password,
        auth_source=auth_source,
        auth_mechanism=auth_mechanism,
        min_size=min_size,
        max_size=max_size,
        max_lifetime=max_lifetime,
        **kwargs,
    )

    await pool.connect()
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
    max_lifetime: int = 3600,
    **kwargs: Any,
) -> RedisPool[Any]:
    """Create Redis connection pool.

    Args:
        host: Redis host
        port: Redis port
        db: Redis database number
        username: Redis username
        password: Redis password
        min_size: Minimum pool size
        max_size: Maximum pool size
        max_lifetime: Maximum connection lifetime
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
            max_size=5
        )
        ```
    """
    pool = RedisPool[Any](
        host=host,
        port=port,
        db=db,
        username=username,
        password=password,
        min_size=min_size,
        max_size=max_size,
        max_lifetime=max_lifetime,
        **kwargs,
    )

    await pool.connect()
    return pool
