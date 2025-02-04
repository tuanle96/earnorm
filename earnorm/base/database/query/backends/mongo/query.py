"""MongoDB query implementation.

This module provides MongoDB-specific implementation for database queries.
It uses MongoDB's aggregation framework for complex queries.

Examples:
    >>> class User(DatabaseModel):
    ...     name: str
    ...     age: int
    ...
    >>> query = MongoQuery[User]()
    >>> # Filter and sort
    >>> query.where(User.age > 18).order_by(User.name)
    >>> # Join with another collection
    >>> query.join(Post).on(User.id == Post.user_id)
    >>> # Group and aggregate
    >>> query.aggregate().group_by(User.age).having(User.age > 20)
    >>> query.aggregate().group_by(User.age).count()
    >>> # Window functions
    >>> query.window().over(partition_by=[User.age]).row_number()
"""

import asyncio
import logging
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    List,
    Optional,
    Protocol,
    Type,
    TypeVar,
    Union,
    cast,
)

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorCommandCursor

from earnorm.base.database.query.core.query import BaseQuery
from earnorm.base.database.query.interfaces.domain import (
    DomainExpression,
    DomainItem,
    DomainLeaf,
    DomainNode,
)
from earnorm.base.database.query.interfaces.operations.aggregate import (
    AggregateProtocol,
)
from earnorm.base.database.query.interfaces.operations.join import JoinProtocol
from earnorm.base.database.query.interfaces.operations.window import WindowProtocol
from earnorm.base.database.query.interfaces.query import QueryProtocol
from earnorm.types import DatabaseModel, JsonDict

from .operations.aggregate import MongoAggregate
from .operations.join import MongoJoin
from .operations.window import MongoWindow

ModelT = TypeVar("ModelT", bound=DatabaseModel)
JoinT = TypeVar("JoinT", bound=DatabaseModel)


