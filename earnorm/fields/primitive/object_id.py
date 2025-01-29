"""ObjectId field implementation.

This module provides ObjectId field type for handling MongoDB ObjectId values.
It supports:
- ObjectId validation
- String conversion
- Database type mapping
- ObjectId comparison operations

Examples:
    >>> class User(Model):
    ...     _id = ObjectIdField(primary_key=True)
    ...     parent_id = ObjectIdField(nullable=True)
    ...
    ...     # Query examples
    ...     created_today = User.find(User._id.created_today())
    ...     recent = User.find(User._id.created_after(datetime(2024, 1, 1)))
    ...     children = User.find(User.parent_id.equals(parent._id))
"""

from datetime import datetime, timedelta
from typing import Any, Final, Optional, Union

from bson import ObjectId, errors

from earnorm.exceptions import FieldValidationError
from earnorm.fields.base import BaseField
from earnorm.types.fields import ComparisonOperator, DatabaseValue, FieldComparisonMixin
from earnorm.fields.validators.base import TypeValidator, Validator

# Constants
DEFAULT_PRIMARY_KEY: Final[bool] = False


class ObjectIdField(BaseField[ObjectId], FieldComparisonMixin):
    """Field for MongoDB ObjectId values.

    This field type handles ObjectId values, with support for:
    - ObjectId validation
    - String conversion
    - Database type mapping
    - ObjectId comparison operations

    Attributes:
        primary_key: Whether this field is the primary key
        backend_options: Database backend options
    """

    primary_key: bool
    backend_options: dict[str, Any]

    def __init__(
        self,
        *,
        primary_key: bool = DEFAULT_PRIMARY_KEY,
        **options: Any,
    ) -> None:
        """Initialize ObjectId field.

        Args:
            primary_key: Whether this field is the primary key
            **options: Additional field options
        """
        field_validators: list[Validator[Any]] = [TypeValidator(ObjectId)]
        super().__init__(validators=field_validators, **options)

        self.primary_key = primary_key

        # Initialize backend options
        self.backend_options = {
            "mongodb": {"type": "objectId"},
            "postgres": {"type": "VARCHAR(24)"},
            "mysql": {"type": "CHAR(24)"},
        }

    async def validate(self, value: Any) -> None:
        """Validate ObjectId value.

        This method validates:
        - Value is ObjectId type
        - Value is a valid ObjectId

        Args:
            value: Value to validate

        Raises:
            FieldValidationError: If validation fails
        """
        await super().validate(value)

        if value is not None:
            if not isinstance(value, ObjectId):
                raise FieldValidationError(
                    message=f"Value must be an ObjectId, got {type(value).__name__}",
                    field_name=self.name,
                    code="invalid_type",
                )

            # Check if value is a valid ObjectId
            try:
                str_value = str(value)
                if not ObjectId.is_valid(str_value):
                    raise ValueError("Invalid ObjectId format")
            except (TypeError, ValueError) as e:
                raise FieldValidationError(
                    message=f"Invalid ObjectId value: {str(e)}",
                    field_name=self.name,
                    code="invalid_format",
                ) from e

    async def convert(self, value: Any) -> Optional[ObjectId]:
        """Convert value to ObjectId.

        Handles:
        - None values
        - ObjectId instances
        - String values (hex format)

        Args:
            value: Value to convert

        Returns:
            Converted ObjectId value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            if isinstance(value, ObjectId):
                return value
            elif isinstance(value, str):
                return ObjectId(value)
            else:
                raise TypeError(f"Cannot convert {type(value).__name__} to ObjectId")
        except (TypeError, errors.InvalidId) as e:
            raise FieldValidationError(
                message=f"Cannot convert value to ObjectId: {str(e)}",
                field_name=self.name,
                code="conversion_error",
            ) from e

    async def to_db(self, value: Optional[ObjectId], backend: str) -> DatabaseValue:
        """Convert ObjectId to database format.

        Args:
            value: ObjectId value to convert
            backend: Database backend type

        Returns:
            Converted ObjectId value or None
        """
        if value is None:
            return None

        if backend == "mongodb":
            return value  # type: ignore
        return str(value)

    async def from_db(self, value: DatabaseValue, backend: str) -> Optional[ObjectId]:
        """Convert database value to ObjectId.

        Args:
            value: Database value to convert
            backend: Database backend type

        Returns:
            Converted ObjectId value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            if isinstance(value, ObjectId):
                return value
            elif isinstance(value, str):
                return ObjectId(value)
            else:
                raise TypeError(f"Cannot convert {type(value).__name__} to ObjectId")
        except (TypeError, errors.InvalidId) as e:
            raise FieldValidationError(
                message=f"Cannot convert database value to ObjectId: {str(e)}",
                field_name=self.name,
                code="conversion_error",
            ) from e

    def _prepare_value(self, value: Any) -> DatabaseValue:
        """Prepare ObjectId value for comparison.

        Converts value to string for database comparison.

        Args:
            value: Value to prepare

        Returns:
            Prepared ObjectId value or None
        """
        if value is None:
            return None

        try:
            if isinstance(value, ObjectId):
                return str(value)
            elif isinstance(value, str) and ObjectId.is_valid(value):
                return value
            return None
        except (TypeError, ValueError):
            return None

    def equals(self, value: Union[ObjectId, str]) -> ComparisonOperator:
        """Check if value equals another ObjectId.

        Args:
            value: Value to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "eq", self._prepare_value(value))

    def not_equals(self, value: Union[ObjectId, str]) -> ComparisonOperator:
        """Check if value does not equal another ObjectId.

        Args:
            value: Value to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "ne", self._prepare_value(value))

    def in_list(self, values: list[Union[ObjectId, str]]) -> ComparisonOperator:
        """Check if value is in list of ObjectIds.

        Args:
            values: List of values to check against

        Returns:
            ComparisonOperator: Comparison operator with field name and values
        """
        prepared_values = [self._prepare_value(value) for value in values]
        return ComparisonOperator(self.name, "in", prepared_values)

    def not_in_list(self, values: list[Union[ObjectId, str]]) -> ComparisonOperator:
        """Check if value is not in list of ObjectIds.

        Args:
            values: List of values to check against

        Returns:
            ComparisonOperator: Comparison operator with field name and values
        """
        prepared_values = [self._prepare_value(value) for value in values]
        return ComparisonOperator(self.name, "not_in", prepared_values)

    def created_before(self, date: datetime) -> ComparisonOperator:
        """Check if ObjectId was created before date.

        Args:
            date: Date to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "created_before", date.isoformat())

    def created_after(self, date: datetime) -> ComparisonOperator:
        """Check if ObjectId was created after date.

        Args:
            date: Date to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "created_after", date.isoformat())

    def created_between(self, start: datetime, end: datetime) -> ComparisonOperator:
        """Check if ObjectId was created between dates.

        Args:
            start: Start date
            end: End date

        Returns:
            ComparisonOperator: Comparison operator with field name and values
        """
        return ComparisonOperator(
            self.name, "created_between", [start.isoformat(), end.isoformat()]
        )

    def created_days_ago(self, days: int) -> ComparisonOperator:
        """Check if ObjectId was created within last N days.

        Args:
            days: Number of days to look back

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        date = datetime.now() - timedelta(days=days)
        return self.created_after(date)

    def created_today(self) -> ComparisonOperator:
        """Check if ObjectId was created today.

        Returns:
            ComparisonOperator: Comparison operator with field name
        """
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        return self.created_between(today, tomorrow)

    def is_null(self) -> ComparisonOperator:
        """Check if value is null.

        Returns:
            ComparisonOperator: Comparison operator with field name
        """
        return ComparisonOperator(self.name, "is_null", None)

    def is_not_null(self) -> ComparisonOperator:
        """Check if value is not null.

        Returns:
            ComparisonOperator: Comparison operator with field name
        """
        return ComparisonOperator(self.name, "is_not_null", None)
