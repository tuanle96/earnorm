"""DateTime field implementation.

This module provides datetime field types for handling date and time values.
It supports:
- DateTime values with timezone awareness
- Date values with automatic conversion
- Time values with validation
- Timezone handling (aware/naive)
- Auto-now and auto-now-add options
- Custom date/time formats
- Range validation (min/max)
- ISO format parsing/formatting

Examples:
    >>> class Article(Model):
    ...     created_at = DateTimeField(auto_now_add=True)
    ...     updated_at = DateTimeField(auto_now=True)
    ...     published_at = DateTimeField(nullable=True)
    ...     due_date = DateField(required=True)
    ...     reminder_time = TimeField(default=time(9, 0))  # 9:00 AM

    >>> article = Article()
    >>> await article.validate()  # Sets created_at and updated_at
    >>> article.published_at = "2024-01-01"  # Converts to datetime
    >>> article.due_date = date(2024, 12, 31)  # Valid
    >>> article.reminder_time = "09:00:00"  # Converts to time
"""

from datetime import date, datetime, time, timezone
from typing import Any, Optional, Union

from earnorm.fields.base import Field, ValidationError

DateTimeValue = Union[datetime, date, time]


class DateTimeField(Field[datetime]):
    """Field for datetime values.

    This field handles:
    - Datetime validation and conversion
    - Timezone awareness/naiveness
    - Auto-now and auto-now-add
    - Format parsing/formatting
    - Range validation

    Attributes:
        auto_now: Update value on every save
        auto_now_add: Set value on creation only
        use_tz: Whether to use timezone-aware datetimes
        default_tz: Default timezone for naive datetimes (defaults to UTC)
        format: Custom datetime format string for parsing/formatting
        min_value: Minimum allowed value (inclusive)
        max_value: Maximum allowed value (inclusive)

    Raises:
        ValidationError: With codes:
            - invalid_type: Value is not a datetime
            - min_value: Value is less than min_value
            - max_value: Value is greater than max_value
            - invalid_timezone: Value has incorrect timezone awareness
            - conversion_failed: Value cannot be converted to datetime

    Examples:
        >>> field = DateTimeField(auto_now_add=True, use_tz=True)
        >>> await field.validate(None)  # Sets current datetime with timezone

        >>> field = DateTimeField(min_value=datetime(2024, 1, 1))
        >>> await field.validate(datetime(2023, 12, 31))  # Raises ValidationError

        >>> field = DateTimeField(format="%Y-%m-%d %H:%M")
        >>> await field.convert("2024-01-01 09:00")  # Returns datetime
    """

    def __init__(
        self,
        *,
        auto_now: bool = False,
        auto_now_add: bool = False,
        use_tz: bool = True,
        default_tz: Optional[timezone] = None,
        format: Optional[str] = None,
        min_value: Optional[datetime] = None,
        max_value: Optional[datetime] = None,
        **options: Any,
    ) -> None:
        """Initialize datetime field.

        Args:
            auto_now: Update value on every save
            auto_now_add: Set value on creation only
            use_tz: Whether to use timezone-aware datetimes
            default_tz: Default timezone for naive datetimes (defaults to UTC)
            format: Custom datetime format string for parsing/formatting
            min_value: Minimum allowed value (inclusive)
            max_value: Maximum allowed value (inclusive)
            **options: Additional field options

        Examples:
            >>> field = DateTimeField(auto_now=True)  # Updates on every save
            >>> field = DateTimeField(format="%Y-%m-%d")  # Custom format
            >>> field = DateTimeField(use_tz=False)  # Naive datetimes
        """
        super().__init__(**options)
        self.auto_now = auto_now
        self.auto_now_add = auto_now_add
        self.use_tz = use_tz
        self.default_tz = default_tz or timezone.utc
        self.format = format
        self.min_value = min_value
        self.max_value = max_value

        # Update backend options
        self.backend_options.update(
            {
                "mongodb": {
                    "type": "date",
                },
                "postgres": {
                    "type": "TIMESTAMP WITH TIME ZONE" if use_tz else "TIMESTAMP",
                },
                "mysql": {
                    "type": "DATETIME",
                },
            }
        )

    async def validate(self, value: Any) -> None:
        """Validate datetime value.

        Validates:
        - Type is datetime
        - Within min/max range
        - Timezone awareness matches configuration
        - Not None if required

        Args:
            value: Value to validate

        Raises:
            ValidationError: With codes:
                - invalid_type: Value is not a datetime
                - min_value: Value is less than min_value
                - max_value: Value is greater than max_value
                - invalid_timezone: Value has incorrect timezone awareness

        Examples:
            >>> field = DateTimeField(min_value=datetime(2024, 1, 1))
            >>> await field.validate("2024-01-01")  # Raises ValidationError(code="invalid_type")
            >>> await field.validate(datetime(2023, 12, 31))  # Raises ValidationError(code="min_value")
            >>> await field.validate(datetime(2024, 1, 1))  # Valid
        """
        await super().validate(value)

        if value is not None:
            if not isinstance(value, datetime):
                raise ValidationError(
                    message=f"Value must be a datetime, got {type(value).__name__}",
                    field_name=self.name,
                    code="invalid_type",
                )

            if self.min_value is not None and value < self.min_value:
                raise ValidationError(
                    message=f"Value must be greater than or equal to {self.min_value}, got {value}",
                    field_name=self.name,
                    code="min_value",
                )

            if self.max_value is not None and value > self.max_value:
                raise ValidationError(
                    message=f"Value must be less than or equal to {self.max_value}, got {value}",
                    field_name=self.name,
                    code="max_value",
                )

            # Ensure timezone awareness matches field configuration
            if self.use_tz and value.tzinfo is None:
                raise ValidationError(
                    message="Value must be timezone-aware when use_tz=True",
                    field_name=self.name,
                    code="invalid_timezone",
                )
            elif not self.use_tz and value.tzinfo is not None:
                raise ValidationError(
                    message="Value must be timezone-naive when use_tz=False",
                    field_name=self.name,
                    code="invalid_timezone",
                )

    async def convert(self, value: Any) -> Optional[datetime]:
        """Convert value to datetime.

        Handles:
        - None values with auto-now/auto-now-add
        - datetime values with timezone adjustment
        - date values converted to datetime
        - string values parsed with format
        - timestamp values (int/float)

        Args:
            value: Value to convert

        Returns:
            Converted datetime value or None

        Raises:
            ValidationError: With code "conversion_failed" if value cannot be converted

        Examples:
            >>> field = DateTimeField(format="%Y-%m-%d")
            >>> await field.convert("2024-01-01")  # Returns datetime(2024, 1, 1)
            >>> await field.convert(date(2024, 1, 1))  # Returns datetime at midnight
            >>> await field.convert(1704067200)  # Returns datetime from timestamp
            >>> await field.convert(None)  # Returns None or current time if auto_now
        """
        if value is None:
            if self.auto_now or self.auto_now_add:
                value = datetime.now(self.default_tz if self.use_tz else None)
            else:
                return self.default

        try:
            if isinstance(value, datetime):
                dt = value
            elif isinstance(value, date):
                dt = datetime.combine(value, time())
            elif isinstance(value, str):
                if self.format:
                    dt = datetime.strptime(value, self.format)
                else:
                    # Try ISO format as fallback
                    dt = datetime.fromisoformat(value)
            elif isinstance(value, (int, float)):
                dt = datetime.fromtimestamp(
                    value, self.default_tz if self.use_tz else None
                )
            else:
                raise ValueError(f"Cannot convert {type(value).__name__} to datetime")

            # Ensure correct timezone awareness
            if self.use_tz and dt.tzinfo is None:
                dt = dt.replace(tzinfo=self.default_tz)
            elif not self.use_tz and dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)

            return dt
        except (TypeError, ValueError) as e:
            raise ValidationError(
                message=f"Cannot convert value to datetime: {str(e)}",
                field_name=self.name,
                code="conversion_failed",
            )

    async def to_db(
        self, value: Optional[datetime], backend: str
    ) -> Optional[datetime]:
        """Convert datetime to database format.

        Args:
            value: Datetime value to convert
            backend: Database backend type ('mongodb', 'postgres', 'mysql')

        Returns:
            Database datetime value or None

        Examples:
            >>> field = DateTimeField(use_tz=True)
            >>> dt = datetime(2024, 1, 1, tzinfo=timezone.utc)
            >>> await field.to_db(dt, "mongodb")  # Returns UTC datetime
            >>> await field.to_db(None, "postgres")  # Returns None
        """
        if value is None:
            return None

        if backend == "mongodb":
            # MongoDB requires timezone-aware datetimes
            if value.tzinfo is None:
                value = value.replace(tzinfo=self.default_tz)
        elif backend in ("postgres", "mysql"):
            # PostgreSQL and MySQL handle timezone conversion
            pass

        return value

    async def from_db(self, value: Any, backend: str) -> Optional[datetime]:
        """Convert database value to datetime.

        Args:
            value: Database value to convert
            backend: Database backend type ('mongodb', 'postgres', 'mysql')

        Returns:
            Converted datetime value or None

        Raises:
            ValidationError: With code "conversion_failed" if value cannot be converted

        Examples:
            >>> field = DateTimeField(use_tz=True)
            >>> await field.from_db("2024-01-01T00:00:00Z", "postgres")  # Returns UTC datetime
            >>> await field.from_db(None, "mongodb")  # Returns None
        """
        if value is None:
            return None

        try:
            if isinstance(value, str):
                # Handle ISO format strings
                value = datetime.fromisoformat(value.replace("Z", "+00:00"))
            elif not isinstance(value, datetime):
                value = datetime.fromtimestamp(float(value))

            # Ensure correct timezone awareness
            if self.use_tz and value.tzinfo is None:
                value = value.replace(tzinfo=self.default_tz)
            elif not self.use_tz and value.tzinfo is not None:
                value = value.replace(tzinfo=None)

            return value
        except (TypeError, ValueError) as e:
            raise ValidationError(
                message=f"Cannot convert database value to datetime: {str(e)}",
                field_name=self.name,
                code="conversion_failed",
            )


