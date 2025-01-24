"""UUID field implementation.

This module provides UUID field types for handling UUID values.
It supports:
- UUID values and string representations
- Auto-generation of UUIDs (v1 or v4)
- Version validation (v1, v3, v4, v5)
- Primary key support
- Database backend support

Examples:
    >>> class User(Model):
    ...     id = UUIDField(primary_key=True, auto_generate=True)  # Auto UUID v4
    ...     session_id = UUIDField(version=4)  # Must be UUID v4
    ...     device_id = UUIDField(required=True)  # Any UUID version
"""

import uuid
from typing import Any, Optional, Union

from earnorm.fields.base import Field, ValidationError


class UUIDField(Field[uuid.UUID]):
    """Field for UUID values.

    This field handles:
    - UUID validation and conversion
    - Auto-generation of UUIDs
    - Version validation
    - Database serialization

    Attributes:
        version: Required UUID version (1-5)
        auto_generate: Whether to auto-generate UUID
        primary_key: Whether this field is the primary key
        required: Whether field is required
        unique: Whether field value must be unique
        default: Default UUID value

    Raises:
        ValidationError: With codes:
            - invalid_type: Value is not a valid UUID
            - invalid_version: UUID version does not match required version
            - required: Value is required but None
            - auto_generate_error: Cannot auto-generate UUID v3/v5

    Examples:
        >>> field = UUIDField(version=4)
        >>> await field.convert("123e4567-e89b-12d3-a456-426614174000")
        >>> await field.convert(uuid.uuid4())
        >>> await field.convert("invalid")  # Raises ValidationError
    """

    def __init__(
        self,
        *,
        version: Optional[int] = None,
        auto_generate: bool = False,
        primary_key: bool = False,
        **options: Any,
    ) -> None:
        """Initialize UUID field.

        Args:
            version: Required UUID version (1-5)
            auto_generate: Whether to auto-generate UUID
            primary_key: Whether this field is the primary key
            **options: Additional field options

        Raises:
            ValueError: If version is invalid

        Examples:
            >>> field = UUIDField()  # Any UUID version
            >>> field = UUIDField(version=4)  # Must be UUID v4
            >>> field = UUIDField(auto_generate=True)  # Auto UUID v4
            >>> field = UUIDField(primary_key=True)  # Primary key field
        """
        if version is not None and version not in {1, 3, 4, 5}:
            raise ValueError("UUID version must be 1, 3, 4, or 5")

        super().__init__(**options)
        self.version = version
        self.auto_generate = auto_generate
        self.primary_key = primary_key

        # Update backend options
        self.backend_options.update(
            {
                "mongodb": {
                    "type": "uuid",
                },
                "postgres": {
                    "type": "UUID",
                },
                "mysql": {
                    "type": "CHAR(36)",
                },
            }
        )

    async def validate(self, value: Any) -> None:
        """Validate UUID value.

        Validates:
        - Value is valid UUID type
        - UUID version matches if specified
        - Not None if required

        Args:
            value: Value to validate

        Raises:
            ValidationError: With codes:
                - invalid_type: Value is not a valid UUID
                - invalid_version: UUID version does not match
                - required: Value is required but None

        Examples:
            >>> field = UUIDField(version=4)
            >>> await field.validate(uuid.uuid4())  # Valid
            >>> await field.validate(uuid.uuid1())  # Raises ValidationError
            >>> await field.validate("invalid")  # Raises ValidationError
        """
        await super().validate(value)

        if value is not None:
            if not isinstance(value, uuid.UUID):
                raise ValidationError(
                    message=f"Value must be a UUID, got {type(value).__name__}",
                    field_name=self.name,
                    code="invalid_type",
                )

            if self.version is not None and value.version != self.version:
                raise ValidationError(
                    message=f"UUID must be version {self.version}, got version {value.version}",
                    field_name=self.name,
                    code="invalid_version",
                )

    async def convert(self, value: Any) -> Optional[uuid.UUID]:
        """Convert value to UUID.

        Handles:
        - None values (returns default or auto-generates)
        - UUID values (returned as is)
        - String values (parsed as UUID)
        - Bytes values (parsed as UUID bytes)
        - Integer values (parsed as UUID int)

        Args:
            value: Value to convert

        Returns:
            Converted UUID value

        Raises:
            ValidationError: With codes:
                - invalid_type: Cannot convert value type
                - invalid_format: Invalid UUID format
                - auto_generate_error: Cannot auto-generate v3/v5

        Examples:
            >>> field = UUIDField(auto_generate=True)
            >>> await field.convert(None)  # Auto-generates UUID
            >>> await field.convert(uuid.uuid4())  # Returns as is
            >>> await field.convert("123e4567-e89b-12d3-a456-426614174000")
            >>> await field.convert(b"\\x12\\x3e\\x45\\x67...")  # From bytes
        """
        if value is None:
            if self.auto_generate:
                if self.version == 1:
                    return uuid.uuid1()
                elif self.version == 3:
                    raise ValidationError(
                        message="Cannot auto-generate UUID v3 without namespace and name",
                        field_name=self.name,
                        code="auto_generate_error",
                    )
                elif self.version == 5:
                    raise ValidationError(
                        message="Cannot auto-generate UUID v5 without namespace and name",
                        field_name=self.name,
                        code="auto_generate_error",
                    )
                else:  # version 4 or None
                    return uuid.uuid4()
            return self.default

        try:
            if isinstance(value, uuid.UUID):
                return value
            elif isinstance(value, str):
                return uuid.UUID(value)
            elif isinstance(value, (bytes, bytearray)):
                return uuid.UUID(bytes=bytes(value))
            elif isinstance(value, int):
                return uuid.UUID(int=value)
            else:
                raise ValidationError(
                    message=f"Cannot convert {type(value).__name__} to UUID",
                    field_name=self.name,
                    code="invalid_type",
                )
        except (TypeError, ValueError) as e:
            raise ValidationError(
                message=str(e), field_name=self.name, code="invalid_format"
            )

    async def to_db(
        self, value: Optional[uuid.UUID], backend: str
    ) -> Optional[Union[str, bytes]]:
        """Convert UUID to database format.

        Args:
            value: UUID value to convert
            backend: Database backend type ('mongodb', 'postgres', 'mysql')

        Returns:
            Database value:
                - mongodb: UUID bytes
                - postgres/mysql: UUID string

        Examples:
            >>> field = UUIDField()
            >>> uuid_val = uuid.uuid4()
            >>> await field.to_db(uuid_val, "mongodb")  # Returns bytes
            >>> await field.to_db(uuid_val, "postgres")  # Returns string
            >>> await field.to_db(None, "mysql")  # Returns None
        """
        if value is None:
            return None

        if backend == "mongodb":
            return value.bytes
        return str(value)

    async def from_db(self, value: Any, backend: str) -> Optional[uuid.UUID]:
        """Convert database value to UUID.

        Args:
            value: Database value to convert
            backend: Database backend type ('mongodb', 'postgres', 'mysql')

        Returns:
            Converted UUID value

        Raises:
            ValidationError: With codes:
                - invalid_type: Cannot convert value type
                - invalid_format: Invalid UUID format

        Examples:
            >>> field = UUIDField()
            >>> await field.from_db("123e4567-e89b-12d3-a456-426614174000", "postgres")
            >>> await field.from_db(b"\\x12\\x3e\\x45\\x67...", "mongodb")
            >>> await field.from_db(None, "mysql")  # Returns None
            >>> await field.from_db("invalid", "postgres")  # Raises ValidationError
        """
        if value is None:
            return None

        try:
            if isinstance(value, uuid.UUID):
                return value
            elif isinstance(value, str):
                return uuid.UUID(value)
            elif isinstance(value, (bytes, bytearray)):
                return uuid.UUID(bytes=bytes(value))
            else:
                raise ValidationError(
                    message=f"Cannot convert {type(value).__name__} to UUID",
                    field_name=self.name,
                    code="invalid_type",
                )
        except (TypeError, ValueError) as e:
            raise ValidationError(
                message=str(e), field_name=self.name, code="invalid_format"
            )
