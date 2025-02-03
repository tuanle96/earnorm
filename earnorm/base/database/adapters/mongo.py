"""MongoDB adapter implementation.

This module provides MongoDB adapter implementation.

Examples:
    >>> # Create adapter
    >>> adapter = MongoAdapter(uri="mongodb://localhost:27017", database="test")
    >>> await adapter.init()
    >>>
    >>> # Basic query
    >>> users = await adapter.query(User).filter(
    ...     DomainBuilder()
    ...     .field("age").greater_than(18)
    ...     .and_()
    ...     .field("status").equals("active")
    ...     .build()
    ... ).all()
    >>> # Join query
    >>> users = await adapter.query(User).join(Post).on(User.id == Post.user_id)
    >>> # Aggregate query
    >>> stats = await adapter.query(User).aggregate().group_by(User.age).count()
    >>> # Window query
    >>> ranked = await adapter.query(User).window().over(partition_by=[User.age]).row_number()
    >>> # Transaction
    >>> async with adapter.transaction(User) as tx:
    ...     user = User(name="John", age=25)
    ...     await tx.insert(user)
    ...     await tx.commit()
"""

import logging
from typing import Any, Dict, List, Optional, Sequence, Type, TypeVar

from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)
from pymongo.operations import UpdateOne
from pymongo.results import DeleteResult, InsertOneResult, UpdateResult

from earnorm.base.database.adapter import DatabaseAdapter
from earnorm.base.database.query.backends.mongo.operations.aggregate import (
    MongoAggregate,
)
from earnorm.base.database.query.backends.mongo.operations.join import MongoJoin
from earnorm.base.database.query.backends.mongo.query import MongoQuery
from earnorm.base.database.query.interfaces.operations.aggregate import (
    AggregateProtocol as AggregateQuery,
)
from earnorm.base.database.query.interfaces.operations.join import (
    JoinProtocol as JoinQuery,
)
from earnorm.base.database.transaction.backends.mongo import MongoTransactionManager
from earnorm.di import container
from earnorm.pool.backends.mongo import MongoPool
from earnorm.pool.protocols import AsyncConnectionProtocol
from earnorm.types import DatabaseModel, JsonDict

logger = logging.getLogger(__name__)
ModelT = TypeVar("ModelT", bound=DatabaseModel)


