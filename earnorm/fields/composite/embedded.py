"""Embedded field implementation.

This module provides embedded field type for handling nested model instances.
It supports:
- Model instance validation
- Dictionary conversion
- Lazy loading
- Database type mapping
- Embedded model comparison operations

Examples:
    >>> class Address(Model):
    ...     street = StringField(required=True)
    ...     city = StringField(required=True)
    ...     country = StringField(required=True)
    ...
    >>> class User(Model):
    ...     name = StringField(required=True)
    ...     home_address = EmbeddedField(Address)
    ...     work_address = EmbeddedField(Address, nullable=True)
    ...
    ...     # Query examples
    ...     us_users = User.find(User.home_address.matches({"country": "US"}))
    ...     same_city = User.find(User.home_address.equals(User.work_address, ["city"]))
    ...     has_address = User.find(User.home_address.is_not_null())
"""

from typing import TYPE_CHECKING, Any, Dict, Generic, List, Optional, Type, TypeVar

from earnorm.exceptions import FieldValidationError
from earnorm.fields.base import BaseField
from earnorm.types import ComparisonOperator, DatabaseValue, FieldComparisonMixin

if TYPE_CHECKING:
    from earnorm.base.model.base import BaseModel

    M = TypeVar("M", bound="BaseModel")  # Type variable for embedded model
else:
    M = TypeVar("M")  # Type variable for runtime


