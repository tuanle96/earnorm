"""JSON field implementation.

This module provides JSON field type for handling JSON data.
It supports:
- JSON validation
- Schema validation
- Type conversion
- Database type mapping
- JSON comparison operations

Examples:
    >>> class Product(Model):
    ...     metadata = JSONField(default={})
    ...     settings = JSONField(schema={
    ...         "type": "object",
    ...         "properties": {
    ...             "notifications": {"type": "boolean"},
    ...             "theme": {"type": "string", "enum": ["light", "dark"]},
    ...         },
    ...     })
    ...
    ...     # Query examples
    ...     has_tags = Product.find(Product.metadata.has_key("tags"))
    ...     dark_theme = Product.find(Product.settings.has_value("dark", path="theme"))
    ...     notified = Product.find(Product.settings.has_value(True, path="notifications"))
"""

import json
from typing import Any, Final

from jsonschema import Draft202012Validator, ValidationError, validate

from earnorm.exceptions import FieldValidationError
from earnorm.fields.base import BaseField
from earnorm.fields.validators.base import Validator
from earnorm.types.fields import ComparisonOperator, DatabaseValue, FieldComparisonMixin

# Constants
DEFAULT_ENCODER: Final[type[json.JSONEncoder]] = json.JSONEncoder
DEFAULT_DECODER: Final[type[json.JSONDecoder]] = json.JSONDecoder


