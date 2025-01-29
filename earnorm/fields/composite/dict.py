"""Dictionary field implementation.

This module provides dictionary field type for handling key-value pairs.
It supports:
- Dictionary validation
- Key/value validation
- Schema validation
- Database type mapping
- Dictionary comparison operations

Examples:
    >>> class Product(Model):
    ...     metadata = DictField(
    ...         key_field=StringField(),
    ...         value_field=AnyField(),
    ...     )
    ...     settings = DictField(
    ...         key_field=StringField(),
    ...         value_field=AnyField(),
    ...         schema={
    ...             "type": "object",
    ...             "properties": {
    ...                 "notifications": {"type": "boolean"},
    ...                 "theme": {"type": "string", "enum": ["light", "dark"]},
    ...             },
    ...         },
    ...     )
    ...
    ...     # Query examples
    ...     has_tags = Product.find(Product.metadata.has_key("tags"))
    ...     dark_theme = Product.find(Product.settings.has_value("dark", path="theme"))
    ...     configured = Product.find(Product.settings.length_greater_than(0))
"""

from typing import Any, Generic, Optional, TypeVar, cast

from jsonschema import Draft202012Validator, ValidationError, validate

from earnorm.exceptions import FieldValidationError
from earnorm.fields.base import BaseField
from earnorm.types.fields import ComparisonOperator, DatabaseValue, FieldComparisonMixin

# Type variables for key and value types
K = TypeVar("K")
V = TypeVar("V")


