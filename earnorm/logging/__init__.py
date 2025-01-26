"""Logging module for EarnORM.

This module provides logging functionality for EarnORM applications.

Examples:
    >>> from earnorm.logging import Log
    >>> 
    >>> # Create a log entry
    >>> log = await Log.create({
    ...     'level': 'INFO',
    ...     'module': 'auth',
    ...     'message': 'User logged in',
    ...     'user_id': '123'
    ... })
    >>> 
    >>> # Query logs
    >>> error_logs = await Log.search([
    ...     ('level', '=', 'ERROR'),
    ...     ('module', '=', 'auth')
    ... ]).limit(10)
    >>> 
    >>> # Clean up old logs
    >>> deleted = await Log.cleanup_old_logs(days=30)
"""

import os
import socket
from typing import Any, Dict, List, Optional

from earnorm.logging.analytics.queries import LogAnalytics
from earnorm.logging.analytics.reports import LogReports
from earnorm.logging.exceptions import LogError, LogLevelError, LogValidationError
from earnorm.logging.fields import LogLevelField
from earnorm.logging.handlers import BaseHandler, ConsoleHandler, MongoHandler
from earnorm.logging.maintenance.archive import LogArchiver
from earnorm.logging.maintenance.cleanup import LogMaintenance
from earnorm.logging.models.log import Log
from earnorm.logging.models.metrics import Metrics
from earnorm.logging.processors import (
    BaseProcessor,
    ContextProcessor,
    FilterProcessor,
    FormatterProcessor,
)


