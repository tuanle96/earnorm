"""Context processor for adding context information to log entries."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .base import BaseProcessor


class ContextProcessor(BaseProcessor):
    """Processor for adding context information to log entries.

    This processor adds context information like timestamp, hostname,
    environment, trace ID, and user ID to log entries.

    Examples:
        >>> processor = ContextProcessor(
        ...     environment='production',
        ...     hostname='web-1',
        ...     trace_id='abc123',
        ...     user_id='user123'
        ... )
        >>> log_entry = {'message': 'test'}
        >>> processed = processor.process(log_entry)
        >>> assert processed['environment'] == 'production'
        >>> assert processed['hostname'] == 'web-1'
        >>> assert processed['trace_id'] == 'abc123'
        >>> assert processed['user_id'] == 'user123'
        >>> assert isinstance(processed['timestamp'], datetime)
    """

    def __init__(
        self,
        environment: str,
        hostname: str,
        trace_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        """Initialize the context processor.

        Args:
            environment: The environment name (e.g. production, staging).
            hostname: The hostname of the machine.
            trace_id: Optional trace ID for request tracing.
            user_id: Optional user ID for user tracking.
        """
        self.environment = environment
        self.hostname = hostname
        self.trace_id = trace_id
        self.user_id = user_id

    def process(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Process a log entry by adding context information.

        Args:
            log_entry: The log entry to process.

        Returns:
            The processed log entry with added context information.
        """
        # Add timestamp
        log_entry["timestamp"] = datetime.now(timezone.utc)

        # Add environment and hostname
        log_entry["environment"] = self.environment
        log_entry["hostname"] = self.hostname

        # Add trace ID if available
        if self.trace_id:
            log_entry["trace_id"] = self.trace_id

        # Add user ID if available
        if self.user_id:
            log_entry["user_id"] = self.user_id

        return log_entry