class DictField(BaseField[dict[K, V]], FieldComparisonMixin, Generic[K, V]):
    """Field for dictionary values.

    This field type handles key-value pairs, with support for:
    - Dictionary validation
    - Key/value validation
    - Schema validation
    - Database type mapping
    - Dictionary comparison operations

    Attributes:
        key_field: Field type for dictionary keys
        value_field: Field type for dictionary values
        schema: JSON schema for validation
        backend_options: Database backend options
    """

    min_length: Optional[int]
    max_length: Optional[int]
    schema: Optional[dict[str, Any]]
    backend_options: dict[str, Any]

    def __init__(
        self,
        key_field: BaseField[K],
        value_field: BaseField[V],
        *,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        schema: Optional[dict[str, Any]] = None,
        **options: Any,
    ) -> None:
        """Initialize dictionary field.

        Args:
            key_field: Field type for dictionary keys
            value_field: Field type for dictionary values
            min_length: Minimum dictionary length
            max_length: Maximum dictionary length
            schema: JSON schema for validation
            **options: Additional field options

        Raises:
            ValueError: If min_length or max_length are invalid
            ValueError: If schema is invalid
        """
        if min_length is not None and min_length < 0:
            raise ValueError("min_length must be non-negative")
        if max_length is not None and max_length < 0:
            raise ValueError("max_length must be non-negative")
        if (
            min_length is not None
            and max_length is not None
            and min_length > max_length
        ):
            raise ValueError("min_length cannot be greater than max_length")

        super().__init__(**options)

        # Store fields as protected attributes
        object.__setattr__(self, "_key_field", key_field)
        object.__setattr__(self, "_value_field", value_field)
        self.min_length = min_length
        self.max_length = max_length
        self.schema = schema

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

    @property
    def key_field(self) -> BaseField[K]:
        """Get key field instance."""
        return cast(BaseField[K], object.__getattribute__(self, "_key_field"))

    @property
    def value_field(self) -> BaseField[V]:
        """Get value field instance."""
        return cast(BaseField[V], object.__getattribute__(self, "_value_field"))

    async def validate(self, value: Any) -> None:
        """Validate dictionary value.

        This method validates:
        - Value is dictionary type
        - Dictionary length is within limits
        - Keys and values are valid
        - Schema validation if provided

        Args:
            value: Value to validate

        Raises:
            FieldValidationError: If validation fails
        """
        await super().validate(value)

        if value is not None:
            if not isinstance(value, dict):
                raise FieldValidationError(
                    message=f"Value must be a dictionary, got {type(value).__name__}",
                    field_name=self.name,
                    code="invalid_type",
                )

            value_dict = cast(dict[Any, Any], value)

            # Check length
            if self.min_length is not None and len(value_dict) < self.min_length:
                raise FieldValidationError(
                    message=f"Dictionary must have at least {self.min_length} items",
                    field_name=self.name,
                    code="min_length",
                )

            if self.max_length is not None and len(value_dict) > self.max_length:
                raise FieldValidationError(
                    message=f"Dictionary cannot have more than {self.max_length} items",
                    field_name=self.name,
                    code="max_length",
                )

            # Validate schema if provided
            if self.schema is not None:
                try:
                    validate(instance=value_dict, schema=self.schema)
                except ValidationError as e:
                    raise FieldValidationError(
                        message=f"Schema validation failed: {str(e)}",
                        field_name=self.name,
                        code="schema_error",
                    ) from e

            # Validate keys and values
            for key, val in value_dict.items():
                try:
                    await self.key_field.validate(key)
                except FieldValidationError as e:
                    raise FieldValidationError(
                        message=f"Invalid key {key!r}: {str(e)}",
                        field_name=self.name,
                        code="invalid_key",
                    ) from e

                try:
                    await self.value_field.validate(val)
                except FieldValidationError as e:
                    raise FieldValidationError(
                        message=f"Invalid value for key {key!r}: {str(e)}",
                        field_name=self.name,
                        code="invalid_value",
                    ) from e

    async def convert(self, value: Any) -> Optional[dict[K, V]]:
        """Convert value to dictionary.

        Handles:
        - None values
        - Dictionary values
        - Mapping values

        Args:
            value: Value to convert

        Returns:
            Converted dictionary value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            if not isinstance(value, dict):
                raise TypeError(f"Cannot convert {type(value).__name__} to dictionary")

            value_dict = cast(dict[Any, Any], value)

            # Convert keys and values
            result: dict[K, V] = {}
            for key, val in value_dict.items():
                try:
                    converted_key = await self.key_field.convert(key)
                    if converted_key is None:
                        raise ValueError("Dictionary keys cannot be None")
                except FieldValidationError as e:
                    raise FieldValidationError(
                        message=f"Cannot convert key {key!r}: {str(e)}",
                        field_name=self.name,
                        code="conversion_error",
                    ) from e

                try:
                    converted_value = await self.value_field.convert(val)
                    if converted_value is not None:
                        result[converted_key] = converted_value
                except FieldValidationError as e:
                    raise FieldValidationError(
                        message=f"Cannot convert value for key {key!r}: {str(e)}",
                        field_name=self.name,
                        code="conversion_error",
                    ) from e

            return result
        except (TypeError, ValueError) as e:
            raise FieldValidationError(
                message=f"Cannot convert value to dictionary: {str(e)}",
                field_name=self.name,
                code="conversion_error",
            ) from e

    async def to_db(self, value: Optional[dict[K, V]], backend: str) -> DatabaseValue:
        """Convert dictionary to database format.

        Args:
            value: Dictionary value to convert
            backend: Database backend type

        Returns:
            Converted dictionary value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            # Convert keys and values
            result: dict[Any, Any] = {}
            for key, val in value.items():
                try:
                    converted_key = await self.key_field.to_db(key, backend)
                    if converted_key is None:
                        raise ValueError("Dictionary keys cannot be None")
                except FieldValidationError as e:
                    raise FieldValidationError(
                        message=f"Cannot convert key {key!r}: {str(e)}",
                        field_name=self.name,
                        code="conversion_error",
                    ) from e

                try:
                    converted_value = await self.value_field.to_db(val, backend)
                    if converted_value is not None:
                        result[converted_key] = converted_value
                except FieldValidationError as e:
                    raise FieldValidationError(
                        message=f"Cannot convert value for key {key!r}: {str(e)}",
                        field_name=self.name,
                        code="conversion_error",
                    ) from e

            return result
        except Exception as e:
            raise FieldValidationError(
                message=f"Cannot convert dictionary to database format: {str(e)}",
                field_name=self.name,
                code="conversion_error",
            ) from e

    async def from_db(self, value: DatabaseValue, backend: str) -> Optional[dict[K, V]]:
        """Convert database value to dictionary.

        Args:
            value: Database value to convert
            backend: Database backend type

        Returns:
            Converted dictionary value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            if not isinstance(value, dict):
                raise TypeError(
                    f"Expected dictionary from database, got {type(value).__name__}"
                )

            value_dict = cast(dict[Any, Any], value)

            # Convert keys and values
            result: dict[K, V] = {}
            for key, val in value_dict.items():
                try:
                    converted_key = await self.key_field.from_db(key, backend)
                    if converted_key is None:
                        raise ValueError("Dictionary keys cannot be None")
                except FieldValidationError as e:
                    raise FieldValidationError(
                        message=f"Cannot convert key {key!r}: {str(e)}",
                        field_name=self.name,
                        code="conversion_error",
                    ) from e

                try:
                    converted_value = await self.value_field.from_db(val, backend)
                    if converted_value is not None:
                        result[converted_key] = converted_value
                except FieldValidationError as e:
                    raise FieldValidationError(
                        message=f"Cannot convert value for key {key!r}: {str(e)}",
                        field_name=self.name,
                        code="conversion_error",
                    ) from e

            return result
        except Exception as e:
            raise FieldValidationError(
                message=f"Cannot convert database value to dictionary: {str(e)}",
                field_name=self.name,
                code="conversion_error",
            ) from e

    def _prepare_value(self, value: Any) -> DatabaseValue:
        """Prepare dictionary value for comparison.

        Converts value to dictionary for database comparison.

        Args:
            value: Value to prepare

        Returns:
            Prepared dictionary value or None
        """
        if value is None:
            return None

        try:
            if isinstance(value, dict):
                return value  # type: ignore
            return None
        except (TypeError, ValueError):
            return None

    def has_key(self, key: K) -> ComparisonOperator:
        """Check if dictionary has specific key.

        Args:
            key: Key to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "has_key", self._prepare_value(key))

    def has_value(self, value: V, path: Optional[str] = None) -> ComparisonOperator:
        """Check if dictionary has specific value.

        Args:
            value: Value to check for
            path: Optional path to nested value (dot notation)

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(
            self.name, "has_value", {"value": self._prepare_value(value), "path": path}
        )

    def has_all_keys(self, keys: list[K]) -> ComparisonOperator:
        """Check if dictionary has all specified keys.

        Args:
            keys: List of keys to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and values
        """
        prepared_values = [self._prepare_value(key) for key in keys]
        return ComparisonOperator(self.name, "has_all_keys", prepared_values)

    def has_any_keys(self, keys: list[K]) -> ComparisonOperator:
        """Check if dictionary has any of specified keys.

        Args:
            keys: List of keys to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and values
        """
        prepared_values = [self._prepare_value(key) for key in keys]
        return ComparisonOperator(self.name, "has_any_keys", prepared_values)

    def length_equals(self, length: int) -> ComparisonOperator:
        """Check if dictionary length equals value.

        Args:
            length: Length to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "length_eq", length)

    def length_greater_than(self, length: int) -> ComparisonOperator:
        """Check if dictionary length is greater than value.

        Args:
            length: Length to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "length_gt", length)

    def length_less_than(self, length: int) -> ComparisonOperator:
        """Check if dictionary length is less than value.

        Args:
            length: Length to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "length_lt", length)

    def matches_schema(self, schema: dict[str, Any]) -> ComparisonOperator:
        """Check if dictionary matches JSON schema.

        Args:
            schema: JSON schema to validate against

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "matches_schema", schema)

    def is_subset(self, other: dict[K, V]) -> ComparisonOperator:
        """Check if dictionary is subset of another dictionary.

        Args:
            other: Dictionary to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "is_subset", self._prepare_value(other))

    def is_superset(self, other: dict[K, V]) -> ComparisonOperator:
        """Check if dictionary is superset of another dictionary.

        Args:
            other: Dictionary to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "is_superset", self._prepare_value(other))

    def is_empty(self) -> ComparisonOperator:
        """Check if dictionary is empty.

        Returns:
            ComparisonOperator: Comparison operator with field name
        """
        return ComparisonOperator(self.name, "is_empty", None)

    def is_not_empty(self) -> ComparisonOperator:
        """Check if dictionary is not empty.

        Returns:
            ComparisonOperator: Comparison operator with field name
        """
        return ComparisonOperator(self.name, "is_not_empty", None)
