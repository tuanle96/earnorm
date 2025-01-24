"""Metrics model for storing system metrics."""

from datetime import UTC, datetime
from typing import Any, Dict, Optional

from earnorm.base import BaseModel
from earnorm.fields import DateTimeField, DictField, FloatField, StringField


class Metrics(BaseModel):
    """
    System metrics model for storing performance and health metrics.

    Examples:
        >>> # Record system metrics
        >>> metrics = Metrics(
        ...     name="cpu_usage",
        ...     value=45.2,
        ...     tags={"host": "server1", "environment": "production"},
        ...     extra_data={"process_count": 120}
        ... )
        >>> await metrics.save()

        >>> # Query metrics
        >>> cpu_metrics = await Metrics.find(
        ...     {"name": "cpu_usage", "tags.environment": "production"}
        ... ).sort("timestamp", -1).limit(100)

        >>> # Calculate average
        >>> pipeline = [
        ...     {"$match": {"name": "cpu_usage"}},
        ...     {"$group": {"_id": None, "avg": {"$avg": "$value"}}}
        ... ]
        >>> result = await Metrics.aggregate(pipeline).to_list(1)
        >>> avg_cpu = result[0]["avg"] if result else None
    """

    # Required fields
    timestamp = DateTimeField(default=lambda: datetime.now(UTC))
    name = StringField(required=True)
    value = FloatField(required=True)

    # Optional fields
    tags = DictField(default=dict)
    extra_data = DictField(default=dict)

    class Meta:
        collection = "metrics"
        indexes = [
            [("timestamp", -1)],  # Recent metrics first
            [("name", 1)],  # Query by metric name
            [("tags.host", 1)],  # Query by host
            # Compound indexes
            [("name", 1), ("timestamp", -1)],
            [("name", 1), ("tags.host", 1)],
            # TTL index for auto-cleanup
            [("timestamp", 1)],
        ]

    @classmethod
    async def get_metric_stats(
        cls,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
        group_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get statistics for a metric within a time period.

        Args:
            metric_name: Name of the metric
            start_time: Start time for the period
            end_time: End time for the period
            group_by: Optional field to group by (e.g. "tags.host")

        Returns:
            Dictionary containing metric statistics
        """
        group_id = f"${group_by}" if group_by else None

        pipeline = [
            {
                "$match": {
                    "name": metric_name,
                    "timestamp": {"$gte": start_time, "$lte": end_time},
                }
            },
            {
                "$group": {
                    "_id": group_id,
                    "min": {"$min": "$value"},
                    "max": {"$max": "$value"},
                    "avg": {"$avg": "$value"},
                    "count": {"$sum": 1},
                }
            },
        ]

        results = await cls.aggregate(pipeline)
        stats = {}

        async for result in results:
            key = str(result["_id"]) if result["_id"] else "total"
            stats[key] = {
                "min": result["min"],
                "max": result["max"],
                "avg": result["avg"],
                "count": result["count"],
            }

        return stats

    @classmethod
    async def cleanup_old_metrics(cls, days: int = 7) -> int:
        """Clean up metrics older than specified days."""
        result = await cls.delete_many(
            {"timestamp": {"$lt": datetime.now(UTC) - timedelta(days=days)}}
        )
        return result.deleted_count if result else 0
