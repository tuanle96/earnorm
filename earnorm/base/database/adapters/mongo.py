"""MongoDB adapter implementation.

This module provides MongoDB adapter implementation.
It handles the conversion between string IDs (used by models) and ObjectId (used by MongoDB).

ID Handling:
    - Models use string IDs for database-agnostic operations
    - MongoDB uses ObjectId internally
    - This adapter handles the conversion between these formats:
        - String ID -> ObjectId when sending to MongoDB
        - ObjectId -> String ID when receiving from MongoDB

    Examples:
        >>> # String ID to ObjectId (when writing to MongoDB)
        >>> object_id = adapter._to_object_id("507f1f77bcf86cd799439011")
        >>> print(object_id)  # ObjectId("507f1f77bcf86cd799439011")

        >>> # ObjectId to String ID (when reading from MongoDB)
        >>> str_id = adapter._to_string_id(ObjectId("507f1f77bcf86cd799439011"))
        >>> print(str_id)  # "507f1f77bcf86cd799439011"
"""

import logging
from typing import Any, Dict, List, Optional, Protocol, Type, TypeVar, Union

from bson import ObjectId
from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)
from pymongo.operations import DeleteOne, InsertOne, ReplaceOne, UpdateMany, UpdateOne
from pymongo.results import BulkWriteResult, DeleteResult, InsertOneResult, UpdateResult

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

ModelT = TypeVar("ModelT", bound=DatabaseModel)


