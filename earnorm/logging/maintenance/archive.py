"""Log archiver module.

This module provides functionality for archiving logs to files or external storage.

Examples:
    >>> archiver = LogArchiver("/path/to/archives")
    >>> # Archive old logs
    >>> await archiver.archive_old_logs(days=30)
    >>> # Archive specific logs
    >>> await archiver.archive_logs([log1, log2], "custom_archive.zip")
"""

import gzip
import json
import os
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from earnorm.logging.models.log import Log

try:
    from earnorm.utils import dumps  # type: ignore
except ImportError:
    dumps = json.dumps


class LogArchiver:
    """Class for archiving logs.

    This class provides methods for:
    - Archiving old logs to files
    - Compressing log archives
    - Managing archive storage

    Attributes:
        archive_dir: Directory to store archives
        compress: Whether to compress archives
    """

    def __init__(self, archive_dir: Union[str, Path], compress: bool = True) -> None:
        """Initialize the archiver.

        Args:
            archive_dir: Directory to store archives
            compress: Whether to compress archives
        """
        self.archive_dir = Path(archive_dir)
        self.compress = compress
        self._ensure_archive_dir()

    def _ensure_archive_dir(self) -> None:
        """Ensure archive directory exists."""
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
        filtered: List[Path] = []

        if not (start_date or end_date):
            return files

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

        logs: List[Dict[str, Any]] = []
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

    async def archive_logs(self, logs: List[Log], name: Optional[str] = None) -> Path:
        """Archive specific logs.

        Args:
            logs: List of logs to archive
            name: Custom name for archive file

        Returns:
            Path to archive file
        """
        archive_path = self._get_archive_path(name)

        # Convert logs to JSON
        log_data = [log.to_dict() for log in logs]

        if self.compress:
            # Write to ZIP file
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("logs.json", str(log_data))
        else:
            # Write directly to JSON file
            archive_path.write_text(str(log_data))

        return archive_path

    async def archive_old_logs(self, days: int = 30, delete_after: bool = True) -> Path:
        """Archive logs older than specified days.

        Args:
            days: Number of days to archive
            delete_after: Whether to delete logs after archiving

        Returns:
            Path to archive file

        Raises:
            ValueError: If days is negative
        """
        if days < 0:
            raise ValueError("days must be >= 0")

        # Get old logs
        cutoff_date = datetime.now(UTC) - timedelta(days=days)
        old_logs = await Log.search([("timestamp", "<", cutoff_date)]).all()

        # Archive logs
        archive_path = await self.archive_logs(old_logs, f"old_logs_{days}days")

        # Delete logs if requested
        if delete_after and old_logs:
            await Log.cleanup_old_logs(days)

        return archive_path

    def cleanup_old_archives(self, days: int = 30) -> int:
        """Clean up archives older than specified days.

        Args:
            days: Number of days to keep archives

        Returns:
            Number of archives deleted

        Raises:
            ValueError: If days is negative
        """
        if days < 0:
            raise ValueError("days must be >= 0")

        cutoff_date = datetime.now(UTC) - timedelta(days=days)
        count = 0

        for archive in self.archive_dir.glob("*.json*"):
            if archive.stat().st_mtime < cutoff_date.timestamp():
                archive.unlink()
                count += 1

        return count

    def get_archive_info(self) -> Dict[str, Union[int, datetime, None]]:
        """Get information about archives.

        Returns:
            Dictionary with archive information:
            - total_size: Total size of archives in bytes
            - count: Number of archives
            - oldest: Timestamp of oldest archive
            - newest: Timestamp of newest archive
        """
        total_size = 0
        count = 0
        oldest: Optional[datetime] = None
        newest: Optional[datetime] = None

        for archive in self.archive_dir.glob("*.json*"):
            stat = archive.stat()
            total_size += stat.st_size
            count += 1

            mtime = datetime.fromtimestamp(stat.st_mtime, UTC)
            if oldest is None or mtime < oldest:
                oldest = mtime
            if newest is None or mtime > newest:
                newest = mtime

        return {
            "total_size": total_size,
            "count": count,
            "oldest": oldest,
            "newest": newest,
        }

    def _get_archive_path(
        self, name: Optional[str] = None, timestamp: Optional[datetime] = None
    ) -> Path:
        """Get path for archive file.

        Args:
            name: Custom archive name
            timestamp: Timestamp to use in filename

        Returns:
            Path to archive file
        """
        timestamp = timestamp or datetime.now(UTC)
        if name:
            filename = f"{name}.json"
            if self.compress:
                filename += ".zip"
        else:
            date_str = timestamp.strftime("%Y%m%d_%H%M%S")
            filename = f"logs_{date_str}.json"
            if self.compress:
                filename += ".zip"
        return self.archive_dir / filename

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