class EmbeddedField(BaseField[M], FieldComparisonMixin, Generic[M]):
    """Field for embedded model instances.

    This field type handles embedded model instances, with support for:
    - Model instance validation
    - Dictionary conversion
    - Lazy loading
    - Database type mapping
    - Embedded model comparison operations

    Attributes:
        model_class: Model class for embedded instances
        allow_dict: Whether to allow dictionary input
        lazy_load: Whether to load embedded models lazily
        backend_options: Database backend options
    """

    model_class: Type[M]
    allow_dict: bool
    lazy_load: bool
    backend_options: dict[str, Any]
    _parent_model: Optional[Any]

    def __init__(
        self,
        model_class: Type[M],
        *,
        allow_dict: bool = True,
        lazy_load: bool = False,
        **options: Any,
    ) -> None:
        """Initialize embedded field.

        Args:
            model_class: Model class for embedded instances
            allow_dict: Whether to allow dictionary input
            lazy_load: Whether to load embedded models lazily
            **options: Additional field options
        """
        super().__init__(**options)

        self.model_class = model_class
        self.allow_dict = allow_dict
        self.lazy_load = lazy_load
        self._parent_model = None

        # Initialize backend options
        self.backend_options = {
            "mongodb": {"type": "object"},
            "postgres": {"type": "JSONB"},
            "mysql": {"type": "JSON"},
        }

    def _get_model_env(self) -> Any:
        """Get environment from parent model.

        Returns:
            Model environment

        Raises:
            FieldValidationError: If parent model or environment not found
        """
        if self._parent_model is None:
            raise FieldValidationError(
                message="Cannot create embedded instance without parent model",
                field_name=self.name,
                code="missing_parent",
            )

        model_env = getattr(self._parent_model, "env", None)
        if model_env is None:
            raise FieldValidationError(
                message="Parent model has no environment",
                field_name=self.name,
                code="missing_env",
            )

        return model_env

    async def setup(self, name: str, model_name: str) -> None:
        """Set up the field.

        Args:
            name: Field name
            model_name: Model name
        """
        await super().setup(name, model_name)
        self._parent_model = object.__getattribute__(self, "model")

    async def validate(self, value: Any) -> None:
        """Validate embedded value.

        This method validates:
        - Value is model instance or dict (if allowed)
        - Model instance is valid
        - Dictionary values can be converted to model instance

        Args:
            value: Value to validate

        Raises:
            FieldValidationError: If validation fails
        """
        await super().validate(value)

        if value is not None:
            # Convert dict to model instance for validation
            if isinstance(value, dict):
                if not self.allow_dict:
                    raise FieldValidationError(
                        message="Dictionary input not allowed",
                        field_name=self.name,
                        code="dict_not_allowed",
                    )

                try:
                    model_env = self._get_model_env()
                    value = self.model_class(model_env, **value)  # type: ignore
                except (TypeError, ValueError) as e:
                    raise FieldValidationError(
                        message=str(e),
                        field_name=self.name,
                        code="invalid_dict",
                    ) from e

            # Validate model instance
            if not isinstance(value, self.model_class):
                raise FieldValidationError(
                    message=f"Value must be a {self.model_class.__name__} instance",
                    field_name=self.name,
                    code="invalid_type",
                )

            try:
                await value.validate()  # type: ignore
            except FieldValidationError as e:
                raise FieldValidationError(
                    message=str(e),
                    field_name=self.name,
                    code="validation_error",
                ) from e

    async def convert(self, value: Any) -> Optional[M]:
        """Convert value to model instance.

        Handles:
        - None values
        - Model instances
        - Dictionary values
        - JSON string values

        Args:
            value: Value to convert

        Returns:
            Converted model instance or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            if isinstance(value, self.model_class):
                return value
            elif isinstance(value, dict) and self.allow_dict:
                model_env = self._get_model_env()
                instance = object.__new__(self.model_class)
                instance.env = model_env  # type: ignore

                # Convert dictionary to model instance
                value_dict: dict[str, Any] = value
                for key, val in value_dict.items():
                    key_type = type(key).__name__
                    # Check key type without isinstance since we know it's str from dict
                    if key_type != "str":
                        raise FieldValidationError(
                            message=f"Dictionary key must be string, got {key_type}",
                            field_name=self.name,
                            code="invalid_key_type",
                        )
                    setattr(instance, key, val)
                return instance
            elif isinstance(value, str) and self.allow_dict:
                # Try to parse as JSON object
                import json

                try:
                    data = json.loads(value)
                    if not isinstance(data, dict):
                        raise FieldValidationError(
                            message="JSON value must be an object",
                            field_name=self.name,
                            code="invalid_json",
                        )

                    model_env = self._get_model_env()
                    instance = object.__new__(self.model_class)
                    instance.env = model_env  # type: ignore

                    # Convert JSON object to model instance
                    json_dict: dict[str, Any] = data
                    for key, val in json_dict.items():
                        key_type = type(key).__name__
                        # Check key type without isinstance since we know it's str from dict
                        if key_type != "str":
                            raise FieldValidationError(
                                message=f"Dictionary key must be string, got {key_type}",
                                field_name=self.name,
                                code="invalid_key_type",
                            )
                        setattr(instance, key, val)
                    return instance
                except json.JSONDecodeError as e:
                    raise FieldValidationError(
                        message=f"Invalid JSON object: {str(e)}",
                        field_name=self.name,
                        code="invalid_json",
                    ) from e
            else:
                # Get type names for error message
                value_type = type(value).__name__ if value is not None else "None"  # type: ignore
                model_type = self.model_class.__name__
                raise FieldValidationError(
                    message=f"Cannot convert {value_type} to {model_type}",
                    field_name=self.name,
                    code="conversion_error",
                )
        except (TypeError, ValueError) as e:
            raise FieldValidationError(
                message=str(e),
                field_name=self.name,
                code="conversion_error",
            ) from e

    async def to_db(self, value: Optional[M], backend: str) -> DatabaseValue:
        """Convert model instance to database format.

        Args:
            value: Model instance to convert
            backend: Database backend type

        Returns:
            Converted model instance or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            return await value.to_db(backend)  # type: ignore
        except Exception as e:
            raise FieldValidationError(
                message=f"Cannot convert to database format: {str(e)}",
                field_name=self.name,
                code="conversion_error",
            ) from e

    async def from_db(self, value: DatabaseValue, backend: str) -> Optional[M]:
        """Convert database value to model instance.

        Args:
            value: Database value to convert
            backend: Database backend type

        Returns:
            Converted model instance or None

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

            model_env = self._get_model_env()

            if self.lazy_load:
                # Create model instance without validation
                instance = object.__new__(self.model_class)
                instance.env = model_env  # type: ignore
                await instance.from_db(value, backend)  # type: ignore
                return instance
            else:
                # Create and validate model instance
                instance = object.__new__(self.model_class)
                instance.env = model_env  # type: ignore
                await instance.from_db(value, backend)  # type: ignore
                await instance.validate()  # type: ignore
                return instance
        except Exception as e:
            raise FieldValidationError(
                message=f"Cannot convert database value: {str(e)}",
                field_name=self.name,
                code="conversion_error",
            ) from e

    def _prepare_value(self, value: Any) -> DatabaseValue:
        """Prepare embedded value for comparison.

        Converts value to dictionary for database comparison.

        Args:
            value: Value to prepare

        Returns:
            Prepared dictionary value or None
        """
        if value is None:
            return None

        try:
            if isinstance(value, self.model_class):
                return value.to_dict()
            elif isinstance(value, dict):
                return value  # type: ignore
            return None
        except (TypeError, ValueError):
            return None

    def matches(self, criteria: Dict[str, Any]) -> ComparisonOperator:
        """Check if embedded model matches criteria.

        Args:
            criteria: Dictionary of field values to match

        Returns:
            ComparisonOperator: Comparison operator with field name and criteria
        """
        return ComparisonOperator(self.name, "matches", self._prepare_value(criteria))

    def equals(
        self, other: Any, fields: Optional[List[str]] = None
    ) -> ComparisonOperator:
        """Check if embedded model equals another model or dictionary.

        Args:
            other: Model instance or dictionary to compare with
            fields: Optional list of fields to compare, if None compares all fields

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(
            self.name, "equals", {"value": self._prepare_value(other), "fields": fields}
        )

    def not_equals(
        self, other: Any, fields: Optional[List[str]] = None
    ) -> ComparisonOperator:
        """Check if embedded model does not equal another model or dictionary.

        Args:
            other: Model instance or dictionary to compare with
            fields: Optional list of fields to compare, if None compares all fields

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(
            self.name,
            "not_equals",
            {"value": self._prepare_value(other), "fields": fields},
        )

    def has_fields(self, fields: List[str]) -> ComparisonOperator:
        """Check if embedded model has all specified fields with non-null values.

        Args:
            fields: List of field names to check

        Returns:
            ComparisonOperator: Comparison operator with field name and fields
        """
        return ComparisonOperator(self.name, "has_fields", fields)

    def is_null(self) -> ComparisonOperator:
        """Check if embedded model is null.

        Returns:
            ComparisonOperator: Comparison operator with field name
        """
        return ComparisonOperator(self.name, "is_null", None)

    def is_not_null(self) -> ComparisonOperator:
        """Check if embedded model is not null.

        Returns:
            ComparisonOperator: Comparison operator with field name
        """
        return ComparisonOperator(self.name, "is_not_null", None)
