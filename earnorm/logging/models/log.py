"""Log model for storing log entries."""

from datetime import UTC, datetime, timedelta
from typing import Any, Coroutine, Dict

from bson import ObjectId

from earnorm.base import BaseModel
from earnorm.fields import DateTimeField, DictField, ListField, StringField


class Log(BaseModel):
    """
    Log entry model for storing application logs.

    Examples:
        >>> log = Log(
        ...     level="INFO",
        ...     module="earnorm.base",
        ...     message="Operation completed successfully",
        ...     trace_id="abc123",
        ...     user_id="user123",
        ...     model="User",
        ...     model_id="123",
        ...     operation="create",
        ...     extra_data={"name": "John"},
        ... )
        >>> await log.save()

        >>> # Query logs
        >>> logs = await Log.find(
        ...     {"level": "ERROR", "module": "earnorm.base"}
        ... ).sort("timestamp", -1).limit(10)

        >>> # Clean up old logs
        >>> await Log.delete_many(
        ...     {"timestamp": {"$lt": datetime.now(UTC) - timedelta(days=30)}}
        ... )
    """

    # Required fields
    timestamp = DateTimeField(default=lambda: datetime.now(UTC))
    level = StringField(required=True)
    module = StringField(required=True)
    message = StringField(required=True)

    # Context fields
    trace_id = StringField()
    user_id = StringField()
    model = StringField()
    model_id = StringField()
    operation = StringField()

    # Additional data
    extra_data = DictField(default=dict)
    error_type = StringField()
    error_message = StringField()
    stack_trace = ListField(StringField(), default=list)

    # Environment
    host = StringField()
    environment = StringField()

    class Meta:
        collection = "logs"
        indexes = [
            [("timestamp", -1)],  # Recent logs first
            [("level", 1)],  # Query by level
            [("module", 1)],  # Query by module
            [("trace_id", 1)],  # Query by trace
            [("user_id", 1)],  # Query by user
            [("model", 1)],  # Query by model
            [("operation", 1)],  # Query by operation
            [("environment", 1)],  # Query by environment
            # Compound indexes
            [("level", 1), ("timestamp", -1)],
            [("module", 1), ("timestamp", -1)],
            # TTL index for auto-cleanup
            [("timestamp", 1)],
        ]

    async def save(self, *args: Any, **kwargs: Any) -> Coroutine[Any, Any, None]:
        """Save log entry with automatic timestamp."""
        if not self.timestamp:
            self.timestamp = datetime.now(UTC)
        return await super().save(*args, **kwargs)

    @classmethod
    async def cleanup_old_logs(cls, days: int = 30) -> int:
        """Clean up logs older than specified days."""
        result = await cls.delete_many(
            {"timestamp": {"$lt": datetime.now(UTC) - timedelta(days=days)}}
        )
        return result.deleted_count if result else 0

    @classmethod
    async def get_log_stats(
        cls, start_time: datetime, end_time: datetime
    ) -> Dict[str, Any]:
        """Get log statistics for a time period."""
        pipeline = [
            {"$match": {"timestamp": {"$gte": start_time, "$lte": end_time}}},
            {"$group": {"_id": "$level", "count": {"$sum": 1}}},
        ]

        results = await cls.aggregate(pipeline)
        stats = {"total": 0}
        async for result in results:
            level = result["_id"]
            count = result["count"]
            stats[level.lower()] = count
            stats["total"] += count

        return stats
