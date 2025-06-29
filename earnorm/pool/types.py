"""Pool types module.

This module contains all type hints used in the pool module.
"""

from typing import Any, TypeAlias, TypeVar

from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from redis.asyncio import Redis  # pylint: disable=import-error,no-name-in-module

# Generic types
T = TypeVar("T")
DB = TypeVar("DB")
COLL = TypeVar("COLL")

# Type aliases for MongoDB
MongoDBType = AsyncIOMotorDatabase[dict[str, Any]]  # type: ignore
MongoCollectionType = AsyncIOMotorCollection[dict[str, Any]]  # type: ignore

# Type alias for Redis
RedisType = Redis  # type: ignore

# Type variables for pools
DBType = TypeVar("DBType")
CollType = TypeVar("CollType")

# MongoDB types
MongoDocument: TypeAlias = dict[str, Any]
MongoFilter: TypeAlias = dict[str, Any]
MongoUpdate: TypeAlias = dict[str, Any]
MongoProjection: TypeAlias = dict[str, int | bool]
MongoSort: TypeAlias = list[tuple[str, int]]
MongoOptions: TypeAlias = dict[str, Any]
MongoResult: TypeAlias = dict[str, Any]
MongoSession: TypeAlias = Any  # Will be replaced with proper type

# Redis types
RedisKey: TypeAlias = str
RedisValue: TypeAlias = str | int | float | bytes
RedisHash: TypeAlias = dict[str, RedisValue]
RedisList: TypeAlias = list[RedisValue]
RedisSet: TypeAlias = set[RedisValue]
RedisZSet: TypeAlias = dict[RedisValue, float]
RedisOptions: TypeAlias = dict[str, Any]
RedisResult: TypeAlias = str | int | float | bytes | list[Any] | dict[str, Any] | None
RedisSession: TypeAlias = Any  # Will be replaced with proper type

# Pool types
PoolConfig: TypeAlias = dict[str, Any]
PoolStats: TypeAlias = dict[str, Any]
PoolMetrics: TypeAlias = dict[str, Any]
ConnectionStats: TypeAlias = dict[str, Any]
ConnectionMetrics: TypeAlias = dict[str, Any]

# Operation types
OperationResult: TypeAlias = MongoResult | RedisResult
OperationOptions: TypeAlias = MongoOptions | RedisOptions
OperationSession: TypeAlias = MongoSession | RedisSession

# Callback types
ErrorCallback: TypeAlias = Any  # Will be replaced with proper type
SuccessCallback: TypeAlias = Any  # Will be replaced with proper type
HealthCallback: TypeAlias = Any  # Will be replaced with proper type
