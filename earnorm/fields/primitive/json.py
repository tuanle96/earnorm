"""JSON field implementation.

This module provides JSON field type for handling JSON data.
It supports:
- JSON validation
- Schema validation
- Type conversion
- Database type mapping

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
"""

import json
from typing import Any, Final, Optional

from jsonschema import Draft202012Validator, ValidationError, validate

from earnorm.exceptions import FieldValidationError
from earnorm.fields.base import BaseField
from earnorm.fields.types import DatabaseValue
from earnorm.fields.validators.base import Validator

# Constants
DEFAULT_ENCODER: Final[type[json.JSONEncoder]] = json.JSONEncoder
DEFAULT_DECODER: Final[type[json.JSONDecoder]] = json.JSONDecoder


class JSONField(BaseField[Any]):
    """Field for JSON data.

    This field type handles JSON data, with support for:
    - JSON validation
    - Schema validation
    - Type conversion
    - Database type mapping

    Attributes:
        schema: JSON schema for validation
        encoder: JSON encoder class
        decoder: JSON decoder class
        backend_options: Database backend options
    """

    schema: Optional[dict[str, Any]]
    encoder: type[json.JSONEncoder]
    decoder: type[json.JSONDecoder]
    backend_options: dict[str, Any]

    def __init__(
        self,
        *,
        schema: Optional[dict[str, Any]] = None,
        encoder: Optional[type[json.JSONEncoder]] = None,
        decoder: Optional[type[json.JSONDecoder]] = None,
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
                raise ValueError(f"Invalid JSON schema: {str(e)}") from e

        # Initialize backend options
        self.backend_options = {
            "mongodb": {"type": "object"},
            "postgres": {"type": "JSONB"},
            "mysql": {"type": "JSON"},
        }

    async def validate(self, value: Any) -> None:
        """Validate JSON value.

        This method validates:
        - Value can be serialized to JSON
        - Value matches JSON schema if provided

        Args:
            value: Value to validate

        Raises:
            FieldValidationError: If validation fails
        """
        await super().validate(value)

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
                            message=f"JSON schema validation failed: {str(e)}",
                            field_name=self.name,
                            code="schema_error",
                        ) from e
            except (TypeError, ValueError) as e:
                raise FieldValidationError(
                    message=f"Invalid JSON value: {str(e)}",
                    field_name=self.name,
                    code="invalid_json",
                ) from e

    async def convert(self, value: Any) -> Optional[Any]:
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
                message=f"Cannot convert value to JSON: {str(e)}",
                field_name=self.name,
                code="conversion_error",
            ) from e

    async def to_db(self, value: Optional[Any], backend: str) -> DatabaseValue:
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
                message=f"Cannot convert value to JSON: {str(e)}",
                field_name=self.name,
                code="conversion_error",
            ) from e

    async def from_db(self, value: DatabaseValue, backend: str) -> Optional[Any]:
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
                message=f"Cannot convert database value to JSON: {str(e)}",
                field_name=self.name,
                code="conversion_error",
            ) from e
