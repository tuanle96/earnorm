"""MongoDB aggregate query implementation."""

from typing import Any, Dict, List, Type, TypeVar

from motor.motor_asyncio import AsyncIOMotorCollection

from earnorm.base.database.query.base.operations.aggregate import AggregateQuery
from earnorm.types import DatabaseModel, JsonDict

ModelT = TypeVar("ModelT", bound=DatabaseModel)


class MongoAggregateQuery(AggregateQuery[ModelT]):
    """MongoDB aggregate query implementation."""

    def __init__(
        self,
        collection: AsyncIOMotorCollection[Dict[str, Any]],
        model_cls: Type[ModelT],
    ) -> None:
        """Initialize MongoDB aggregate query.

        Args:
            collection: MongoDB collection
            model_cls: Model class
        """
        super().__init__()
        self._collection = collection
        self._model_cls = model_cls

    async def execute(self) -> List[JsonDict]:
        """Execute MongoDB aggregation pipeline.

        Returns:
            List of aggregation results
        """
        pipeline: List[Dict[str, Any]] = []

        # Add group stage
        if self._group_by:
            group_fields = {field: f"${field}" for field in self._group_by}
            group_stage: Dict[str, Any] = {"_id": group_fields}

            # Add aggregates
            for op in self._pipeline:
                if op["type"] == "count":
                    group_stage[op["alias"]] = {"$sum": 1}
                elif op["type"] == "sum":
                    group_stage[op["alias"]] = {"$sum": f"${op['field']}"}
                elif op["type"] == "avg":
                    group_stage[op["alias"]] = {"$avg": f"${op['field']}"}

            pipeline.append({"$group": group_stage})

        # Add having stage
        if self._having:
            pipeline.append({"$match": self._having})

        # Execute pipeline
        cursor = self._collection.aggregate(pipeline)
        return [doc async for doc in cursor]
