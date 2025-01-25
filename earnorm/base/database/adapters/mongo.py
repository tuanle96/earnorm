"""MongoDB adapter implementation.

This module provides MongoDB adapter implementation.

Examples:
    >>> # Create adapter
    >>> adapter = MongoAdapter(uri="mongodb://localhost:27017", database="test")
    >>> await adapter.init()
    >>>
    >>> # Query using domain expressions
    >>> users = await adapter.query(User).filter(
    ...     DomainBuilder()
    ...     .field("age").greater_than(18)
    ...     .and_()
    ...     .field("status").equals("active")
    ...     .build()
    ... ).all()
    >>>
    >>> # Using transactions
    >>> async with adapter.transaction(User) as tx:
    ...     user = User(name="John", age=25)
    ...     await tx.insert(user)
    ...     await tx.commit()
"""

from typing import Any, Dict, List, Optional, Type, TypeVar

from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)
from pymongo.collection import Collection
from pymongo.database import Database

from earnorm.base.database.async_adapter import AsyncDatabaseAdapter
from earnorm.base.database.query.backends.mongo.builder import MongoQueryBuilder
from earnorm.base.database.query.backends.mongo.query import MongoQuery
from earnorm.base.database.transaction.backends.mongo import MongoTransactionManager
from earnorm.di import container
from earnorm.pool.backends.mongo import MongoPool
from earnorm.pool.protocols import AsyncConnectionProtocol
from earnorm.types import DatabaseModel, JsonDict

ModelT = TypeVar("ModelT", bound=DatabaseModel)