class DateField(DateTimeField):
    """Field for date values.

    Examples:
        >>> class Event(Model):
        ...     start_date = DateField(required=True)
        ...     end_date = DateField(required=True)
    """

    def __init__(
        self,
        *,
        min_value: Optional[date] = None,
        max_value: Optional[date] = None,
        **options: Any,
    ) -> None:
        """Initialize date field.

        Args:
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            **options: Additional field options
        """
        super().__init__(
            use_tz=False,
            format="%Y-%m-%d",
            min_value=datetime.combine(min_value, time()) if min_value else None,
            max_value=datetime.combine(max_value, time()) if max_value else None,
            **options,
        )

        # Update backend options
        self.backend_options.update(
            {
                "mongodb": {
                    "type": "date",
                },
                "postgres": {
                    "type": "DATE",
                },
                "mysql": {
                    "type": "DATE",
                },
            }
        )

    async def convert(self, value: Any) -> Optional[datetime]:
        """Convert value to date.

        Args:
            value: Value to convert

        Returns:
            Date value as datetime

        Raises:
            ValidationError: If conversion fails
        """
        if value is None:
            if self.auto_now or self.auto_now_add:
                return datetime.combine(date.today(), time())
            return self.default

        if isinstance(value, date):
            return datetime.combine(value, time())
        elif isinstance(value, datetime):
            return datetime.combine(value.date(), time())
        elif isinstance(value, str):
            try:
                parsed_date = datetime.strptime(value, "%Y-%m-%d").date()
                return datetime.combine(parsed_date, time())
            except ValueError as e:
                raise ValidationError(str(e), self.name)
        else:
            raise ValidationError(
                f"Cannot convert {type(value).__name__} to date",
                self.name,
            )


