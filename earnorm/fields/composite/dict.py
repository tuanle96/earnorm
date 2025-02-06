"""Dictionary field implementation.

This module provides dictionary field type for handling key-value mappings.
It supports:
- Dictionary validation
- Key and value validation
- Nested dictionaries
- Type checking
- Database type mapping
- Dictionary comparison operations

Examples:
    >>> class User(Model):
    ...     metadata = DictField(StringField())
    ...     settings = DictField(
    ...         JSONField(),
    ...         min_length=1,
    ...         max_length=100
    ...     )
    ...
    ...     # Query examples
    ...     with_key = User.find(User.metadata.has_key("role"))
    ...     admins = User.find(User.metadata.has_value("admin"))
"""

from typing import Any, Dict, Generic, Mapping, Optional, TypeVar, cast

from earnorm.exceptions import FieldValidationError
from earnorm.fields.base import BaseField
from earnorm.types.fields import ComparisonOperator, DatabaseValue, FieldComparisonMixin

T = TypeVar("T")


class DictField(BaseField[Dict[str, T]], FieldComparisonMixin, Generic[T]):
    """Field for dictionary values.

    This field type handles dictionaries, with support for:
    - Dictionary validation
    - Key and value validation
    - Nested dictionaries
    - Type checking
    - Database type mapping
    - Dictionary comparison operations

    Attributes:
        value_field: Field type for dictionary values
        min_length: Minimum dictionary length
        max_length: Maximum dictionary length
        backend_options: Database backend options
    """

    _value_field: BaseField[T]
    min_length: Optional[int]
    max_length: Optional[int]
    backend_options: Dict[str, Any]

    def __init__(
        self,
        value_field: BaseField[T],
        *,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        **options: Any,
    ) -> None:
        """Initialize dictionary field.

        Args:
            value_field: Field type for dictionary values
            min_length: Minimum dictionary length
            max_length: Maximum dictionary length
            **options: Additional field options
        """
        super().__init__(**options)

        # Store field options
        self._value_field = value_field  # type: ignore
        self.min_length = min_length
        self.max_length = max_length

        # Initialize backend options
        self.backend_options = {}
        for backend in ["mongodb", "postgres", "mysql"]:
            try:
                from earnorm.database.type_mapping import (
                    get_field_options,
                    get_field_type,
                )

                field_type = get_field_type("dict", backend)
                field_options = get_field_options(backend)
                self.backend_options[backend] = {
                    "type": field_type,
                    **field_options,
                }
            except ImportError:
                # Fallback options if type_mapping not available
                self.backend_options[backend] = {
                    "type": "object" if backend == "mongodb" else "JSON",
                    "index": False,
                    "unique": False,
                }

    async def get_value_field(self) -> BaseField[T]:
        """Get value field type.

        Returns:
            Field type for dictionary values
        """
        if not hasattr(self, "_value_field"):
            raise AttributeError("value_field has not been initialized")
        return await self._value_field  # type: ignore

    async def setup(self, name: str, model_name: str) -> None:
        """Set up field.

        This method:
        1. Sets up base field
        2. Sets up value field

        Args:
            name: Field name
            model_name: Model name
        """
        await super().setup(name, model_name)
        value_field = await self.get_value_field()
        await value_field.setup(f"{name}.value", model_name)

    async def validate(
        self, value: Any, context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, T]]:
        """Validate dictionary value.

        This method validates:
        - Value is a dictionary
        - Dictionary length
        - Key types
        - Value types using value_field

        Args:
            value: Value to validate
            context: Validation context

        Returns:
            Validated dictionary value

        Raises:
            FieldValidationError: If validation fails
        """
        value = await super().validate(value, context)

        if value is not None:
            if not isinstance(value, Mapping):
                raise FieldValidationError(
                    message=f"Expected dictionary, got {type(value).__name__}",
                    field_name=self.name,
                    code="invalid_type",
                )

            dict_value = cast(Dict[Any, Any], value)

            # Validate length
            if self.min_length is not None and len(dict_value) < self.min_length:
                raise FieldValidationError(
                    message=f"Dictionary must have at least {self.min_length} items",
                    field_name=self.name,
                    code="min_length",
                )

            if self.max_length is not None and len(dict_value) > self.max_length:
                raise FieldValidationError(
                    message=f"Dictionary cannot have more than {self.max_length} items",
                    field_name=self.name,
                    code="max_length",
                )

            # Validate keys and values
            result: Dict[str, T] = {}
            for key, val in dict_value.items():
                key_str = str(key)
                # Validate value
                try:
                    value_field = await self.get_value_field()
                    validated_value = await value_field.validate(val, context)
                    if validated_value is not None:
                        result[key_str] = validated_value
                except FieldValidationError as e:
                    raise FieldValidationError(
                        message=f"Invalid value for key '{key_str}': {str(e)}",
                        field_name=self.name,
                        code="invalid_value",
                    ) from e

            return result

        return None

    async def convert(self, value: Any) -> Optional[Dict[str, T]]:
        """Convert value to dictionary.

        This method handles:
        - None values
        - Dictionary values
        - Mapping values
        - Value type conversion using value_field

        Args:
            value: Value to convert

        Returns:
            Converted dictionary value

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            if isinstance(value, Mapping):
                dict_value = cast(Dict[Any, Any], value)
                result: Dict[str, T] = {}
                value_field = self.get_value_field()
                for key, val in dict_value.items():
                    key_str = str(key)
                    converted_value = await value_field.convert(val)  # type: ignore
                    if converted_value is not None:
                        result[key_str] = converted_value
                return result
            else:
                raise TypeError(f"Cannot convert {type(value).__name__} to dictionary")

        except (TypeError, ValueError) as e:
            raise FieldValidationError(
                message=str(e),
                field_name=self.name,
                code="conversion_error",
            ) from e

    async def to_db(
        self, value: Optional[Dict[str, T]], backend: str
    ) -> Optional[Dict[str, Any]]:
        """Convert dictionary to database format.

        Args:
            value: Dictionary value to convert
            backend: Database backend type

        Returns:
            Converted dictionary value
        """
        if value is None:
            return None

        result: Dict[str, Any] = {}
        value_field = self.get_value_field()
        for key, val in value.items():
            db_value = await value_field.to_db(val, backend)  # type: ignore
            if db_value is not None:
                result[key] = db_value
        return result

    async def from_db(
        self, value: DatabaseValue, backend: str
    ) -> Optional[Dict[str, T]]:
        """Convert database value to dictionary.

        Args:
            value: Database value to convert
            backend: Database backend type

        Returns:
            Converted dictionary value

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        if not isinstance(value, Mapping):
            raise FieldValidationError(
                message=f"Expected dictionary from database, got {type(value).__name__}",
                field_name=self.name,
                code="invalid_type",
            )

        try:
            result: Dict[str, T] = {}
            value_field = self.get_value_field()
            for key, val in value.items():
                converted_value = await value_field.from_db(val, backend)  # type: ignore
                if converted_value is not None:
                    result[key] = converted_value
            return result

        except Exception as e:
            raise FieldValidationError(
                message=f"Cannot convert database value: {str(e)}",
                field_name=self.name,
                code="conversion_error",
            ) from e

    def has_key(self, key: str) -> ComparisonOperator:
        """Check if dictionary has key.

        Args:
            key: Key to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and key
        """
        return ComparisonOperator(self.name, "has_key", key)

    def has_value(self, value: T) -> ComparisonOperator:
        """Check if dictionary has value.

        Args:
            value: Value to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "has_value", value)

    def matches(self, query: Dict[str, Any]) -> ComparisonOperator:
        """Check if dictionary matches query.

        Args:
            query: Query dict to match against

        Returns:
            ComparisonOperator: Comparison operator with field name and query
        """
        return ComparisonOperator(self.name, "matches", query)

    def length_equals(self, length: int) -> ComparisonOperator:
        """Check if dictionary has exact length.

        Args:
            length: Length to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and length
        """
        return ComparisonOperator(self.name, "length_equals", length)

    def length_greater_than(self, length: int) -> ComparisonOperator:
        """Check if dictionary length is greater than value.

        Args:
            length: Length to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and length
        """
        return ComparisonOperator(self.name, "length_greater_than", length)

    def length_less_than(self, length: int) -> ComparisonOperator:
        """Check if dictionary length is less than value.

        Args:
            length: Length to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and length
        """
        return ComparisonOperator(self.name, "length_less_than", length)

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
