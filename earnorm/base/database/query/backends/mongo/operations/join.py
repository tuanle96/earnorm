"""MongoDB join query implementation."""

from typing import Any, Dict, List, Type, TypeVar

from motor.motor_asyncio import AsyncIOMotorCollection

from earnorm.base.database.query.base.operations.join import JoinQuery
from earnorm.types import DatabaseModel, JsonDict

ModelT = TypeVar("ModelT", bound=DatabaseModel)


class MongoJoinQuery(JoinQuery[ModelT]):
    """MongoDB join query implementation."""

    def __init__(
        self,
        collection: AsyncIOMotorCollection[Dict[str, Any]],
        model_cls: Type[ModelT],
    ) -> None:
        """Initialize MongoDB join query.

        Args:
            collection: MongoDB collection
            model_cls: Model class
        """
        super().__init__()
        self._collection = collection
        self._model_cls = model_cls

    async def execute(self) -> List[JsonDict]:
        """Execute MongoDB join query using aggregation pipeline.

        Returns:
            List of joined results
        """
        pipeline: List[Dict[str, Any]] = []

        # Add joins
        for join in self._joins:
            pipeline.append(
                {
                    "$lookup": {
                        "from": join["model"],
                        "localField": list(join["conditions"].keys())[0],
                        "foreignField": list(join["conditions"].values())[0],
                        "as": join["model"],
                    }
                }
            )

            # Handle join type
            if join["type"] == "inner":
                pipeline.append({"$match": {f"{join['model']}": {"$ne": []}}})

        # Add filters
        if self._domain:
            pipeline.append({"$match": self._domain})

        # Add projections
        if self._select:
            pipeline.append({"$project": {field: 1 for field in self._select}})

        # Execute pipeline
        cursor = self._collection.aggregate(pipeline)
        return [doc async for doc in cursor]
