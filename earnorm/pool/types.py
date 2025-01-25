"""Pool types module.

This module contains all type hints used in the pool module.
"""

from typing import Any, Dict, List, Set, TypeVar, Union
from typing_extensions import TypeAlias

# Generic types
T = TypeVar("T")
DB = TypeVar("DB")
COLL = TypeVar("COLL")

# MongoDB types
MongoDocument: TypeAlias = Dict[str, Any]
MongoFilter: TypeAlias = Dict[str, Any]
MongoUpdate: TypeAlias = Dict[str, Any]
MongoProjection: TypeAlias = Dict[str, Union[int, bool]]
MongoSort: TypeAlias = List[tuple[str, int]]
MongoOptions: TypeAlias = Dict[str, Any]
MongoResult: TypeAlias = Dict[str, Any]
MongoSession: TypeAlias = Any  # Will be replaced with proper type

# Redis types
RedisKey: TypeAlias = str
RedisValue: TypeAlias = Union[str, int, float, bytes]
RedisHash: TypeAlias = Dict[str, RedisValue]
RedisList: TypeAlias = List[RedisValue]
RedisSet: TypeAlias = Set[RedisValue]
RedisZSet: TypeAlias = Dict[RedisValue, float]
RedisOptions: TypeAlias = Dict[str, Any]
RedisResult: TypeAlias = Union[str, int, float, bytes, List[Any], Dict[str, Any], None]
RedisSession: TypeAlias = Any  # Will be replaced with proper type

# Pool types
PoolConfig: TypeAlias = Dict[str, Any]
PoolStats: TypeAlias = Dict[str, Any]
PoolMetrics: TypeAlias = Dict[str, Any]
ConnectionStats: TypeAlias = Dict[str, Any]
ConnectionMetrics: TypeAlias = Dict[str, Any]

# Operation types
OperationResult: TypeAlias = Union[MongoResult, RedisResult]
OperationOptions: TypeAlias = Union[MongoOptions, RedisOptions]
OperationSession: TypeAlias = Union[MongoSession, RedisSession]

# Callback types
ErrorCallback: TypeAlias = Any  # Will be replaced with proper type
SuccessCallback: TypeAlias = Any  # Will be replaced with proper type
HealthCallback: TypeAlias = Any  # Will be replaced with proper type