class LoggerProtocol(Protocol):
    """Protocol for logger interface."""

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def error(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def info(self, msg: str, *args: Any, **kwargs: Any) -> None: ...


class MongoAdapter(DatabaseAdapter[ModelT]):
    """MongoDB adapter implementation.

    This class provides MongoDB-specific implementation of the database adapter interface.
    It handles all database operations including querying, transactions, and CRUD operations.

    ID Handling:
        - Models use string IDs for database-agnostic operations
        - MongoDB uses ObjectId internally
        - This adapter handles the conversion between these formats

    Attributes:
        pool_name: Name of the pool in registry (default: mongodb)
        logger: Logger instance for this class
    """

    logger: LoggerProtocol = logging.getLogger(__name__)

    def __init__(self, pool_name: str = "mongodb") -> None:
        """Initialize MongoDB adapter.

        Args:
            pool_name: Name of the pool in registry (default: mongodb)
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
            self.logger.debug("Connecting to MongoDB with pool: %s", self._pool_name)

            # Get pool registry from container
            pool_registry = await container.get("pool_registry")
            if not pool_registry:
                self.logger.error("Pool registry not initialized")
                raise RuntimeError("Pool registry not initialized")

            # Get pool from registry (sync operation)
            self._pool = pool_registry.get(self._pool_name)
            if not self._pool:
                self.logger.error("Pool not found: %s", self._pool_name)
                raise RuntimeError(f"Pool {self._pool_name} not found")

            self.logger.debug("Got pool from registry: %s", self._pool_name)

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

            self.logger.info(
                "Successfully connected to MongoDB with pool: %s",
                self._pool_name,
            )

        except Exception as e:
            self.logger.error("Failed to connect to MongoDB: %s", str(e))
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

    def _to_object_id(self, str_id: Optional[str]) -> Optional[ObjectId]:
        """Convert string ID to MongoDB ObjectId.

        Args:
            str_id: String ID to convert

        Returns:
            ObjectId if conversion successful, None otherwise

        Examples:
            >>> object_id = adapter._to_object_id("507f1f77bcf86cd799439011")
            >>> print(object_id)  # ObjectId("507f1f77bcf86cd799439011")
        """
        if not str_id:
            return None
        try:
            return ObjectId(str_id)
        except Exception as e:
            self.logger.warning(f"Failed to convert string ID to ObjectId: {e}")
            return None

    def _to_string_id(self, object_id: Any) -> Optional[str]:
        """Convert MongoDB ObjectId to string ID.

        Args:
            object_id: ObjectId to convert

        Returns:
            String ID if conversion successful, None otherwise

        Examples:
            >>> str_id = adapter._to_string_id(ObjectId("507f1f77bcf86cd799439011"))
            >>> print(str_id)  # "507f1f77bcf86cd799439011"
        """
        if not object_id:
            return None
        try:
            return str(object_id)
        except Exception as e:
            self.logger.warning(f"Failed to convert ObjectId to string: {e}")
            return None

    async def _convert_document(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Convert MongoDB document to internal format.

        This method handles the conversion of MongoDB specific types to Python types,
        particularly focusing on ObjectId to string conversion for the _id field.
        It preserves all other fields in the document.

        Args:
            doc: MongoDB document to convert

        Returns:
            Converted document with standardized types and all fields preserved

        Examples:
            >>> doc = {
            ...     "_id": ObjectId("507f1f77bcf86cd799439011"),
            ...     "name": "John",
            ...     "email": "john@example.com",
            ...     "age": 25
            ... }
            >>> converted = await adapter._convert_document(doc)
            >>> print(converted)
            {
                "id": "507f1f77bcf86cd799439011",
                "name": "John",
                "email": "john@example.com",
                "age": 25
            }
        """
        try:
            # Create a copy of the document to avoid modifying the original
            converted_doc = doc.copy()

            # Convert _id to id if present
            if "_id" in converted_doc:
                str_id = self._to_string_id(converted_doc.pop("_id"))
                converted_doc["id"] = str_id
                self.logger.debug(f"Converted _id to id: {str_id}")

            return converted_doc
        except Exception as e:
            self.logger.error(f"Failed to convert document: {e}", exc_info=True)
            # Keep original document but set id to None to indicate conversion error
            converted_doc = doc.copy()
            converted_doc["id"] = None
            return converted_doc

    async def query(self, model_type: Type[ModelT]) -> MongoQuery[ModelT]:
        """Create query for model type.

        Args:
            model_type: Model class to query

        Returns:
            MongoQuery instance configured for the model

        Examples:
            >>> query = await adapter.query(User)
            >>> users = await query.filter({"age": {"$gt": 18}}).all()
        """
        collection = await self.get_collection(self._get_collection_name(model_type))
        query = MongoQuery[ModelT](
            collection=collection,
            model_type=model_type,
        )
        query.add_postprocessor(self._convert_document)
        return query

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

        Raises:
            ValueError: If failed to get valid ID after insertion
        """
        collection: AsyncIOMotorCollection[JsonDict] = await self.get_collection(
            self._get_collection_name(type(model))
        )
        values = await model.to_dict()
        result: InsertOneResult = await collection.insert_one(values)
        str_id = self._to_string_id(result.inserted_id)
        if not str_id:
            raise ValueError("Failed to get valid ID after insertion")
        model.id = str_id
        return model

    async def insert_many(self, models: List[ModelT]) -> List[ModelT]:
        """Insert multiple models into database.

        Args:
            models: Models to insert

        Returns:
            Inserted models with IDs

        Raises:
            ValueError: If failed to get valid ID for any model
        """
        if not models:
            return []

        collection: AsyncIOMotorCollection[JsonDict] = await self.get_collection(
            self._get_collection_name(type(models[0]))
        )
        values: List[JsonDict] = []
        for model in models:
            model_dict = await model.to_dict()
            values.append(model_dict)
        result = await collection.insert_many(values)
        for model, _id in zip(models, result.inserted_ids):
            str_id = self._to_string_id(_id)
            if not str_id:
                raise ValueError(f"Failed to get valid ID for model: {model}")
            model.id = str_id
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
        return self._to_string_id(result.inserted_id)

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
        values = await model.to_dict()
        object_id = self._to_object_id(model.id)
        if not object_id:
            raise ValueError(f"Invalid MongoDB ObjectId: {model.id}")

        await collection.update_one({"_id": object_id}, {"$set": values})
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

        collection: AsyncIOMotorCollection[Dict[str, Any]] = self._get_collection(
            type(models[0])
        )

        operations: List[
            Union[
                InsertOne[Dict[str, Any]],
                UpdateOne,
                DeleteOne,
                ReplaceOne[Dict[str, Any]],
                UpdateMany,
            ]
        ] = []
        for model in models:
            if not model.id:
                continue

            object_id = self._to_object_id(model.id)
            if not object_id:
                self.logger.warning(f"Skipping update for invalid ID: {model.id}")
                continue

            values = await model.to_dict()
            operations.append(UpdateOne({"_id": object_id}, {"$set": values}))

        if operations:
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
        object_id = self._to_object_id(model.id)
        if not object_id:
            raise ValueError(f"Invalid MongoDB ObjectId: {model.id}")

        await collection.delete_one({"_id": object_id})

    async def delete_many(self, models: List[ModelT]) -> None:
        """Delete multiple models in database.

        Args:
            models: Models to delete

        Raises:
            ValueError: If any model has no ID
        """
        if not models:
            return

        collection: AsyncIOMotorCollection[JsonDict] = await self.get_collection(
            self._get_collection_name(type(models[0]))
        )

        object_ids: List[ObjectId] = []
        for model in models:
            if not model.id:
                raise ValueError("Model has no ID")

            object_id = self._to_object_id(model.id)
            if not object_id:
                raise ValueError(f"Invalid MongoDB ObjectId: {model.id}")
            object_ids.append(object_id)

        await collection.delete_many({"_id": {"$in": object_ids}})

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

    async def bulk_write(
        self, table_name: str, operations: List[Dict[str, Dict[str, Any]]]
    ) -> BulkWriteResult:
        """Execute bulk write operations.

        Args:
            table_name: Table name
            operations: List of write operations in format:
                [{"filter": {...}, "update": {...}}]

        Returns:
            Result of bulk write operation
        """
        collection: AsyncIOMotorCollection[Dict[str, Any]] = await self.get_collection(
            table_name
        )

        # Convert dict operations to UpdateOne objects
        bulk_ops: List[UpdateOne] = [
            UpdateOne(op["filter"], op["update"]) for op in operations
        ]

        return await collection.bulk_write(bulk_ops)  # type: ignore

    async def convert_id(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """MongoDB-specific ID conversion.

        This method standardizes the ID field in MongoDB documents by converting
        ObjectId to string and ensuring consistent field naming (id vs _id).

        Args:
            document: Document to convert

        Returns:
            Document with standardized id field

        Examples:
            >>> doc = {"_id": ObjectId("507f1f77bcf86cd799439011"), "name": "John"}
            >>> converted = await adapter.convert_id(doc)
            >>> print(converted)
            {"id": "507f1f77bcf86cd799439011", "name": "John"}
        """
        try:
            if "_id" in document:
                # Convert ObjectId to string and update field name
                document["id"] = str(document.pop("_id"))
                self.logger.debug(f"Converted _id to id: {document['id']}")
            return document
        except Exception as e:
            self.logger.error(f"Failed to convert document ID: {e}", exc_info=True)
            # Keep original document but set id to None to indicate conversion error
            document["id"] = None
            return document
