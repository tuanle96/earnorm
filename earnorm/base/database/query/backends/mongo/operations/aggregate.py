"""MongoDB aggregate operation implementation.

This module provides MongoDB-specific implementation for aggregate operations.
It uses MongoDB's aggregation framework for aggregations and grouping.

Examples:
    >>> class User(DatabaseModel):
    ...     name: str
    ...     age: int
    ...
    >>> query = MongoQuery[User]()
    >>> # Group by age and count
    >>> query.aggregate().group_by(User.age).count()
    >>> # Group by age and filter groups
    >>> query.aggregate().group_by(User.age).having(User.age > 20)
    >>> # Aggregate functions
    >>> query.aggregate().group_by(User.age).sum(User.salary)
    >>> query.aggregate().group_by(User.age).avg(User.salary)
    >>> query.aggregate().group_by(User.age).min(User.salary)
    >>> query.aggregate().group_by(User.age).max(User.salary)
"""

from typing import Any, Dict, List, Optional, Type, TypeVar, Union

from motor.motor_asyncio import AsyncIOMotorCollection

from earnorm.base.database.query.interfaces.domain import (
    DomainExpression,
    DomainItem,
    DomainLeaf,
    DomainNode,
)
from earnorm.base.database.query.interfaces.operations.aggregate import (
    AggregateProtocol,
)
from earnorm.types import DatabaseModel, JsonDict

ModelT = TypeVar("ModelT", bound=DatabaseModel)


