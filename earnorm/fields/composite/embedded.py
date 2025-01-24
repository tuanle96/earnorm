"""Embedded field implementation.

This module provides embedded field types for handling nested model instances.
It supports:
- Embedding model instances as field values
- Nested validation
- Model instance creation from dictionaries
- Recursive database conversion
- Lazy model loading

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
"""

from typing import Any, Dict, Optional, Type, TypeVar

from earnorm.base.model.base import BaseModel
from earnorm.fields.base import Field, ValidationError

M = TypeVar("M", bound=BaseModel)  # Type of embedded model


class EmbeddedField(Field[M]):
    """Field for embedded model instances.

    Attributes:
        model_class: Model class for embedded instances
        allow_dict: Whether to allow dictionary input
        lazy_load: Whether to load embedded models lazily
    """

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
        """Validate embedded value.

        Args:
            value: Value to validate

        Raises:
            ValidationError: If validation fails
        """
        await super().validate(value)

        if value is not None:
            if not isinstance(value, (self.model_class, dict)):
                raise ValidationError(
                    f"Value must be an instance of {self.model_class.__name__} or dict",
                    self.name,
                )

            if isinstance(value, dict) and not self.allow_dict:
                raise ValidationError(
                    "Dictionary input is not allowed for this field",
                    self.name,
                )

            # Convert dict to model instance for validation
            if isinstance(value, dict):
                try:
                    if not hasattr(self, "model"):
                        raise ValidationError(
                            "Cannot create embedded instance without parent model",
                            self.name,
                        )
                    value = self.model_class(self.model.env, **value)  # type: ignore
                except (TypeError, ValueError) as e:
                    raise ValidationError(str(e), self.name)

            # Validate model instance
            try:
                await value.validate()  # type: ignore
            except ValidationError as e:
                raise ValidationError(str(e), self.name)

    async def convert(self, value: Any) -> Optional[M]:
        """Convert value to model instance.

        Args:
            value: Value to convert

        Returns:
            Model instance

        Raises:
            ValidationError: If conversion fails
        """
        if value is None:
            return self.default

        try:
            if isinstance(value, self.model_class):
                return value
            elif isinstance(value, dict) and self.allow_dict:
                if not hasattr(self, "model"):
                    raise ValidationError(
                        "Cannot create embedded instance without parent model",
                        self.name,
                    )
                return self.model_class(self.model.env, **value)  # type: ignore
            elif isinstance(value, str):
                # Try to parse as JSON object
                import json

                try:
                    data = json.loads(value)
                    if not isinstance(data, dict):
                        raise ValidationError(
                            "JSON value must be an object",
                            self.name,
                        )
                    if not hasattr(self, "model"):
                        raise ValidationError(
                            "Cannot create embedded instance without parent model",
                            self.name,
                        )
                    return self.model_class(self.model.env, **data)  # type: ignore
                except json.JSONDecodeError as e:
                    raise ValidationError(
                        f"Invalid JSON object: {str(e)}",
                        self.name,
                    )
            else:
                raise ValidationError(
                    f"Cannot convert {type(value).__name__} to {self.model_class.__name__}",  # type: ignore
                    self.name,
                )
        except (TypeError, ValueError) as e:
            raise ValidationError(str(e), self.name)

    async def to_db(self, value: Optional[M], backend: str) -> Optional[Dict[str, Any]]:
        """Convert model instance to database format.

        Args:
            value: Model instance
            backend: Database backend type

        Returns:
            Database value
        """
        if value is None:
            return None

        return await value.to_db(backend)  # type: ignore

    async def from_db(self, value: Any, backend: str) -> Optional[M]:
        """Convert database value to model instance.

        Args:
            value: Database value
            backend: Database backend type

        Returns:
            Model instance
        """
        if value is None:
            return None

        if not isinstance(value, dict):
            raise ValidationError(
                f"Expected dictionary from database, got {type(value).__name__}",
                self.name,
            )

        try:
            if not hasattr(self, "model"):
                raise ValidationError(
                    "Cannot create embedded instance without parent model",
                    self.name,
                )

            if self.lazy_load:
                # Create model instance without validation
                instance = self.model_class(self.model.env)  # type: ignore
                await instance.from_db(value, backend)  # type: ignore
                return instance
            else:
                # Create and validate model instance
                instance = self.model_class(self.model.env)  # type: ignore
                await instance.from_db(value, backend)  # type: ignore
                await instance.validate()  # type: ignore
                return instance
        except Exception as e:
            raise ValidationError(str(e), self.name)