class JSONField(BaseField[Any], FieldComparisonMixin):
    """Field for JSON data.

    This field type handles JSON data, with support for:
    - JSON validation
    - Schema validation
    - Type conversion
    - Database type mapping
    - JSON comparison operations

    Attributes:
        schema: JSON schema for validation
        encoder: JSON encoder class
        decoder: JSON decoder class
        backend_options: Database backend options
    """

    schema: dict[str, Any] | None
    encoder: type[json.JSONEncoder]
    decoder: type[json.JSONDecoder]
    backend_options: dict[str, Any]

    def __init__(
        self,
        *,
        schema: dict[str, Any] | None = None,
        encoder: type[json.JSONEncoder] | None = None,
        decoder: type[json.JSONDecoder] | None = None,
        **options: Any,
    ) -> None:
        """Initialize JSON field.

        Args:
            schema: JSON schema for validation
            encoder: JSON encoder class
            decoder: JSON decoder class
            **options: Additional field options

        Raises:
            ValueError: If schema is invalid
        """
        field_validators: list[Validator[Any]] = []
        super().__init__(validators=field_validators, **options)

        self.schema = schema
        self.encoder = encoder or DEFAULT_ENCODER
        self.decoder = decoder or DEFAULT_DECODER

        # Validate schema if provided
        if schema is not None:
            try:
                Draft202012Validator.check_schema(schema)
            except ValidationError as e:
                raise ValueError(f"Invalid JSON schema: {e!s}") from e

        # Initialize backend options
        self.backend_options = {
            "mongodb": {"type": "object"},
            "postgres": {"type": "JSONB"},
            "mysql": {"type": "JSON"},
        }

    async def validate(self, value: Any, context: dict[str, Any] | None = None) -> Any:
        """Validate JSON value.

        This method validates:
        - Value can be serialized to JSON
        - Value matches JSON schema if provided

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
            try:
                # Check if value can be serialized
                json.dumps(value, cls=self.encoder)

                # Validate against schema if provided
                if self.schema is not None:
                    try:
                        validate(instance=value, schema=self.schema)
                    except ValidationError as e:
                        raise FieldValidationError(
                            message=f"JSON schema validation failed: {e!s}",
                            field_name=self.name,
                            code="schema_error",
                        ) from e
            except (TypeError, ValueError) as e:
                raise FieldValidationError(
                    message=f"Invalid JSON value: {e!s}",
                    field_name=self.name,
                    code="invalid_json",
                ) from e

        return value

    async def convert(self, value: Any) -> Any | None:
        """Convert value to JSON-compatible type.

        Handles:
        - None values
        - JSON-compatible values
        - String values (JSON strings)

        Args:
            value: Value to convert

        Returns:
            Converted JSON value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            if isinstance(value, str):
                return json.loads(value, cls=self.decoder)
            return value
        except (TypeError, ValueError) as e:
            raise FieldValidationError(
                message=f"Cannot convert value to JSON: {e!s}",
                field_name=self.name,
                code="conversion_error",
            ) from e

    async def to_db(self, value: Any | None, backend: str) -> DatabaseValue:
        """Convert value to database format.

        Args:
            value: Value to convert
            backend: Database backend type

        Returns:
            Converted JSON value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            if backend == "mongodb":
                return value
            return json.dumps(value, cls=self.encoder)
        except (TypeError, ValueError) as e:
            raise FieldValidationError(
                message=f"Cannot convert value to JSON: {e!s}",
                field_name=self.name,
                code="conversion_error",
            ) from e

    async def from_db(self, value: DatabaseValue, backend: str) -> Any | None:
        """Convert database value to JSON.

        Args:
            value: Database value to convert
            backend: Database backend type

        Returns:
            Converted JSON value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            if backend == "mongodb":
                return value
            if isinstance(value, str):
                return json.loads(value, cls=self.decoder)
            return value
        except (TypeError, ValueError) as e:
            raise FieldValidationError(
                message=f"Cannot convert database value to JSON: {e!s}",
                field_name=self.name,
                code="conversion_error",
            ) from e

    def _prepare_value(self, value: Any) -> DatabaseValue:
        """Prepare JSON value for comparison.

        Converts value to JSON string for database comparison.

        Args:
            value: Value to prepare

        Returns:
            Prepared JSON value or None
        """
        if value is None:
            return None

        try:
            return json.dumps(value, cls=self.encoder)
        except (TypeError, ValueError):
            return None

    def has_key(self, key: str, path: str | None = None) -> ComparisonOperator:
        """Check if JSON object has specific key.

        Args:
            key: Key to check for
            path: Optional JSON path to check in (dot notation)

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "has_key", {"key": key, "path": path})

    def has_value(self, value: Any, path: str | None = None) -> ComparisonOperator:
        """Check if JSON object has specific value.

        Args:
            value: Value to check for
            path: Optional JSON path to check in (dot notation)

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "has_value", {"value": self._prepare_value(value), "path": path})

    def contains(self, value: Any) -> ComparisonOperator:
        """Check if JSON array contains value.

        Args:
            value: Value to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "contains", self._prepare_value(value))

    def length_equals(self, length: int) -> ComparisonOperator:
        """Check if JSON array length equals value.

        Args:
            length: Length to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "length_eq", length)

    def length_greater_than(self, length: int) -> ComparisonOperator:
        """Check if JSON array length is greater than value.

        Args:
            length: Length to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "length_gt", length)

    def length_less_than(self, length: int) -> ComparisonOperator:
        """Check if JSON array length is less than value.

        Args:
            length: Length to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "length_lt", length)

    def matches_schema(self, schema: dict[str, Any]) -> ComparisonOperator:
        """Check if JSON value matches schema.

        Args:
            schema: JSON schema to validate against

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "matches_schema", schema)

    def type_equals(self, json_type: str) -> ComparisonOperator:
        """Check if JSON value is of specific type.

        Args:
            json_type: JSON type ("object", "array", "string", "number", "boolean", "null")

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "type_equals", json_type)

    def is_empty(self) -> ComparisonOperator:
        """Check if JSON object/array is empty.

        Returns:
            ComparisonOperator: Comparison operator with field name
        """
        return ComparisonOperator(self.name, "is_empty", None)

    def is_not_empty(self) -> ComparisonOperator:
        """Check if JSON object/array is not empty.

        Returns:
            ComparisonOperator: Comparison operator with field name
        """
        return ComparisonOperator(self.name, "is_not_empty", None)
