"""Rotating file handler for rotating log files."""

import glob
import gzip
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from .file import FileHandler

logger = logging.getLogger(__name__)


class RotatingFileHandler(FileHandler):
    """Handler for rotating log files.

    This handler extends FileHandler to support log rotation based on:
    - File size
    - Time interval
    - Backup count

    Examples:
        >>> # Rotate by size
        >>> handler = RotatingFileHandler(
        ...     filename='app.log',
        ...     max_bytes=1024 * 1024,  # 1MB
        ...     backup_count=5
        ... )
        >>> await handler.emit({'message': 'test'})

        >>> # Rotate by time
        >>> handler = RotatingFileHandler(
        ...     filename='app.log',
        ...     when='D',  # Daily
        ...     backup_count=7
        ... )
        >>> await handler.emit({'message': 'test'})

        >>> # With compression
        >>> handler = RotatingFileHandler(
        ...     filename='app.log',
        ...     max_bytes=1024 * 1024,
        ...     backup_count=5,
        ...     compress=True
        ... )
        >>> await handler.emit({'message': 'test'})
    """

    def __init__(
        self,
        filename: str,
        mode: str = "a",
        encoding: str = "utf-8",
        max_bytes: int = 0,
        backup_count: int = 0,
        when: Optional[str] = None,
        compress: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize the rotating file handler.

        Args:
            filename: Path to the log file.
            mode: File open mode ('a' for append, 'w' for write).
            encoding: File encoding.
            max_bytes: Maximum file size in bytes before rotating.
                0 means no size limit.
            backup_count: Number of backup files to keep.
                0 means no backups.
            when: When to rotate:
                'S': Seconds
                'M': Minutes
                'H': Hours
                'D': Days
                'W0'-'W6': Weekday (0=Monday)
                'midnight': Roll over at midnight
            compress: Whether to compress rotated files.
            **kwargs: Additional arguments passed to FileHandler.

        Raises:
            ValueError: If max_bytes or backup_count is negative,
                or if when is not a valid value.
            OSError: If there is an error creating directories or
                setting permissions.
        """
        if max_bytes < 0:
            raise ValueError("max_bytes must be >= 0")
        if backup_count < 0:
            raise ValueError("backup_count must be >= 0")
        if (
            when
            and when not in {"S", "M", "H", "D", "midnight"}
            and not (when.startswith("W") and len(when) == 2 and "0" <= when[1] <= "6")
        ):
            raise ValueError("when must be one of: S, M, H, D, W0-W6, midnight")

        super().__init__(filename, mode, encoding, **kwargs)
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.when = when
        self.compress = compress
        self._next_rollover: Optional[datetime] = self._compute_next_rollover()

    def _compute_next_rollover(self) -> Optional[datetime]:
        """Compute the next rollover time based on 'when'.

        Returns:
            The next rollover time, or None if time-based rotation
            is not enabled.

        Raises:
            ValueError: If when is not a valid value.
        """
        if not self.when:
            return None

        try:
            now = datetime.now()

            if self.when == "S":
                return now.replace(microsecond=0) + timedelta(seconds=1)
            elif self.when == "M":
                return now.replace(second=0, microsecond=0) + timedelta(minutes=1)
            elif self.when == "H":
                return now.replace(minute=0, second=0, microsecond=0) + timedelta(
                    hours=1
                )
            elif self.when == "D":
                return now.replace(
                    hour=0, minute=0, second=0, microsecond=0
                ) + timedelta(days=1)
            elif self.when == "midnight":
                return now.replace(
                    hour=0, minute=0, second=0, microsecond=0
                ) + timedelta(days=1)
            elif self.when.startswith("W"):
                weekday = int(self.when[1])
                days_ahead = weekday - now.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                return now.replace(
                    hour=0, minute=0, second=0, microsecond=0
                ) + timedelta(days=days_ahead)

            return None
        except ValueError as e:
            logger.exception("Error computing next rollover: %s", e)
            raise

    def _should_rollover(self, log_entry: Dict[str, Any]) -> bool:
        """Check if we should perform a rollover.

        Args:
            log_entry: The log entry being processed.

        Returns:
            True if we should rollover, False otherwise.

        Raises:
            OSError: If there is an error checking file size.
        """
        try:
            # Check size-based rollover
            if self.max_bytes > 0:
                if os.path.exists(self.filename):
                    if os.path.getsize(self.filename) >= self.max_bytes:
                        return True

            # Check time-based rollover
            if self._next_rollover:
                if datetime.now() >= self._next_rollover:
                    return True

            return False
        except OSError as e:
            logger.exception("Error checking rollover condition: %s", e)
            raise

    def _do_rollover(self) -> None:
        """Perform the rollover.

        This method:
        1. Closes the current file
        2. Rotates existing backup files
        3. Renames the current file
        4. Compresses rotated files if enabled

        Raises:
            OSError: If there is an error rotating files or compressing.
            ValueError: If there is an error computing next rollover time.
        """
        try:
            if self._file is not None:
                self._file.close()
                self._file = None

            if self.backup_count > 0:
                # Get list of existing backup files
                pattern = f"{self.filename}.*"
                files = sorted(glob.glob(pattern), reverse=True)

                # Remove excess backups
                while len(files) >= self.backup_count:
                    try:
                        os.remove(files.pop())
                    except OSError as e:
                        logger.warning("Error removing old backup: %s", e)

                # Rotate existing backups
                for i in range(len(files)):
                    src = files[i]
                    dst = f"{self.filename}.{len(files) - i + 1}"
                    try:
                        os.rename(src, dst)

                        if self.compress and not dst.endswith(".gz"):
                            with open(dst, "rb") as f_in:
                                with gzip.open(f"{dst}.gz", "wb") as f_out:
                                    f_out.writelines(f_in)
                            os.remove(dst)
                    except OSError as e:
                        logger.warning("Error rotating backup file: %s", e)

                # Rename current log file
                if os.path.exists(self.filename):
                    try:
                        os.rename(self.filename, f"{self.filename}.1")
                        if self.compress:
                            with open(f"{self.filename}.1", "rb") as f_in:
                                with gzip.open(f"{self.filename}.1.gz", "wb") as f_out:
                                    f_out.writelines(f_in)
                            os.remove(f"{self.filename}.1")
                    except OSError as e:
                        logger.warning("Error renaming current log file: %s", e)

            # Update next rollover time
            self._next_rollover = self._compute_next_rollover()
        except Exception as e:
            logger.exception("Error performing rollover: %s", e)
            raise

    async def emit(self, log_entry: Dict[str, Any]) -> None:
        """Write a log entry to the file, rotating if necessary.

        Args:
            log_entry: The log entry to write.

        Raises:
            OSError: If there is an error writing to the file or rotating.
            ValueError: If the log entry cannot be formatted or if there
                is an error computing next rollover time.
        """
        try:
            if self._should_rollover(log_entry):
                self._do_rollover()

            await super().emit(log_entry)
        except Exception as e:
            logger.exception("Error emitting log entry: %s", e)
            raise