class EarnLogger:
    """Main logger class for EarnORM.

    This class provides a high-level interface for logging in EarnORM.
    It supports multiple handlers, processors, and analytics features.

    Examples:
        >>> # Basic setup
        >>> logger = EarnLogger()
        >>> await logger.setup(
        ...     level='INFO',
        ...     handlers=['console', 'mongo']
        ... )
        >>> await logger.info('Test message')

        >>> # With context
        >>> with logger.context(user_id='123'):
        ...     await logger.error(
        ...         'Operation failed',
        ...         error=ValueError('Invalid input')
        ...     )

        >>> # Get analytics
        >>> analytics = logger.get_analytics()
        >>> errors = await analytics.get_error_distribution(
        ...     start_time=datetime.now(UTC) - timedelta(days=1),
        ...     end_time=datetime.now(UTC)
        ... )
    """

    def __init__(self):
        """Initialize the logger."""
        self.handlers: List[BaseHandler] = []
        self.hostname = socket.gethostname()
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.analytics = LogAnalytics()
        self.reports = LogReports()
        self.maintenance = LogMaintenance()
        self.archiver: Optional[LogArchiver] = None
        self._context: Dict[str, Any] = {}

    def get_context(self) -> Dict[str, Any]:
        """Get current context."""
        return self._context.copy()

    def set_context(self, context: Dict[str, Any]) -> None:
        """Set current context."""
        self._context = context.copy()

    def update_context(self, context: Dict[str, Any]) -> None:
        """Update current context."""
        self._context.update(context)

    async def setup(
        self,
        level: str = "INFO",
        handlers: Optional[List[str]] = None,
        archive_dir: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Set up the logger.

        Args:
            level: Minimum log level.
            handlers: List of handler names to enable.
            archive_dir: Directory for log archives.
            **kwargs: Additional configuration options
                - console_format: Format string for console handler
                - mongo_batch_size: Batch size for MongoDB handler
                - exclude_patterns: List of patterns to exclude
                - include_patterns: List of patterns to include
                - max_trace_length: Maximum number of stack trace lines
        """
        # Set up handlers
        handlers = handlers or ["console"]

        for handler_name in handlers:
            if handler_name == "console":
                self.handlers.append(
                    ConsoleHandler(
                        format_string=kwargs.get("console_format"), batch_size=1
                    )
                )
            elif handler_name == "mongo":
                self.handlers.append(
                    MongoHandler(batch_size=kwargs.get("mongo_batch_size", 100))
                )

        # Set up processors
        self.context_processor = ContextProcessor(
            environment=self.environment, hostname=self.hostname
        )

        self.filter_processor = FilterProcessor(
            min_level=level,
            exclude_patterns=kwargs.get("exclude_patterns"),
            include_patterns=kwargs.get("include_patterns"),
        )

        self.formatter_processor = FormatterProcessor(
            max_trace_length=kwargs.get("max_trace_length")
        )

        # Set up archiver if directory provided
        if archive_dir:
            self.archiver = LogArchiver(archive_dir)

    async def log(
        self,
        level: str,
        message: str,
        module: Optional[str] = None,
        error: Optional[Exception] = None,
        extra_data: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Log a message.

        Args:
            level: Log level.
            message: Log message.
            module: Module name.
            error: Exception object.
            extra_data: Additional data.
            **kwargs: Additional fields.
        """
        # Create log entry
        log_entry = {
            "level": level.upper(),
            "message": message,
            "module": module or "earnorm",
            "extra_data": extra_data or {},
        }

        # Add error if present
        if error:
            log_entry["error_message"] = str(error)
            log_entry["error_type"] = error.__class__.__name__

        # Add additional fields
        log_entry.update(kwargs)

        # Add context
        log_entry.update(self._context)

        # Process log entry
        filtered = self.filter_processor.process(log_entry)
        if not filtered:
            return

        processed = self.context_processor.process(filtered)
        formatted = self.formatter_processor.process(processed)

        # Send to handlers
        for handler in self.handlers:
            await handler.handle(formatted)

    async def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        await self.log("DEBUG", message, **kwargs)

    async def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        await self.log("INFO", message, **kwargs)

    async def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        await self.log("WARNING", message, **kwargs)

    async def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        await self.log("ERROR", message, **kwargs)

    async def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical message."""
        await self.log("CRITICAL", message, **kwargs)

    def context(self, **kwargs: Any) -> "LogContext":
        """Create a context manager with additional context."""
        return LogContext(self, **kwargs)

    def get_analytics(self) -> LogAnalytics:
        """Get analytics interface."""
        return self.analytics

    def get_reports(self) -> LogReports:
        """Get reports interface."""
        return self.reports

    def get_maintenance(self) -> LogMaintenance:
        """Get maintenance interface."""
        return self.maintenance

    def get_archiver(self) -> Optional[LogArchiver]:
        """Get archiver interface."""
        return self.archiver

    async def close(self) -> None:
        """Close all handlers."""
        for handler in self.handlers:
            await handler.close()


class LogContext:
    """Context manager for adding context to logs."""

    def __init__(self, logger: EarnLogger, **kwargs: Any):
        """Initialize the context.

        Args:
            logger: Logger instance.
            **kwargs: Context fields to add.
        """
        self.logger = logger
        self.context = kwargs
        self.previous_context: Optional[Dict[str, Any]] = None

    async def __aenter__(self) -> None:
        """Enter the context."""
        # Save current context
        self.previous_context = self.logger.get_context()

        # Update context
        self.logger.update_context(self.context)

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the context."""
        # Restore previous context
        if self.previous_context is not None:
            self.logger.set_context(self.previous_context)


# Global logger instance
logger = EarnLogger()


# Convenience functions
async def setup_logging(**kwargs: Any) -> None:
    """Set up global logger."""
    await logger.setup(**kwargs)


async def debug(message: str, **kwargs: Any) -> None:
    """Log debug message."""
    await logger.debug(message, **kwargs)


async def info(message: str, **kwargs: Any) -> None:
    """Log info message."""
    await logger.info(message, **kwargs)


async def warning(message: str, **kwargs: Any) -> None:
    """Log warning message."""
    await logger.warning(message, **kwargs)


async def error(message: str, **kwargs: Any) -> None:
    """Log error message."""
    await logger.error(message, **kwargs)


async def critical(message: str, **kwargs: Any) -> None:
    """Log critical message."""
    await logger.critical(message, **kwargs)


__all__ = [
    # Main classes
    "EarnLogger",
    "LogContext",
    # Handlers
    "BaseHandler",
    "ConsoleHandler",
    "MongoHandler",
    # Processors
    "BaseProcessor",
    "ContextProcessor",
    "FilterProcessor",
    "FormatterProcessor",
    # Models
    "Log",
    "Metrics",
    # Analytics
    "LogAnalytics",
    "LogReports",
    # Maintenance
    "LogMaintenance",
    "LogArchiver",
    # Convenience functions
    "setup_logging",
    "debug",
    "info",
    "warning",
    "error",
    "critical",
    # Global instance
    "logger",
    "LogLevelField",
    "LogError",
    "LogLevelError",
    "LogValidationError",
]
