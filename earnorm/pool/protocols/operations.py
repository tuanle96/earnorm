"""Operation enums for database operations.

This module defines enums for database operations to ensure type safety.
Each database type has its own set of supported operations.

Examples:
    ```python
    from earnorm.pool.protocols.operations import MongoOperation

    async def execute(self, operation: MongoOperation, *args: Any) -> Any:
        if operation == MongoOperation.FIND_ONE:
            return await self.collection.find_one(*args)
    ```
"""

from enum import Enum
from typing import Any, Dict, List, Set, Union


class MongoOperation(str, Enum):
    """MongoDB operations."""

    # Query operations
    FIND = "find"
    FIND_ONE = "find_one"
    AGGREGATE = "aggregate"
    COUNT_DOCUMENTS = "count_documents"
    DISTINCT = "distinct"

    # Write operations
    INSERT_ONE = "insert_one"
    INSERT_MANY = "insert_many"
    UPDATE_ONE = "update_one"
    UPDATE_MANY = "update_many"
    REPLACE_ONE = "replace_one"
    DELETE_ONE = "delete_one"
    DELETE_MANY = "delete_many"

    # Index operations
    CREATE_INDEX = "create_index"
    CREATE_INDEXES = "create_indexes"
    DROP_INDEX = "drop_index"
    DROP_INDEXES = "drop_indexes"
    LIST_INDEXES = "list_indexes"

    # Collection operations
    CREATE_COLLECTION = "create_collection"
    DROP_COLLECTION = "drop_collection"
    RENAME_COLLECTION = "rename_collection"
    LIST_COLLECTIONS = "list_collections"


class RedisOperation(str, Enum):
    """Redis operations."""

    # String operations
    GET = "get"
    SET = "set"
    SETEX = "setex"
    SETNX = "setnx"
    MGET = "mget"
    MSET = "mset"
    DELETE = "delete"
    EXISTS = "exists"
    EXPIRE = "expire"

    # Hash operations
    HGET = "hget"
    HSET = "hset"
    HMGET = "hmget"
    HMSET = "hmset"
    HDEL = "hdel"
    HEXISTS = "hexists"
    HGETALL = "hgetall"

    # List operations
    LPUSH = "lpush"
    RPUSH = "rpush"
    LPOP = "lpop"
    RPOP = "rpop"
    LRANGE = "lrange"
    LLEN = "llen"

    # Set operations
    SADD = "sadd"
    SREM = "srem"
    SMEMBERS = "smembers"
    SISMEMBER = "sismember"
    SCARD = "scard"

    # Sorted set operations
    ZADD = "zadd"
    ZREM = "zrem"
    ZRANGE = "zrange"
    ZRANK = "zrank"
    ZCARD = "zcard"

    # Pub/sub operations
    PUBLISH = "publish"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"

    # Transaction operations
    MULTI = "multi"
    EXEC = "exec"
    DISCARD = "discard"
    WATCH = "watch"
    UNWATCH = "unwatch"


# Type aliases for operation parameters
MongoDocument = Dict[str, Any]
MongoFilter = Dict[str, Any]
MongoUpdate = Dict[str, Any]
MongoProjection = Dict[str, Union[int, bool]]
MongoSort = List[tuple[str, int]]

RedisKey = str
RedisValue = Union[str, int, float, bytes]
RedisHash = Dict[str, RedisValue]
RedisList = List[RedisValue]
RedisSet = Set[RedisValue]
RedisZSet = Dict[RedisValue, float]
