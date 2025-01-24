"""Many-to-many relationship field implementation.

This module provides many-to-many relationship field types for handling relationships between models.
It supports:
- Forward and reverse relationships
- Lazy loading of related models
- Cascade deletion
- Database foreign key constraints
- Validation of related models
- Filtering and ordering of related models
- Through models for additional relationship data

Examples:
    >>> class Student(Model):
    ...     name = StringField(required=True)
    ...     courses = ManyToManyField("Course", reverse_name="students")
    ...
    >>> class Course(Model):
    ...     name = StringField(required=True)
    ...     # students field will be added automatically with reverse_name="students"
    ...
    >>> # With through model
    >>> class Enrollment(Model):
    ...     student = OneToOneField("Student")
    ...     course = OneToOneField("Course")
    ...     date = DateField(required=True)
    ...     grade = FloatField()
    ...
    >>> class Student(Model):
    ...     name = StringField(required=True)
    ...     courses = ManyToManyField("Course", through="Enrollment", reverse_name="students")
"""

from typing import Any, Optional, Type, TypeVar, cast

from earnorm.base.model.base import BaseModel
from earnorm.fields.base import Field, ValidationError

M = TypeVar("M", bound=BaseModel)


class ManyToManyField(Field[list[M]]):
    """Field for many-to-many relationships.

    Attributes:
        model_class: Related model class
        through: Through model class
        reverse_name: Name of reverse relationship field
        cascade_delete: Whether to delete related models on deletion
        lazy_load: Whether to load related models lazily
        order_by: Fields to order related models by
    """

    def __init__(
        self,
        model_class: Type[M] | str,
        *,
        through: Optional[Type[BaseModel] | str] = None,
        reverse_name: Optional[str] = None,
        cascade_delete: bool = True,
        lazy_load: bool = False,
        order_by: Optional[list[str]] = None,
        **options: Any,
    ) -> None:
        """Initialize many-to-many field.

        Args:
            model_class: Related model class or its name
            through: Through model class or its name
            reverse_name: Name of reverse relationship field
            cascade_delete: Whether to delete related models on deletion
            lazy_load: Whether to load related models lazily
            order_by: Fields to order related models by
            **options: Additional field options
        """
        super().__init__(**options)
        self._model_class = model_class
        self._through = through
        self.reverse_name = reverse_name
        self.cascade_delete = cascade_delete
        self.lazy_load = lazy_load
        self.order_by = list(order_by) if order_by else []
        self._resolved_model: Optional[Type[M]] = None
        self._resolved_through: Optional[Type[BaseModel]] = None

        # Update backend options
        self.backend_options.update(
            {
                "mongodb": {
                    "type": "array",
                    "items": {
                        "type": "objectId",
                        "ref": self._get_model_name(),
                    },
                },
                "postgres": {
                    "type": "ARRAY",
                    "items": {
                        "type": "UUID",
                        "foreignKey": {
                            "table": self._get_model_name(),
                            "column": "id",
                            "onDelete": "CASCADE" if cascade_delete else "SET NULL",
                        },
                    },
                },
                "mysql": {
                    "type": "JSON",
                    "check": [
                        f"JSON_TYPE({self.name}) = 'ARRAY'",
                    ],
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

    async def _resolve_through(self) -> Optional[Type[BaseModel]]:
        """Resolve through model class.

        Returns:
            Through model class

        Raises:
            ValidationError: If model cannot be resolved
        """
        if self._through is None:
            return None

        if self._resolved_through is not None:
            return self._resolved_through

        if isinstance(self._through, str):
            # Get model class from registry
            if not hasattr(self, "model"):
                raise ValidationError(
                    "Cannot resolve through model class without parent model",
                    self.name,
                )
            try:
                model_class = self.model.env.get_model(self._through)  # type: ignore
                self._resolved_through = cast(Type[BaseModel], model_class)
                return self._resolved_through
            except KeyError:
                raise ValidationError(
                    f"Model {self._through} not found in registry",
                    self.name,
                )
        else:
            self._resolved_through = self._through
            return self._resolved_through

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
            reverse_field = ManyToManyField[M](
                self.model.__class__,  # type: ignore
                through=self._through,
                reverse_name=None,  # Prevent infinite recursion
                cascade_delete=self.cascade_delete,
                lazy_load=self.lazy_load,
                required=False,
            )
            setattr(model_class, self.reverse_name, reverse_field)

    async def validate(self, value: Any) -> None:
        """Validate related models.

        Args:
            value: Value to validate

        Raises:
            ValidationError: If validation fails
        """
        await super().validate(value)

        if value is not None:
            if not isinstance(value, (list, tuple)):
                raise ValidationError(
                    f"Value must be a list or tuple, got {type(value).__name__}",
                    self.name,
                )

            model_class = await self._resolve_model()
            # Cast value to list of Any since we'll check types in the loop
            items = cast(list[Any], value)
            for item in items:
                if not isinstance(item, model_class):
                    raise ValidationError(
                        f"Item must be an instance of {model_class.__name__}",
                        self.name,
                    )

                # Validate model instance
                try:
                    await item.validate()  # type: ignore
                except ValidationError as e:
                    raise ValidationError(str(e), self.name)

    async def convert(self, value: Any) -> list[M]:
        """Convert value to list of model instances.

        Args:
            value: Value to convert

        Returns:
            List of model instances

        Raises:
            ValidationError: If conversion fails
        """
        if value is None:
            return []

        model_class = await self._resolve_model()
        result: list[M] = []

        try:
            if isinstance(value, (list, tuple)):
                # Cast value to list of Any since we'll check types in the loop
                items = cast(list[Any], value)
                for item in items:
                    if isinstance(item, model_class):
                        result.append(cast(M, item))  # type: ignore[redundant-cast]
                    elif isinstance(item, str):
                        # Try to load by ID
                        if not hasattr(self, "model"):
                            raise ValidationError(
                                "Cannot load related models without parent model",
                                self.name,
                            )
                        try:
                            instance = await model_class.get(  # type: ignore
                                self.model.env,  # type: ignore
                                item,
                            )
                            result.append(cast(M, instance))  # type: ignore[redundant-cast]
                        except Exception as e:
                            raise ValidationError(str(e), self.name)
                    else:
                        raise ValidationError(
                            f"Cannot convert {type(item).__name__} to {model_class.__name__}",
                            self.name,
                        )
            else:
                raise ValidationError(
                    f"Cannot convert {type(value).__name__} to list of {model_class.__name__}",
                    self.name,
                )
        except Exception as e:
            raise ValidationError(str(e), self.name)

        return result

    async def to_db(
        self, value: Optional[list[M]], backend: str
    ) -> Optional[list[str]]:
        """Convert model instances to database format.

        Args:
            value: List of model instances
            backend: Database backend type

        Returns:
            Database value
        """
        if not value:
            return None

        result: list[str] = []
        for item in value:
            if not hasattr(item, "id"):
                raise ValidationError(
                    f"Model instance {item} has no id attribute",
                    self.name,
                )
            result.append(str(item.id))  # type: ignore

        return result

    async def from_db(self, value: Any, backend: str) -> list[M]:
        """Convert database value to list of model instances.

        Args:
            value: Database value
            backend: Database backend type

        Returns:
            List of model instances
        """
        if not value:
            return []

        model_class = await self._resolve_model()
        result: list[M] = []

        if not hasattr(self, "model"):
            raise ValidationError(
                "Cannot load related models without parent model",
                self.name,
            )

        try:
            # Cast value to list of strings since we know it contains IDs
            id_list = cast(list[str], value)
            for item_id in id_list:
                if self.lazy_load:
                    # Create model instance without loading
                    instance = model_class(self.model.env)  # type: ignore
                    instance.id = item_id  # type: ignore
                    result.append(cast(M, instance))  # type: ignore[redundant-cast]
                else:
                    # Load and validate model instance
                    instance = await model_class.get(  # type: ignore
                        self.model.env,  # type: ignore
                        item_id,
                    )
                    await instance.validate()  # type: ignore
                    result.append(cast(M, instance))  # type: ignore[redundant-cast]
            return result
        except Exception as e:
            raise ValidationError(str(e), self.name)
