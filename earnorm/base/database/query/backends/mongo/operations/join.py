"""MongoDB join operation implementation.

This module provides MongoDB-specific implementation for join operations.
It uses MongoDB's $lookup aggregation stage for joins.

Examples:
    >>> class User(DatabaseModel):
    ...     name: str
    ...     age: int
    ...
    >>> class Post(DatabaseModel):
    ...     title: str
    ...     user_id: str
    ...
    >>> query = MongoQuery[User]()
    >>> query.join(Post).on(User.id == Post.user_id)
"""

from typing import Any, Dict, List, Optional, Type, TypeVar, Union, cast

from motor.motor_asyncio import AsyncIOMotorCollection

from earnorm.base.database.query.interfaces.operations.join import JoinProtocol
from earnorm.types import DatabaseModel, JsonDict

ModelT = TypeVar("ModelT", bound=DatabaseModel)
JoinT = TypeVar("JoinT", bound=DatabaseModel)


class MongoJoin(JoinProtocol[ModelT, JoinT]):
    """MongoDB join operation implementation.

    This class provides MongoDB-specific implementation for join operations.
    It uses MongoDB's $lookup aggregation stage for joins.

    Args:
        ModelT: Type of model being queried
        JoinT: Type of model being joined
    """

    def __init__(
        self,
        collection: AsyncIOMotorCollection[Dict[str, Any]],  # type: ignore
        model_cls: Type[ModelT],
    ) -> None:
        """Initialize MongoDB join operation.

        Args:
            collection: MongoDB collection
            model_cls: Model class
        """
        self._collection = collection
        self._model_cls = model_cls
        self._model: Optional[Union[str, Type[JoinT]]] = None
        self._conditions: Dict[str, str] = {}
        self._join_type = "inner"

    def join(
        self,
        model: Union[str, Type[JoinT]],
        on: Optional[Dict[str, str]] = None,
        join_type: str = "inner",
    ) -> JoinProtocol[ModelT, JoinT]:
        """Add join condition.

        Args:
            model: Model to join with
            on: Join conditions {local_field: foreign_field}
            join_type: Join type (inner, left, right, cross, full)

        Returns:
            Self for chaining
        """
        self._model = model
        if on:
            self._conditions.update(on)
        self._join_type = join_type
        return self

    def on(self, *conditions: Any) -> JoinProtocol[ModelT, JoinT]:
        """Add join conditions.

        Args:
            conditions: Join conditions

        Returns:
            Self for chaining
        """
        for condition in conditions:
            if isinstance(condition, dict):
                self._conditions.update(cast(Dict[str, str], condition))
            elif isinstance(condition, tuple):
                self._conditions[condition[0]] = condition[1]
            elif hasattr(condition, "last_comparison"):
                comp = getattr(condition, "last_comparison")
                self._conditions[comp[0]] = comp[1]
        return self

    def inner(self) -> JoinProtocol[ModelT, JoinT]:
        """Make this an inner join.

        Returns:
            Self for chaining
        """
        self._join_type = "inner"
        return self

    def left(self) -> JoinProtocol[ModelT, JoinT]:
        """Make this a left join.

        Returns:
            Self for chaining
        """
        self._join_type = "left"
        return self

    def right(self) -> JoinProtocol[ModelT, JoinT]:
        """Make this a right join.

        Returns:
            Self for chaining
        """
        self._join_type = "right"
        return self

    def full(self) -> JoinProtocol[ModelT, JoinT]:
        """Make this a full join.

        Returns:
            Self for chaining
        """
        self._join_type = "full"
        return self

    def cross(self) -> JoinProtocol[ModelT, JoinT]:
        """Make this a cross join.

        Returns:
            Self for chaining
        """
        self._join_type = "cross"
        return self

    def validate(self) -> None:
        """Validate join configuration.

        Raises:
            ValueError: If join configuration is invalid
        """
        if not self._model:
            raise ValueError("Join model is required")
        if not self._conditions:
            raise ValueError("Join conditions are required")

    def get_pipeline_stages(self) -> List[JsonDict]:
        """Get MongoDB aggregation pipeline stages for this join.

        Returns:
            List[JsonDict]: List of pipeline stages
        """
        if not self._model or not self._conditions:
            return []

        # Get foreign collection name
        foreign_collection = (
            self._model
            if isinstance(self._model, str)
            else getattr(self._model, "__collection__", self._model.__name__.lower())
        )

        # Build $lookup stage
        lookup_stage = {
            "$lookup": {
                "from": foreign_collection,
                "let": {field: f"${field}" for field in self._conditions.keys()},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {
                                        "$eq": [
                                            f"${foreign_field}",
                                            f"$$${local_field}",
                                        ]
                                    }
                                    for local_field, foreign_field in self._conditions.items()
                                ]
                            }
                        }
                    }
                ],
                "as": foreign_collection,
            }
        }

        # For inner join, add $unwind stage
        stages = [lookup_stage]
        if self._join_type == "inner":
            stages.append(
                {
                    "$unwind": {
                        "path": f"${foreign_collection}",
                        "preserveNullAndEmptyArrays": False,
                    }
                }
            )
        elif self._join_type == "left":
            stages.append(
                {
                    "$unwind": {
                        "path": f"${foreign_collection}",
                        "preserveNullAndEmptyArrays": True,
                    }
                }
            )

        return stages

    def to_pipeline(self) -> List[JsonDict]:
        """Convert join operation to MongoDB pipeline.

        Returns:
            List of pipeline stages

        Raises:
            ValueError: If join type is not supported by MongoDB
        """
        if not self._model:
            raise ValueError("Join model not specified")

        # Get collection name from model
        collection_name = (
            self._model
            if isinstance(self._model, str)
            else getattr(self._model, "__collection__", self._model.__name__.lower())
        )

        # Build lookup stage
        lookup_stage: JsonDict = {
            "$lookup": {
                "from": collection_name,
                "let": {},  # Will be filled with local variables
                "pipeline": [],  # Will be filled with match conditions
                "as": collection_name,  # Store joined documents in array field
            }
        }

        # Add join conditions
        if self._conditions:
            # Convert conditions to MongoDB format
            match_conditions: JsonDict = {}
            let_vars: JsonDict = {}

            for local_field, foreign_field in self._conditions.items():
                # Remove $ prefix if present
                local_field = local_field.replace("$", "")
                foreign_field = foreign_field.replace("$", "")

                # Add to let vars
                let_var_name = f"local_{local_field}"
                let_vars[let_var_name] = f"${local_field}"

                # Add to match conditions
                match_conditions[foreign_field] = {
                    "$eq": [f"$${let_var_name}", f"${foreign_field}"]
                }

            # Update lookup stage
            lookup_stage["$lookup"]["let"] = let_vars
            lookup_stage["$lookup"]["pipeline"].append({"$match": match_conditions})

        # Handle different join types
        pipeline: List[JsonDict] = [lookup_stage]

        if self._join_type == "inner":
            # Filter out documents with no matches
            pipeline.append(
                {"$match": {collection_name: {"$ne": None, "$not": {"$size": 0}}}}
            )
        elif self._join_type == "left":
            # Left join is default in MongoDB
            pass
        elif self._join_type in ("right", "full"):
            raise ValueError(
                f"Join type '{self._join_type}' is not supported by MongoDB"
            )

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
