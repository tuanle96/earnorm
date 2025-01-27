"""DateTime field implementation.

This module provides datetime field types for handling date and time values.
It supports:
- Date and time validation
- Timezone handling
- Format validation
- Range validation
- Auto now and auto now add
- DateTime comparison operations

Examples:
    >>> class Post(Model):
    ...     created_at = DateTimeField(auto_now_add=True)
    ...     updated_at = DateTimeField(auto_now=True)
    ...     published_at = DateTimeField(nullable=True)
    ...
    ...     # Query examples
    ...     recent_posts = Post.find(
    ...         Post.published_at.after(datetime.now() - timedelta(days=7)),
    ...         Post.published_at.before(datetime.now())
    ...     )
    ...     today_posts = Post.find(Post.published_at.is_today())
    ...     this_month = Post.find(Post.published_at.same_month(datetime.now()))
"""

from datetime import date, datetime, time, timezone
from typing import Any, Dict, Final, List, Optional, Union

from earnorm.exceptions import FieldValidationError
from earnorm.fields.base import BaseField
from earnorm.fields.types import ComparisonOperator, DatabaseValue, FieldComparisonMixin
from earnorm.fields.validators.base import RangeValidator, TypeValidator, Validator

# Constants
DEFAULT_AUTO_NOW: Final[bool] = False
DEFAULT_AUTO_NOW_ADD: Final[bool] = False
DEFAULT_USE_TZ: Final[bool] = True
DEFAULT_TIME_FORMAT: Final[str] = "%H:%M:%S"


