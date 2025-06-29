"""UUID field implementation.

This module provides UUID field type for handling UUID values.
It supports:
- Auto-generation of UUIDs
- Version validation (v1, v4, etc.)
- String/UUID conversion
- Database type mapping
- UUID comparison operations

Examples:
    >>> class Document(Model):
    ...     id = UUIDField(version=4, auto_generate=True, primary_key=True)
    ...     parent_id = UUIDField(nullable=True)
    ...
    ...     # Query examples
    ...     docs = Document.find(
    ...         Document.parent_id.in_list(['uuid1', 'uuid2']),
    ...         Document.id.version(4)
    ...     )
"""

import uuid
from typing import Any, Final, Literal

from earnorm.exceptions import FieldValidationError
from earnorm.fields.base import BaseField
from earnorm.fields.validators.base import TypeValidator, Validator
from earnorm.types.fields import ComparisonOperator, DatabaseValue, FieldComparisonMixin

# Constants
DEFAULT_VERSION: Final[Literal[1, 3, 4, 5] | None] = 4
DEFAULT_AUTO_GENERATE: Final[bool] = False


class UUIDField(BaseField[uuid.UUID], FieldComparisonMixin):
    """Field for UUID values.

    This field type handles UUID values, with support for:
    - Auto-generation of UUIDs
    - Version validation (v1, v4, etc.)
    - String/UUID conversion
    - Database type mapping
    - UUID comparison operations

    Attributes:
        version: UUID version to use (1, 3, 4, or 5)
        auto_generate: Whether to auto-generate UUID if not provided
        backend_options: Database backend options
    """

    version: Literal[1, 3, 4, 5] | None
    auto_generate: bool
    backend_options: dict[str, Any]

    def __init__(
        self,
        *,
        version: Literal[1, 3, 4, 5] | None = DEFAULT_VERSION,
        auto_generate: bool = DEFAULT_AUTO_GENERATE,
        **options: Any,
    ) -> None:
        """Initialize UUID field.

        Args:
            version: UUID version to use (1, 3, 4, or 5)
            auto_generate: Whether to auto-generate UUID if not provided
            **options: Additional field options
        """
        field_validators: list[Validator[Any]] = [TypeValidator(uuid.UUID)]
        super().__init__(validators=field_validators, **options)

        self.version = version
        self.auto_generate = auto_generate

        # Initialize backend options
        self.backend_options = {
            "mongodb": {"type": "uuid"},
            "postgres": {"type": "UUID"},
            "mysql": {"type": "CHAR", "maxLength": 36},
        }

    def _prepare_value(self, value: Any) -> DatabaseValue:
        """Prepare UUID value for comparison.

        Converts value to UUID and returns string representation.

        Args:
            value: Value to prepare

        Returns:
            Prepared UUID value as string
        """
        if value is None:
            return None

        try:
            if isinstance(value, uuid.UUID):
                return str(value)
            elif isinstance(value, str):
                return str(uuid.UUID(value))
            elif isinstance(value, bytes):
                return str(uuid.UUID(bytes=value))
            else:
                raise TypeError(f"Cannot convert {type(value).__name__} to UUID")
        except (TypeError, ValueError):
            return None

    def in_list(self, values: list[uuid.UUID | str | bytes]) -> ComparisonOperator:
        """Check if value is in list of UUIDs.

        Args:
            values: List of UUIDs to check against

        Returns:
            ComparisonOperator: Comparison operator with field name and values
        """
        prepared_values = [self._prepare_value(value) for value in values]
        return ComparisonOperator(self.name, "in", prepared_values)

    def not_in_list(self, values: list[uuid.UUID | str | bytes]) -> ComparisonOperator:
        """Check if value is not in list of UUIDs.

        Args:
            values: List of UUIDs to check against

        Returns:
            ComparisonOperator: Comparison operator with field name and values
        """
        prepared_values = [self._prepare_value(value) for value in values]
        return ComparisonOperator(self.name, "not_in", prepared_values)

    def has_version(self, version: Literal[1, 3, 4, 5]) -> ComparisonOperator:
        """Check if UUID is of specific version.

        Args:
            version: UUID version to check

        Returns:
            ComparisonOperator: Comparison operator with field name and version
        """
        return ComparisonOperator(self.name, "version", version)

    def namespace(self, namespace: uuid.UUID | str) -> ComparisonOperator:
        """Check if UUID was generated with specific namespace (v3/v5 only).

        Args:
            namespace: Namespace UUID to check

        Returns:
            ComparisonOperator: Comparison operator with field name and namespace
        """
        return ComparisonOperator(self.name, "namespace", self._prepare_value(namespace))

    def node(self, node: bytes) -> ComparisonOperator:
        """Check if UUID was generated on specific node (v1 only).

        Args:
            node: Node ID to check

        Returns:
            ComparisonOperator: Comparison operator with field name and node
        """
        return ComparisonOperator(self.name, "node", node.hex())

    def time(self, timestamp: int) -> ComparisonOperator:
        """Check if UUID was generated at specific time (v1 only).

        Args:
            timestamp: Timestamp to check

        Returns:
            ComparisonOperator: Comparison operator with field name and timestamp
        """
        return ComparisonOperator(self.name, "time", timestamp)

    async def validate(self, value: Any, context: dict[str, Any] | None = None) -> Any:
        """Validate UUID value.

        This method validates:
        - Value is UUID type
        - UUID version matches if specified

        Args:
            value: Value to validate
            context: Validation context with following keys:
                    - model: Model instance
                    - env: Environment instance
                    - operation: Operation type (create/write/search...)
                    - values: Values being validated
                    - field_name: Name of field being validated

        Returns:
            Any: The validated value

        Raises:
            FieldValidationError: If validation fails
        """
        value = await super().validate(value, context)

        if value is not None:
            if not isinstance(value, uuid.UUID):
                raise FieldValidationError(
                    message=f"Value must be a UUID, got {type(value).__name__}",
                    field_name=self.name,
                    code="invalid_type",
                )

            if self.version is not None and value.version != self.version:
                raise FieldValidationError(
                    message=f"UUID must be version {self.version}, got version {value.version}",
                    field_name=self.name,
                    code="invalid_version",
                )

        return value

    async def convert(self, value: Any) -> uuid.UUID | None:
        """Convert value to UUID.

        Handles:
        - None values
        - UUID objects
        - String values (hex format)
        - Bytes values
        - Auto-generation if enabled

        Args:
            value: Value to convert

        Returns:
            Converted UUID value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            if self.auto_generate:
                match self.version:
                    case 1:
                        return uuid.uuid1()
                    case 3:
                        raise ValueError("UUID version 3 requires namespace and name")
                    case 4:
                        return uuid.uuid4()
                    case 5:
                        raise ValueError("UUID version 5 requires namespace and name")
                    case _:
                        return uuid.uuid4()  # Default to v4
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
                message=f"Cannot convert {type(value).__name__} to UUID: {e!s}",
                field_name=self.name,
                code="conversion_error",
            ) from e

    async def to_db(self, value: uuid.UUID | None, backend: str) -> DatabaseValue:
        """Convert UUID to database format.

        Args:
            value: UUID value to convert
            backend: Database backend type

        Returns:
            Converted UUID value or None
        """
        if value is None:
            return None

        # Always convert to string for database storage
        return str(value)

    async def from_db(self, value: DatabaseValue, backend: str) -> uuid.UUID | None:
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
            elif isinstance(value, (str, bytes)):
                return uuid.UUID(str(value))
            else:
                raise TypeError(f"Cannot convert {type(value).__name__} to UUID")
        except (TypeError, ValueError) as e:
            raise FieldValidationError(
                message=f"Cannot convert database value to UUID: {e!s}",
                field_name=self.name,
                code="conversion_error",
            ) from e
