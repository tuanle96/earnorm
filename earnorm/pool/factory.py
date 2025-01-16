"""Pool factory implementation."""

from typing import Any, Dict, Optional, Type, Union, cast

from earnorm.pool.backends.mongo.pool import MongoPool
from earnorm.pool.backends.redis.pool import RedisPool


class PoolFactory:
    """Factory for creating pool instances.

    This factory provides a centralized way to create pool instances with proper
    initialization and configuration. It supports different pool types and ensures
    consistent pool creation across the application.

    Examples:
        ```python
        # Create MongoDB pool
        mongo_pool = await PoolFactory.create_mongo_pool(
            uri="mongodb://localhost:27017",
            database="test",
            min_size=5,
            max_size=20
        )

        # Create Redis pool
        redis_pool = await PoolFactory.create_redis_pool(
            host="localhost",
            port=6379,
            db=0,
            min_size=5,
            max_size=20
        )
        ```
    """

    _pool_types: Dict[str, Type[Union[MongoPool, RedisPool]]] = {
        "mongodb": MongoPool,
        "redis": RedisPool,
    }

    @classmethod
    def register_pool_type(
        cls, name: str, pool_type: Type[Union[MongoPool, RedisPool]]
    ) -> None:
        """Register new pool type.

        Args:
            name: Pool type identifier
            pool_type: Pool type class
        """
        cls._pool_types[name] = pool_type

    @classmethod
    async def create_pool(
        cls, pool_type: Type[Union[MongoPool, RedisPool]], **config: Any
    ) -> Union[MongoPool, RedisPool]:
        """Create pool instance.

        Args:
            pool_type: Pool type class
            **config: Pool configuration

        Returns:
            Pool instance
        """
        pool = pool_type(**config)
        await pool.init()
        return pool

    @classmethod
    async def create_mongo_pool(
        cls,
        uri: str,
        database: str,
        min_size: int = 5,
        max_size: int = 20,
        timeout: float = 30.0,
        max_lifetime: int = 3600,
        idle_timeout: int = 300,
        validate_on_borrow: bool = True,
        test_on_return: bool = True,
        **config: Any,
    ) -> MongoPool:
        """Create MongoDB pool instance.

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
            **config: Additional configuration

        Returns:
            MongoPool instance
        """
        pool = await cls.create_pool(
            MongoPool,
            uri=uri,
            database=database,
            min_size=min_size,
            max_size=max_size,
            timeout=timeout,
            max_lifetime=max_lifetime,
            idle_timeout=idle_timeout,
            validate_on_borrow=validate_on_borrow,
            test_on_return=test_on_return,
            **config,
        )
        return cast(MongoPool, pool)

    @classmethod
    async def create_redis_pool(
        cls,
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
    ) -> RedisPool:
        """Create Redis pool instance.

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

        Returns:
            RedisPool instance
        """
        pool = await cls.create_pool(
            RedisPool,
            host=host,
            port=port,
            db=db,
            password=password,
            username=username,
            ssl=ssl,
            encoding=encoding,
            decode_responses=decode_responses,
            min_size=min_size,
            max_size=max_size,
            timeout=timeout,
            max_lifetime=max_lifetime,
            idle_timeout=idle_timeout,
            validate_on_borrow=validate_on_borrow,
            test_on_return=test_on_return,
            **config,
        )
        return cast(RedisPool, pool)
