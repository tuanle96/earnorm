"""MongoDB group query implementation."""

from typing import Any, Dict, List, Type, TypeVar

from motor.motor_asyncio import AsyncIOMotorCollection

from earnorm.base.database.query.base.operations.group import GroupQuery
from earnorm.types import DatabaseModel, JsonDict

ModelT = TypeVar("ModelT", bound=DatabaseModel)


class MongoGroupQuery(GroupQuery[ModelT]):
    """MongoDB group query implementation."""

    def __init__(
        self,
        collection: AsyncIOMotorCollection[Dict[str, Any]],
        model_cls: Type[ModelT],
    ) -> None:
        """Initialize MongoDB group query.

        Args:
            collection: MongoDB collection
            model_cls: Model class
        """
        super().__init__()
        self._collection = collection
        self._model_cls = model_cls

    async def execute(self) -> List[JsonDict]:
        """Execute MongoDB group query.

        Returns:
            List of grouped results
        """
        pipeline: List[Dict[str, Any]] = []

        # Build group stage
        group_stage: Dict[str, Any] = {
            "_id": {field: f"${field}" for field in self._group_fields}
        }

        # Add aggregates
        for agg in self._aggregates:
            if agg["type"] == "count":
                group_stage[agg["alias"]] = {"$sum": 1}
            elif agg["type"] == "sum":
                group_stage[agg["alias"]] = {"$sum": f"${agg['field']}"}
            elif agg["type"] == "avg":
                group_stage[agg["alias"]] = {"$avg": f"${agg['field']}"}

        pipeline.append({"$group": group_stage})

        # Add having
        if self._having:
            pipeline.append({"$match": self._having})

        # Execute pipeline
        cursor = self._collection.aggregate(pipeline)
        return [doc async for doc in cursor]