class MongoAdapter(DatabaseAdapter[ModelT]):
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
        self._sync_db: Optional[AsyncIOMotorDatabase[Dict[str, Any]]] = None

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
            RuntimeError: If pool registry or pool not found
        """
        try:
            logger.debug("Connecting to MongoDB with pool: %s", self._pool_name)

            # Get pool registry from container
            pool_registry = await container.get("pool_registry")
            if not pool_registry:
                logger.error("Pool registry not initialized")
                raise RuntimeError("Pool registry not initialized")

            # Get pool from registry (sync operation)
            self._pool = pool_registry.get(self._pool_name)
            if not self._pool:
                logger.error("Pool not found: %s", self._pool_name)
                raise RuntimeError(f"Pool {self._pool_name} not found")

            logger.debug("Got pool from registry: %s", self._pool_name)

            # Get client options
            client_options = getattr(self._pool, "_kwargs", {}).get("options", {})
            mapped_options = self._pool.map_client_options(client_options)

            # Create client with mapped options
            client = AsyncIOMotorClient[Dict[str, Any]](
                getattr(self._pool, "_uri"),
                **mapped_options,
            )

            # Get sync database for transactions
            self._sync_db = AsyncIOMotorDatabase(
                client, getattr(self._pool, "_database")
            )

            logger.info(
                "Successfully connected to MongoDB with pool: %s",
                self._pool_name,
            )

        except Exception as e:
            logger.error("Failed to connect to MongoDB: %s", str(e))
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
            collection: AsyncIOMotorCollection[JsonDict] = conn.get_collection(name)
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

    def _get_collection(
        self, model_type: Type[ModelT]
    ) -> AsyncIOMotorCollection[Dict[str, Any]]:
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

    async def query(self, model_type: Type[ModelT]) -> MongoQuery[ModelT]:
        """Create query for model type.

        Args:
            model_type: Type of model to query

        Returns:
            MongoDB query builder

        Examples:
            >>> # Basic query
            >>> users = await adapter.query(User).filter({"age": {"$gt": 18}})
            >>> # Join query
            >>> users = await adapter.query(User).join(Post).on(User.id == Post.user_id)
            >>> # Aggregate query
            >>> stats = await adapter.query(User).aggregate().group_by(User.age).count()
            >>> # Window query
            >>> ranked = await adapter.query(User).window().over(partition_by=[User.age]).row_number()
        """
        collection = await self.get_collection(self._get_collection_name(model_type))
        return MongoQuery[ModelT](
            collection=collection,
            model_type=model_type,
        )

    async def transaction(
        self, model_type: Type[ModelT]
    ) -> MongoTransactionManager[ModelT]:
        """Create new transaction.

        Args:
            model_type: Type of model to use in transaction

        Returns:
            Transaction context manager
        """
        if self._sync_db is None:
            raise RuntimeError("Not connected to MongoDB")

        # Create transaction manager with type hints
        manager: MongoTransactionManager[ModelT] = MongoTransactionManager(
            db=self._sync_db
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
        collection: AsyncIOMotorCollection[JsonDict] = await self.get_collection(
            self._get_collection_name(type(model))
        )
        result: InsertOneResult = await collection.insert_one(model.to_dict())
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

        collection: AsyncIOMotorCollection[JsonDict] = await self.get_collection(
            self._get_collection_name(type(models[0]))
        )
        result = await collection.insert_many([model.to_dict() for model in models])
        for model, _id in zip(models, result.inserted_ids):
            model.id = _id
        return models

    async def insert_one(self, table_name: str, values: Dict[str, Any]) -> Any:
        """Insert one document into table.

        Args:
            table_name: Table name
            values: Document values

        Returns:
            Document ID
        """
        collection: AsyncIOMotorCollection[JsonDict] = await self.get_collection(
            table_name
        )
        result: InsertOneResult = await collection.insert_one(values)
        return result.inserted_id

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

        collection: AsyncIOMotorCollection[JsonDict] = await self.get_collection(
            self._get_collection_name(type(model))
        )
        await collection.update_one({"_id": model.id}, {"$set": model.to_dict()})
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

        # Check if all models have IDs
        for model in models:
            if not model.id:
                raise ValueError("Model has no ID")

        collection: AsyncIOMotorCollection[JsonDict] = await self.get_collection(
            self._get_collection_name(type(models[0]))
        )
        # Create operations with type hints
        operations: Sequence[UpdateOne] = [
            UpdateOne(
                filter={"_id": model.id},
                update={"$set": model.to_dict()},
            )
            for model in models
        ]
        # Execute bulk write with type ignore
        await collection.bulk_write(operations)  # type: ignore
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

        collection: AsyncIOMotorCollection[JsonDict] = await self.get_collection(
            self._get_collection_name(type(model))
        )
        await collection.delete_one({"_id": model.id})

    async def delete_many(self, models: List[ModelT]) -> None:
        """Delete multiple models from database.

        Args:
            models: Models to delete

        Raises:
            ValueError: If any model has no ID
        """
        if not models:
            return

        # Check if all models have IDs
        for model in models:
            if not model.id:
                raise ValueError("Model has no ID")

        collection: AsyncIOMotorCollection[JsonDict] = await self.get_collection(
            self._get_collection_name(type(models[0]))
        )
        await collection.delete_many({"_id": {"$in": [model.id for model in models]}})

    @property
    def backend_type(self) -> str:
        """Get backend type.

        Returns:
            Backend type (e.g. 'mongodb', 'postgresql', etc.)
        """
        return "mongodb"

    async def update_many_by_filter(
        self, table_name: str, domain_filter: Dict[str, Any], values: Dict[str, Any]
    ) -> int:
        """Update multiple documents in table by filter.

        Args:
            table_name: Table name
            filter: Filter to match documents
            values: Values to update

        Returns:
            Number of documents updated
        """
        collection: AsyncIOMotorCollection[JsonDict] = await self.get_collection(
            table_name
        )
        result: UpdateResult = await collection.update_many(
            domain_filter, {"$set": values}
        )
        return result.modified_count

    async def delete_many_by_filter(
        self, table_name: str, domain_filter: Dict[str, Any]
    ) -> int:
        """Delete multiple documents in table by filter.

        Args:
            table_name: Table name
            filter: Filter to match documents

        Returns:
            Number of documents deleted
        """
        collection: AsyncIOMotorCollection[JsonDict] = await self.get_collection(
            table_name
        )
        result: DeleteResult = await collection.delete_many(domain_filter)
        return result.deleted_count

    async def get_aggregate_query(
        self, model_type: Type[ModelT]
    ) -> AggregateQuery[ModelT]:
        """Create aggregate query for model type.

        Args:
            model_type: Type of model to query

        Returns:
            Aggregate query builder instance
        """
        collection = await self.get_collection(self._get_collection_name(model_type))
        return MongoAggregate[ModelT](collection, model_type)

    async def get_join_query(self, model_type: Type[ModelT]) -> JoinQuery[ModelT, Any]:
        """Create join query for model type.

        Args:
            model_type: Type of model to query

        Returns:
            Join query builder instance
        """
        collection = await self.get_collection(self._get_collection_name(model_type))
        return MongoJoin[ModelT, DatabaseModel](collection, model_type)

    async def get_group_query(self, model_type: Type[ModelT]) -> AggregateQuery[ModelT]:
        """Create group query for model type.

        Args:
            model_type: Type of model to query

        Returns:
            Group query builder instance
        """
        collection = await self.get_collection(self._get_collection_name(model_type))
        return MongoAggregate[ModelT](collection, model_type)
