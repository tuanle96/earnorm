"""Archive module for log maintenance."""

import gzip
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from earnorm.logging.models.log import Log
from earnorm.utils import dumps


class LogArchiver:
    """
    Archive logs to files and manage archived data.

    Examples:
        >>> archiver = LogArchiver("/path/to/archives")
        >>> # Archive logs to file
        >>> archived = await archiver.archive_to_file(
        ...     start_time=datetime.now(UTC) - timedelta(days=90),
        ...     end_time=datetime.now(UTC) - timedelta(days=60)
        ... )
        >>> print(f"Archived {archived} logs")

        >>> # List archive files
        >>> files = archiver.list_archive_files()
        >>> for file in files:
        ...     print(file)

        >>> # Read archived logs
        >>> logs = await archiver.read_archive_file(
        ...     "logs_2024_01.gz"
        ... )
        >>> print(f"Found {len(logs)} logs")
    """

    def __init__(self, archive_dir: Union[str, Path]):
        """
        Initialize the log archiver.

        Args:
            archive_dir: Directory to store archive files
        """
        self.archive_dir = Path(archive_dir)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    def _get_archive_filename(self, start_time: datetime, end_time: datetime) -> str:
        """Generate archive filename from time range."""
        return (
            f"logs_{start_time.strftime('%Y_%m_%d')}_"
            f"to_{end_time.strftime('%Y_%m_%d')}.gz"
        )

    async def archive_to_file(
        self,
        start_time: datetime,
        end_time: datetime,
        batch_size: int = 1000,
        delete_after: bool = True,
    ) -> int:
        """
        Archive logs to compressed file.

        Args:
            start_time: Start of time range
            end_time: End of time range
            batch_size: Size of processing batches
            delete_after: Whether to delete logs after archiving

        Returns:
            Number of logs archived
        """
        filename = self._get_archive_filename(start_time, end_time)
        filepath = self.archive_dir / filename

        # Build query
        query = {"timestamp": {"$gte": start_time, "$lte": end_time}}

        total_archived = 0
        with gzip.open(filepath, "wt", encoding="utf-8") as f:
            while True:
                # Get batch of logs
                logs = await Log.find(query).limit(batch_size)

                # Break if no more logs
                batch = await logs.to_list(length=batch_size)
                if not batch:
                    break

                # Write logs to file
                for log in batch:
                    f.write(dumps(log) + "\n")

                if delete_after:
                    # Delete processed logs
                    result = await Log.delete_many(
                        {"_id": {"$in": [log["_id"] for log in batch]}}
                    )
                    total_archived += result.deleted_count
                else:
                    total_archived += len(batch)

        return total_archived

    def list_archive_files(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> List[Path]:
        """
        List archive files in date range.

        Args:
            start_date: Start date for filtering
            end_date: End date for filtering

        Returns:
            List of archive file paths
        """
        files = sorted(self.archive_dir.glob("logs_*.gz"))

        if not (start_date or end_date):
            return files

        filtered = []
        for file in files:
            # Extract date from filename
            try:
                date_str = file.stem.split("_")[1:4]  # ['YYYY', 'MM', 'DD']
                file_date = datetime.strptime("_".join(date_str), "%Y_%m_%d")

                if start_date and file_date < start_date:
                    continue
                if end_date and file_date > end_date:
                    continue

                filtered.append(file)
            except (IndexError, ValueError):
                continue

        return filtered

    async def read_archive_file(
        self,
        filename: Union[str, Path],
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Read logs from archive file.

        Args:
            filename: Name of archive file
            start_time: Optional start time filter
            end_time: Optional end time filter

        Returns:
            List of log entries
        """
        filepath = self.archive_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Archive file not found: {filename}")

        logs = []
        with gzip.open(filepath, "rt", encoding="utf-8") as f:
            for line in f:
                try:
                    log = json.loads(line.strip())

                    # Apply time filter if specified
                    if start_time or end_time:
                        log_time = datetime.fromisoformat(log["timestamp"])

                        if start_time and log_time < start_time:
                            continue
                        if end_time and log_time > end_time:
                            continue

                    logs.append(log)
                except (json.JSONDecodeError, KeyError):
                    continue

        return logs

    async def restore_from_file(
        self,
        filename: Union[str, Path],
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        batch_size: int = 1000,
    ) -> int:
        """
        Restore logs from archive file to database.

        Args:
            filename: Name of archive file
            start_time: Optional start time filter
            end_time: Optional end time filter
            batch_size: Size of insertion batches

        Returns:
            Number of logs restored
        """
        # Read logs from file
        logs = await self.read_archive_file(
            filename, start_time=start_time, end_time=end_time
        )

        total_restored = 0
        for i in range(0, len(logs), batch_size):
            batch = logs[i : i + batch_size]

            # Insert batch
            result = await Log.insert_many(batch)
            total_restored += len(result.inserted_ids)

        return total_restored

    def cleanup_old_archives(self, max_age_days: int = 365) -> int:
        """
        Delete archive files older than specified age.

        Args:
            max_age_days: Maximum age of archives to keep

        Returns:
            Number of files deleted
        """
        cutoff_date = datetime.now(UTC) - timedelta(days=max_age_days)
        files = self.list_archive_files(end_date=cutoff_date)

        deleted = 0
        for file in files:
            try:
                file.unlink()
                deleted += 1
            except OSError:
                continue

        return deleted
