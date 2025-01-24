"""Cleanup module for log maintenance."""

from datetime import UTC, datetime, timedelta
from typing import Dict, List, Optional

from earnorm.logging.models.log import Log
from earnorm.logging.models.metrics import Metrics


class LogMaintenance:
    """
    Maintenance operations for log data.

    Examples:
        >>> maintenance = LogMaintenance()
        >>> # Clean up old logs
        >>> cleaned = await maintenance.cleanup_old_logs(
        ...     max_age_days=30,
        ...     batch_size=1000
        ... )
        >>> print(f"Cleaned up {cleaned} logs")

        >>> # Archive logs
        >>> archived = await maintenance.archive_logs(
        ...     start_time=datetime.now(UTC) - timedelta(days=90),
        ...     end_time=datetime.now(UTC) - timedelta(days=60)
        ... )
        >>> print(f"Archived {archived} logs")
    """

    async def cleanup_old_logs(
        self,
        max_age_days: int = 30,
        batch_size: int = 1000,
        exclude_levels: Optional[List[str]] = None,
    ) -> int:
        """
        Clean up logs older than specified age.

        Args:
            max_age_days: Maximum age of logs to keep
            batch_size: Size of deletion batches
            exclude_levels: Log levels to exclude from cleanup

        Returns:
            Number of logs cleaned up
        """
        cutoff_time = datetime.now(UTC) - timedelta(days=max_age_days)

        # Build query
        query = {"timestamp": {"$lt": cutoff_time}}
        if exclude_levels:
            query["level"] = {"$nin": exclude_levels}

        total_deleted = 0
        while True:
            # Get batch of logs to delete
            logs = await Log.find(query).limit(batch_size)

            # Break if no more logs
            batch = await logs.to_list(length=batch_size)
            if not batch:
                break

            # Delete batch
            result = await Log.delete_many(
                {"_id": {"$in": [log["_id"] for log in batch]}}
            )

            total_deleted += result.deleted_count

        return total_deleted

    async def archive_logs(
        self,
        start_time: datetime,
        end_time: datetime,
        target_collection: str = "archived_logs",
        batch_size: int = 1000,
    ) -> int:
        """
        Archive logs within time range to another collection.

        Args:
            start_time: Start of time range
            end_time: End of time range
            target_collection: Name of archive collection
            batch_size: Size of archival batches

        Returns:
            Number of logs archived
        """
        # Build query
        query = {"timestamp": {"$gte": start_time, "$lte": end_time}}

        total_archived = 0
        while True:
            # Get batch of logs to archive
            logs = await Log.find(query).limit(batch_size)

            # Break if no more logs
            batch = await logs.to_list(length=batch_size)
            if not batch:
                break

            # Insert into archive collection
            await Log.get_collection(target_collection).insert_many(batch)

            # Delete from main collection
            result = await Log.delete_many(
                {"_id": {"$in": [log["_id"] for log in batch]}}
            )

            total_archived += result.deleted_count

        return total_archived

    async def cleanup_metrics(
        self, max_age_days: int = 7, batch_size: int = 1000
    ) -> int:
        """
        Clean up old metrics data.

        Args:
            max_age_days: Maximum age of metrics to keep
            batch_size: Size of deletion batches

        Returns:
            Number of metrics cleaned up
        """
        return await Metrics.cleanup_old_metrics(days=max_age_days)

    async def get_storage_stats(self) -> Dict[str, int]:
        """
        Get storage statistics for logs and metrics.

        Returns:
            Dictionary containing collection sizes
        """
        stats = {}

        # Get log collection stats
        log_stats = await Log.get_collection().stats()
        stats["logs"] = {
            "count": log_stats.get("count", 0),
            "size": log_stats.get("size", 0),
            "avg_obj_size": log_stats.get("avgObjSize", 0),
        }

        # Get metrics collection stats
        metrics_stats = await Metrics.get_collection().stats()
        stats["metrics"] = {
            "count": metrics_stats.get("count", 0),
            "size": metrics_stats.get("size", 0),
            "avg_obj_size": metrics_stats.get("avgObjSize", 0),
        }

        # Get archived logs stats if collection exists
        try:
            archive_stats = await Log.get_collection("archived_logs").stats()
            stats["archived_logs"] = {
                "count": archive_stats.get("count", 0),
                "size": archive_stats.get("size", 0),
                "avg_obj_size": archive_stats.get("avgObjSize", 0),
            }
        except Exception:
            stats["archived_logs"] = None

        return stats