class DateTimeField(BaseField[datetime], FieldComparisonMixin):
    """Field for datetime values.

    This field type handles datetime values, with support for:
    - Date and time validation
    - Timezone handling
    - Format validation
    - Range validation
    - Auto now and auto now add
    - DateTime comparison operations

    Attributes:
        auto_now: Update value on every save
        auto_now_add: Set value on creation
        use_tz: Whether to use timezone-aware datetimes
        backend_options: Database backend options
    """

    auto_now: bool
    auto_now_add: bool
    use_tz: bool
    backend_options: Dict[str, Any]

    def __init__(
        self,
        *,
        auto_now: bool = DEFAULT_AUTO_NOW,
        auto_now_add: bool = DEFAULT_AUTO_NOW_ADD,
        use_tz: bool = DEFAULT_USE_TZ,
        **options: Any,
    ) -> None:
        """Initialize datetime field.

        Args:
            auto_now: Update value on every save
            auto_now_add: Set value on creation
            use_tz: Whether to use timezone-aware datetimes
            **options: Additional field options
        """
        field_validators: List[Validator[Any]] = [TypeValidator(datetime)]
        super().__init__(validators=field_validators, **options)

        self.auto_now = auto_now
        self.auto_now_add = auto_now_add
        self.use_tz = use_tz

        # Initialize backend options
        self.backend_options = {
            "mongodb": {"type": "date"},
            "postgres": {"type": "TIMESTAMP WITH TIME ZONE" if use_tz else "TIMESTAMP"},
            "mysql": {"type": "DATETIME"},
        }

    def _prepare_value(self, value: Any) -> DatabaseValue:
        """Prepare datetime value for comparison.

        Converts value to datetime and handles timezone.

        Args:
            value: Value to prepare

        Returns:
            Prepared datetime value as ISO format string
        """
        if value is None:
            return None

        try:
            if isinstance(value, str):
                value = datetime.fromisoformat(value)
            elif isinstance(value, (int, float)):
                value = datetime.fromtimestamp(value)
            elif isinstance(value, date) and not isinstance(value, datetime):
                value = datetime.combine(value, time())

            if self.use_tz and value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            elif not self.use_tz and value.tzinfo is not None:
                value = value.replace(tzinfo=None)

            return value.isoformat()
        except (TypeError, ValueError):
            return None

    def before(
        self, other: Union[datetime, date, str, int, float]
    ) -> ComparisonOperator:
        """Check if value is before other datetime.

        Args:
            other: Datetime to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "before", self._prepare_value(other))

    def after(
        self, other: Union[datetime, date, str, int, float]
    ) -> ComparisonOperator:
        """Check if value is after other datetime.

        Args:
            other: Datetime to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "after", self._prepare_value(other))

    def between(
        self,
        start: Union[datetime, date, str, int, float],
        end: Union[datetime, date, str, int, float],
    ) -> ComparisonOperator:
        """Check if value is between start and end dates.

        Args:
            start: Start datetime
            end: End datetime

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(
            self.name,
            "between",
            [self._prepare_value(start), self._prepare_value(end)],
        )

    def in_range(
        self,
        start: Union[datetime, date, str, int, float],
        end: Union[datetime, date, str, int, float],
    ) -> ComparisonOperator:
        """Alias for between().

        Args:
            start: Start datetime
            end: End datetime

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return self.between(start, end)

    def same_day(
        self, other: Union[datetime, date, str, int, float]
    ) -> ComparisonOperator:
        """Check if value is on the same day as other datetime.

        Args:
            other: Datetime to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "same_day", self._prepare_value(other))

    def same_month(
        self, other: Union[datetime, date, str, int, float]
    ) -> ComparisonOperator:
        """Check if value is in the same month as other datetime.

        Args:
            other: Datetime to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "same_month", self._prepare_value(other))

    def same_year(
        self, other: Union[datetime, date, str, int, float]
    ) -> ComparisonOperator:
        """Check if value is in the same year as other datetime.

        Args:
            other: Datetime to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "same_year", self._prepare_value(other))

    def days_ago(self, days: int) -> ComparisonOperator:
        """Check if value is exactly days ago.

        Args:
            days: Number of days

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "days_ago", days)

    def days_before(self, days: int) -> ComparisonOperator:
        """Check if value is at least days ago.

        Args:
            days: Number of days

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "days_before", days)

    def days_after(self, days: int) -> ComparisonOperator:
        """Check if value is at most days ago.

        Args:
            days: Number of days

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "days_after", days)

    def hours_ago(self, hours: int) -> ComparisonOperator:
        """Check if value is exactly hours ago.

        Args:
            hours: Number of hours

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "hours_ago", hours)

    def minutes_ago(self, minutes: int) -> ComparisonOperator:
        """Check if value is exactly minutes ago.

        Args:
            minutes: Number of minutes

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "minutes_ago", minutes)

    def seconds_ago(self, seconds: int) -> ComparisonOperator:
        """Check if value is exactly seconds ago.

        Args:
            seconds: Number of seconds

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "seconds_ago", seconds)

    def is_future(self) -> ComparisonOperator:
        """Check if value is in the future.

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "is_future", None)

    def is_past(self) -> ComparisonOperator:
        """Check if value is in the past.

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "is_past", None)

    def is_today(self) -> ComparisonOperator:
        """Check if value is today.

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "is_today", None)

    def is_this_week(self) -> ComparisonOperator:
        """Check if value is in current week.

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "is_this_week", None)

    def is_this_month(self) -> ComparisonOperator:
        """Check if value is in current month.

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "is_this_month", None)

    def is_this_year(self) -> ComparisonOperator:
        """Check if value is in current year.

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "is_this_year", None)

    def in_list(
        self, values: List[Union[datetime, date, str, int, float]]
    ) -> ComparisonOperator:
        """Check if value is in list of datetimes.

        Args:
            values: List of datetimes to check against

        Returns:
            ComparisonOperator: Comparison operator with field name and values
        """
        prepared_values = [self._prepare_value(value) for value in values]
        return ComparisonOperator(self.name, "in", prepared_values)

    def not_in_list(
        self, values: List[Union[datetime, date, str, int, float]]
    ) -> ComparisonOperator:
        """Check if value is not in list of datetimes.

        Args:
            values: List of datetimes to check against

        Returns:
            ComparisonOperator: Comparison operator with field name and values
        """
        prepared_values = [self._prepare_value(value) for value in values]
        return ComparisonOperator(self.name, "not_in", prepared_values)

    async def validate(self, value: Any) -> None:
        """Validate datetime value.

        This method validates:
        - Value is datetime type
        - Timezone info matches field configuration

        Args:
            value: Value to validate

        Raises:
            FieldValidationError: If validation fails
        """
        await super().validate(value)

        if value is not None:
            if not isinstance(value, datetime):
                raise FieldValidationError(
                    message=f"Value must be a datetime, got {type(value).__name__}",
                    field_name=self.name,
                    code="invalid_type",
                )

            if self.use_tz and value.tzinfo is None:
                raise FieldValidationError(
                    message="Timezone-aware datetime is required",
                    field_name=self.name,
                    code="missing_timezone",
                )
            elif not self.use_tz and value.tzinfo is not None:
                raise FieldValidationError(
                    message="Naive datetime is required",
                    field_name=self.name,
                    code="unexpected_timezone",
                )

    async def convert(self, value: Any) -> Optional[datetime]:
        """Convert value to datetime.

        Handles:
        - None values
        - Datetime objects
        - String values (ISO format)
        - Integer/float values (Unix timestamps)

        Args:
            value: Value to convert

        Returns:
            Converted datetime value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            if isinstance(value, datetime):
                dt = value
            elif isinstance(value, (int, float)):
                dt = datetime.fromtimestamp(value)
            elif isinstance(value, str):
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            else:
                raise TypeError(f"Cannot convert {type(value).__name__} to datetime")

            # Handle timezone
            if self.use_tz:
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            else:
                if dt.tzinfo is not None:
                    dt = dt.replace(tzinfo=None)

            return dt
        except (TypeError, ValueError) as e:
            raise FieldValidationError(
                message=f"Cannot convert {type(value).__name__} to datetime: {str(e)}",
                field_name=self.name,
                code="conversion_error",
            ) from e

    async def to_db(self, value: Optional[datetime], backend: str) -> DatabaseValue:
        """Convert datetime to database format.

        Args:
            value: Datetime value to convert
            backend: Database backend type

        Returns:
            Converted datetime value or None
        """
        if value is None:
            return None

        # Handle auto-now
        if self.auto_now:
            value = datetime.now(timezone.utc if self.use_tz else None)

        # Handle timezone
        if self.use_tz:
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
        else:
            if value.tzinfo is not None:
                value = value.replace(tzinfo=None)

        return value.isoformat()

    async def from_db(self, value: DatabaseValue, backend: str) -> Optional[datetime]:
        """Convert database value to datetime.

        Args:
            value: Database value to convert
            backend: Database backend type

        Returns:
            Converted datetime value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            if isinstance(value, datetime):
                dt = value
            elif isinstance(value, str):
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            else:
                raise TypeError(f"Cannot convert {type(value).__name__} to datetime")

            # Handle timezone
            if self.use_tz:
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)  # type: ignore
            else:
                if dt.tzinfo is not None:
                    dt = dt.replace(tzinfo=None)  # type: ignore

            return dt
        except (TypeError, ValueError) as e:
            raise FieldValidationError(
                message=f"Cannot convert database value to datetime: {str(e)}",
                field_name=self.name,
                code="conversion_error",
            ) from e


class DateField(DateTimeField):
    """Field for date values.

    This field type handles date values, with support for:
    - Date validation
    - Range validation (min/max)
    - Auto-now and auto-now-add options
    - Database type mapping

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
            min_value=datetime.combine(min_value, time()) if min_value else None,
            max_value=datetime.combine(max_value, time()) if max_value else None,
            **options,
        )

        # Initialize backend options
        self.backend_options = {
            "mongodb": {"type": "date"},
            "postgres": {"type": "DATE"},
            "mysql": {"type": "DATE"},
        }

    async def convert(self, value: Any) -> Optional[datetime]:
        """Convert value to date.

        Handles:
        - None values
        - Date objects
        - Datetime objects (date part only)
        - String values (ISO format)

        Args:
            value: Value to convert

        Returns:
            Converted datetime value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            if isinstance(value, datetime):
                dt = value.replace(
                    hour=0, minute=0, second=0, microsecond=0, tzinfo=None
                )
            elif isinstance(value, date):
                dt = datetime.combine(value, time())
            elif isinstance(value, str):
                dt = datetime.fromisoformat(value.split("T")[0])
            else:
                raise TypeError(f"Cannot convert {type(value).__name__} to date")

            return dt
        except (TypeError, ValueError) as e:
            raise FieldValidationError(
                message=f"Cannot convert {type(value).__name__} to date: {str(e)}",
                field_name=self.name,
                code="conversion_error",
            ) from e


class TimeField(BaseField[time]):
    """Field for time values.

    This field type handles time values, with support for:
    - Time validation
    - Range validation (min/max)
    - Format parsing and validation
    - Database type mapping

    Examples:
        >>> class Schedule(Model):
        ...     start_time = TimeField(required=True)
        ...     end_time = TimeField(required=True)
    """

    min_value: Optional[time]
    max_value: Optional[time]
    format: str
    backend_options: dict[str, Any]

    def __init__(
        self,
        *,
        min_value: Optional[time] = None,
        max_value: Optional[time] = None,
        format: str = DEFAULT_TIME_FORMAT,  # pylint: disable=redefined-builtin
        **options: Any,
    ) -> None:
        """Initialize time field.

        Args:
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            format: Time format string
            **options: Additional field options
        """
        field_validators: list[Validator[Any]] = [TypeValidator(time)]
        if min_value is not None or max_value is not None:
            field_validators.append(
                RangeValidator(
                    min_value=min_value,
                    max_value=max_value,
                    message=(
                        f"Value must be between {min_value or '00:00:00'} "
                        f"and {max_value or '23:59:59'}"
                    ),
                )
            )

        super().__init__(validators=field_validators, **options)

        self.min_value = min_value
        self.max_value = max_value
        self.format = format

        # Initialize backend options
        self.backend_options = {
            "mongodb": {"type": "time"},
            "postgres": {"type": "TIME"},
            "mysql": {"type": "TIME"},
        }

    async def validate(self, value: Any) -> None:
        """Validate time value.

        This method validates:
        - Value is time type
        - Value is within min/max range

        Args:
            value: Value to validate

        Raises:
            FieldValidationError: If validation fails
        """
        await super().validate(value)

        if value is not None and not isinstance(value, time):
            raise FieldValidationError(
                message=f"Value must be a time, got {type(value).__name__}",
                field_name=self.name,
                code="invalid_type",
            )

    async def convert(self, value: Any) -> Optional[time]:
        """Convert value to time.

        Handles:
        - None values
        - Time objects
        - Datetime objects (time part only)
        - String values (using format)

        Args:
            value: Value to convert

        Returns:
            Converted time value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            if isinstance(value, time):
                return value
            elif isinstance(value, datetime):
                return value.time()
            elif isinstance(value, str):
                return datetime.strptime(value, self.format).time()
            else:
                raise TypeError(f"Cannot convert {type(value).__name__} to time")
        except (TypeError, ValueError) as e:
            raise FieldValidationError(
                message=(
                    f"Cannot convert {type(value).__name__} to time: {str(e)}. "
                    f"Expected format: {self.format}"
                ),
                field_name=self.name,
                code="conversion_error",
            ) from e

    async def to_db(self, value: Optional[time], backend: str) -> DatabaseValue:
        """Convert time to database format.

        Args:
            value: Time value to convert
            backend: Database backend type

        Returns:
            Converted time value or None
        """
        if value is None:
            return None
        return value.strftime(self.format)

    async def from_db(self, value: DatabaseValue, backend: str) -> Optional[time]:
        """Convert database value to time.

        Args:
            value: Database value to convert
            backend: Database backend type

        Returns:
            Converted time value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        if not isinstance(value, time):
            raise FieldValidationError(
                message=f"Expected time from database, got {type(value).__name__}",
                field_name=self.name,
                code="invalid_type",
            )
