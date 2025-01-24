"""Reports module for generating log analytics reports."""

from datetime import datetime, timedelta
from typing import Any, AsyncIterator, Dict, List, Optional, Sequence, TypedDict, cast

from earnorm.logging.analytics.queries import LogAnalytics
from earnorm.logging.models.log import Log
from earnorm.logging.models.metrics import Metrics


class LogStats(TypedDict):
    """Type definition for log statistics."""

    total: int
    error: int
    warning: int


class LogPeriod(TypedDict):
    """Type definition for time period."""

    start: str
    end: str


class LogSummary(TypedDict):
    """Type definition for log summary."""

    total_logs: int
    error_count: int
    warning_count: int


class ErrorDistribution(TypedDict):
    """Type definition for error distribution."""

    distribution: Dict[str, int]
    examples: Sequence[Dict[str, Any]]


class DailyReport(TypedDict):
    """Type definition for daily report."""

    date: str
    period: LogPeriod
    summary: LogSummary
    errors: ErrorDistribution
    volume: Dict[str, List[Dict[str, Any]]]
    metrics: Optional[Dict[str, Any]]


class ModuleError(TypedDict):
    """Type definition for module error."""

    count: int
    examples: List[Dict[str, Any]]


class ErrorSummary(TypedDict):
    """Type definition for error summary."""

    period: LogPeriod
    trends: List[Dict[str, Any]]
    by_module: Optional[Dict[str, Dict[str, ModuleError]]]


class MongoResult(TypedDict):
    """Type definition for MongoDB result."""

    _id: Dict[str, str]
    count: int
    examples: List[Dict[str, Any]]


class MongoAggregateResult(AsyncIterator[Dict[str, Any]]):
    """Type definition for MongoDB aggregate result."""

    async def __anext__(self) -> Dict[str, Any]:
        """Get next result."""
        ...


class LogReports:
    """Generate reports from log analytics."""

    def __init__(self):
        """Initialize the reports generator."""
        self.analytics = LogAnalytics()

    async def generate_daily_report(
        self, date: datetime, include_metrics: bool = True
    ) -> DailyReport:
        """Generate a daily report for the specified date."""
        start_time = datetime.combine(date, datetime.min.time())
        end_time = start_time + timedelta(days=1)

        # Get log statistics
        log_stats = await Log.get_log_stats(start_time, end_time)  # type: ignore

        # Get error distribution
        error_dist = await self.analytics.get_error_distribution(
            start_time=start_time, end_time=end_time
        )

        # Get log volume by level
        volume = await self.analytics.get_log_volume_by_level(
            start_time=start_time, end_time=end_time, interval_minutes=60
        )

        # Get slow operations
        slow_ops = await self.analytics.get_slow_operations(
            start_time=start_time, end_time=end_time, threshold_ms=1000, limit=10
        )

        # Convert volume data to dictionary format
        volume_dict = {
            level: [
                {"timestamp": point["timestamp"].isoformat(), "count": point["count"]}
                for point in points
            ]
            for level, points in volume.items()
        }

        # Convert slow operations to dictionary format
        slow_ops_dict = [
            {
                "timestamp": op["timestamp"].isoformat(),
                "module": op["module"],
                "operation": op["operation"],
                "duration_ms": op["duration_ms"],
                "extra_data": op["extra_data"],
            }
            for op in slow_ops
        ]

        report: DailyReport = {
            "date": date.isoformat(),
            "period": {"start": start_time.isoformat(), "end": end_time.isoformat()},
            "summary": {
                "total_logs": log_stats["total"],
                "error_count": log_stats.get("error", 0),
                "warning_count": log_stats.get("warning", 0),
            },
            "errors": {"distribution": error_dist, "examples": slow_ops_dict},
            "volume": volume_dict,
            "metrics": None,
        }

        # Include metrics if requested
        if include_metrics:
            report["metrics"] = await self._get_daily_metrics(start_time, end_time)

        return report

    async def generate_error_summary(
        self, start_time: datetime, end_time: datetime, group_by_module: bool = True
    ) -> ErrorSummary:
        """Generate an error summary report."""
        if start_time > end_time:
            raise ValueError("start_time must be before end_time")

        # Get error trends
        trends = await self.analytics.get_error_trends(
            start_time=start_time, end_time=end_time, interval_minutes=30
        )

        # Convert trends to dictionary format
        trends_dict = [
            {
                "timestamp": trend["timestamp"].isoformat(),
                "error_type": trend["error_type"],
                "count": trend["count"],
                "examples": [
                    {
                        "message": ex["message"],
                        "module": ex["module"],
                        "timestamp": ex["timestamp"].isoformat(),
                    }
                    for ex in trend["examples"]
                ],
            }
            for trend in trends
        ]

        # Get error distribution by module if requested
        modules_dist: Dict[str, Dict[str, ModuleError]] = {}
        if group_by_module:
            pipeline = [
                {
                    "$match": {
                        "level": "ERROR",
                        "timestamp": {"$gte": start_time, "$lte": end_time},
                    }
                },
                {
                    "$group": {
                        "_id": {"module": "$module", "error_type": "$error_type"},
                        "count": {"$sum": 1},
                        "examples": {
                            "$push": {
                                "message": "$error_message",
                                "timestamp": "$timestamp",
                            }
                        },
                    }
                },
            ]

            results: MongoAggregateResult = await Log.aggregate(pipeline)  # type: ignore

            async for result in results:
                result_dict = cast(MongoResult, result)
                module = result_dict["_id"]["module"] or "unknown"
                error_type = result_dict["_id"]["error_type"] or "Unknown"

                if module not in modules_dist:
                    modules_dist[module] = {}

                modules_dist[module][error_type] = {
                    "count": result["count"],
                    "examples": result["examples"][:3],  # Limit examples
                }

        return {
            "period": {"start": start_time.isoformat(), "end": end_time.isoformat()},
            "trends": trends_dict,
            "by_module": modules_dist if group_by_module else None,
        }

    async def _get_daily_metrics(
        self, start_time: datetime, end_time: datetime
    ) -> Dict[str, Any]:
        """Get system metrics for the daily report."""
        if start_time > end_time:
            raise ValueError("start_time must be before end_time")

        metrics: Dict[str, Any] = {}

        # CPU usage
        cpu_stats = await Metrics.get_metric_stats(  # type: ignore
            metric_name="cpu_usage", start_time=start_time, end_time=end_time
        )
        if cpu_stats:
            metrics["cpu"] = cpu_stats

        # Memory usage
        memory_stats = await Metrics.get_metric_stats(  # type: ignore
            metric_name="memory_usage", start_time=start_time, end_time=end_time
        )
        if memory_stats:
            metrics["memory"] = memory_stats

        # Database connections
        db_stats = await Metrics.get_metric_stats(  # type: ignore
            metric_name="db_connections", start_time=start_time, end_time=end_time
        )
        if db_stats:
            metrics["database"] = db_stats

        return metrics
