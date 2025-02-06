"""MongoDB adapter implementation.

This module provides MongoDB adapter implementation.
It handles the conversion between string IDs (used by models) and ObjectId (used by MongoDB).
"""

import json
import logging
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import (
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Protocol,
    Type,
    TypeVar,
    Union,
    get_args,
    get_origin,
    overload,
)

from bson import ObjectId
from bson.decimal128 import Decimal128
from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)
from pymongo.operations import DeleteOne, InsertOne, UpdateOne

from earnorm.base.database.adapter import DatabaseAdapter, FieldType
from earnorm.base.database.query.backends.mongo.operations.aggregate import (
    MongoAggregate,
)
from earnorm.base.database.query.backends.mongo.operations.join import MongoJoin
from earnorm.base.database.query.backends.mongo.query import MongoQuery
from earnorm.base.database.query.core.query import BaseQuery
from earnorm.base.database.query.interfaces.operations.aggregate import (
    AggregateProtocol as AggregateQuery,
)
from earnorm.base.database.query.interfaces.operations.join import (
    JoinProtocol as JoinQuery,
)
from earnorm.base.database.transaction.backends.mongo import MongoTransactionManager
from earnorm.di import container
from earnorm.exceptions import DatabaseError
from earnorm.pool.backends.mongo import MongoPool
from earnorm.pool.protocols import AsyncConnectionProtocol
from earnorm.types import DatabaseModel, JsonDict

ModelT = TypeVar("ModelT", bound=DatabaseModel)
T = TypeVar("T")

