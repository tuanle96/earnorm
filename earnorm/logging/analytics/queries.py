"""Log analyzer module.

This module provides tools for analyzing logs through queries and aggregations.
It supports various analysis types like error trends, performance metrics,
and custom aggregations.

Examples:
    >>> analyzer = LogAnalyzer()
    >>> 
    >>> # Get error trends
    >>> trends = await analyzer.get_error_trends(days=7)
    >>> 
    >>> # Get performance metrics
    >>> metrics = await analyzer.get_performance_metrics(
    ...     start_time=datetime(2024, 1, 1),
    ...     end_time=datetime(2024, 1, 7)
    ... )
"""

from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from earnorm.logging.models.log import Log


class LogAnalyzer:
    """Class for analyzing logs.

    This class provides methods for:
    - Querying logs with filters
    - Calculating statistics and trends
    - Generating performance metrics
    """

    def __init__(self) -> None:
        """Initialize the analyzer."""
        pass

    async def get_error_trends(
        self,
        days: int = 7,
        interval: str = "1h",
        error_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Get error trends over time.

        Args:
            days: Number of days to analyze
            interval: Time interval for grouping (e.g. 1h, 1d)
            error_types: List of error types to filter by

        Returns:
            List of error counts by interval

        Raises:
            ValueError: If days is negative or interval is invalid
        """
        if days < 0:
            raise ValueError("days must be >= 0")

        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=days)

        # Build pipeline
        pipeline = [
            {
                "$match": {
                    "level": "ERROR",
                    "timestamp": {"$gte": start_time, "$lte": end_time},
                }
            }
        ]

        if error_types:
            pipeline.append({"$match": {"error_type": {"$in": error_types}}})

        # Group by interval
        pipeline.extend(
            [
                {
                    "$group": {
                        "_id": {
                            "interval": {
                                "$dateTrunc": {
                                    "date": "$timestamp",
                                    "unit": interval[:-1],  # Remove h/d suffix
                                    "binSize": int(interval[:-1]),
                                }
                            },
                            "error_type": "$error_type",
                        },
                        "count": {"$sum": 1},
                    }
                },
                {"$sort": {"_id.interval": 1}},
            ]
        )

        # Execute pipeline
        results = await Log.aggregate(pipeline)
        return [
            {
                "time": r["_id"]["interval"],
                "error_type": r["_id"]["error_type"],
                "count": r["count"],
            }
            for r in results
        ]

    async def get_performance_metrics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        service: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get performance metrics for a time period.

        Args:
            start_time: Start of time period
            end_time: End of time period
            service: Service name to filter by

        Returns:
            Dictionary with performance metrics:
            - request_count: Total number of requests
            - avg_response_time: Average response time
            - error_rate: Error rate percentage
            - p95_response_time: 95th percentile response time
        """
        end_time = end_time or datetime.now(UTC)
        start_time = start_time or (end_time - timedelta(days=1))

        # Build match stage
        match = {"timestamp": {"$gte": start_time, "$lte": end_time}, "type": "request"}
        if service:
            match["service"] = service

        # Build pipeline
        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": None,
                    "request_count": {"$sum": 1},
                    "error_count": {
                        "$sum": {"$cond": [{"$eq": ["$level", "ERROR"]}, 1, 0]}
                    },
                    "total_time": {"$sum": "$response_time"},
                    "response_times": {"$push": "$response_time"},
                }
            },
            {
                "$project": {
                    "request_count": 1,
                    "error_rate": {
                        "$multiply": [
                            {"$divide": ["$error_count", "$request_count"]},
                            100,
                        ]
                    },
                    "avg_response_time": {"$divide": ["$total_time", "$request_count"]},
                    "p95_response_time": {
                        "$arrayElemAt": [
                            "$response_times",
                            {"$floor": {"$multiply": [0.95, "$request_count"]}},
                        ]
                    },
                }
            },
        ]

        # Execute pipeline
        results = await Log.aggregate(pipeline)
        return (
            results[0]
            if results
            else {
                "request_count": 0,
                "error_rate": 0.0,
                "avg_response_time": 0.0,
                "p95_response_time": 0.0,
            }
        )

    async def get_log_patterns(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        min_occurrences: int = 5,
    ) -> List[Dict[str, Any]]:
        """Get common log message patterns.

        This method finds repeated log patterns by:
        1. Grouping similar messages
        2. Counting occurrences
        3. Sorting by frequency

        Args:
            start_time: Start of time period
            end_time: End of time period
            min_occurrences: Minimum number of occurrences

        Returns:
            List of patterns with counts
        """
        end_time = end_time or datetime.now(UTC)
        start_time = start_time or (end_time - timedelta(days=1))

        pipeline = [
            {"$match": {"timestamp": {"$gte": start_time, "$lte": end_time}}},
            {
                "$group": {
                    "_id": "$message",
                    "count": {"$sum": 1},
                    "level": {"$first": "$level"},
                    "first_seen": {"$min": "$timestamp"},
                    "last_seen": {"$max": "$timestamp"},
                }
            },
            {"$match": {"count": {"$gte": min_occurrences}}},
            {"$sort": {"count": -1}},
            {
                "$project": {
                    "pattern": "$_id",
                    "count": 1,
                    "level": 1,
                    "first_seen": 1,
                    "last_seen": 1,
                    "_id": 0,
                }
            },
        ]

        results = await Log.aggregate(pipeline)
        return results

    async def get_service_stats(
        self, services: Optional[List[str]] = None, days: int = 1
    ) -> Dict[str, Dict[str, Any]]:
        """Get statistics for each service.

        Args:
            services: List of services to include
            days: Number of days to analyze

        Returns:
            Dictionary with service stats:
            - log_count: Total number of logs
            - error_count: Number of errors
            - warning_count: Number of warnings
            - avg_response_time: Average response time
        """
        if days < 0:
            raise ValueError("days must be >= 0")

        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=days)

        # Build match stage
        match = {"timestamp": {"$gte": start_time, "$lte": end_time}}
        if services:
            match["service"] = {"$in": services}

        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": "$service",
                    "log_count": {"$sum": 1},
                    "error_count": {
                        "$sum": {"$cond": [{"$eq": ["$level", "ERROR"]}, 1, 0]}
                    },
                    "warning_count": {
                        "$sum": {"$cond": [{"$eq": ["$level", "WARNING"]}, 1, 0]}
                    },
                    "total_time": {"$sum": {"$ifNull": ["$response_time", 0]}},
                    "request_count": {
                        "$sum": {"$cond": [{"$eq": ["$type", "request"]}, 1, 0]}
                    },
                }
            },
            {
                "$project": {
                    "log_count": 1,
                    "error_count": 1,
                    "warning_count": 1,
                    "avg_response_time": {
                        "$cond": [
                            {"$gt": ["$request_count", 0]},
                            {"$divide": ["$total_time", "$request_count"]},
                            0,
                        ]
                    },
                }
            },
        ]

        results = await Log.aggregate(pipeline)
        return {
            r["_id"]: {
                "log_count": r["log_count"],
                "error_count": r["error_count"],
                "warning_count": r["warning_count"],
                "avg_response_time": r["avg_response_time"],
            }
            for r in results
        }