class TimeField(Field[time]):
    """Field for time values.

    Examples:
        >>> class Schedule(Model):
        ...     start_time = TimeField(required=True)
        ...     end_time = TimeField(required=True)
    """

    def __init__(
        self,
        *,
        format: Optional[str] = None,
        min_value: Optional[time] = None,
        max_value: Optional[time] = None,
        **options: Any,
    ) -> None:
        """Initialize time field.

        Args:
            format: Custom time format string
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            **options: Additional field options
        """
        super().__init__(**options)
        self.format = format or "%H:%M:%S"
        self.min_value = min_value
        self.max_value = max_value

        # Update backend options
        self.backend_options.update(
            {
                "mongodb": {
                    "type": "string",
                },
                "postgres": {
                    "type": "TIME",
                },
                "mysql": {
                    "type": "TIME",
                },
            }
        )

    async def validate(self, value: Any) -> None:
        """Validate time value.

        Args:
            value: Value to validate

        Raises:
            ValidationError: If validation fails
        """
        await super().validate(value)

        if value is not None:
            if not isinstance(value, time):
                raise ValidationError("Value must be a time", self.name)

            if self.min_value is not None and value < self.min_value:
                raise ValidationError(
                    f"Value must be greater than or equal to {self.min_value}",
                    self.name,
                )

            if self.max_value is not None and value > self.max_value:
                raise ValidationError(
                    f"Value must be less than or equal to {self.max_value}",
                    self.name,
                )

    async def convert(self, value: Any) -> Optional[time]:
        """Convert value to time.

        Args:
            value: Value to convert

        Returns:
            Time value

        Raises:
            ValidationError: If conversion fails
        """
        if value is None:
            return self.default

        if isinstance(value, time):
            return value
        elif isinstance(value, datetime):
            return value.time()
        elif isinstance(value, str):
            try:
                return datetime.strptime(value, self.format).time()
            except ValueError as e:
                raise ValidationError(str(e), self.name)
        else:
            raise ValidationError(
                f"Cannot convert {type(value).__name__} to time",
                self.name,
            )

    async def to_db(self, value: Optional[time], backend: str) -> Optional[str]:
        """Convert time to database format.

        Args:
            value: Time value
            backend: Database backend type

        Returns:
            Database value
        """
        if value is None:
            return None

        return value.strftime(self.format)

    async def from_db(self, value: Any, backend: str) -> Optional[time]:
        """Convert database value to time.

        Args:
            value: Database value
            backend: Database backend type

        Returns:
            Time value
        """
        if value is None:
            return None

        return await self.convert(value)
