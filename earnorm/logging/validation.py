"""Log validation for validating log entries."""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Pattern, Union


class LogValidator:
    """Class for validating log entries.

    This class provides functionality to:
    - Validate required fields
    - Validate field types
    - Validate field formats (e.g. timestamps, levels)
    - Custom validation rules

    Examples:
        >>> # Basic validation
        >>> validator = LogValidator(
        ...     required_fields=['timestamp', 'level', 'message']
        ... )
        >>> log_entry = {
        ...     'timestamp': '2024-01-01T12:00:00',
        ...     'level': 'info',
        ...     'message': 'test'
        ... }
        >>> is_valid, errors = validator.validate(log_entry)
        >>> assert is_valid

        >>> # Type validation
        >>> validator = LogValidator(
        ...     field_types={
        ...         'count': int,
        ...         'ratio': float,
        ...         'tags': list
        ...     }
        ... )
        >>> log_entry = {
        ...     'count': 1,
        ...     'ratio': 0.5,
        ...     'tags': ['test']
        ... }
        >>> is_valid, errors = validator.validate(log_entry)
        >>> assert is_valid

        >>> # Format validation
        >>> validator = LogValidator(
        ...     field_formats={
        ...         'email': '[^@]+@[^@]+\\.[^@]+',
        ...         'ip': '\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}'
        ...     }
        ... )
        >>> log_entry = {
        ...     'email': 'test@example.com',
        ...     'ip': '192.168.1.1'
        ... }
        >>> is_valid, errors = validator.validate(log_entry)
        >>> assert is_valid
    """

    VALID_LEVELS = {"debug", "info", "warning", "error", "critical"}

    def __init__(
        self,
        required_fields: Optional[List[str]] = None,
        field_types: Optional[Dict[str, type]] = None,
        field_formats: Optional[Dict[str, Union[str, Pattern[str]]]] = None,
        validate_level: bool = True,
        validate_timestamp: bool = True,
    ):
        """Initialize the log validator.

        Args:
            required_fields: List of fields that must be present.
            field_types: Dict mapping field names to expected types.
            field_formats: Dict mapping field names to regex patterns.
            validate_level: Whether to validate log levels.
            validate_timestamp: Whether to validate timestamps.
        """
        self.required_fields = set(required_fields or [])
        self.field_types = field_types or {}
        self.field_formats = {
            name: re.compile(pattern) if isinstance(pattern, str) else pattern
            for name, pattern in (field_formats or {}).items()
        }
        self.validate_level = validate_level
        self.validate_timestamp = validate_timestamp

    def _validate_required(self, log_entry: Dict[str, Any]) -> List[str]:
        """Validate required fields are present.

        Args:
            log_entry: The log entry to validate.

        Returns:
            List[str]: List of validation errors.
        """
        errors: List[str] = []
        for field in self.required_fields:
            if field not in log_entry:
                errors.append(f"Missing required field: {field}")
        return errors

    def _validate_types(self, log_entry: Dict[str, Any]) -> List[str]:
        """Validate field types.

        Args:
            log_entry: The log entry to validate.

        Returns:
            List[str]: List of validation errors.
        """
        errors: List[str] = []
        for field, expected_type in self.field_types.items():
            if field in log_entry:
                value = log_entry[field]
                if not isinstance(value, expected_type):
                    errors.append(
                        f"Invalid type for {field}: "
                        f"expected {expected_type.__name__}, "
                        f"got {type(value).__name__}"
                    )
        return errors

    def _validate_formats(self, log_entry: Dict[str, Any]) -> List[str]:
        """Validate field formats.

        Args:
            log_entry: The log entry to validate.

        Returns:
            List[str]: List of validation errors.
        """
        errors: List[str] = []
        for field, pattern in self.field_formats.items():
            if field in log_entry:
                value = str(log_entry[field])
                if not pattern.match(value):
                    errors.append(f"Invalid format for {field}: {value}")
        return errors

    def _validate_level(self, log_entry: Dict[str, Any]) -> List[str]:
        """Validate log level.

        Args:
            log_entry: The log entry to validate.

        Returns:
            List[str]: List of validation errors.
        """
        errors: List[str] = []
        if "level" in log_entry:
            level = str(log_entry["level"]).lower()
            if level not in self.VALID_LEVELS:
                errors.append(f"Invalid log level: {level}")
        return errors

    def _validate_timestamp(self, log_entry: Dict[str, Any]) -> List[str]:
        """Validate timestamp.

        Args:
            log_entry: The log entry to validate.

        Returns:
            List[str]: List of validation errors.
        """
        errors: List[str] = []
        if "timestamp" in log_entry:
            timestamp = log_entry["timestamp"]
            if isinstance(timestamp, str):
                try:
                    datetime.fromisoformat(timestamp)
                except ValueError:
                    errors.append(f"Invalid timestamp format: {timestamp}")
            elif not isinstance(timestamp, datetime):
                errors.append("Timestamp must be ISO format string or datetime")
        return errors

    def validate(self, log_entry: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate a log entry.

        Args:
            log_entry: The log entry to validate.

        Returns:
            Tuple[bool, List[str]]: (is_valid, list of validation errors)
        """
        errors: List[str] = []

        # Required fields
        errors.extend(self._validate_required(log_entry))

        # Field types
        errors.extend(self._validate_types(log_entry))

        # Field formats
        errors.extend(self._validate_formats(log_entry))

        # Log level
        if self.validate_level:
            errors.extend(self._validate_level(log_entry))

        # Timestamp
        if self.validate_timestamp:
            errors.extend(self._validate_timestamp(log_entry))

        return not bool(errors), errors
