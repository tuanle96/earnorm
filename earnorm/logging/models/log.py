"""Log model for storing log entries.

This module provides the Log model for storing application logs with proper
field definitions and validation.

Examples:
    >>> log = await Log.create({
    ...     'level': 'INFO',
    ...     'module': 'auth',
    ...     'message': 'User logged in',
    ...     'user_id': '123',
    ...     'extra_data': {'ip': '127.0.0.1'}
    ... })
    >>> print(log.level)
    'INFO'
"""

from datetime import UTC, datetime
from typing import Dict, Type, TypeVar

from earnorm.base import BaseModel
from earnorm.fields import DateTimeField, DictField, ListField, StringField
from earnorm.logging.fields import LogLevelField
from earnorm.types import JsonDict

T = TypeVar("T", bound="Log")


class Log(BaseModel):
    """Log entry model for storing application logs.

    This model represents a log entry in the application, containing information
    about events, errors, and system state.

    Attributes:
        timestamp: When the log was created
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        module: Module/component that generated the log
        message: Log message content
        trace_id: Trace ID for request tracing
        user_id: User ID for user tracking
        model: Model name for model-related logs
        model_id: Model ID for model-related logs
        operation: Operation type
        extra_data: Additional data as key-value pairs
        error_type: Type of error if this is an error log
        error_message: Error message if this is an error log
        stack_trace: Stack trace lines if this is an error log
        host: Hostname where the log was generated
        environment: Environment (development, staging, production)
    """

    _name = "logging.log"
    _description = "Log Entry"
    _table = "logs"

    # Required fields
    timestamp = DateTimeField(
        required=True,
        readonly=True,
        default=lambda: datetime.now(UTC),
        help="When the log was created",
    )
    level = LogLevelField(
        required=True, help="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    module = StringField(required=True, help="Module/component that generated the log")
    message = StringField(required=True, help="Log message content")

    # Context fields
    trace_id = StringField(help="Trace ID for request tracing")
    user_id = StringField(help="User ID for user tracking")
    model = StringField(help="Model name for model-related logs")
    model_id = StringField(help="Model ID for model-related logs")
    operation = StringField(help="Operation type")

    # Additional data
    extra_data = DictField[str, str](  # Use str type for both key and value
        key_field=StringField(),
        value_field=StringField(),
        default=dict,
        help="Additional data as key-value pairs",
    )
    error_type = StringField(help="Type of error if this is an error log")
    error_message = StringField(help="Error message if this is an error log")
    stack_trace = ListField(
        StringField(), default=list, help="Stack trace lines if this is an error log"
    )

    # Environment
    host = StringField(help="Hostname where the log was generated")
    environment = StringField(help="Environment (development, staging, production)")

    def to_dict(self) -> JsonDict:
        """Convert log entry to dictionary.

        Returns:
            Dictionary representation of log entry
        """
        extra_data = {}
        if hasattr(self.extra_data, "items"):
            extra_data = {str(k): str(v) for k, v in self.extra_data.items()}

        stack_trace = []
        if hasattr(self.stack_trace, "__iter__"):
            stack_trace = [str(line) for line in self.stack_trace]

        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "level": self.level,
            "module": self.module,
            "message": self.message,
            "trace_id": self.trace_id,
            "user_id": self.user_id,
            "model": self.model,
            "model_id": self.model_id,
            "operation": self.operation,
            "extra_data": extra_data,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "stack_trace": stack_trace,
            "host": self.host,
            "environment": self.environment,
        }

    @classmethod
    async def cleanup_old_logs(cls: Type[T], days: int = 30) -> int:
        """Clean up logs older than specified days.

        Args:
            days: Number of days to keep logs for

        Returns:
            Number of logs deleted

        Raises:
            ValueError: If days is negative
            NotImplementedError: Method not implemented yet
        """
        if days < 0:
            raise ValueError("days must be >= 0")

        raise NotImplementedError("Method not implemented yet")

    @classmethod
    async def get_log_stats(
        cls: Type[T], start_time: datetime, end_time: datetime
    ) -> Dict[str, int]:
        """Get log statistics for a time period.

        Args:
            start_time: Start of time period
            end_time: End of time period

        Returns:
            Dictionary with log counts by level and total

        Raises:
            ValueError: If start_time is after end_time
            NotImplementedError: Method not implemented yet
        """
        if start_time > end_time:
            raise ValueError("start_time must be before end_time")

        raise NotImplementedError("Method not implemented yet")
