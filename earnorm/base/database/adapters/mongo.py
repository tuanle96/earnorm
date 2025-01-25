"""MongoDB adapter implementation.

This module provides MongoDB adapter implementation.

Examples:
    >>> # Create adapter
    >>> adapter = MongoAdapter(uri="mongodb://localhost:27017", database="test")
    >>> 
    >>> # Query using domain expressions
    >>> users = adapter.query(User).filter(
    ...     DomainBuilder()
    ...     .field("age").greater_than(18)
    ...     .and_()
    ...     .field("status").equals("active")
    ...     .build()
    ... ).all()
    >>> 
    >>> # Using transactions
    >>> with adapter.transaction(User) as tx:
    ...     user = User(name="John", age=25)
    ...     tx.insert(user)
    ...     tx.commit()
"""

from typing import Any, Dict, List, Optional, Type, TypeVar

from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)
from pymongo.collection import Collection
from pymongo.database import Database

from earnorm.base.database.adapter import DatabaseAdapter
from earnorm.base.database.query.backends.mongo.builder import MongoQueryBuilder
from earnorm.base.database.query.backends.mongo.query import MongoQuery
from earnorm.base.database.transaction.backends.mongo import MongoTransactionManager
from earnorm.pool.backends.mongo import MongoPool
from earnorm.pool.registry import PoolRegistry
from earnorm.types import DatabaseModel, JsonDict

ModelT = TypeVar("ModelT", bound=DatabaseModel)