# Type mapping for field conversions
TYPE_MAPPING = {
    "string": str,
    "integer": int,
    "float": float,
    "decimal": Decimal,
    "boolean": bool,
    "datetime": datetime,
    "date": date,
    "array": list,
    "json": dict,
}


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
        name = getattr(model_type, "_name", None)
        table = getattr(model_type, "_table", None)
        if not (table or name):
            raise ValueError(f"Model {model_type} has no table or name")
        return str(table) if table else str(name)

    def _get_collection(
        self, model_type: Union[Type[ModelT], str]
    ) -> AsyncIOMotorCollection[Dict[str, Any]]:
        """Get MongoDB collection for model type or collection name.

        Args:
            model_type: Type of model or collection name

        Returns:
            MongoDB collection

        Raises:
            RuntimeError: If not connected
        """
        if self._sync_db is None:
            raise RuntimeError("Not connected to MongoDB")

        collection_name = (
            self._get_collection_name(model_type)
            if isinstance(model_type, type)
            else str(model_type)
        )
        return self._sync_db[collection_name]

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

    @overload
    async def query(
        self, model_type: Type[ModelT], query_type: Literal["base"] = "base"
    ) -> BaseQuery[ModelT]: ...

    @overload
    async def query(
        self, model_type: Type[ModelT], query_type: Literal["aggregate"]
    ) -> AggregateQuery[ModelT]: ...

    @overload
    async def query(
        self, model_type: Type[ModelT], query_type: Literal["join"]
    ) -> JoinQuery[ModelT, Any]: ...

    async def query(
        self,
        model_type: Type[ModelT],
        query_type: Literal["base", "aggregate", "join"] = "base",
    ) -> Union[BaseQuery[ModelT], AggregateQuery[ModelT], JoinQuery[ModelT, Any]]:
        """Create query builder of specified type."""
        collection = self._get_collection(self._get_collection_name(model_type))

        if query_type == "base":
            query = MongoQuery[ModelT](collection=collection, model_type=model_type)
            query.add_postprocessor(self._convert_document)
            return query
        elif query_type == "aggregate":
            return MongoAggregate[ModelT](collection, model_type)
        elif query_type == "join":
            return MongoJoin[ModelT, DatabaseModel](collection, model_type)
        else:
            raise ValueError(f"Unsupported query type: {query_type}")

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

    @overload
    async def create(self, model_type: Type[ModelT], values: Dict[str, Any]) -> str: ...

    @overload
    async def create(
        self, model_type: Type[ModelT], values: List[Dict[str, Any]]
    ) -> List[str]: ...

    async def create(
        self,
        model_type: Type[ModelT],
        values: Union[Dict[str, Any], List[Dict[str, Any]]],
    ) -> Union[str, List[str]]:
        """Create one or multiple records."""
        try:
            collection = self._get_collection(model_type)

            # Handle single record
            if isinstance(values, dict):
                result = await collection.insert_one(values)
                return str(result.inserted_id)

            # Handle multiple records
            result = await collection.insert_many(values)
            return [str(id) for id in result.inserted_ids]

        except Exception as e:
            self.logger.error(f"Failed to create records: {e}")
            raise DatabaseError(
                message=f"Failed to create records: {e}", backend="mongodb"
            ) from e

    @property
    def backend_type(self) -> str:
        """Get backend type.

        Returns:
            Backend type (e.g. 'mongodb', 'postgresql', etc.)
        """
        return "mongodb"

    @overload
    async def update(self, model: ModelT) -> ModelT: ...

    @overload
    async def update(
        self,
        model: Type[ModelT],
        filter_or_ops: Dict[str, Any],
        values: Dict[str, Any],
    ) -> int: ...

    @overload
    async def update(
        self,
        model: Type[ModelT],
        filter_or_ops: List[Dict[str, Any]],
    ) -> Dict[str, int]: ...

    async def update(
        self,
        model: Union[ModelT, Type[ModelT]],
        filter_or_ops: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,
        values: Optional[Dict[str, Any]] = None,
    ) -> Union[ModelT, int, Dict[str, int]]:
        """Update one or multiple records."""
        try:
            # Case 1: Update single model instance
            if isinstance(model, DatabaseModel):
                if not model.id:
                    raise ValueError("Model has no ID")

                collection = self._get_collection(type(model))
                object_id = self._to_object_id(model.id)
                if not object_id:
                    raise ValueError(f"Invalid MongoDB ObjectId: {model.id}")

                values_dict = await model.to_dict()
                await collection.update_one({"_id": object_id}, {"$set": values_dict})
                return model

            # Case 2: Update multiple records by filter
            if isinstance(filter_or_ops, dict) and values:
                collection = self._get_collection(model)
                result = await collection.update_many(filter_or_ops, {"$set": values})
                return result.modified_count

            # Case 3: Bulk operations
            if isinstance(filter_or_ops, list):
                collection = self._get_collection(model)
                operations: List[
                    Union[UpdateOne, InsertOne[Dict[str, Any]], DeleteOne]
                ] = []
                stats = {"updated": 0, "inserted": 0, "deleted": 0}

                for op in filter_or_ops:
                    operation_type = op.get("operation")
                    if operation_type == "update":
                        operations.append(
                            UpdateOne(op["filter"], {"$set": op["values"]})
                        )
                        stats["updated"] += 1
                    elif operation_type == "insert":
                        operations.append(InsertOne(op["values"]))
                        stats["inserted"] += 1
                    elif operation_type == "delete":
                        operations.append(DeleteOne(op["filter"]))
                        stats["deleted"] += 1

                if operations:
                    await collection.bulk_write(operations)  # type: ignore
                return stats

            raise ValueError("Invalid update parameters")

        except Exception as e:
            self.logger.error(f"Failed to update records: {e}")
            raise DatabaseError(
                message=f"Failed to update records: {e}", backend="mongodb"
            ) from e

    @overload
    async def delete(self, model: ModelT) -> None: ...

    @overload
    async def delete(self, model: Type[ModelT], filter: Dict[str, Any]) -> int: ...

    async def delete(
        self,
        model: Union[ModelT, Type[ModelT]],
        filter: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """Delete one or multiple records."""
        try:
            # Case 1: Delete single model instance
            if isinstance(model, DatabaseModel):
                if not model.id:
                    raise ValueError("Model has no ID")

                collection = self._get_collection(type(model))
                object_id = self._to_object_id(model.id)
                if not object_id:
                    raise ValueError(f"Invalid MongoDB ObjectId: {model.id}")

                await collection.delete_one({"_id": object_id})
                return None

            # Case 2: Delete multiple records by filter
            if filter:
                collection = self._get_collection(model)
                result = await collection.delete_many(filter)
                return result.deleted_count

            raise ValueError("Invalid delete parameters")

        except Exception as e:
            self.logger.error(f"Failed to delete records: {e}")
            raise DatabaseError(
                message=f"Failed to delete records: {e}", backend="mongodb"
            ) from e

    @overload
    async def convert_value(
        self,
        value: Any,
        field_type: Literal["string"],
        target_type: Type[str] = str,
    ) -> str: ...

    @overload
    async def convert_value(
        self,
        value: Any,
        field_type: Literal["integer"],
        target_type: Type[int] = int,
    ) -> int: ...

    @overload
    async def convert_value(
        self,
        value: Any,
        field_type: Literal["float"],
        target_type: Type[float] = float,
    ) -> float: ...

    @overload
    async def convert_value(
        self,
        value: Any,
        field_type: Literal["decimal"],
        target_type: Type[Decimal] = Decimal,
    ) -> Decimal: ...

    @overload
    async def convert_value(
        self,
        value: Any,
        field_type: Literal["boolean"],
        target_type: Type[bool] = bool,
    ) -> bool: ...

    @overload
    async def convert_value(
        self,
        value: Any,
        field_type: Literal["datetime"],
        target_type: Type[datetime] = datetime,
    ) -> datetime: ...

    @overload
    async def convert_value(
        self,
        value: Any,
        field_type: Literal["date"],
        target_type: Type[date] = date,
    ) -> date: ...

    @overload
    async def convert_value(
        self,
        value: Any,
        field_type: Literal["enum"],
        target_type: Type[Enum],
    ) -> Enum: ...

    @overload
    async def convert_value(
        self,
        value: Any,
        field_type: Literal["json"],
        target_type: Type[Dict[str, Any]] = dict,
    ) -> Dict[str, Any]: ...

    @overload
    async def convert_value(
        self,
        value: Any,
        field_type: Literal["array"],
        target_type: Type[List[T]] = list,
    ) -> List[T]: ...

    async def convert_value(
        self,
        value: Any,
        field_type: FieldType,
        target_type: Optional[Type[T]] = None,
    ) -> T:
        """Convert between MongoDB and Python types."""
        try:
            if value is None:
                return None  # type: ignore

            # Handle MongoDB specific types first
            if isinstance(value, ObjectId):
                return str(value)  # type: ignore
            if isinstance(value, Decimal128):
                value = float(value.to_decimal())

            # Get target type if not provided
            if target_type is None:
                target_type = TYPE_MAPPING.get(field_type, Any)  # type: ignore

            # Validate type compatibility
            expected_type = TYPE_MAPPING.get(field_type)
            if expected_type and not issubclass(get_origin(target_type) or target_type, expected_type):  # type: ignore
                raise TypeError(
                    f"Target type {target_type} is not compatible with field type {field_type}"
                )

            # Convert based on field type
            if field_type == "string":
                return str(value)  # type: ignore
            elif field_type == "integer":
                return int(value)  # type: ignore
            elif field_type == "float":
                return float(value)  # type: ignore
            elif field_type == "decimal":
                return Decimal(str(value))  # type: ignore
            elif field_type == "boolean":
                if isinstance(value, str):
                    return value.lower() in ("true", "1", "yes", "on")  # type: ignore
                return bool(value)  # type: ignore
            elif field_type == "datetime":
                if isinstance(value, str):
                    return datetime.fromisoformat(value)  # type: ignore
                return value  # type: ignore
            elif field_type == "date":
                if isinstance(value, str):
                    return date.fromisoformat(value)  # type: ignore
                elif isinstance(value, datetime):
                    return value.date()  # type: ignore
                return value  # type: ignore
            elif field_type == "enum" and target_type:
                if isinstance(value, target_type):
                    return value  # type: ignore
                return target_type(value)  # type: ignore
            elif field_type == "array":
                if isinstance(value, str):
                    value = json.loads(value)
                if not isinstance(value, (list, tuple)):
                    raise ValueError(f"Cannot convert {value} to array")

                # Get item type from List[T]
                item_type = get_args(target_type)[0] if get_args(target_type) else Any
                if item_type is None or item_type == Any:
                    return list(value)  # type: ignore

                # Convert each item using the specified type
                converted: List[T] = [
                    item_type(item) if item is not None else None  # type: ignore
                    for item in value  # type: ignore
                ]
                return converted  # type: ignore
            elif field_type == "json":
                if isinstance(value, str):
                    return json.loads(value)  # type: ignore
                return value  # type: ignore
            else:
                raise ValueError(f"Unsupported field type: {field_type}")

        except Exception as e:
            self.logger.error(f"Failed to convert value: {e}")
            raise ValueError(f"Failed to convert value: {e}") from e

    @overload
    async def read(
        self, source: Type[ModelT], id_or_ids: str, fields: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]: ...

    @overload
    async def read(
        self, source: str, id_or_ids: str, fields: List[str]
    ) -> Optional[Dict[str, Any]]: ...

    @overload
    async def read(
        self,
        source: Type[ModelT],
        id_or_ids: List[str],
        fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]: ...

    @overload
    async def read(
        self, source: str, id_or_ids: List[str], fields: List[str]
    ) -> List[Dict[str, Any]]: ...

    async def read(
        self,
        source: Union[Type[ModelT], str],
        id_or_ids: Union[str, List[str]],
        fields: Optional[List[str]] = None,
    ) -> Union[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        """Read one or multiple records."""
        try:
            # Get collection name
            collection_name = (
                self._get_collection_name(source)
                if isinstance(source, type)
                else source
            )

            # Handle single ID
            if isinstance(id_or_ids, str):
                object_id = self._to_object_id(id_or_ids)
                if not object_id:
                    return None

                collection = self._get_collection(collection_name)
                proj = {field: 1 for field in fields} if fields else None
                doc = await collection.find_one({"_id": object_id}, projection=proj)

                if doc:
                    return await self._convert_document(doc)
                return None

            # Handle multiple IDs
            object_ids = [self._to_object_id(id) for id in id_or_ids if id]
            if not object_ids:
                return []

            collection = self._get_collection(collection_name)
            proj = {field: 1 for field in fields} if fields else None
            cursor = collection.find({"_id": {"$in": object_ids}}, projection=proj)
            docs = await cursor.to_list(length=None)

            return [await self._convert_document(doc) for doc in docs]

        except Exception as e:
            self.logger.error(f"Failed to read records: {e}")
            raise DatabaseError(
                message=f"Failed to read records: {e}", backend="mongodb"
            ) from e

    async def get_aggregate_query(
        self, model_type: Type[ModelT]
    ) -> AggregateQuery[ModelT]:
        """Create aggregate query.

        Args:
            model_type: Type of model

        Returns:
            AggregateQuery: Aggregate query builder
        """
        collection = self._get_collection(model_type)
        return MongoAggregate[ModelT](collection, model_type)

    async def get_join_query(self, model_type: Type[ModelT]) -> JoinQuery[ModelT, Any]:
        """Create join query.

        Args:
            model_type: Type of model

        Returns:
            JoinQuery: Join query builder
        """
        collection = self._get_collection(model_type)
        return MongoJoin[ModelT, DatabaseModel](collection, model_type)