class MongoAggregate(AggregateProtocol[ModelT]):
    """MongoDB aggregate operation implementation.

    This class provides MongoDB-specific implementation for aggregate operations.
    It supports both aggregation functions and grouping operations.
    """

    def __init__(
        self,
        collection: AsyncIOMotorCollection[JsonDict],  # type: ignore
        model_type: Type[ModelT],
    ) -> None:
        """Initialize MongoDB aggregate.

        Args:
            collection: MongoDB collection
            model_type: Model class being queried
        """
        self._collection = collection
        self._model_type = model_type
        self._group_fields: List[str] = []
        self._aggregations: List[Dict[str, Any]] = []
        self._having_conditions: Dict[str, Any] = {}

    def group_by(self, *fields: str) -> "MongoAggregate[ModelT]":
        """Group by fields.

        Args:
            fields: Fields to group by

        Returns:
            Self for chaining
        """
        self._group_fields.extend(fields)
        return self

    def count(
        self, field: str = "*", alias: Optional[str] = None
    ) -> "MongoAggregate[ModelT]":
        """Count records.

        Args:
            field: Field to count, defaults to "*" for count all
            alias: Alias for count field, defaults to "count"

        Returns:
            Self for chaining
        """
        alias = alias or "count"
        self._aggregations.append({alias: {"$sum": 1}})
        return self

    def sum(self, field: str, alias: Optional[str] = None) -> "MongoAggregate[ModelT]":
        """Sum field values.

        Args:
            field: Field to sum
            alias: Alias for sum field

        Returns:
            Self for chaining
        """
        alias = alias or f"sum_{field}"
        self._aggregations.append({alias: {"$sum": f"${field}"}})
        return self

    def avg(self, field: str, alias: Optional[str] = None) -> "MongoAggregate[ModelT]":
        """Average field values.

        Args:
            field: Field to average
            alias: Alias for average field

        Returns:
            Self for chaining
        """
        alias = alias or f"avg_{field}"
        self._aggregations.append({alias: {"$avg": f"${field}"}})
        return self

    def min(self, field: str, alias: Optional[str] = None) -> "MongoAggregate[ModelT]":
        """Get minimum field value.

        Args:
            field: Field to get minimum of
            alias: Alias for min field

        Returns:
            Self for chaining
        """
        alias = alias or f"min_{field}"
        self._aggregations.append({alias: {"$min": f"${field}"}})
        return self

    def max(self, field: str, alias: Optional[str] = None) -> "MongoAggregate[ModelT]":
        """Get maximum field value.

        Args:
            field: Field to get maximum of
            alias: Alias for max field

        Returns:
            Self for chaining
        """
        alias = alias or f"max_{field}"
        self._aggregations.append({alias: {"$max": f"${field}"}})
        return self

    def having(
        self, domain: Union[List[DomainItem], JsonDict]
    ) -> "MongoAggregate[ModelT]":
        """Add having conditions.

        Args:
            domain: Having conditions in domain expression format or MongoDB query format

        Returns:
            Self for chaining
        """
        if isinstance(domain, dict):
            self._having_conditions.update(domain)
        else:
            # Convert domain expression to MongoDB query
            expr = DomainExpression(domain)
            expr.validate()
            mongo_query = self._convert_domain_to_mongo(expr)
            self._having_conditions.update(mongo_query)
        return self

    def validate(self) -> None:
        """Validate aggregate configuration.

        Raises:
            ValueError: If aggregate configuration is invalid
        """
        if not self._group_fields and not self._aggregations:
            raise ValueError("No grouping fields or aggregations specified")

    def get_pipeline_stages(self) -> List[JsonDict]:
        """Get MongoDB aggregation pipeline stages for this aggregation.

        Returns:
            List[JsonDict]: List of pipeline stages
        """
        stages: List[JsonDict] = []

        # Build $group stage
        group_stage: JsonDict = {
            "$group": {
                "_id": (
                    {field: f"${field}" for field in self._group_fields}
                    if self._group_fields
                    else None
                )
            }
        }

        # Add aggregations
        for agg in self._aggregations:
            group_stage["$group"].update(agg)

        stages.append(group_stage)

        # Add $match stage for having conditions
        if self._having_conditions:
            having_stage: JsonDict = {"$match": {}}
            for field, value in self._having_conditions.items():
                if "__" in field:
                    field_name, op = field.split("__")
                    if op == "gt":
                        having_stage["$match"][field_name] = {"$gt": value}
                    elif op == "gte":
                        having_stage["$match"][field_name] = {"$gte": value}
                    elif op == "lt":
                        having_stage["$match"][field_name] = {"$lt": value}
                    elif op == "lte":
                        having_stage["$match"][field_name] = {"$lte": value}
                    elif op == "ne":
                        having_stage["$match"][field_name] = {"$ne": value}
                    else:
                        having_stage["$match"][field] = value
                else:
                    having_stage["$match"][field] = value

            stages.append(having_stage)

        return stages

    def to_pipeline(self) -> List[JsonDict]:
        """Convert aggregate operation to MongoDB pipeline.

        Returns:
            List[JsonDict]: List of pipeline stages

        Example:
            >>> aggregate = MongoAggregate[User](collection, User)
            >>> aggregate.group_by("age").count()
            >>> pipeline = aggregate.to_pipeline()
            >>> print(pipeline)
            [{"$group": {"_id": "$age", "count": {"$sum": 1}}}]
        """
        stages: List[JsonDict] = []

        # Build $group stage
        group_stage: JsonDict = {
            "$group": {
                "_id": (
                    {field: f"${field}" for field in self._group_fields}
                    if self._group_fields
                    else None
                )
            }
        }

        # Add aggregations
        for agg in self._aggregations:
            group_stage["$group"].update(agg)

        stages.append(group_stage)

        # Add $match stage for having conditions
        if self._having_conditions:
            having_stage: JsonDict = {"$match": {}}
            for field, value in self._having_conditions.items():
                if "__" in field:
                    field_name, op = field.split("__")
                    if op == "gt":
                        having_stage["$match"][field_name] = {"$gt": value}
                    elif op == "gte":
                        having_stage["$match"][field_name] = {"$gte": value}
                    elif op == "lt":
                        having_stage["$match"][field_name] = {"$lt": value}
                    elif op == "lte":
                        having_stage["$match"][field_name] = {"$lte": value}
                    elif op == "ne":
                        having_stage["$match"][field_name] = {"$ne": value}
                    else:
                        having_stage["$match"][field] = value
                else:
                    having_stage["$match"][field] = value

            stages.append(having_stage)

        return stages

    @property
    def model_type(self) -> Type[ModelT]:
        """Get model type.

        Returns:
            Model type
        """
        return self._model_type

    @property
    def collection(self) -> AsyncIOMotorCollection[JsonDict]:  # type: ignore
        """Get MongoDB collection.

        Returns:
            MongoDB collection
        """
        return self._collection

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
                value = node.value

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
