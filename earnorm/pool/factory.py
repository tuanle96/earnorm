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
        uri="redis://localhost:6379",
    )
    ```
"""

from typing import Any, Dict, Type, TypeVar

from earnorm.pool.backends.mongo.pool import MongoPool
from earnorm.pool.backends.mysql.pool import MySQLPool
from earnorm.pool.backends.postgres.pool import PostgresPool
from earnorm.pool.backends.redis.pool import RedisPool
from earnorm.pool.protocols.pool import PoolProtocol

# Define type variables for database and collection types
DB = TypeVar("DB")
COLL = TypeVar("COLL")


class PoolFactory:
    """Pool factory for creating database connection pools."""

    _pools: Dict[str, Type[PoolProtocol[Any, Any]]] = {
        "mongodb": MongoPool,
        "redis": RedisPool,
        "mysql": MySQLPool,
        "postgres": PostgresPool,
    }

    @classmethod
    def register(cls, name: str, pool_class: Type[PoolProtocol[DB, COLL]]) -> None:
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
    def create(cls, backend: str, **config: Any) -> PoolProtocol[Any, Any]:
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
    max_lifetime: int = 3600,
    **kwargs: Any,
) -> MongoPool[Any, Any]:
    """Create MongoDB connection pool.

    Args:
        uri: MongoDB connection URI
        database: Database name
        min_size: Minimum pool size
        max_size: Maximum pool size
        connection_timeout: Connection timeout
        max_lifetime: Maximum connection lifetime
        idle_timeout: Connection idle timeout
        validate_on_borrow: Whether to validate connections on borrow
        test_on_return: Whether to test connections on return
        **kwargs: Additional pool options
            - username: MongoDB username
            - password: MongoDB password
            - auth_source: Authentication database
            - auth_mechanism: Authentication mechanism
            - replica_set: Replica set name
            - read_preference: Read preference
            - write_concern: Write concern

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
        max_lifetime=max_lifetime,
        **kwargs,
    )

    await pool.init()
    return pool


async def create_redis_pool(
    *,
    host: str,
    port: int,
    db: int = 0,
    min_size: int = 1,
    max_size: int = 10,
    timeout: float = 30.0,
    **kwargs: Any,
) -> RedisPool[Any, Any]:
    """Create Redis connection pool.

    Args:
        host: Redis host
        port: Redis port
        db: Redis database number
        min_size: Minimum pool size
        max_size: Maximum pool size
        timeout: Connection timeout
        **kwargs: Additional pool options
            - username: Redis username
            - password: Redis password
            - ssl: Whether to use SSL
            - ssl_ca_certs: Path to CA certificates file
            - ssl_certfile: Path to client certificate file
            - ssl_keyfile: Path to client key file
            - ssl_cert_reqs: SSL certificate requirements

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
    pool = RedisPool[Any, Any](
        host=host,
        port=port,
        db=db,
        min_size=min_size,
        max_size=max_size,
        timeout=timeout,
        **kwargs,
    )

    await pool.init()
    return pool
