"""ObjectId field implementation.

This module provides ObjectId field type for handling MongoDB ObjectId values.
It supports:
- ObjectId validation
- String conversion
- Database type mapping

Examples:
    >>> class User(Model):
    ...     _id = ObjectIdField(primary_key=True)
    ...     parent_id = ObjectIdField(nullable=True)
"""

from typing import Any, Final, Optional

from bson import ObjectId, errors

from earnorm.exceptions import FieldValidationError
from earnorm.fields.base import BaseField
from earnorm.fields.types import DatabaseValue
from earnorm.fields.validators.base import TypeValidator, Validator

# Constants
DEFAULT_PRIMARY_KEY: Final[bool] = False


class ObjectIdField(BaseField[ObjectId]):
    """Field for MongoDB ObjectId values.

    This field type handles ObjectId values, with support for:
    - ObjectId validation
    - String conversion
    - Database type mapping

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
            return value
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
