"""Dictionary field implementation.

This module provides dictionary field types for handling key-value mappings.
It supports:
- Dictionaries with typed keys and values
- Required and optional keys
- Key validation
- Value validation
- Default values
- Nested validation

Examples:
    >>> class User(Model):
    ...     metadata = DictField(StringField(), JsonField(), default=dict)
    ...     settings = DictField(
    ...         StringField(),
    ...         BooleanField(),
    ...         required_keys={'active', 'notifications'},
    ...     )
    ...     scores = DictField(StringField(), IntegerField(), min_length=1)
"""

from typing import Any, Dict, Generic, Optional, Set, Type, TypeVar, Union, cast

from earnorm.fields.base import Field, ValidationError

K = TypeVar("K")  # Key type
V = TypeVar("V")  # Value type


class DictField(Field[Dict[K, V]], Generic[K, V]):
    """Field for dictionary values.

    Attributes:
        key_field: Field type for dictionary keys
        value_field: Field type for dictionary values
        min_length: Minimum number of items
        max_length: Maximum number of items
        required_keys: Set of required keys
    """

    def __init__(
        self,
        key_field: Field[K],
        value_field: Field[V],
        *,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        required_keys: Optional[Set[K]] = None,
        default: Optional[Union[Dict[K, V], Type[Dict[Any, Any]]]] = None,
        **options: Any,
    ) -> None:
        """Initialize dictionary field.

        Args:
            key_field: Field type for dictionary keys
            value_field: Field type for dictionary values
            min_length: Minimum number of items
            max_length: Maximum number of items
            required_keys: Set of required keys
            default: Default value or dict type
            **options: Additional field options
        """
        # Handle default value
        processed_default: Optional[Dict[K, V]] = None
        if default is not None:
            if default is dict:
                processed_default = cast(Dict[K, V], {})
            else:
                processed_default = cast(Dict[K, V], default)

        super().__init__(default=processed_default, **options)
        self.key_field = key_field
        self.value_field = value_field
        self.min_length = min_length
        self.max_length = max_length
        self.required_keys = required_keys or set()

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

        # Set up key and value fields
        self.key_field.name = f"{self.name}[key]"
        self.value_field.name = f"{self.name}[value]"
        self.key_field.required = True  # Dict keys can't be None
        self.value_field.required = True  # Dict values can't be None

    async def validate(self, value: Any) -> None:
        """Validate dictionary value.

        Args:
            value: Value to validate

        Raises:
            ValidationError: If validation fails
        """
        await super().validate(value)

        if value is not None:
            if not isinstance(value, dict):
                raise ValidationError("Value must be a dictionary", self.name)

            value_dict = cast(Dict[Any, Any], value)
            if self.min_length is not None and len(value_dict) < self.min_length:
                raise ValidationError(
                    f"Dictionary must have at least {self.min_length} items",
                    self.name,
                )

            if self.max_length is not None and len(value_dict) > self.max_length:
                raise ValidationError(
                    f"Dictionary must have at most {self.max_length} items",
                    self.name,
                )

            # Check required keys
            missing_keys = self.required_keys - set(value_dict.keys())
            if missing_keys:
                raise ValidationError(
                    f"Missing required keys: {missing_keys}",
                    self.name,
                )

            # Validate keys and values
            for key, val in value_dict.items():
                try:
                    await self.key_field.validate(key)
                except ValidationError as e:
                    raise ValidationError(
                        f"Invalid key {key!r}: {str(e)}",
                        self.name,
                    )

                try:
                    await self.value_field.validate(val)
                except ValidationError as e:
                    raise ValidationError(
                        f"Invalid value for key {key!r}: {str(e)}",
                        self.name,
                    )

    async def convert(self, value: Any) -> Optional[Dict[K, V]]:
        """Convert value to dictionary.

        Args:
            value: Value to convert

        Returns:
            Dictionary value

        Raises:
            ValidationError: If conversion fails
        """
        if value is None:
            return self.default

        try:
            if isinstance(value, str):
                # Try to parse as JSON object
                import json

                try:
                    value = json.loads(value)
                    if not isinstance(value, dict):
                        raise ValidationError(
                            "JSON value must be an object",
                            self.name,
                        )
                except json.JSONDecodeError as e:
                    raise ValidationError(
                        f"Invalid JSON object: {str(e)}",
                        self.name,
                    )
            elif not isinstance(value, dict):
                raise ValidationError(
                    f"Cannot convert {type(value).__name__} to dictionary",
                    self.name,
                )

            # Convert keys and values
            value_dict = cast(Dict[Any, Any], value)
            result: Dict[K, V] = {}
            for key, val in value_dict.items():
                try:
                    converted_key = await self.key_field.convert(key)
                    if converted_key is None:
                        raise ValidationError(
                            "Dictionary keys cannot be None",
                            self.name,
                        )

                    converted_value = await self.value_field.convert(val)
                    if converted_value is None:
                        raise ValidationError(
                            "Dictionary values cannot be None",
                            self.name,
                        )

                    result[converted_key] = converted_value
                except ValidationError as e:
                    raise ValidationError(
                        f"Failed to convert item with key {key!r}: {str(e)}",
                        self.name,
                    )

            return result
        except Exception as e:
            raise ValidationError(str(e), self.name)

    async def to_db(
        self, value: Optional[Dict[K, V]], backend: str
    ) -> Optional[Dict[str, Any]]:
        """Convert dictionary to database format.

        Args:
            value: Dictionary value
            backend: Database backend type

        Returns:
            Database value
        """
        if value is None:
            return None

        result: Dict[str, Any] = {}
        for key, val in value.items():
            db_key = await self.key_field.to_db(key, backend)
            if not isinstance(db_key, str):
                # Convert key to string for database storage
                db_key = str(db_key)
            db_value = await self.value_field.to_db(val, backend)
            result[db_key] = db_value

        return result

    async def from_db(self, value: Any, backend: str) -> Optional[Dict[K, V]]:
        """Convert database value to dictionary.

        Args:
            value: Database value
            backend: Database backend type

        Returns:
            Dictionary value
        """
        if value is None:
            return None

        if not isinstance(value, dict):
            raise ValidationError(
                f"Expected dictionary from database, got {type(value).__name__}",
                self.name,
            )

        value_dict = cast(Dict[str, Any], value)
        result: Dict[K, V] = {}
        for key, val in value_dict.items():
            try:
                converted_key = await self.key_field.from_db(key, backend)
                if converted_key is None:
                    raise ValidationError(
                        "Dictionary keys cannot be None",
                        self.name,
                    )

                converted_value = await self.value_field.from_db(val, backend)
                if converted_value is None:
                    raise ValidationError(
                        "Dictionary values cannot be None",
                        self.name,
                    )

                result[converted_key] = converted_value
            except ValidationError as e:
                raise ValidationError(
                    f"Failed to convert item with key {key!r}: {str(e)}",
                    self.name,
                )

        return result