class MongoAdapter(AsyncDatabaseAdapter[ModelT]):
    """MongoDB adapter implementation.

    This class provides MongoDB-specific implementation of the database adapter interface.
    It handles all database operations including querying, transactions, and CRUD operations.

    Attributes:
        pool_name: Name of the pool in registry
    """

    def __init__(self, pool_name: str = "default") -> None:
        """Initialize MongoDB adapter.

        Args:
            pool_name: Name of the pool in registry
        """
        super().__init__()
        self._pool_name = pool_name
        self._pool: Optional[
            MongoPool[
                AsyncIOMotorDatabase[Dict[str, Any]], AsyncIOMotorCollection[JsonDict]
            ]
        ] = None
        self._sync_db: Optional[Database[Dict[str, Any]]] = None

    async def init(self) -> None:
        """Initialize the adapter.

        This method should be called before using the adapter.
        It initializes the pool and sync database connection.
        """
        await self.connect()

    async def close(self) -> None:
        """Close the adapter.

        This method should be called when the adapter is no longer needed.
        It cleans up the pool and sync database connection.
        """
        await self.disconnect()

    async def get_connection(
        self,
    ) -> AsyncConnectionProtocol[
        AsyncIOMotorDatabase[Dict[str, Any]], AsyncIOMotorCollection[JsonDict]
    ]:
        """Get a connection from the adapter.

        Returns:
            AsyncConnectionProtocol: A MongoDB database connection.

        Raises:
            RuntimeError: If not connected to MongoDB.
        """
        if self._pool is None:
            raise RuntimeError("Not connected to MongoDB")
        conn = await self._pool.acquire()
        return conn

    async def connect(self) -> None:
        """Connect to MongoDB.

        Raises:
            ConnectionError: If connection fails
        """
        try:
            # Get pool from registry
            pool_registry = await container.get("pool_registry")
            if not pool_registry:
                raise RuntimeError("Pool registry not initialized")

            self._pool = await pool_registry.get(self._pool_name)
            if not self._pool:
                raise RuntimeError(f"Pool {self._pool_name} not found")

            # Get sync database for transactions
            client = AsyncIOMotorClient[Dict[str, Any]](getattr(self._pool, "_uri"))
            self._sync_db = Database(client.delegate, getattr(self._pool, "_database"))

        except Exception as e:
            raise ConnectionError(f"Failed to connect to MongoDB: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from MongoDB."""
        if self._sync_db is not None:
            self._sync_db.client.close()
            self._sync_db = None
        self._pool = None

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
        conn = await self._pool.acquire()
        try:
            # Get collection from connection
            collection = conn.get_collection(name)
            return collection
        finally:
            # Release connection back to pool
            await self._pool.release(conn)

    def _get_collection_name(self, model_type: Type[ModelT]) -> str:
        """Get collection name for model type.

        Args:
            model_type: Type of model

        Returns:
            Collection name

        Raises:
            ValueError: If model has no table or name
        """
        # Use getattr to access protected attributes
        table = getattr(model_type, "_table", None)
        name = getattr(model_type, "_name", None)
        if not (table or name):
            raise ValueError(f"Model {model_type} has no table or name")
        return str(table) if table else str(name)

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
        return self._sync_db[self._get_collection_name(model_type)]

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
            collection = self._get_collection_name(model_type)
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
            collection=await self.get_collection(self._get_collection_name(model_type)),
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

        Raises:
            ValueError: If model has no table or name
            RuntimeError: If not connected to MongoDB
        """
        collection = await self.get_collection(self._get_collection_name(type(model)))
        result = await collection.insert_one(model.to_dict())
        model.id = result.inserted_id
        return model

    async def insert_many(self, models: List[ModelT]) -> List[ModelT]:
        """Insert multiple models into database.

        Args:
            models: Models to insert

        Returns:
            Inserted models with IDs

        Raises:
            ValueError: If any model has no table or name
            RuntimeError: If not connected to MongoDB
        """
        if not models:
            return []

        collection = await self.get_collection(
            self._get_collection_name(type(models[0]))
        )
        docs = [model.to_dict() for model in models]
        result = await collection.insert_many(docs)

        for model, id in zip(models, result.inserted_ids):
            model.id = id
        return models

    async def update(self, model: ModelT) -> ModelT:
        """Update model in database.

        Args:
            model: Model to update

        Returns:
            Updated model

        Raises:
            ValueError: If model has no ID or no table/name
            RuntimeError: If not connected to MongoDB
        """
        if not model.id:
            raise ValueError("Model has no ID")

        collection = await self.get_collection(self._get_collection_name(type(model)))
        await collection.update_one({"_id": model.id}, {"$set": model.to_dict()})
        return model

    async def update_many(self, models: List[ModelT]) -> List[ModelT]:
        """Update multiple models in database.

        Args:
            models: Models to update

        Returns:
            Updated models

        Raises:
            ValueError: If any model has no ID or no table/name
            RuntimeError: If not connected to MongoDB
        """
        if not models:
            return []

        collection = await self.get_collection(
            self._get_collection_name(type(models[0]))
        )

        # Check all models have IDs
        for model in models:
            if not model.id:
                raise ValueError("Model has no ID")

        # Update each model individually since bulk_write has type issues
        for model in models:
            await collection.update_one({"_id": model.id}, {"$set": model.to_dict()})
        return models

    async def delete(self, model: ModelT) -> None:
        """Delete model from database.

        Args:
            model: Model to delete

        Raises:
            ValueError: If model has no ID or no table/name
            RuntimeError: If not connected to MongoDB
        """
        if not model.id:
            raise ValueError("Model has no ID")

        collection = await self.get_collection(self._get_collection_name(type(model)))
        await collection.delete_one({"_id": model.id})

    async def delete_many(self, models: List[ModelT]) -> None:
        """Delete multiple models from database.

        Args:
            models: Models to delete

        Raises:
            ValueError: If any model has no ID or no table/name
            RuntimeError: If not connected to MongoDB
        """
        if not models:
            return

        collection = await self.get_collection(
            self._get_collection_name(type(models[0]))
        )

        # Check all models have IDs
        for model in models:
            if not model.id:
                raise ValueError("Model has no ID")

        # Bulk delete
        ids = [model.id for model in models]
        await collection.delete_many({"_id": {"$in": ids}})