class LoggerProtocol(Protocol):
    """Protocol for logger interface."""

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def error(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None: ...


class MongoQuery(BaseQuery[ModelT]):
    """MongoDB query implementation.

    This class provides MongoDB-specific implementation for database queries.
    It uses MongoDB's aggregation framework for complex queries.

    Args:
        ModelT: Type of model being queried
    """

    logger: LoggerProtocol = logging.getLogger(__name__)

    # pylint: disable=dangerous-default-value
    def __init__(
        self,
        collection: AsyncIOMotorCollection[JsonDict],  # type: ignore
        model_type: Type[ModelT],
        filter: JsonDict = {},  # pylint: disable=redefined-builtin
        projection: JsonDict = {},
        sort: List[tuple[str, int]] = [],
        skip: int = 0,
        limit: int = 0,
        pipeline: List[JsonDict] = [],
        allow_disk_use: bool = False,
        hint: Optional[Union[str, List[tuple[str, int]]]] = None,
        operation: Optional[str] = None,
        document: JsonDict = {},
        update: JsonDict = {},
        options: dict[str, Any] = {},
    ) -> None:
        """Initialize MongoDB query.

        Args:
            collection: MongoDB collection
            model_type: Model class being queried
            filter: Query filter
            projection: Field projection
            sort: Sort specification
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            pipeline: Aggregation pipeline
            allow_disk_use: Allow disk use for large queries
            hint: Index hint
            operation: Operation type (insert_one, update, delete)
            document: Document to insert
            update: Update operation
            options: Additional options
        """
        super().__init__(model_type)
        self._collection = collection
        self._model_type = model_type
        self._filter = filter
        self._projection = projection
        self._sort = sort
        self._skip = skip
        self._limit = limit
        self._pipeline = pipeline
        self._allow_disk_use = allow_disk_use
        self._hint = hint
        self._operation = operation
        self._document = document
        self._update = update
        self._options = options
        self._postprocessors: List[
            Callable[
                [Dict[str, Any]],
                Union[Dict[str, Any], Coroutine[Any, Any, Dict[str, Any]]],
            ]
        ] = []
        self._processed_docs: List[Dict[str, Any]] = []

    def add_postprocessor(
        self,
        processor: Callable[
            [Dict[str, Any]], Union[Dict[str, Any], Coroutine[Any, Any, Dict[str, Any]]]
        ],
    ) -> None:
        """Add document post-processor function."""
        self._postprocessors.append(processor)

    async def _process_document(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Process single document with post-processors.

        Args:
            doc: Document to process

        Returns:
            Processed document
        """
        try:
            for processor in self._postprocessors:
                if asyncio.iscoroutinefunction(processor):
                    doc = await processor(doc)
                else:
                    result = processor(doc)
                    doc = await result if asyncio.iscoroutine(result) else result
            return doc
        except Exception as e:
            self.logger.warning(
                f"Document processing failed: {str(e)} for document: {doc}",
                exc_info=True,
            )
            return doc

    async def execute(self) -> List[ModelT]:
        """Execute query and return results.

        Returns:
            List of model instances
        """
        pipeline: List[JsonDict] = []

        # Add filter stage
        if self._filter:
            filter_dict = self._filter.copy()
            if "id" in filter_dict:
                try:
                    filter_dict["_id"] = ObjectId(filter_dict.pop("id"))
                except InvalidId as e:
                    self.logger.warning(f"Invalid ID in filter: {e}")
                    filter_dict["_id"] = None
            pipeline.append({"$match": filter_dict})

        # Add sort stage
        if self._sort:
            # Convert id to _id in sort if exists
            sort_dict = {}
            for field, order in self._sort:
                if field == "id":
                    sort_dict["_id"] = order
                else:
                    sort_dict[field] = order
            pipeline.append({"$sort": sort_dict})

        # Add skip stage
        if self._skip:
            pipeline.append({"$skip": self._skip})

        # Add limit stage
        if self._limit:
            pipeline.append({"$limit": self._limit})

        # Add custom pipeline stages
        if self._pipeline:
            pipeline.extend(self._pipeline)

        # Add projection to rename _id to id
        pipeline.append({"$addFields": {"id": "$_id"}})
        pipeline.append({"$project": {"_id": 0}})

        # Handle hint parameter
        aggregate_kwargs = {"allowDiskUse": self._allow_disk_use, **self._options}
        if self._hint is not None:
            if isinstance(self._hint, str):
                aggregate_kwargs["hint"] = self._hint
            else:
                # Convert id to _id in hint if exists
                hint_dict = {}
                for field, order in self._hint:
                    if field == "id":
                        hint_dict["_id"] = order
                    else:
                        hint_dict[field] = order
                aggregate_kwargs["hint"] = hint_dict

        # Execute pipeline
        cursor: AsyncIOMotorCommandCursor[JsonDict] = self._collection.aggregate(
            pipeline, **aggregate_kwargs
        )
        docs = [doc async for doc in cursor]

        # Process documents
        self._processed_docs = []
        for doc in docs:
            try:
                # Convert _id to id with type checking
                if "_id" in doc:
                    if isinstance(doc["_id"], (ObjectId, str)):
                        doc["id"] = str(doc["_id"])
                    elif doc["_id"] is None:
                        doc["id"] = None
                    else:
                        self.logger.error(
                            "Invalid _id type: %s for document: %s",
                            type(doc["_id"]),
                            doc,
                        )
                        continue
                    del doc["_id"]

                # Apply post-processors
                doc = await self._process_document(doc)
                self._processed_docs.append(doc)
            except Exception as e:
                self.logger.warning(
                    f"Document processing failed: {str(e)} for document: {doc}",
                    exc_info=True,
                )

        # Create model instances
        results: List[ModelT] = []
        for doc in self._processed_docs:
            try:
                model = self._model_type()
                if "id" in doc:
                    model.id = doc["id"]
                object.__setattr__(model, "_data", doc)
                object.__setattr__(model, "_ids", (model.id,))
                results.append(model)
            except Exception as e:
                self.logger.warning(f"Error creating model instance: {e}")
                continue

        return results

    def filter(self, domain: Union[List[Any], JsonDict]) -> "MongoQuery[ModelT]":
        """Filter documents.

        Args:
            domain: Filter conditions

        Returns:
            Self for chaining
        """
        if isinstance(domain, dict):
            # Direct MongoDB filter
            self._filter.update(domain)
        else:
            # Convert domain expression to MongoDB query
            expr = DomainExpression(cast(List[DomainItem], domain))
            expr.validate()
            mongo_query = self._convert_domain_to_mongo(expr)
            self._filter.update(mongo_query)
        return self

    def _convert_domain_to_mongo(self, expr: DomainExpression) -> JsonDict:
        """Convert domain expression to MongoDB query.

        Args:
            expr: Domain expression

        Returns:
            MongoDB query
        """

        def convert_node(node: Union[DomainNode, DomainLeaf]) -> JsonDict:
            if isinstance(node, DomainLeaf):
                field = node.field
                op = node.operator
                value: Union[str, int, List[Union[str, int, ObjectId]], Any] = (
                    node.value
                )

                # Convert id field and value
                if field == "id":
                    field = "_id"
                    # Convert value to ObjectId if needed
                    if isinstance(value, str):
                        value = ObjectId(value)
                    elif isinstance(value, list) and op in ("in", "not in"):
                        value = [
                            ObjectId(str(v)) if isinstance(v, (str, int)) else v
                            for v in cast(List[Union[str, int, Any]], value)
                        ]

                if op == "=":
                    return {field: value}
                elif op == "!=":
                    return {field: {"$ne": value}}
                elif op == ">":
                    return {field: {"$gt": value}}
                elif op == ">=":
                    return {field: {"$gte": value}}
                elif op == "<":
                    return {field: {"$lt": value}}
                elif op == "<=":
                    return {field: {"$lte": value}}
                elif op == "in":
                    return {field: {"$in": value}}
                elif op == "not in":
                    return {field: {"$nin": value}}
                elif op == "like":
                    return {field: {"$regex": value}}
                elif op == "ilike":
                    return {field: {"$regex": value, "$options": "i"}}
                elif op == "not like":
                    return {field: {"$not": {"$regex": value}}}
                elif op == "not ilike":
                    return {field: {"$not": {"$regex": value, "$options": "i"}}}
                elif op == "is null":
                    return {field: None}
                elif op == "is not null":
                    return {field: {"$ne": None}}
                else:
                    raise ValueError(f"Unsupported operator: {op}")
            else:
                if node.operator == "&":
                    return {"$and": [convert_node(op) for op in node.operands]}
                elif node.operator == "|":
                    return {"$or": [convert_node(op) for op in node.operands]}
                elif node.operator == "!":
                    return {"$not": convert_node(node.operands[0])}
                else:
                    raise ValueError(f"Unsupported logical operator: {node.operator}")

        if not expr.root:
            return {}
        return convert_node(expr.root)

    def order_by(self, *fields: str) -> "MongoQuery[ModelT]":
        """Add order by fields.

        Args:
            fields: Fields to order by

        Returns:
            Self for chaining
        """
        for field in fields:
            if field.startswith("-"):
                self._sort.append((field[1:], -1))
            else:
                self._sort.append((field, 1))
        return self

    def limit(self, limit: int) -> "MongoQuery[ModelT]":
        """Set result limit.

        Args:
            limit: Maximum number of results

        Returns:
            Self for chaining
        """
        self._limit = limit
        return self

    def offset(self, offset: int) -> "MongoQuery[ModelT]":
        """Set result offset.

        Args:
            offset: Number of results to skip

        Returns:
            Self for chaining
        """
        self._skip = offset
        return self

    async def count(self) -> int:
        """Count documents.

        Returns:
            Number of documents
        """
        pipeline: List[JsonDict] = []

        # Add filter stage
        if self._filter:
            pipeline.append({"$match": self._filter})

        # Add count stage
        pipeline.append({"$count": "count"})

        # Execute pipeline
        cursor: AsyncIOMotorCommandCursor[JsonDict] = self._collection.aggregate(
            pipeline
        )
        result = [doc async for doc in cursor]
        return result[0]["count"] if result else 0

    async def exists(self) -> bool:
        """Check if any results exist.

        Returns:
            True if results exist
        """
        return await self.count() > 0

    async def first(self) -> Optional[ModelT]:
        """Get first result or None.

        Returns:
            First result or None
        """
        self._limit = 1
        results = await self.execute()
        return results[0] if results else None

    def join(
        self,
        model: Union[str, Type[JoinT]],
        on: Optional[dict[str, Any]] = None,
        join_type: str = "inner",
    ) -> JoinProtocol[ModelT, JoinT]:
        """Create join operation.

        Args:
            model: Model to join with
            on: Join conditions {local_field: foreign_field}
            join_type: Join type (inner, left, right, cross, full)

        Returns:
            Join operation
        """
        join = MongoJoin[ModelT, JoinT](self._collection, self._model_type)
        join.join(model, on, join_type)
        self._joins.append(join)
        return join

    def aggregate(self) -> AggregateProtocol[ModelT]:
        """Create aggregate operation.

        Returns:
            Aggregate operation
        """
        aggregate = MongoAggregate[ModelT](self._collection, self._model_type)
        self._aggregates.append(aggregate)
        return aggregate

    def window(self) -> WindowProtocol[ModelT]:
        """Create window operation.

        Returns:
            Window operation
        """
        window = MongoWindow[ModelT]()
        self._windows.append(window)
        return window

    async def insert(self, document: JsonDict) -> JsonDict:
        """Insert document.

        Args:
            document: Document to insert

        Returns:
            Inserted document
        """
        result = await self._collection.insert_one(document)
        return {"_id": result.inserted_id}

    async def update(self, update: JsonDict) -> JsonDict:
        """Update documents.

        Args:
            update: Update operation

        Returns:
            Update result
        """
        result = await self._collection.update_many(self._filter, update)
        return {
            "matched_count": result.matched_count,
            "modified_count": result.modified_count,
        }

    async def delete(self) -> JsonDict:
        """Delete documents.

        Returns:
            Delete result
        """
        result = await self._collection.delete_many(self._filter)
        return {"deleted_count": result.deleted_count}

    async def _process_id(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Convert _id to id and validate format."""
        if "_id" in doc:
            try:
                doc["id"] = str(ObjectId(doc["_id"]))
            except InvalidId:
                self.logger.warning(f"Invalid ObjectId: {doc['_id']}")
                doc["id"] = None
        return doc

    def hint(self, index_hint: Dict[str, Any]) -> "QueryProtocol[ModelT]":
        """Add index hint for query optimization."""
        self._hint = index_hint
        return self

    def prefetch(self, fields: List[str]) -> "QueryProtocol[ModelT]":
        """Add fields to prefetch."""
        self._prefetch_fields = fields
        return self
