"""Maintenance module for logging.

This module provides functionality for log maintenance tasks like:
- Cleanup of old logs
- Archiving logs to files
- Database optimization
- Log statistics

Examples:
    >>> from earnorm.logging.maintenance import LogMaintenance, LogArchiver
    >>> 
    >>> # Set up maintenance
    >>> maintenance = LogMaintenance()
    >>> archiver = LogArchiver("/path/to/archives")
    >>> 
    >>> # Clean up old logs
    >>> await maintenance.cleanup_old_logs(days=30)
    >>> 
    >>> # Archive logs
    >>> await archiver.archive_old_logs(days=90)
"""

from earnorm.logging.maintenance.archive import LogArchiver
from earnorm.logging.maintenance.cleanup import LogMaintenance

__all__ = ["LogArchiver", "LogMaintenance"]
