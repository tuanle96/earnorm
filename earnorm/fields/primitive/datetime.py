"""Date and datetime field types."""

from datetime import date, datetime
from typing import Any, List, Optional, Type

from earnorm.fields.base import Field
from earnorm.validators.types import ValidatorFunc


class DateField(Field[date]):
    """Date field.

    Examples:
        >>> birth_date = DateField(required=True)
        >>> birth_date.convert("2000-01-01")
        datetime.date(2000, 1, 1)
        >>> birth_date.convert(datetime(2000, 1, 1))
        datetime.date(2000, 1, 1)
        >>> birth_date.convert(None)
        datetime.date(1970, 1, 1)  # Default date
    """

    def _get_field_type(self) -> Type[Any]:
        """Get field type."""
        return date

    def __init__(
        self,
        *,
        required: bool = False,
        unique: bool = False,
        default: Any = None,
        validators: Optional[List[ValidatorFunc]] = None,
        auto_now: bool = False,
        auto_now_add: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize field.

        Args:
            required: Whether field is required
            unique: Whether field value must be unique
            default: Default value
            validators: List of validator functions
            auto_now: Whether to set value to current date on every save
            auto_now_add: Whether to set value to current date on creation
        """
        super().__init__(
            required=required,
            unique=unique,
            default=default,
            validators=validators,
            **kwargs,
        )
        self.auto_now = auto_now
        self.auto_now_add = auto_now_add

    def convert(self, value: Any) -> date:
        """Convert value to date."""
        if value is None:
            return date(1970, 1, 1)  # Default date
        if isinstance(value, date):
            return value
        if isinstance(value, datetime):
            return value.date()
        return datetime.strptime(str(value), "%Y-%m-%d").date()

    def to_mongo(self, value: Optional[date]) -> Optional[datetime]:
        """Convert Python date to MongoDB date."""
        if value is None:
            return None
        return datetime.combine(value, datetime.min.time())

    def from_mongo(self, value: Any) -> date:
        """Convert MongoDB date to Python date."""
        if value is None:
            return date(1970, 1, 1)  # Default date
        if isinstance(value, datetime):
            return value.date()
        return value


class DateTimeField(Field[datetime]):
    """Datetime field.

    Examples:
        >>> created_at = DateTimeField(auto_now_add=True)
        >>> created_at.convert("2000-01-01 12:00:00")
        datetime.datetime(2000, 1, 1, 12, 0)
        >>> created_at.convert(date(2000, 1, 1))
        datetime.datetime(2000, 1, 1, 0, 0)
        >>> created_at.convert(None)
        datetime.datetime(1970, 1, 1, 0, 0)  # Default datetime
    """

    def _get_field_type(self) -> Type[Any]:
        """Get field type."""
        return datetime

    def __init__(
        self,
        *,
        required: bool = False,
        unique: bool = False,
        default: Any = None,
        validators: Optional[List[ValidatorFunc]] = None,
        auto_now: bool = False,
        auto_now_add: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize field.

        Args:
            required: Whether field is required
            unique: Whether field value must be unique
            default: Default value
            validators: List of validator functions
            auto_now: Whether to set value to current datetime on every save
            auto_now_add: Whether to set value to current datetime on creation
        """
        super().__init__(
            required=required,
            unique=unique,
            default=default,
            validators=validators,
            **kwargs,
        )
        self.auto_now = auto_now
        self.auto_now_add = auto_now_add

    def convert(self, value: Any) -> datetime:
        """Convert value to datetime."""
        if value is None:
            return datetime(1970, 1, 1)  # Default datetime
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time())
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            return datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")

    def to_mongo(self, value: Optional[datetime]) -> Optional[datetime]:
        """Convert Python datetime to MongoDB datetime."""
        return value

    def from_mongo(self, value: Any) -> datetime:
        """Convert MongoDB datetime to Python datetime."""
        if value is None:
            return datetime(1970, 1, 1)  # Default datetime
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value))
