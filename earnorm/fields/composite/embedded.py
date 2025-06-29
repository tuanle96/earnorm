"""Embedded field implementation.

This module provides embedded field type for handling nested model instances.
It supports:
- Model validation
- Nested validation
- Database type mapping
- Model comparison operations
- Lazy model loading
- Recursive validation

Examples:
    >>> class Address(Model):
    ...     street = StringField(required=True)
    ...     city = StringField(required=True)
    ...     country = StringField(required=True)
    ...
    >>> class User(Model):
    ...     name = StringField(required=True)
    ...     address = EmbeddedField(Address)
    ...     shipping_address = EmbeddedField(
    ...         Address,
    ...         nullable=True,
    ...         lazy=True
    ...     )
    ...
    ...     # Query examples
    ...     local = User.find(User.address.city.equals("New York"))
    ...     international = User.find(
    ...         User.shipping_address.country.not_equals("USA")
    ...     )
"""

from typing import (
    Any,
    Generic,
    Protocol,
    TypeVar,
    runtime_checkable,
)

from earnorm.database.mappers import get_mapper
from earnorm.exceptions import FieldValidationError, ModelResolutionError
from earnorm.fields.base import BaseField
from earnorm.types.fields import ComparisonOperator, FieldComparisonMixin

JsonDict = dict[str, Any]


@runtime_checkable
class ModelProtocol(Protocol):
    """Protocol for model interface."""

    def __init__(self) -> None:
        """Initialize model instance."""
        ...

    def from_dict(self, data: JsonDict) -> None:
        """Load model from dictionary."""
        ...

    async def validate(self, context: JsonDict | None = None) -> None:
        """Validate model instance."""
        ...

    def to_dict(self) -> JsonDict:
        """Convert model to dictionary."""
        ...


@runtime_checkable
class Environment(Protocol):
    """Protocol for environment interface."""

    async def get_model(self, name: str) -> type[ModelProtocol]:
        """Get model class by name."""
        ...


@runtime_checkable
class Container(Protocol):
    """Protocol for DI container interface."""

    async def get(self, key: str) -> Any:
        """Get service by key."""
        ...

    async def get_environment(self) -> Environment | None:
        """Get environment instance."""
        ...


T = TypeVar("T", bound=ModelProtocol)


class EmbeddedField(BaseField[T], FieldComparisonMixin, Generic[T]):
    """Field for embedded model instances.

    This field type handles nested model instances, with support for:
    - Model validation
    - Nested validation
    - Database type mapping
    - Model comparison operations
    - Lazy model loading
    - Recursive validation

    Attributes:
        model_type: Model class or name
        lazy: Whether to load model class lazily
        _model_class: Cached model class instance
        backend_options: Database backend options
    """

    model_type: str | type[T]
    lazy: bool
    _model_class: type[T] | None
    backend_options: dict[str, Any]

    def __init__(
        self,
        model_type: str | type[T],
        *,
        lazy: bool = False,
        **options: Any,
    ) -> None:
        """Initialize embedded field.

        Args:
            model_type: Model class or name (if lazy loading)
            lazy: Whether to load model class lazily
            **options: Additional field options
        """
        super().__init__(**options)

        # Store model type and lazy loading flag
        self.model_type = model_type
        self.lazy = lazy

        # Initialize model class
        if lazy:
            object.__setattr__(self, "_model_class", None)
        else:
            object.__setattr__(self, "_model_class", model_type)

        # Initialize backend options using mappers
        self.backend_options = {}
        for backend in ["mongodb", "postgres", "mysql"]:
            mapper = get_mapper(backend)
            self.backend_options[backend] = {
                "type": mapper.get_field_type(self),
                **mapper.get_field_options(self),
            }

    async def get_model_class(self) -> type[T]:
        """Get model class instance.

        This method handles lazy loading of model classes.

        Returns:
            Model class instance

        Raises:
            ModelResolutionError: If model class cannot be resolved
        """
        if self._model_class is not None:
            return self._model_class

        if isinstance(self.model_type, str):
            try:
                from earnorm.di import container

                env = await container.get("environment")
                if env is None:
                    raise ModelResolutionError(
                        message="Environment not initialized",
                        field_name=self.name,
                    )

                model_class = await env.get_model(self.model_type)
                object.__setattr__(self, "_model_class", model_class)
                return model_class

            except Exception as e:
                raise ModelResolutionError(
                    message=f"Cannot resolve model class {self.model_type}: {e!s}",
                    field_name=self.name,
                ) from e

        return self.model_type

    async def prepare_value(self, value: T | JsonDict | None) -> T | None:
        """Prepare value for validation.

        This method handles conversion from dictionary to model instance.

        Args:
            value: Value to prepare

        Returns:
            Prepared value

        Raises:
            FieldValidationError: If value cannot be prepared
        """
        if value is None:
            return None

        try:
            model_class = await self.get_model_class()
            if isinstance(value, dict):
                instance = model_class()
                instance.from_dict(value)
                return instance
            elif isinstance(value, model_class):
                return value
            else:
                raise FieldValidationError(
                    message=(f"Expected {model_class.__name__} or dict, " f"got {type(value).__name__}"),
                    field_name=self.name,
                    code="invalid_type",
                )

        except Exception as e:
            raise FieldValidationError(
                message=str(e),
                field_name=self.name,
                code="validation_error",
            ) from e

    async def validate_value(
        self,
        value: T | None,
        context: JsonDict | None = None,
    ) -> None:
        """Validate value.

        This method handles validation of model instances.

        Args:
            value: Value to validate
            context: Validation context

        Raises:
            FieldValidationError: If value is invalid
        """
        if value is None:
            return

        try:
            await value.validate(context)
        except Exception as e:
            raise FieldValidationError(
                message=str(e),
                field_name=self.name,
                code="validation_error",
            ) from e

    def prepare_for_comparison(self, value: Any) -> JsonDict | None:
        """Prepare model instance for comparison.

        Args:
            value: Value to prepare

        Returns:
            Prepared model instance as dictionary or None
        """
        if value is None:
            return None

        try:
            if isinstance(value, dict):
                return dict(value)  # type: ignore
            elif isinstance(value, ModelProtocol):
                return value.to_dict()
            return None
        except (TypeError, ValueError, AttributeError):
            return None

    def has_field(self, field_name: str) -> ComparisonOperator:
        """Check if model has field.

        Args:
            field_name: Field name to check for

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "has_field", field_name)

    def matches(self, query: dict[str, Any]) -> ComparisonOperator:
        """Check if model matches query.

        Args:
            query: Query dict to match against

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "matches", query)

    def is_empty(self) -> ComparisonOperator:
        """Check if model has no fields set.

        Returns:
            ComparisonOperator: Comparison operator with field name
        """
        return ComparisonOperator(self.name, "is_empty", None)

    def is_not_empty(self) -> ComparisonOperator:
        """Check if model has any fields set.

        Returns:
            ComparisonOperator: Comparison operator with field name
        """
        return ComparisonOperator(self.name, "is_not_empty", None)
