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

from typing import Any, Dict, List, Type, TypeVar

from motor.motor_asyncio import AsyncIOMotorCollection

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
        collection: AsyncIOMotorCollection[Dict[str, Any]],  # type: ignore
        model_cls: Type[ModelT],
    ) -> None:
        """Initialize MongoDB aggregate operation.

        Args:
            collection: MongoDB collection
            model_cls: Model class
        """
        self._collection = collection
        self._model_cls = model_cls
        self._group_fields: List[str] = []
        self._having: JsonDict | List[Any] | None = None
        self._aggregates: Dict[str, JsonDict] = {}

    def group_by(self, *fields: str) -> AggregateProtocol[ModelT]:
        """Group results by fields.

        Args:
            fields: Fields to group by

        Returns:
            Self for chaining
        """
        self._group_fields.extend(fields)
        return self

    def having(self, domain: JsonDict | List[Any]) -> AggregateProtocol[ModelT]:
        """Add having conditions.

        Args:
            domain: Having conditions

        Returns:
            Self for chaining
        """
        self._having = domain
        return self

    def count(
        self, field: str = "*", alias: str | None = None
    ) -> AggregateProtocol[ModelT]:
        """Count records.

        Args:
            field: Field to count
            alias: Result alias

        Returns:
            Self for chaining
        """
        alias = alias or f"count_{field}"
        self._aggregates[alias] = {"$sum": 1}
        return self

    def sum(self, field: str, alias: str | None = None) -> AggregateProtocol[ModelT]:
        """Sum field values.

        Args:
            field: Field to sum
            alias: Result alias

        Returns:
            Self for chaining
        """
        alias = alias or f"sum_{field}"
        self._aggregates[alias] = {"$sum": f"${field}"}
        return self

    def avg(self, field: str, alias: str | None = None) -> AggregateProtocol[ModelT]:
        """Average field values.

        Args:
            field: Field to average
            alias: Result alias

        Returns:
            Self for chaining
        """
        alias = alias or f"avg_{field}"
        self._aggregates[alias] = {"$avg": f"${field}"}
        return self

    def min(self, field: str, alias: str | None = None) -> AggregateProtocol[ModelT]:
        """Get minimum field value.

        Args:
            field: Field to get minimum of
            alias: Result alias

        Returns:
            Self for chaining
        """
        alias = alias or f"min_{field}"
        self._aggregates[alias] = {"$min": f"${field}"}
        return self

    def max(self, field: str, alias: str | None = None) -> AggregateProtocol[ModelT]:
        """Get maximum field value.

        Args:
            field: Field to get maximum of
            alias: Result alias

        Returns:
            Self for chaining
        """
        alias = alias or f"max_{field}"
        self._aggregates[alias] = {"$max": f"${field}"}
        return self

    def validate(self) -> None:
        """Validate aggregate configuration.

        Raises:
            ValueError: If aggregate configuration is invalid
        """
        if not self._group_fields and not self._aggregates:
            raise ValueError("No grouping fields or aggregate functions specified")

    def to_pipeline(self) -> List[JsonDict]:
        """Convert aggregate operation to MongoDB pipeline.

        Returns:
            List of pipeline stages
        """
        pipeline: List[JsonDict] = []

        # Add group stage if grouping fields or aggregates exist
        if self._group_fields or self._aggregates:
            group_stage: JsonDict = {}

            # Add group fields
            if self._group_fields:
                group_stage["_id"] = {
                    field: f"${field}" for field in self._group_fields
                }
            else:
                group_stage["_id"] = None

            # Add aggregates
            group_stage.update(self._aggregates)
            pipeline.append({"$group": group_stage})

        # Add having stage
        if self._having:
            pipeline.append({"$match": self._having})

        return pipeline

    @property
    def model_type(self) -> Type[ModelT]:
        """Get model type.

        Returns:
            Model type
        """
        return self._model_cls

    @property
    def collection(self) -> AsyncIOMotorCollection[Dict[str, Any]]:  # type: ignore
        """Get MongoDB collection.

        Returns:
            MongoDB collection
        """
        return self._collection
