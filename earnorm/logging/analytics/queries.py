"""Queries module for log analytics."""

from datetime import datetime, timedelta
from typing import Any, AsyncIterator, Dict, List, Optional, TypedDict, cast

from earnorm.logging.models.log import Log


class ErrorExample(TypedDict):
    """Type definition for error example."""

    message: str
    module: str
    timestamp: datetime


class ErrorTrend(TypedDict):
    """Type definition for error trend."""

    timestamp: datetime
    error_type: str
    count: int
    examples: List[ErrorExample]


class SlowOperation(TypedDict):
    """Type definition for slow operation."""

    timestamp: datetime
    module: str
    operation: str
    duration_ms: int
    extra_data: Dict[str, Any]


class VolumePoint(TypedDict):
    """Type definition for volume data point."""

    timestamp: datetime
    count: int


class MongoResult(TypedDict):
    """Type definition for MongoDB result."""

    _id: Any
    count: int
    examples: List[Dict[str, Any]]


class MongoAggregateResult(AsyncIterator[Dict[str, Any]]):
    """MongoDB aggregation result iterator."""

    def __init__(self, cursor: Any) -> None:
        """Initialize result iterator.

        Args:
            cursor: MongoDB cursor
        """
        self._cursor = cursor

    async def __anext__(self) -> Dict[str, Any]:
        """Get next result.

        Returns:
            Dict[str, Any]: Next result

        Raises:
            StopAsyncIteration: When no more results
        """
        try:
            result = await self._cursor.__anext__()
            if result is None:
                raise StopAsyncIteration
            return cast(Dict[str, Any], result)
        except StopAsyncIteration:
            raise


