"""Base implementation for relation fields.

This module provides the base class for all relation fields in EarnORM.
It implements core functionality like:
1. Field setup and initialization
2. Relation type validation
3. Model resolution
4. Reverse relation setup
5. Database operations

Examples:
    >>> from earnorm.fields.relations.base import RelationField
    >>> from earnorm.types.relations import RelationType
    >>> from earnorm.base.model import BaseModel

    >>> class User(BaseModel):
    ...     _name = 'res.user'

    >>> class CustomRelation(RelationField[User]):
    ...     def __init__(self, **options):
    ...         super().__init__(
    ...             'res.user',  # Can use string
    ...             RelationType.ONE_TO_ONE,
    ...             **options
    ...         )
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, TypeVar, Union, cast

from earnorm.exceptions import ValidationError
from earnorm.fields.base import BaseField
from earnorm.types.fields import DatabaseValue
from earnorm.types.models import ModelProtocol
from earnorm.types.relations import RelationOptions, RelationProtocol, RelationType

if TYPE_CHECKING:
    from earnorm.base.model import BaseModel

    T = TypeVar("T", bound="BaseModel")
else:
    T = TypeVar("T", bound=ModelProtocol)

logger = logging.getLogger(__name__)

# Type for model reference - can be string or class
ModelType = Union[str, Type[T]]


class RelationField(BaseField[T], RelationProtocol[T]):
    """Base class for relation fields.

    This class provides core functionality for relation fields including:
    1. Field setup and initialization
    2. Relation type validation
    3. Model resolution
    4. Reverse relation setup
    5. Database operations

    Args:
        model: Related model class or string reference
        relation_type: Type of relation
        related_name: Name of reverse relation field
        on_delete: Delete behavior ('CASCADE', 'SET_NULL', 'PROTECT')
        lazy: Whether to use lazy loading
        required: Whether relation is required
        help: Help text for the field
        **options: Additional field options

    Examples:
        >>> class Department(BaseModel):
        ...     _name = 'res.department'
        ...
        >>> class Employee(BaseModel):
        ...     _name = 'res.employee'
        ...     department = RelationField(
        ...         'res.department',  # Using string reference
        ...         RelationType.MANY_TO_ONE,
        ...         related_name='employees'
        ...     )
    """

    logger = logging.getLogger(__name__)

    def __init__(
        self,
        model: ModelType[T],
        relation_type: RelationType,
        *,
        related_name: Optional[str] = None,
        on_delete: str = "CASCADE",
        lazy: bool = True,
        required: bool = False,
        help: Optional[str] = None,
        **options: Any,
    ) -> None:
        """Initialize relation field.

        Args:
            model: Related model class or string reference
            relation_type: Type of relation
            related_name: Name of reverse relation field
            on_delete: Delete behavior ('CASCADE', 'SET_NULL', 'PROTECT')
            required: Whether relation is required
            lazy: Whether to load related records lazily
            help: Help text for the field
            **options: Additional field options
        """
        if help is not None:
            options["help"] = help
        super().__init__(required=required, **options)
        self._model_ref = model
        self._resolved_model: Optional[Type[T]] = None
        self.relation_type = relation_type
        self.related_name = related_name
        self.on_delete = on_delete
        self.lazy = lazy

        # Will be set during setup
        self._owner_model: Optional[Type[T]] = None

    @staticmethod
    def _convert_class_name_to_model_name(class_name: str) -> str:
        """Convert class name to model name.

        This method converts PascalCase class names to snake_case model names.

        Args:
            class_name: Class name in PascalCase (e.g. "UserGroup")

        Returns:
            Model name in snake_case (e.g. "user_group")

        Examples:
            >>> RelationField._convert_class_name_to_model_name("User")
            'user'
            >>> RelationField._convert_class_name_to_model_name("UserGroup")
            'user_group'
            >>> RelationField._convert_class_name_to_model_name("APIKey")
            'api_key'
        """
        # Handle empty or invalid input
        if not class_name:
            raise ValueError("Class name cannot be empty")

        # Convert camel case to snake case and lowercase
        import re

        name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", class_name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()

    async def _resolve_model(self) -> Type[T]:
        """Resolve model reference to actual class.

        Returns:
            Type[T]: Resolved model class

        Raises:
            RuntimeError: If environment not set or model not found
            ValueError: If model reference is invalid
        """
        # Return cached model if available
        if self._resolved_model is not None:
            self.logger.info(f"Using cached resolved model: {self._resolved_model}")
            return self._resolved_model

        # Handle class reference - nếu đã là class thì dùng trực tiếp
        if hasattr(self._model_ref, "_name"):
            self.logger.info(f"Model reference is already a class: {self._model_ref}")
            self._resolved_model = cast(Type[T], self._model_ref)
            return self._resolved_model

        # Handle string reference
        if not self.env:
            self.logger.error("Environment not set during model resolution")
            raise RuntimeError("Environment not set")

        # Resolve model using exact name
        self.logger.info(f"Resolving model by name: {self._model_ref}")
        model = await self.env.get_model(self._model_ref)  # type: ignore
        if model:
            self.logger.info(f"Found model: {model}")
            self._resolved_model = cast(Type[T], model)
            return self._resolved_model

        # Model not found
        error_msg = (
            f"Model not found for reference '{self._model_ref}'. "
            f"Make sure the model exists and is properly registered with correct _name attribute."
        )
        self.logger.error(error_msg)
        raise RuntimeError(error_msg)

    @property
    async def model(self) -> Type[T]:
        """Get model reference.

        Returns:
            Model reference

        Raises:
            RuntimeError: If model is not resolved
        """
        if isinstance(self._model_ref, type):
            return cast(Type[T], self._model_ref)
        if self._resolved_model is None:
            self.logger.info(f"Auto resolving model for {self._model_ref}")
            self._resolved_model = await self._resolve_model()
        return self._resolved_model

    async def get_model(self) -> Type[T]:
        """Get resolved model class.

        Returns:
            Resolved model class
        """
        return await self._resolve_model()

    async def setup(self, name: str, model_name: str) -> None:
        """Set up relation field.

        This method:
        1. Sets up basic field attributes
        2. Validates relation configuration
        3. Sets up reverse relation if needed
        4. Creates database indexes
        5. Resolves model reference if needed

        Args:
            name: Field name
            model_name: Model name
        """
        await super().setup(name, model_name)

        # Get owner model
        if not self.env:
            raise RuntimeError("Environment not set")

        owner_model = await self.env.get_model(model_name)
        if not owner_model:
            raise RuntimeError(f"Model {model_name} not found")

        self._owner_model = cast(Type[T], owner_model)

        # Resolve model reference if needed
        if not isinstance(self._model_ref, type):
            self.logger.info(f"Resolving model during setup: {self._model_ref}")
            self._resolved_model = await self._resolve_model()

        # Set up reverse relation
        if self.related_name:
            await self._setup_reverse_relation()

        # Set up database
        await self._setup_database()

    async def _setup_reverse_relation(self) -> None:
        """Set up reverse relation field.

        This method creates the reverse relation field on the related model.
        The type of reverse relation depends on the relation type:
        - one_to_one -> one_to_one
        - many_to_one -> one_to_many
        - one_to_many -> many_to_one
        - many_to_many -> many_to_many
        """
        if not self.related_name or not self._owner_model:
            return

        # Get reverse relation type
        reverse_type = {
            RelationType.ONE_TO_ONE: RelationType.ONE_TO_ONE,
            RelationType.MANY_TO_ONE: RelationType.ONE_TO_MANY,
            RelationType.ONE_TO_MANY: RelationType.MANY_TO_ONE,
            RelationType.MANY_TO_MANY: RelationType.MANY_TO_MANY,
        }[self.relation_type]

        # Create reverse field
        reverse_field = RelationField(
            self._owner_model,
            reverse_type,
            related_name=self.name,
            on_delete=self.on_delete,
            lazy=self.lazy,
        )

        # Add to related model
        setattr(self.model, self.related_name, reverse_field)

    async def _setup_database(self) -> None:
        """Set up database for relation.

        This method:
        1. Creates necessary indexes
        2. Sets up foreign key constraints
        3. Creates junction tables for many-to-many
        """
        if not self.env or not self._owner_model:
            return

        # Get relation options
        options = RelationOptions(
            model=cast(Union[Type[ModelProtocol], str], self._model_ref),
            related_name=self.related_name or "",
            on_delete=self.on_delete,
            through=None,
            through_fields=None,
        )

        # Set up in database
        await self.env.adapter.setup_relations(self._owner_model, {self.name: options})

    async def validate(
        self, value: Any, context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Validate relation value.

        Args:
            value: Value to validate
            context: Validation context

        Raises:
            ValidationError: If validation fails
        """
        if value is None:
            if self.required:
                raise ValidationError(
                    f"Field {self.name} is required",
                    field_name=self.name,
                    code="required",
                )
            return

        model = await self._resolve_model()

        if isinstance(value, list):
            if self.relation_type not in (
                RelationType.ONE_TO_MANY,
                RelationType.MANY_TO_MANY,
            ):
                raise ValidationError(
                    f"Field {self.name} does not support multiple values",
                    field_name=self.name,
                    code="multiple_values_not_supported",
                )
            for item in value:  # type: ignore
                if not isinstance(item, model):
                    raise ValidationError(
                        f"Expected {model.__name__}, got {type(item)}",  # type: ignore
                        field_name=self.name,
                        code="invalid_relation_type",
                    )
        else:
            if not isinstance(value, model):
                raise ValidationError(
                    f"Expected {model.__name__}, got {type(value)}",
                    field_name=self.name,
                    code="invalid_relation_type",
                )

    async def to_db(self, value: Optional[T], backend: str) -> DatabaseValue:
        """Convert Python value to database format.

        Args:
            value: Value to convert
            backend: Database backend type

        Returns:
            Converted value for database
        """
        if value is None:
            return None

        if isinstance(value, str):
            return value

        if isinstance(value, list):
            return [str(item.id) for item in value]

        return str(value.id)

    async def from_db(self, value: DatabaseValue, backend: str) -> Optional[T]:
        """Convert database value to Python format.

        Args:
            value: Value to convert
            backend: Database backend type

        Returns:
            Converted value
        """
        if value is None:
            return None

        model = await self._resolve_model()

        if isinstance(value, list):
            records = []
            for item in value:
                record = await model.browse(str(item))
                if record:
                    records.append(record)  # type: ignore
            return cast(Optional[T], records)

        record = await model.browse(str(value))
        return cast(Optional[T], record)

    @property
    def model_ref(self) -> ModelType[T]:
        """Get model reference.

        Returns:
            Model reference (string or class)
        """
        return self._model_ref

    @property
    def resolved_model(self) -> Optional[Type[T]]:
        """Get resolved model class.

        Returns:
            Resolved model class or None if not resolved
        """
        return self._resolved_model

    async def get_related(self, instance: Any) -> Union[Optional[T], List[T]]:
        """Get related record(s).

        Args:
            instance: Model instance to get related records for

        Returns:
            Related record(s)
        """
        if not self.env:
            raise RuntimeError("Environment not set")

        # Get from database
        records = await self.env.adapter.get_related(
            instance,
            self.name,
            RelationType(self.field_type),
            RelationOptions(
                model=cast(Union[Type[ModelProtocol], str], self._model_ref),
                related_name=self.related_name or "",
                on_delete=self.on_delete,
                through=None,
                through_fields=None,
            ),
        )

        return records

    async def set_related(
        self, instance: Any, value: Union[Optional[T], List[T]]
    ) -> None:
        """Set related record(s).

        Args:
            instance: Model instance to set related records for
            value: Related record(s) to set
        """
        if not self.env:
            raise RuntimeError("Environment not set")

        # Validate value
        await self.validate(value)

        # Set in database
        await self.env.adapter.set_related(
            instance,
            self.name,
            value,
            RelationType(self.field_type),
            RelationOptions(
                model=cast(Union[Type[ModelProtocol], str], self._model_ref),
                related_name=self.related_name or "",
                on_delete=self.on_delete,
                through=None,
                through_fields=None,
            ),
        )

    async def delete_related(self, instance: Any) -> None:
        """Delete related record(s).

        Args:
            instance: Model instance to delete related records for
        """
        if not self.env:
            raise RuntimeError("Environment not set")

        # Delete from database
        await self.env.adapter.delete_related(
            instance,
            self.name,
            RelationType(self.field_type),
            RelationOptions(
                model=cast(Union[Type[ModelProtocol], str], self._model_ref),
                related_name=self.related_name or "",
                on_delete=self.on_delete,
                through=None,
                through_fields=None,
            ),
        )

    async def __get__(self, instance: Optional[Any], owner: Optional[type] = None) -> T:
        """Get related record(s).

        This method is common for all relation fields. It ensures that:
        1. Always returns a recordset (never None)
        2. Returns empty recordset if no related records found
        3. Properly casts return type to recordset type

        Args:
            instance: Model instance
            owner: Model class

        Returns:
            Recordset containing related record(s) (may be empty)

        Examples:
            >>> model = Model()
            >>> related = await model.relation  # Returns recordset
            >>> if related.id:  # Check if has records
            ...     print(await related.name)
        """
        if instance is None:
            return self  # type: ignore

        value = await super().__get__(instance, owner)
        if value is None:
            # Return empty recordset instead of None
            model = await self._resolve_model()
            return model._browse(model._env, [])  # type: ignore

        return cast(T, value)  # Cast to recordset type
