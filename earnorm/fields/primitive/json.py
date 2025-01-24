"""JSON field implementation.

This module provides JSON field types for handling JSON data.
It supports:
- Dict and list values
- JSON serialization/deserialization
- Schema validation
- Default values
- Custom encoders/decoders

Examples:
    >>> class Product(Model):
    ...     metadata = JSONField(default={})
    ...     tags = JSONField(default=list)
    ...     settings = JSONField(schema={
    ...         "type": "object",
    ...         "properties": {
    ...             "theme": {"type": "string", "enum": ["light", "dark"]},
    ...             "notifications": {"type": "boolean"},
    ...         },
    ...     })
"""

import json
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

from earnorm.fields.base import Field, ValidationError

T = TypeVar("T")  # Generic type for containers
JSONPrimitive = Union[str, int, float, bool, None]
JSONDict = Dict[str, Union[JSONPrimitive, Dict[str, Any], List[Any]]]
JSONList = List[Union[JSONPrimitive, Dict[str, Any], List[Any]]]
JSONValue = Union[JSONDict, JSONList, JSONPrimitive]
ContainerType = Union[Type[Dict[str, Any]], Type[List[Any]]]


class JSONField(Field[JSONValue]):
    """Field for JSON data.

    This class provides:
    - JSON data validation
    - Schema validation
    - Custom serialization/deserialization
    - Default container types
    - Database format conversion

    Attributes:
        schema: JSON schema for validation
        encoder: Custom JSON encoder
        decoder: Custom JSON decoder
        default_type: Default container type (dict or list)
    """

    def __init__(
        self,
        *,
        schema: Optional[Dict[str, Any]] = None,
        encoder: Optional[Type[json.JSONEncoder]] = None,
        decoder: Optional[Type[json.JSONDecoder]] = None,
        default_type: Optional[ContainerType] = None,
        default: Optional[
            Union[JSONValue, Type[Dict[str, Any]], Type[List[Any]]]
        ] = None,
        **options: Any,
    ) -> None:
        """Initialize JSON field.

        Args:
            schema: JSON schema for validation
            encoder: Custom JSON encoder
            decoder: Custom JSON decoder
            default_type: Default container type (dict or list)
            default: Default value or container type
            **options: Additional field options
        """
        # Handle default value
        processed_default: Optional[JSONValue] = None
        if default is not None:
            if isinstance(default, type):
                if default in (dict, list):
                    default_type = default
            else:
                processed_default = default  # type: ignore

        super().__init__(default=processed_default, **options)
        self.schema = schema
        self.encoder = encoder
        self.decoder = decoder
        self.default_type = default_type

        # Update backend options
        self.backend_options.update(
            {
                "mongodb": {
                    "type": "object",
                },
                "postgres": {
                    "type": "JSONB",
                },
                "mysql": {
                    "type": "JSON",
                },
            }
        )

    async def validate(self, value: Any) -> None:
        """Validate JSON value.

        Args:
            value: Value to validate

        Raises:
            ValidationError: If validation fails with code:
                - invalid_json: Value is not JSON serializable
                - invalid_type: Value does not match schema type
                - schema_error: Value does not match schema
        """
        await super().validate(value)

        if value is not None:
            try:
                # Ensure value is JSON serializable
                json.dumps(value, cls=self.encoder)
            except (TypeError, ValueError) as e:
                raise ValidationError(
                    message=f"Value is not JSON serializable: {str(e)}",
                    field_name=self.name,
                    code="invalid_json",
                )

            if self.schema is not None:
                try:
                    # TODO: Implement JSON schema validation
                    # For now, just check basic type
                    if self.schema.get("type") == "object" and not isinstance(
                        value, dict
                    ):
                        raise ValidationError(
                            message="Value must be an object",
                            field_name=self.name,
                            code="invalid_type",
                        )
                    elif self.schema.get("type") == "array" and not isinstance(
                        value, list
                    ):
                        raise ValidationError(
                            message="Value must be an array",
                            field_name=self.name,
                            code="invalid_type",
                        )
                except ValidationError:
                    raise
                except Exception as e:
                    raise ValidationError(
                        message=str(e), field_name=self.name, code="schema_error"
                    )

    async def convert(self, value: Any) -> Optional[JSONValue]:
        """Convert value to JSON.

        This method handles various input types:
        - str: Parsed as JSON string
        - dict/list: Used as is if serializable
        - other: Converted via JSON serialization/deserialization

        Args:
            value: Value to convert

        Returns:
            Converted JSON value

        Raises:
            ValidationError: If conversion fails with code:
                - conversion_failed: Value cannot be converted to JSON
                - invalid_json: Invalid JSON string
        """
        if value is None:
            if self.default_type is not None:
                return self.default_type()
            return self.default

        try:
            if isinstance(value, str):
                try:
                    return json.loads(value, cls=self.decoder)  # type: ignore
                except json.JSONDecodeError as e:
                    raise ValidationError(
                        message=f"Invalid JSON string: {str(e)}",
                        field_name=self.name,
                        code="invalid_json",
                    )
            elif isinstance(value, (dict, list)):
                return value  # type: ignore
            else:
                # Try to convert to JSON
                return json.loads(  # type: ignore
                    json.dumps(value, cls=self.encoder),
                    cls=self.decoder,
                )
        except (TypeError, ValueError) as e:
            raise ValidationError(
                message=str(e), field_name=self.name, code="conversion_failed"
            )

    async def to_db(self, value: Optional[JSONValue], backend: str) -> Optional[str]:
        """Convert JSON to database format.

        Args:
            value: JSON value to convert
            backend: Database backend type ('mongodb', 'postgres', 'mysql')

        Returns:
            JSON string or None

        Raises:
            ValidationError: If conversion fails with code:
                - conversion_failed: Value cannot be converted to JSON string
        """
        if value is None:
            return None

        try:
            if backend == "mongodb":
                return json.dumps(
                    value, cls=self.encoder
                )  # Convert to string for consistency
            return json.dumps(value, cls=self.encoder)
        except (TypeError, ValueError) as e:
            raise ValidationError(
                message=str(e), field_name=self.name, code="conversion_failed"
            )

    async def from_db(self, value: Any, backend: str) -> Optional[JSONValue]:
        """Convert database value to JSON.

        Args:
            value: Database value to convert
            backend: Database backend type ('mongodb', 'postgres', 'mysql')

        Returns:
            Converted JSON value

        Raises:
            ValidationError: If conversion fails with code:
                - conversion_failed: Value cannot be converted to JSON
                - invalid_json: Invalid JSON string
        """
        if value is None:
            return None

        try:
            if backend == "mongodb":
                if isinstance(value, str):
                    return json.loads(value, cls=self.decoder)  # type: ignore
                return value  # type: ignore
            elif isinstance(value, (dict, list)):
                return value  # type: ignore
            elif isinstance(value, str):
                return json.loads(value, cls=self.decoder)  # type: ignore
            else:
                raise TypeError(f"Cannot convert {type(value).__name__} to JSON")
        except json.JSONDecodeError as e:
            raise ValidationError(
                message=f"Invalid JSON string: {str(e)}",
                field_name=self.name,
                code="invalid_json",
            )
        except (TypeError, ValueError) as e:
            raise ValidationError(
                message=str(e), field_name=self.name, code="conversion_failed"
            )
