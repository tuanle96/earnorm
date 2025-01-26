"""UUID field implementation.

This module provides UUID field type for handling UUID values.
It supports:
- UUID validation
- String conversion
- Auto-generation
- Database type mapping

Examples:
    >>> class User(Model):
    ...     id = UUIDField(primary_key=True, auto=True)  # Auto-generate UUID4
    ...     reference_id = UUIDField(nullable=True)
"""

import uuid
from typing import Any, Final, Optional

from earnorm.exceptions import FieldValidationError
from earnorm.fields.base import BaseField
from earnorm.fields.types import DatabaseValue
from earnorm.fields.validators.base import TypeValidator, Validator

# Constants
DEFAULT_PRIMARY_KEY: Final[bool] = False
DEFAULT_AUTO: Final[bool] = False
DEFAULT_VERSION: Final[int] = 4


class UUIDField(BaseField[uuid.UUID]):
    """Field for UUID values.

    This field type handles UUID values, with support for:
    - UUID validation
    - String conversion
    - Auto-generation
    - Database type mapping

    Attributes:
        primary_key: Whether this field is the primary key
        auto: Whether to auto-generate UUID on creation
        version: UUID version to use (1, 3, 4, or 5)
        backend_options: Database backend options
    """

    primary_key: bool
    auto: bool
    version: int
    backend_options: dict[str, Any]

    def __init__(
        self,
        *,
        primary_key: bool = DEFAULT_PRIMARY_KEY,
        auto: bool = DEFAULT_AUTO,
        version: int = DEFAULT_VERSION,
        **options: Any,
    ) -> None:
        """Initialize UUID field.

        Args:
            primary_key: Whether this field is the primary key
            auto: Whether to auto-generate UUID on creation
            version: UUID version to use (1, 3, 4, or 5)
            **options: Additional field options

        Raises:
            ValueError: If version is invalid
        """
        if version not in {1, 3, 4, 5}:
            raise ValueError("UUID version must be 1, 3, 4, or 5")

        field_validators: list[Validator[Any]] = [TypeValidator(uuid.UUID)]
        super().__init__(validators=field_validators, **options)

        self.primary_key = primary_key
        self.auto = auto
        self.version = version

        # Initialize backend options
        self.backend_options = {
            "mongodb": {"type": "uuid"},
            "postgres": {"type": "UUID"},
            "mysql": {"type": "CHAR(36)"},
        }

    async def validate(self, value: Any) -> None:
        """Validate UUID value.

        This method validates:
        - Value is UUID type
        - Value has correct version if specified

        Args:
            value: Value to validate

        Raises:
            FieldValidationError: If validation fails
        """
        await super().validate(value)

        if value is not None:
            if not isinstance(value, uuid.UUID):
                raise FieldValidationError(
                    message=f"Value must be a UUID, got {type(value).__name__}",
                    field_name=self.name,
                    code="invalid_type",
                )

            # Check UUID version
            if value.version != self.version:
                raise FieldValidationError(
                    message=(
                        f"UUID version must be {self.version}, "
                        f"got version {value.version}"
                    ),
                    field_name=self.name,
                    code="invalid_version",
                )

    async def convert(self, value: Any) -> Optional[uuid.UUID]:
        """Convert value to UUID.

        Handles:
        - None values
        - UUID instances
        - String values (hex format)
        - Bytes values (16 bytes)

        Args:
            value: Value to convert

        Returns:
            Converted UUID value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            if self.auto:
                if self.version == 1:
                    return uuid.uuid1()
                elif self.version == 3:
                    # Use a namespace UUID and name for version 3
                    return uuid.uuid3(uuid.NAMESPACE_DNS, str(uuid.uuid4()))
                elif self.version == 4:
                    return uuid.uuid4()
                else:  # version 5
                    # Use a namespace UUID and name for version 5
                    return uuid.uuid5(uuid.NAMESPACE_DNS, str(uuid.uuid4()))
            return None

        try:
            if isinstance(value, uuid.UUID):
                return value
            elif isinstance(value, str):
                return uuid.UUID(value)
            elif isinstance(value, bytes):
                return uuid.UUID(bytes=value)
            else:
                raise TypeError(f"Cannot convert {type(value).__name__} to UUID")
        except (TypeError, ValueError) as e:
            raise FieldValidationError(
                message=f"Cannot convert value to UUID: {str(e)}",
                field_name=self.name,
                code="conversion_error",
            ) from e

    async def to_db(self, value: Optional[uuid.UUID], backend: str) -> DatabaseValue:
        """Convert UUID to database format.

        Args:
            value: UUID value to convert
            backend: Database backend type

        Returns:
            Converted UUID value or None
        """
        if value is None:
            return None

        if backend == "mongodb":
            return value
        return str(value)

    async def from_db(self, value: DatabaseValue, backend: str) -> Optional[uuid.UUID]:
        """Convert database value to UUID.

        Args:
            value: Database value to convert
            backend: Database backend type

        Returns:
            Converted UUID value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            if isinstance(value, uuid.UUID):
                return value
            elif isinstance(value, str):
                return uuid.UUID(value)
            elif isinstance(value, bytes):
                return uuid.UUID(bytes=value)
            else:
                raise TypeError(f"Cannot convert {type(value).__name__} to UUID")
        except (TypeError, ValueError) as e:
            raise FieldValidationError(
                message=f"Cannot convert database value to UUID: {str(e)}",
                field_name=self.name,
                code="conversion_error",
            ) from e
