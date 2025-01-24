"""Log compression for compressing log files."""

import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional


class LogCompression:
    """Class for compressing log files.

    This class provides functionality to:
    - Compress old log files
    - Maintain compressed log archives
    - Clean up old compressed logs

    Examples:
        >>> # Compress logs older than 7 days
        >>> compressor = LogCompression('logs')
        >>> await compressor.compress_old_logs(
        ...     max_age_days=7,
        ...     delete_source=True
        ... )

        >>> # Clean up compressed logs older than 30 days
        >>> await compressor.cleanup_old_archives(max_age_days=30)

        >>> # Compress specific log files
        >>> compressor = LogCompression('logs')
        >>> await compressor.compress_files(['app.log', 'error.log'])
    """

    def __init__(self, log_dir: str):
        """Initialize the log compression.

        Args:
            log_dir: Directory containing log files.
        """
        self.log_dir = Path(log_dir)
        self.archive_dir = self.log_dir / "archive"
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    def _is_old_enough(self, path: Path, max_age_days: int) -> bool:
        """Check if a file is older than max_age_days.

        Args:
            path: Path to the file.
            max_age_days: Maximum age in days.

        Returns:
            bool: True if the file is older than max_age_days.
        """
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        age = datetime.now() - mtime
        return age > timedelta(days=max_age_days)

    def _get_archive_path(self, source: Path) -> Path:
        """Get the archive path for a log file.

        Args:
            source: Path to the source log file.

        Returns:
            Path: Path where the compressed file will be stored.
        """
        timestamp = datetime.fromtimestamp(source.stat().st_mtime)
        archive_name = f"{source.stem}_{timestamp:%Y%m%d_%H%M%S}.gz"
        return self.archive_dir / archive_name

    async def compress_file(
        self, source: Path, delete_source: bool = False
    ) -> Optional[Path]:
        """Compress a single log file.

        Args:
            source: Path to the log file to compress.
            delete_source: Whether to delete the source file after compression.

        Returns:
            Optional[Path]: Path to the compressed file if successful.
        """
        if not source.exists():
            return None

        archive_path = self._get_archive_path(source)

        try:
            with source.open("rb") as f_in:
                with gzip.open(archive_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

            if delete_source:
                source.unlink()

            return archive_path

        except (OSError, IOError):
            if archive_path.exists():
                archive_path.unlink()
            return None

    async def compress_files(
        self, filenames: List[str], delete_source: bool = False
    ) -> List[Path]:
        """Compress multiple log files.

        Args:
            filenames: List of log filenames to compress.
            delete_source: Whether to delete source files after compression.

        Returns:
            List[Path]: List of paths to successfully compressed files.
        """
        results: List[Path] = []
        for filename in filenames:
            source = self.log_dir / filename
            if compressed := await self.compress_file(source, delete_source):
                results.append(compressed)
        return results

    async def compress_old_logs(
        self, max_age_days: int, delete_source: bool = False
    ) -> List[Path]:
        """Compress log files older than max_age_days.

        Args:
            max_age_days: Maximum age in days.
            delete_source: Whether to delete source files after compression.

        Returns:
            List[Path]: List of paths to successfully compressed files.
        """
        results: List[Path] = []
        for path in self.log_dir.glob("*.log"):
            if self._is_old_enough(path, max_age_days):
                if compressed := await self.compress_file(path, delete_source):
                    results.append(compressed)
        return results

    async def cleanup_old_archives(self, max_age_days: int) -> int:
        """Delete compressed logs older than max_age_days.

        Args:
            max_age_days: Maximum age in days.

        Returns:
            int: Number of files deleted.
        """
        count = 0
        for path in self.archive_dir.glob("*.gz"):
            if self._is_old_enough(path, max_age_days):
                try:
                    path.unlink()
                    count += 1
                except OSError:
                    pass
        return count
