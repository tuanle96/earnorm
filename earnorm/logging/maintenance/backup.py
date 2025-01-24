"""Backup and restore functionality for log files."""

import shutil
import tarfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Set, Tuple


class LogBackup:
    """Class for backing up and restoring log files.

    This class provides functionality to:
    - Create backups of log files and archives
    - Restore from backups
    - Manage backup retention

    Examples:
        >>> # Create a backup
        >>> backup = LogBackup('logs', 'backups')
        >>> backup_file = await backup.create_backup()
        >>> print(f'Created backup: {backup_file}')

        >>> # Restore from backup
        >>> await backup.restore_backup('logs_20240101_120000.tar.gz')

        >>> # Clean up old backups
        >>> await backup.cleanup_old_backups(max_backups=5)

        >>> # List available backups
        >>> backups = await backup.list_backups()
        >>> for backup in backups:
        ...     print(f'Backup: {backup.name}')
    """

    def __init__(self, log_dir: str, backup_dir: str, include_archives: bool = True):
        """Initialize the log backup.

        Args:
            log_dir: Directory containing log files.
            backup_dir: Directory to store backups.
            include_archives: Whether to include archived logs in backups.
        """
        self.log_dir = Path(log_dir)
        self.backup_dir = Path(backup_dir)
        self.include_archives = include_archives
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def _get_backup_path(self) -> Path:
        """Get the path for a new backup file.

        Returns:
            Path: Path where the backup will be stored.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"logs_{timestamp}.tar.gz"
        return self.backup_dir / backup_name

    def _get_files_to_backup(self) -> Set[Path]:
        """Get the set of files to include in backup.

        Returns:
            Set[Path]: Set of files to backup.
        """
        files = set(self.log_dir.glob("*.log"))

        if self.include_archives:
            archive_dir = self.log_dir / "archive"
            if archive_dir.exists():
                files.update(archive_dir.glob("*.gz"))

        return files

    async def create_backup(self) -> Optional[Path]:
        """Create a backup of log files.

        Returns:
            Optional[Path]: Path to the backup file if successful.
        """
        backup_path = self._get_backup_path()
        files = self._get_files_to_backup()

        if not files:
            return None

        try:
            with tarfile.open(backup_path, "w:gz") as tar:
                for file in files:
                    tar.add(file, arcname=file.relative_to(self.log_dir))
            return backup_path

        except (OSError, IOError):
            if backup_path.exists():
                backup_path.unlink()
            return None

    async def restore_backup(
        self, backup_file: str, restore_archives: bool = True
    ) -> bool:
        """Restore from a backup file.

        Args:
            backup_file: Name of the backup file to restore from.
            restore_archives: Whether to restore archived logs.

        Returns:
            bool: True if restore was successful.
        """
        backup_path = self.backup_dir / backup_file
        restore_dir: Optional[Path] = None

        if not backup_path.exists():
            return False

        try:
            # Create temporary restore directory
            restore_dir = self.backup_dir / "restore_temp"
            restore_dir.mkdir(exist_ok=True)

            # Extract backup to temp directory
            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(restore_dir)

            # Copy files back to log directory
            for file in restore_dir.glob("*.log"):
                shutil.copy2(file, self.log_dir)

            # Restore archives if requested
            if restore_archives:
                archive_dir = restore_dir / "archive"
                if archive_dir.exists():
                    target_archive = self.log_dir / "archive"
                    target_archive.mkdir(exist_ok=True)
                    for file in archive_dir.glob("*.gz"):
                        shutil.copy2(file, target_archive)

            return True

        except (OSError, IOError, tarfile.TarError):
            return False

        finally:
            # Clean up temp directory
            if restore_dir and restore_dir.exists():
                shutil.rmtree(restore_dir)

    async def list_backups(self) -> List[Tuple[Path, datetime]]:
        """List available backup files.

        Returns:
            List[Tuple[Path, datetime]]: List of (backup_path, timestamp) tuples.
        """
        backups: List[Tuple[Path, datetime]] = []
        for path in self.backup_dir.glob("logs_*.tar.gz"):
            try:
                # Extract timestamp from filename
                timestamp_str = path.stem.split("_", 1)[1]
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                backups.append((path, timestamp))
            except (ValueError, IndexError):
                continue

        return sorted(backups, key=lambda x: x[1], reverse=True)

    async def cleanup_old_backups(
        self, max_backups: Optional[int] = None, max_age_days: Optional[int] = None
    ) -> int:
        """Clean up old backup files.

        Args:
            max_backups: Maximum number of backups to keep.
            max_age_days: Maximum age of backups in days.

        Returns:
            int: Number of backups deleted.
        """
        if not max_backups and not max_age_days:
            return 0

        backups = await self.list_backups()
        to_delete: Set[Path] = set()

        # Mark old backups for deletion
        if max_age_days is not None:
            cutoff = datetime.now() - timedelta(days=max_age_days)
            to_delete.update(path for path, timestamp in backups if timestamp < cutoff)

        # Mark excess backups for deletion
        if max_backups is not None and len(backups) > max_backups:
            to_delete.update(path for path, _ in backups[max_backups:])

        # Delete marked backups
        count = 0
        for path in to_delete:
            try:
                path.unlink()
                count += 1
            except OSError:
                pass

        return count
