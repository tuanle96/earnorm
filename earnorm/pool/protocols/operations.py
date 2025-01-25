"""Operation protocols for database operations.

This module defines protocols for database operations including:
- Basic CRUD operations
- Transaction management
- Session management
- Bulk operations
"""

from enum import Enum
from typing import (
    Any,
    AsyncContextManager,
    Dict,
    List,
    Optional,
    Protocol,
    Set,
    TypeVar,
    Union,
)

from earnorm.exceptions import DatabaseError

__all__ = [
    "TransactionProtocol",
    "SessionProtocol",
    "BulkOperationsProtocol",
    "DatabaseOperationsProtocol",
    "DatabaseError",  # Used in docstrings
    "MongoOperation",
    "RedisOperation",
    "MongoDocument",
    "MongoFilter",
    "MongoUpdate",
    "MongoProjection",
    "MongoSort",
    "RedisKey",
    "RedisValue",
    "RedisHash",
    "RedisList",
    "RedisSet",
    "RedisZSet",
]

T = TypeVar("T")


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


class TransactionProtocol(Protocol):
    """Protocol for transaction management."""

    async def start_transaction(self) -> None:
        """Start a new transaction."""
        ...

    async def commit_transaction(self) -> None:
        """Commit the current transaction."""
        ...

    async def abort_transaction(self) -> None:
        """Abort/rollback the current transaction."""
        ...

    async def in_transaction(self) -> bool:
        """Check if currently in a transaction.

        Returns:
            bool: True if in a transaction, False otherwise
        """
        ...


class SessionProtocol(Protocol):
    """Protocol for session management."""

    async def start_session(self) -> AsyncContextManager[Any]:
        """Start a new session.

        Returns:
            AsyncContextManager: Session context manager
        """
        ...

    async def end_session(self) -> None:
        """End the current session."""
        ...

    async def get_session_id(self) -> str:
        """Get the current session ID.

        Returns:
            str: Current session ID

        Raises:
            DatabaseError: If no active session
        """
        ...


class BulkOperationsProtocol(Protocol):
    """Protocol for bulk operations."""

    async def bulk_write(
        self,
        operations: List[Dict[str, Any]],
        ordered: bool = True,
    ) -> Dict[str, Any]:
        """Execute multiple write operations.

        Args:
            operations: List of write operations
            ordered: Whether to execute operations in order

        Returns:
            Dict[str, Any]: Result of bulk write operation

        Raises:
            DatabaseError: If bulk write fails
        """
        ...

    async def bulk_read(
        self,
        operations: List[Dict[str, Any]],
        ordered: bool = True,
    ) -> List[Any]:
        """Execute multiple read operations.

        Args:
            operations: List of read operations
            ordered: Whether to execute operations in order

        Returns:
            List[Any]: Results of bulk read operations

        Raises:
            DatabaseError: If bulk read fails
        """
        ...


class DatabaseOperationsProtocol(Protocol):
    """Protocol for database operations."""

    async def insert_one(
        self,
        document: Dict[str, Any],
        session: Optional[Any] = None,
    ) -> str:
        """Insert a single document.

        Args:
            document: Document to insert
            session: Optional session for the operation

        Returns:
            str: ID of inserted document

        Raises:
            DatabaseError: If insert fails
        """
        ...

    async def insert_many(
        self,
        documents: List[Dict[str, Any]],
        ordered: bool = True,
        session: Optional[Any] = None,
    ) -> List[str]:
        """Insert multiple documents.

        Args:
            documents: Documents to insert
            ordered: Whether to insert in order
            session: Optional session for the operation

        Returns:
            List[str]: IDs of inserted documents

        Raises:
            DatabaseError: If insert fails
        """
        ...

    async def find_one(
        self,
        filter: Dict[str, Any],
        projection: Optional[Dict[str, Any]] = None,
        session: Optional[Any] = None,
    ) -> Optional[Dict[str, Any]]:
        """Find a single document.

        Args:
            filter: Query filter
            projection: Optional projection
            session: Optional session for the operation

        Returns:
            Optional[Dict[str, Any]]: Found document or None

        Raises:
            DatabaseError: If find fails
        """
        ...

    async def find_many(
        self,
        filter: Dict[str, Any],
        projection: Optional[Dict[str, Any]] = None,
        sort: Optional[List[tuple[str, int]]] = None,
        skip: int = 0,
        limit: Optional[int] = None,
        session: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """Find multiple documents.

        Args:
            filter: Query filter
            projection: Optional projection
            sort: Optional sort specification
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            session: Optional session for the operation

        Returns:
            List[Dict[str, Any]]: Found documents

        Raises:
            DatabaseError: If find fails
        """
        ...

    async def update_one(
        self,
        filter: Dict[str, Any],
        update: Dict[str, Any],
        upsert: bool = False,
        session: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Update a single document.

        Args:
            filter: Query filter
            update: Update specification
            upsert: Whether to insert if not found
            session: Optional session for the operation

        Returns:
            Dict[str, Any]: Update result

        Raises:
            DatabaseError: If update fails
        """
        ...

    async def update_many(
        self,
        filter: Dict[str, Any],
        update: Dict[str, Any],
        upsert: bool = False,
        session: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Update multiple documents.

        Args:
            filter: Query filter
            update: Update specification
            upsert: Whether to insert if not found
            session: Optional session for the operation

        Returns:
            Dict[str, Any]: Update result

        Raises:
            DatabaseError: If update fails
        """
        ...

    async def delete_one(
        self,
        filter: Dict[str, Any],
        session: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Delete a single document.

        Args:
            filter: Query filter
            session: Optional session for the operation

        Returns:
            Dict[str, Any]: Delete result

        Raises:
            DatabaseError: If delete fails
        """
        ...

    async def delete_many(
        self,
        filter: Dict[str, Any],
        session: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Delete multiple documents.

        Args:
            filter: Query filter
            session: Optional session for the operation

        Returns:
            Dict[str, Any]: Delete result

        Raises:
            DatabaseError: If delete fails
        """
        ...

    async def count_documents(
        self,
        filter: Dict[str, Any],
        session: Optional[Any] = None,
    ) -> int:
        """Count documents matching filter.

        Args:
            filter: Query filter
            session: Optional session for the operation

        Returns:
            int: Number of matching documents

        Raises:
            DatabaseError: If count fails
        """
        ...

    async def aggregate(
        self,
        pipeline: List[Dict[str, Any]],
        session: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """Execute an aggregation pipeline.

        Args:
            pipeline: Aggregation pipeline
            session: Optional session for the operation

        Returns:
            List[Dict[str, Any]]: Aggregation results

        Raises:
            DatabaseError: If aggregation fails
        """
        ...