class MongoAdapter(DatabaseAdapter[ModelT]):
    """MongoDB adapter implementation.

    This class provides MongoDB-specific implementation of the database adapter interface.
    It handles all database operations including querying, transactions, and CRUD operations.

    Attributes:
        uri: MongoDB connection URI
        database: Database name
        options: Additional connection options
        pool_name: Name of the pool in registry
        min_pool_size: Minimum pool size
        max_pool_size: Maximum pool size
        max_idle_time: Maximum connection idle time in seconds
        max_lifetime: Maximum connection lifetime in seconds
    """

    def __init__(
        self,
        uri: str,
        database: str,
        options: Optional[Dict[str, Any]] = None,
        pool_name: str = "default",
        min_pool_size: int = 1,
        max_pool_size: int = 10,
        max_idle_time: int = 300,
        max_lifetime: int = 3600,
    ) -> None:
        """Initialize MongoDB adapter.

        Args:
            uri: MongoDB connection URI
            database: Database name
            options: Additional connection options
            pool_name: Name of the pool in registry
            min_pool_size: Minimum pool size
            max_pool_size: Maximum pool size
            max_idle_time: Maximum connection idle time in seconds
            max_lifetime: Maximum connection lifetime in seconds

        Raises:
            ValueError: If URI or database name is empty
        """
        if not uri:
            raise ValueError("MongoDB URI cannot be empty")
        if not database:
            raise ValueError("Database name cannot be empty")

        super().__init__()
        self._uri = uri
        self._database = database
        self._options = options or {}
        self._pool_name = pool_name
        self._min_pool_size = min_pool_size
        self._max_pool_size = max_pool_size
        self._max_idle_time = max_idle_time
        self._max_lifetime = max_lifetime
        self._pool: Optional[
            MongoPool[
                AsyncIOMotorDatabase[Dict[str, Any]], AsyncIOMotorCollection[JsonDict]
            ]
        ] = None
        self._sync_db: Optional[Database[Dict[str, Any]]] = None

    async def connect(self) -> None:
        """Connect to MongoDB.

        Raises:
            ConnectionError: If connection fails
        """
        try:
            # Create and initialize pool
            self._pool = MongoPool[
                AsyncIOMotorDatabase[Dict[str, Any]], AsyncIOMotorCollection[JsonDict]
            ](
                uri=self._uri,
                database=self._database,
                min_size=self._min_pool_size,
                max_size=self._max_pool_size,
                max_idle_time=self._max_idle_time,
                max_lifetime=self._max_lifetime,
                **self._options,
            )
            await self._pool.init()

            # Register pool in registry
            PoolRegistry().register(self._pool_name, self._pool)

            # Get sync database for transactions
            client = AsyncIOMotorClient[Dict[str, Any]](self._uri, **self._options)
            self._sync_db = Database(client.delegate, self._database)

        except Exception as e:
            raise ConnectionError(f"Failed to connect to MongoDB: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from MongoDB."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
        if self._sync_db is not None:
            self._sync_db.client.close()
            self._sync_db = None

    async def get_collection(self, name: str) -> AsyncIOMotorCollection[JsonDict]:
        """Get MongoDB collection.

        Args:
            name: Collection name

        Returns:
            MongoDB collection

        Raises:
            ValueError: If collection name is empty
            RuntimeError: If not connected
        """
        if not name:
            raise ValueError("Collection name cannot be empty")
        if self._pool is None:
            raise RuntimeError("Not connected to MongoDB")

        # Acquire connection from pool
        conn = await (await self._pool.acquire())
        try:
            # Get collection from connection
            collection = conn.get_collection(name)
            return collection
        finally:
            # Release connection back to pool
            await self._pool.release(conn)

    def _get_collection(self, model_type: Type[ModelT]) -> Collection[Dict[str, Any]]:
        """Get MongoDB collection for model type.

        Args:
            model_type: Type of model

        Returns:
            MongoDB collection

        Raises:
            RuntimeError: If not connected
        """
        if self._sync_db is None:
            raise RuntimeError("Not connected to MongoDB")
        return self._sync_db[model_type.__collection__]

    async def query_builder(
        self, model_type: Type[ModelT], collection: Optional[str] = None
    ) -> MongoQueryBuilder[ModelT]:
        """Create query builder.

        Args:
            model_type: Model type to query
            collection: Optional collection name (defaults to model name)

        Returns:
            MongoDB query builder

        Raises:
            ValueError: If collection name is empty
            RuntimeError: If not connected
        """
        if not collection:
            collection = model_type.__collection__
        return MongoQueryBuilder(
            collection=await self.get_collection(collection),
            model_type=model_type,
        )

    async def query(self, model_type: Type[ModelT]) -> MongoQuery[ModelT]:
        """Create query for model type.

        Args:
            model_type: Type of model to query

        Returns:
            Query builder
        """
        return MongoQuery[ModelT](
            collection=await self.get_collection(model_type.__collection__),
            model_cls=model_type,
        )

    async def transaction(
        self, model_type: Type[ModelT]
    ) -> MongoTransactionManager[ModelT]:
        """Create new transaction.

        Args:
            model_type: Type of model to use in transaction

        Returns:
            Transaction context manager

        Raises:
            RuntimeError: If not connected
        """
        if self._sync_db is None:
            raise RuntimeError("Not connected to MongoDB")
        manager: MongoTransactionManager[ModelT] = MongoTransactionManager(
            self._sync_db
        )
        manager.set_model_type(model_type)
        return manager

    async def insert(self, model: ModelT) -> ModelT:
        """Insert model into database.

        Args:
            model: Model to insert

        Returns:
            Inserted model with ID
        """
        collection = self._get_collection(type(model))
        result = collection.insert_one(model.to_dict())
        model.id = result.inserted_id
        return model

    async def insert_many(self, models: List[ModelT]) -> List[ModelT]:
        """Insert multiple models into database.

        Args:
            models: Models to insert

        Returns:
            Inserted models with IDs
        """
        if not models:
            return []
        collection = self._get_collection(type(models[0]))
        result = collection.insert_many([model.to_dict() for model in models])
        for model, id_ in zip(models, result.inserted_ids):
            model.id = id_
        return models

    async def update(self, model: ModelT) -> ModelT:
        """Update model in database.

        Args:
            model: Model to update

        Returns:
            Updated model

        Raises:
            ValueError: If model has no ID
        """
        if not model.id:
            raise ValueError("Model has no ID")
        collection = self._get_collection(type(model))
        collection.update_one({"_id": model.id}, {"$set": model.to_dict()})
        return model

    async def update_many(self, models: List[ModelT]) -> List[ModelT]:
        """Update multiple models in database.

        Args:
            models: Models to update

        Returns:
            Updated models

        Raises:
            ValueError: If any model has no ID
        """
        if not models:
            return []
        for model in models:
            if not model.id:
                raise ValueError("Model has no ID")
        collection = self._get_collection(type(models[0]))
        for model in models:
            collection.update_one({"_id": model.id}, {"$set": model.to_dict()})
        return models

    async def delete(self, model: ModelT) -> None:
        """Delete model from database.

        Args:
            model: Model to delete

        Raises:
            ValueError: If model has no ID
        """
        if not model.id:
            raise ValueError("Model has no ID")
        collection = self._get_collection(type(model))
        collection.delete_one({"_id": model.id})

    async def delete_many(self, models: List[ModelT]) -> None:
        """Delete multiple models from database.

        Args:
            models: Models to delete

        Raises:
            ValueError: If any model has no ID
        """
        if not models:
            return
        for model in models:
            if not model.id:
                raise ValueError("Model has no ID")
        collection = self._get_collection(type(models[0]))
        collection.delete_many({"_id": {"$in": [model.id for model in models]}})