class LogAnalytics:
    """Analytics for log data."""

    async def get_error_distribution(
        self, start_time: datetime, end_time: datetime, module: Optional[str] = None
    ) -> Dict[str, int]:
        """Get error distribution."""
        if start_time > end_time:
            raise ValueError("start_time must be before end_time")

        match = {"level": "ERROR", "timestamp": {"$gte": start_time, "$lte": end_time}}

        if module:
            match["module"] = module

        pipeline = [
            {"$match": match},
            {"$group": {"_id": "$error_type", "count": {"$sum": 1}}},
        ]

        cursor = await Log.aggregate(pipeline)  # type: ignore
        results = MongoAggregateResult(cursor)
        distribution: Dict[str, int] = {}

        async for raw_result in results:
            result = cast(MongoResult, raw_result)
            error_type = str(result["_id"]) or "Unknown"
            distribution[error_type] = result["count"]

        return distribution

    async def get_log_volume_by_level(
        self, start_time: datetime, end_time: datetime, interval_minutes: int = 5
    ) -> Dict[str, List[VolumePoint]]:
        """Get log volume by level over time intervals.

        Args:
            start_time: Start of time range
            end_time: End of time range
            interval_minutes: Size of time intervals in minutes

        Returns:
            Dictionary mapping levels to lists of counts by interval

        Raises:
            ValueError: If start_time is after end_time or interval_minutes <= 0
            TypeError: If start_time or end_time are not datetime objects
        """
        if start_time > end_time:
            raise ValueError("start_time must be before end_time")
        if interval_minutes <= 0:
            raise ValueError("interval_minutes must be positive")

        pipeline = [
            {"$match": {"timestamp": {"$gte": start_time, "$lte": end_time}}},
            {
                "$group": {
                    "_id": {
                        "level": "$level",
                        "interval": {
                            "$subtract": [
                                {"$subtract": ["$timestamp", start_time]},
                                {
                                    "$mod": [
                                        {"$subtract": ["$timestamp", start_time]},
                                        interval_minutes * 60 * 1000,
                                    ]
                                },
                            ]
                        },
                    },
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"_id.interval": 1}},
        ]

        results: MongoAggregateResult = await Log.aggregate(pipeline)  # type: ignore
        volume: Dict[str, List[VolumePoint]] = {}

        async for result in results:
            result_dict = cast(MongoResult, result)
            level = str(result_dict["_id"]["level"])
            interval = int(result_dict["_id"]["interval"])
            count = result_dict["count"]

            if level not in volume:
                volume[level] = []

            volume[level].append(
                {
                    "timestamp": start_time + timedelta(milliseconds=interval),
                    "count": count,
                }
            )

        return volume

    async def get_slow_operations(
        self,
        start_time: datetime,
        end_time: datetime,
        threshold_ms: int = 1000,
        limit: int = 10,
    ) -> List[SlowOperation]:
        """Get slow operations exceeding threshold.

        Args:
            start_time: Start of time range
            end_time: End of time range
            threshold_ms: Threshold in milliseconds
            limit: Maximum number of results

        Returns:
            List of slow operations with details

        Raises:
            ValueError: If start_time is after end_time, threshold_ms <= 0, or limit <= 0
            TypeError: If start_time or end_time are not datetime objects
        """
        if start_time > end_time:
            raise ValueError("start_time must be before end_time")
        if threshold_ms <= 0:
            raise ValueError("threshold_ms must be positive")
        if limit <= 0:
            raise ValueError("limit must be positive")

        pipeline = [
            {
                "$match": {
                    "timestamp": {"$gte": start_time, "$lte": end_time},
                    "extra_data.duration_ms": {"$gte": threshold_ms},
                }
            },
            {
                "$project": {
                    "timestamp": 1,
                    "module": 1,
                    "operation": 1,
                    "duration_ms": "$extra_data.duration_ms",
                    "extra_data": 1,
                }
            },
            {"$sort": {"duration_ms": -1}},
            {"$limit": limit},
        ]

        results: MongoAggregateResult = await Log.aggregate(pipeline)  # type: ignore
        operations: List[SlowOperation] = []

        async for result in results:
            result_dict = cast(SlowOperation, result)
            operations.append(result_dict)

        return operations

    async def get_error_trends(
        self, start_time: datetime, end_time: datetime, interval_minutes: int = 60
    ) -> List[ErrorTrend]:
        """Get error trends over time.

        Args:
            start_time: Start of time range
            end_time: End of time range
            interval_minutes: Size of time intervals in minutes

        Returns:
            List of error counts by interval with details

        Raises:
            ValueError: If start_time is after end_time or interval_minutes <= 0
            TypeError: If start_time or end_time are not datetime objects
        """
        if start_time > end_time:
            raise ValueError("start_time must be before end_time")
        if interval_minutes <= 0:
            raise ValueError("interval_minutes must be positive")

        pipeline = [
            {
                "$match": {
                    "level": "ERROR",
                    "timestamp": {"$gte": start_time, "$lte": end_time},
                }
            },
            {
                "$group": {
                    "_id": {
                        "interval": {
                            "$subtract": [
                                {"$subtract": ["$timestamp", start_time]},
                                {
                                    "$mod": [
                                        {"$subtract": ["$timestamp", start_time]},
                                        interval_minutes * 60 * 1000,
                                    ]
                                },
                            ]
                        },
                        "error_type": "$error_type",
                    },
                    "count": {"$sum": 1},
                    "examples": {
                        "$push": {
                            "message": "$error_message",
                            "module": "$module",
                            "timestamp": "$timestamp",
                        }
                    },
                }
            },
            {"$sort": {"_id.interval": 1}},
        ]

        results: MongoAggregateResult = await Log.aggregate(pipeline)  # type: ignore
        trends: List[ErrorTrend] = []

        async for result in results:
            result_dict = cast(MongoResult, result)
            interval = int(result_dict["_id"]["interval"])
            error_type = str(result_dict["_id"]["error_type"]) or "Unknown"
            examples = cast(List[ErrorExample], result_dict["examples"][:3])

            trends.append(
                {
                    "timestamp": start_time + timedelta(milliseconds=interval),
                    "error_type": error_type,
                    "count": result_dict["count"],
                    "examples": examples,
                }
            )

        return trends
