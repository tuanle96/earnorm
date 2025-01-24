"""Many-to-one relationship field implementation.

This module provides many-to-one relationship field types for handling relationships between models.
It supports:
- Forward and reverse relationships
- Lazy loading of related models
- Cascade deletion
- Database foreign key constraints
- Validation of related models

Examples:
    >>> class Comment(Model):
    ...     content = StringField(required=True)
    ...     post = ManyToOneField("Post", reverse_name="comments")
    ...     author = ManyToOneField("User", reverse_name="comments")
    ...
    >>> class Post(Model):
    ...     title = StringField(required=True)
    ...     content = StringField(required=True)
    ...     # comments field will be added automatically with reverse_name="comments"
"""

from typing import Any, Optional, Type, TypeVar, cast

from earnorm.base.model.base import BaseModel
from earnorm.fields.base import Field, ValidationError
from earnorm.fields.relation.one_to_many import OneToManyField

M = TypeVar("M", bound=BaseModel)


class ManyToOneField(Field[Optional[M]]):
    """Field for many-to-one relationships.

    Attributes:
        model_class: Related model class
        reverse_name: Name of reverse relationship field
        cascade_delete: Whether to delete related model on deletion
        lazy_load: Whether to load related model lazily
    """

    def __init__(
        self,
        model_class: Type[M] | str,
        *,
        reverse_name: Optional[str] = None,
        cascade_delete: bool = True,
        lazy_load: bool = False,
        **options: Any,
    ) -> None:
        """Initialize many-to-one field.

        Args:
            model_class: Related model class or its name
            reverse_name: Name of reverse relationship field
            cascade_delete: Whether to delete related model on deletion
            lazy_load: Whether to load related model lazily
            **options: Additional field options
        """
        super().__init__(**options)
        self._model_class = model_class
        self.reverse_name = reverse_name
        self.cascade_delete = cascade_delete
        self.lazy_load = lazy_load
        self._resolved_model: Optional[Type[M]] = None

        # Update backend options
        self.backend_options.update(
            {
                "mongodb": {
                    "type": "objectId",
                    "ref": self._get_model_name(),
                },
                "postgres": {
                    "type": "UUID",
                    "foreignKey": {
                        "table": self._get_model_name(),
                        "column": "id",
                        "onDelete": "CASCADE" if cascade_delete else "SET NULL",
                    },
                },
                "mysql": {
                    "type": "CHAR(36)",
                    "foreignKey": {
                        "table": self._get_model_name(),
                        "column": "id",
                        "onDelete": "CASCADE" if cascade_delete else "SET NULL",
                    },
                },
            }
        )

    def _get_model_name(self) -> str:
        """Get name of related model class.

        Returns:
            Model name
        """
        if isinstance(self._model_class, str):
            return self._model_class
        return self._model_class.__name__

    async def _resolve_model(self) -> Type[M]:
        """Resolve related model class.

        Returns:
            Model class

        Raises:
            ValidationError: If model cannot be resolved
        """
        if self._resolved_model is not None:
            return self._resolved_model

        if isinstance(self._model_class, str):
            # Get model class from registry
            if not hasattr(self, "model"):
                raise ValidationError(
                    "Cannot resolve model class without parent model",
                    self.name,
                )
            try:
                model_class = self.model.env.get_model(self._model_class)  # type: ignore
                self._resolved_model = cast(Type[M], model_class)
                return self._resolved_model
            except KeyError:
                raise ValidationError(
                    f"Model {self._model_class} not found in registry",
                    self.name,
                )
        else:
            self._resolved_model = self._model_class
            return self._resolved_model

    async def setup(self) -> None:
        """Set up field after model class is created."""
        await super().setup()  # type: ignore

        # Create reverse relationship
        if self.reverse_name:
            model_class = await self._resolve_model()
            if hasattr(model_class, self.reverse_name):
                raise ValidationError(
                    f"Field {self.reverse_name} already exists on {model_class.__name__}",
                    self.name,
                )

            # Create reverse field
            reverse_field = OneToManyField[M](
                self.model.__class__,  # type: ignore
                reverse_name=None,  # Prevent infinite recursion
                cascade_delete=self.cascade_delete,
                lazy_load=self.lazy_load,
                required=False,
            )
            setattr(model_class, self.reverse_name, reverse_field)

    async def validate(self, value: Any) -> None:
        """Validate related model.

        Args:
            value: Value to validate

        Raises:
            ValidationError: If validation fails
        """
        await super().validate(value)

        if value is not None:
            model_class = await self._resolve_model()
            if not isinstance(value, model_class):
                raise ValidationError(
                    f"Value must be an instance of {model_class.__name__}",
                    self.name,
                )

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
            return None

        model_class = await self._resolve_model()

        try:
            if isinstance(value, model_class):
                return value
            elif isinstance(value, str):
                # Try to load by ID
                if not hasattr(self, "model"):
                    raise ValidationError(
                        "Cannot load related model without parent model",
                        self.name,
                    )
                try:
                    instance = await model_class.get(  # type: ignore
                        self.model.env,  # type: ignore
                        value,
                    )
                    return cast(M, instance)  # type: ignore[redundant-cast]
                except Exception as e:
                    raise ValidationError(str(e), self.name)
            else:
                raise ValidationError(
                    f"Cannot convert {type(value).__name__} to {model_class.__name__}",
                    self.name,
                )
        except Exception as e:
            raise ValidationError(str(e), self.name)

    async def to_db(self, value: Optional[M], backend: str) -> Optional[str]:
        """Convert model instance to database format.

        Args:
            value: Model instance
            backend: Database backend type

        Returns:
            Database value
        """
        if value is None:
            return None

        if not hasattr(value, "id"):
            raise ValidationError(
                f"Model instance {value} has no id attribute",
                self.name,
            )
        return str(value.id)  # type: ignore

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

        model_class = await self._resolve_model()

        if not hasattr(self, "model"):
            raise ValidationError(
                "Cannot load related model without parent model",
                self.name,
            )

        try:
            if self.lazy_load:
                # Create model instance without loading
                instance = model_class(self.model.env)  # type: ignore
                instance.id = value  # type: ignore
                return cast(M, instance)  # type: ignore[redundant-cast]
            else:
                # Load and validate model instance
                instance = await model_class.get(  # type: ignore
                    self.model.env,  # type: ignore
                    value,
                )
                await instance.validate()  # type: ignore
                return cast(M, instance)  # type: ignore[redundant-cast]
        except Exception as e:
            raise ValidationError(str(e), self.name)

    async def async_convert(self, value: Any) -> Optional[M]:
        """Convert value to model instance asynchronously.

        Args:
            value: Value to convert

        Returns:
            Model instance or None if value is None

        Raises:
            ValidationError: If conversion fails
        """
        return await self.convert(value)

    async def async_to_dict(self, value: Optional[M]) -> Optional[dict[str, Any]]:
        """Convert model instance to dict representation asynchronously.

        Args:
            value: Model instance to convert

        Returns:
            Dict representation of model instance or None if value is None

        Raises:
            ValidationError: If conversion fails
        """
        if value is None:
            return None

        if not hasattr(value, "to_dict"):
            raise ValidationError(
                f"Model instance {value} has no to_dict method",
                self.name,
            )

        try:
            return await value.to_dict()  # type: ignore[attr-defined]
        except Exception as e:
            raise ValidationError(str(e), self.name)
