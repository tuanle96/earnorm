"""MongoDB adapter implementation.

This module provides MongoDB adapter implementation.
It handles the conversion between string IDs (used by models) and ObjectId (used by MongoDB).
"""

import json
import logging
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Protocol, Type, TypeVar, Union, cast, overload

from bson import ObjectId
from bson.decimal128 import Decimal128
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo.operations import DeleteOne, InsertOne, UpdateOne

from earnorm.base.database.adapter import DatabaseAdapter, FieldType
from earnorm.base.database.query.backends.mongo.converter import MongoConverter
from earnorm.base.database.query.backends.mongo.operations.aggregate import MongoAggregate
from earnorm.base.database.query.backends.mongo.operations.join import MongoJoin
from earnorm.base.database.query.backends.mongo.query import MongoQuery
from earnorm.base.database.query.core.query import BaseQuery
from earnorm.base.database.query.interfaces.domain import DomainExpression
from earnorm.base.database.query.interfaces.operations.aggregate import AggregateProtocol as AggregateQuery
from earnorm.base.database.query.interfaces.operations.join import JoinProtocol as JoinQuery
from earnorm.base.database.transaction.backends.mongo import MongoTransactionManager
from earnorm.di import container
from earnorm.exceptions import DatabaseError
from earnorm.pool.backends.mongo import MongoPool
from earnorm.pool.protocols import AsyncConnectionProtocol
from earnorm.types import DatabaseModel, JsonDict
from earnorm.types.relations import RelationOptions, RelationType

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
        """Get collection for model.

        Args:
            model_type: Model class or name

        Returns:
            Collection instance
        """
        # Get collection name
        if isinstance(model_type, str):
            collection_name = model_type
        else:
            collection_name = model_type._name  # type: ignore

        return self._sync_db[collection_name]  # type: ignore

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
        filter_or_ops: Union[Dict[str, Any], DomainExpression],
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
        filter_or_ops: Optional[
            Union[Dict[str, Any], DomainExpression, List[Dict[str, Any]]]
        ] = None,
        values: Optional[Dict[str, Any]] = None,
    ) -> Union[ModelT, int, Dict[str, int]]:
        """Update one or multiple records."""
        try:
            # Case 1: Update single model instance
            if self.is_model_instance(model):
                # cast to instance
                model = cast(ModelT, model)

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
            if (
                self.is_model_class(model)
                and (
                    isinstance(filter_or_ops, dict)
                    or isinstance(filter_or_ops, DomainExpression)
                )
                and values
            ):
                collection = self._get_collection(model)

                # Convert DomainExpression to MongoDB filter using MongoConverter
                mongo_filter = (
                    MongoConverter().convert(filter_or_ops.to_list())
                    if isinstance(filter_or_ops, DomainExpression)
                    else filter_or_ops
                )

                result = await collection.update_many(mongo_filter, {"$set": values})
                return result.modified_count

            # Case 3: Bulk operations
            if self.is_model_class(model) and isinstance(filter_or_ops, list):
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
        """Convert value between database and Python types.

        This method handles conversion between Python types and MongoDB types:
        - ObjectId <-> str for IDs
        - datetime <-> str for dates
        - Decimal <-> str for decimals
        - Enum <-> str for enums
        - dict <-> str for JSON
        - list <-> list for arrays
        - relation IDs for relationships

        Args:
            value: Value to convert
            field_type: Field type ("string", "integer", etc)
            target_type: Target Python type

        Returns:
            Converted value

        Raises:
            ValueError: If conversion fails
        """
        try:
            if value is None:
                return None  # type: ignore

            # Handle MongoDB specific types first
            if isinstance(value, ObjectId):
                return str(value)  # type: ignore
            if isinstance(value, Decimal128):
                value = float(value.to_decimal())

            # Handle relation fields
            if field_type in ["many2one", "one2one"]:
                # For many-to-one and one-to-one, store single ObjectId
                if hasattr(value, "id"):
                    return ObjectId(str(value.id))  # type: ignore
                elif isinstance(value, str):
                    return ObjectId(value)  # type: ignore
                elif isinstance(value, ObjectId):
                    return value  # type: ignore
                raise ValueError("Cannot convert value to ObjectId")

            elif field_type in ["one2many", "many2many"]:
                # For one-to-many and many-to-many, store list of ObjectIds
                if isinstance(value, list):
                    return [
                        (
                            ObjectId(str(v.id))  # type: ignore
                            if hasattr(v, "id")  # type: ignore
                            else (
                                ObjectId(v) if isinstance(v, str) else v  # type: ignore
                            )
                        )
                        for v in value  # type: ignore
                    ]  # type: ignore
                raise ValueError("Cannot convert value to ObjectId list")

            # Handle other field types
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
                    return value
                return target_type(value)  # type: ignore
            elif field_type == "array":
                if isinstance(value, str):
                    value = json.loads(value)
                if not isinstance(value, (list, tuple)):
                    raise ValueError(f"Expected list or tuple, got {type(value)}")
                return list(value)  # type: ignore
            elif field_type == "json":
                if isinstance(value, str):
                    return json.loads(value)
                return value
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

    async def setup_relations(
        self, model: Type[ModelT], relations: Dict[str, RelationOptions]
    ) -> None:
        """Set up database relations.

        This method:
        1. Creates necessary indexes
        2. Sets up foreign key constraints
        3. Creates junction tables for many-to-many

        Args:
            model: Model class
            relations: Relation field options
        """
        try:
            # Get collection
            collection = self._get_collection(model._name)  # type: ignore

            # Set up each relation
            for field_name, options in relations.items():
                # Get target model
                target_model = options.model
                if isinstance(target_model, str):
                    target_model = await self.env.get_model(target_model)
                    if not target_model:
                        raise RuntimeError(f"Target model not found: {options.model}")

                # Create index on foreign key field
                if options.index:  # type: ignore
                    self.logger.info(f"Creating index for {field_name}")
                    await collection.create_index(
                        [(field_name, 1)],
                        unique=options.relation_type == RelationType.ONE_TO_ONE,  # type: ignore
                        sparse=True,
                    )

                # Create junction collection for many-to-many
                if options.relation_type == RelationType.MANY_TO_MANY:  # type: ignore
                    if options.through:
                        # Use custom through model
                        through_collection = self._get_collection(
                            options.through["model"]._name  # type: ignore
                        )
                        self.logger.info(
                            f"Using custom through collection: {through_collection.name}"
                        )
                    else:
                        # Create default junction collection
                        through_collection = self._get_collection(
                            f"{model._name}_{field_name}"  # type: ignore
                        )
                        self.logger.info(
                            f"Created default junction collection: {through_collection.name}"
                        )

                        # Create indexes on junction collection
                        await through_collection.create_index(
                            [("source_id", 1), ("target_id", 1)],
                            unique=True,
                        )
                        await through_collection.create_index("source_id")
                        await through_collection.create_index("target_id")

        except Exception as e:
            self.logger.error(f"Failed to setup relations: {str(e)}")
            raise

    async def get_related(
        self,
        instance: Any,
        field_name: str,
        relation_type: RelationType,
        options: RelationOptions,
    ) -> ModelT:
        """Get related record(s).

        Args:
            instance: Model instance
            field_name: Field name
            relation_type: Relation type
            options: Relation options

        Returns:
            Related record(s)
        """
        try:
            # Get source ID
            source_id = instance.id
            self.logger.info(
                f"Getting related records for {instance._name}:{source_id}, field: {field_name}, type: {relation_type}"
            )

            # Get target model
            target_model = options.model
            if isinstance(target_model, str):
                # Resolve string reference
                target_model = await self.env.get_model(target_model)
                if target_model is None:
                    raise RuntimeError(f"Target model not found: {options.model}")

            # Now target_model is guaranteed to be a class
            collection = self._get_collection(target_model._name)  # type: ignore

            if relation_type == RelationType.ONE_TO_MANY:
                self.logger.info(
                    f"Handling ONE_TO_MANY relation, related_name: {options.related_name}"
                )
                # Use aggregation pipeline for better performance
                pipeline = [
                    {"$match": {options.related_name: source_id}},
                    {"$project": {"_id": 1}},
                    {"$addFields": {"id": {"$toString": "$_id"}}},
                    {"$replaceRoot": {"newRoot": {"id": "$id"}}},
                    {"$group": {"_id": None, "ids": {"$push": "$id"}}},
                    {"$project": {"_id": 0, "ids": 1}},
                ]

                target_records = await collection.aggregate(pipeline).to_list(
                    length=None
                )

                # Extract IDs from result
                target_ids: List[str] = (
                    target_records[0]["ids"] if target_records else []
                )
                self.logger.info(f"Found {len(target_ids)} records using aggregation")

                # Always return recordset (may be empty)
                result: ModelT = target_model._browse(target_model._env, target_ids)  # type: ignore
                self.logger.info(f"Returning recordset: {result}")
                return result  # type: ignore

            elif relation_type == RelationType.MANY_TO_ONE:
                self.logger.info("Handling MANY_TO_ONE relation")
                # Direct query using foreign key
                target_record = await self.read(target_model._name, source_id)
                self.logger.info(f"Found target record: {target_record}")
                if not target_record:
                    result = target_model._browse(target_model._env, [])
                    self.logger.info("No record found, returning empty recordset")
                    return result
                result = target_model._browse(target_model._env, [target_record])
                self.logger.info(f"Returning recordset with record: {result}")
                return result

            elif relation_type == RelationType.ONE_TO_ONE:
                self.logger.info("Handling ONE_TO_ONE relation")
                # Similar to many-to-one but enforce uniqueness
                target_record = await self.read(target_model._name, source_id)
                self.logger.info(f"Found target record: {target_record}")
                if not target_record:
                    result = target_model._browse(target_model._env, [])
                    self.logger.info("No record found, returning empty recordset")
                    return result
                result = target_model._browse(target_model._env, [target_record])
                self.logger.info(f"Returning recordset with record: {result}")
                return result

            elif relation_type == RelationType.MANY_TO_MANY:
                self.logger.info("Handling MANY_TO_MANY relation")
                # Handle through model if specified
                if options.through:
                    self.logger.info(f"Using through model: {options.through}")
                    # Query through model first
                    through_collection = self._get_collection(
                        options.through["model"]._name  # type: ignore
                    )
                    cursor = through_collection.find(
                        {options.through_fields["fields"][0]: source_id}
                    )
                    through_records = []
                    async for doc in cursor:
                        self.logger.info(f"Found through document: {doc}")
                        converted = await self._convert_document(doc)
                        self.logger.info(f"Converted through document: {converted}")
                        through_records.append(converted)

                    if not through_records:
                        result = target_model._browse(target_model._env, [])
                        self.logger.info(
                            "No through records found, returning empty recordset"
                        )
                        return result

                    # Then query target model
                    target_ids = [
                        r[options.through_fields["fields"][1]] for r in through_records
                    ]
                    self.logger.info(f"Found target IDs: {target_ids}")

                    target_records = []
                    for target_id in target_ids:
                        record = await self.read(target_model._name, target_id)
                        self.logger.info(f"Found target record: {record}")
                        if record:
                            target_records.append(record)

                    result = target_model._browse(target_model._env, target_records)
                    self.logger.info(
                        f"Returning recordset with {len(target_records)} records"
                    )
                    return result
                else:
                    self.logger.info("Using direct many-to-many relation")
                    # Direct many-to-many
                    cursor = collection.find({field_name: source_id})
                    target_records = []
                    async for doc in cursor:
                        self.logger.info(f"Found document: {doc}")
                        converted = await self._convert_document(doc)
                        self.logger.info(f"Converted document: {converted}")
                        target_records.append(converted)

                    result = target_model._browse(
                        target_model._env, target_records or []
                    )
                    self.logger.info(
                        f"Returning recordset with {len(target_records)} records"
                    )
                    return result

            self.logger.warning(f"Unknown relation type: {relation_type}")
            return None

        except Exception as e:
            self.logger.error(f"Failed to get related records: {str(e)}")
            raise

    async def set_related(
        self,
        instance: ModelT,
        field_name: str,
        value: Union[Optional[ModelT], List[ModelT]],
        relation_type: RelationType,
        options: RelationOptions,
    ) -> None:
        """Set related records for relation field.

        Args:
            instance: Model instance
            field_name: Relation field name
            value: Related record(s) to set
            relation_type: Type of relation
            options: Relation options

        Raises:
            DatabaseError: If operation fails
            RuntimeError: If model resolution fails
            ValueError: If value type doesn't match model type
        """
        try:
            # Resolve model if string reference
            model = options.model
            if isinstance(model, str):
                model = await self.env.get_model(model)
                if not model:
                    raise RuntimeError(f"Model {model} not found")
                options.model = cast(Type[ModelT], model)

            resolved_model = cast(Type[ModelT], model)

            # Validate value type
            if isinstance(value, list):
                for item in value:
                    if not isinstance(item, resolved_model):
                        raise ValueError(
                            f"Expected {resolved_model.__name__}, got {type(item)}"
                        )
            elif value is not None and not isinstance(value, resolved_model):
                raise ValueError(
                    f"Expected {resolved_model.__name__}, got {type(value)}"
                )

            # Get target collection
            target_collection = self._get_collection(resolved_model)

            if not instance.id:
                return

            if relation_type == RelationType.MANY_TO_MANY:
                # Get through collection
                if options.through:
                    through_collection = self._get_collection(
                        options.through._name  # type: ignore
                    )
                    local_field, foreign_field = options.through_fields or (
                        "source_id",
                        "target_id",
                    )
                else:
                    through_collection = self._get_collection(
                        f"{instance._name}_{field_name}"  # type: ignore
                    )
                    local_field, foreign_field = "source_id", "target_id"

                # Delete existing relations
                await through_collection.delete_many({local_field: instance.id})

                if not value:
                    return

                # Create new relations
                docs = [  # type: ignore
                    {local_field: instance.id, foreign_field: target.id}  # type: ignore
                    for target in value  # type: ignore
                ]
                await through_collection.insert_many(docs)  # type: ignore

            elif relation_type == RelationType.ONE_TO_MANY:
                if not value:
                    return

                # Update target records
                target_collection = self._get_collection(options.model._name)  # type: ignore
                target_ids = [target.id for target in value]  # type: ignore

                # Remove old relations
                await target_collection.update_many(
                    {options.related_name: instance.id},  # type: ignore
                    {"$unset": {options.related_name: ""}},
                )

                # Set new relations
                await target_collection.update_many(
                    {"_id": {"$in": target_ids}},
                    {"$set": {options.related_name: instance.id}},
                )

            else:
                # Update single target record
                target_collection = self._get_collection(options.model._name)  # type: ignore

                if value:
                    await target_collection.update_one(
                        {"_id": value.id},  # type: ignore
                        {"$set": {options.related_name: instance.id}},  # type: ignore
                    )

        except Exception as e:
            raise DatabaseError(
                message=f"Failed to set related records: {str(e)}",
                backend=self.backend_type,
            ) from e

    async def delete_related(
        self,
        instance: ModelT,
        field_name: str,
        relation_type: RelationType,
        options: RelationOptions,
    ) -> None:
        """Delete related records based on on_delete behavior.

        Args:
            instance: Model instance
            field_name: Relation field name
            relation_type: Type of relation
            options: Relation options

        Raises:
            DatabaseError: If operation fails
            RuntimeError: If model resolution fails
        """
        try:
            # Resolve model if string reference
            model = options.model
            if isinstance(model, str):
                model = await self.env.get_model(model)
                if not model:
                    raise RuntimeError(f"Model {model} not found")
                options.model = cast(Type[ModelT], model)

            resolved_model = cast(Type[ModelT], model)

            # Get target collection
            target_collection = self._get_collection(resolved_model)

            if not instance.id:
                return

            if relation_type == RelationType.MANY_TO_MANY:
                # Get through collection
                if options.through:
                    through_collection = self._get_collection(
                        options.through._name  # type: ignore
                    )
                    local_field, foreign_field = options.through_fields or (  # type: ignore
                        "source_id",
                        "target_id",
                    )
                else:
                    through_collection = self._get_collection(
                        f"{instance._name}_{field_name}"  # type: ignore
                    )
                    local_field, foreign_field = "source_id", "target_id"  # type: ignore

                # Delete relations
                await through_collection.delete_many({local_field: instance.id})

            elif relation_type == RelationType.ONE_TO_MANY:
                # Get target collection
                target_collection = self._get_collection(options.model._name)  # type: ignore

                if options.on_delete == "CASCADE":
                    # Delete target records
                    await target_collection.delete_many(
                        {options.related_name: instance.id}
                    )
                elif options.on_delete == "SET_NULL":
                    # Set relation to null
                    await target_collection.update_many(
                        {options.related_name: instance.id},
                        {"$unset": {options.related_name: ""}},
                    )

            else:
                # Get target collection
                target_collection = self._get_collection(options.model._name)  # type: ignore

                if options.on_delete == "CASCADE":
                    # Delete target record
                    await target_collection.delete_one({"_id": instance.id})
                elif options.on_delete == "SET_NULL":
                    # Set relation to null
                    await target_collection.update_one(
                        {"_id": instance.id}, {"$unset": {options.related_name: ""}}
                    )

        except Exception as e:
            raise DatabaseError(
                message=f"Failed to delete related records: {str(e)}",
                backend=self.backend_type,
            ) from e

    async def bulk_load_related(
        self,
        instances: List[ModelT],
        field_name: str,
        relation_type: RelationType,
        options: RelationOptions,
    ) -> Dict[str, Union[Optional[ModelT], List[ModelT]]]:
        """Load related records for multiple instances efficiently.

        Args:
            instances: List of model instances
            field_name: Relation field name
            relation_type: Type of relation
            options: Relation options

        Returns:
            Dict mapping instance IDs to their related records

        Raises:
            DatabaseError: If operation fails
        """
        try:
            if not instances:
                return {}

            instance_ids = [instance.id for instance in instances]
            result: Dict[str, Union[Optional[ModelT], List[ModelT]]] = {}

            if relation_type == RelationType.MANY_TO_MANY:
                # Get through collection
                if options.through:
                    through_collection = self._get_collection(
                        options.through._name  # type: ignore
                    )
                    local_field, foreign_field = options.through_fields or (
                        "source_id",
                        "target_id",
                    )
                else:
                    through_collection = self._get_collection(
                        f"{instances[0]._name}_{field_name}"  # type: ignore
                    )
                    local_field, foreign_field = "source_id", "target_id"

                # Get all relations
                cursor = through_collection.find({local_field: {"$in": instance_ids}})
                relations = {
                    doc[local_field]: doc[foreign_field] async for doc in cursor
                }

                if not relations:
                    return {instance.id: [] for instance in instances}

                # Get all target records
                target_collection = self._get_collection(options.model._name)  # type: ignore
                target_ids = list(relations.values())
                cursor = target_collection.find({"_id": {"$in": target_ids}})
                targets = {  # type: ignore
                    str(doc["_id"]): options.model._browse(self._env, [str(doc["_id"])])  # type: ignore
                    async for doc in cursor
                }

                # Map relations to instances
                for instance in instances:
                    result[instance.id] = [
                        targets[target_id]
                        for target_id in relations.get(instance.id, [])
                        if target_id in targets
                    ]

            elif relation_type == RelationType.ONE_TO_MANY:
                # Get target collection
                target_collection = self._get_collection(options.model._name)  # type: ignore

                # Get all target records
                cursor = target_collection.find(
                    {options.related_name: {"$in": instance_ids}}
                )
                targets = {  # type: ignore
                    doc[options.related_name]: options.model._browse(  # type: ignore
                        self._env, [str(doc["_id"])]  # type: ignore
                    )
                    async for doc in cursor
                }

                # Map targets to instances
                for instance in instances:
                    result[instance.id] = targets.get(instance.id, [])  # type: ignore

            else:
                # Get target collection
                target_collection = self._get_collection(options.model._name)  # type: ignore

                # Get all target records
                cursor = target_collection.find({"_id": {"$in": instance_ids}})
                targets = {  # type: ignore
                    str(doc["_id"]): options.model._browse(  # type: ignore
                        self._env, [str(doc["_id"])]  # type: ignore
                    )
                    async for doc in cursor
                }

                # Map targets to instances
                for instance in instances:
                    result[instance.id] = targets.get(instance.id)  # type: ignore

            return result

        except Exception as e:
            raise DatabaseError(
                message=f"Failed to bulk load related records: {str(e)}",
                backend=self.backend_type,
            ) from e
