"""Model metaclass implementation.

This module provides the metaclass for all database models in EarnORM.
It handles model class creation and configuration through Python's metaclass system.

Key Features:
    1. Field Registration
       - Automatic field discovery
       - Field name assignment
       - Field validation setup
       - Default field injection

    2. Model Registration
       - Model registry management
       - Environment integration
       - Dependency tracking
       - Name generation

    3. Slot Creation
       - Memory optimization
       - Attribute access control
       - Performance improvement
       - Type safety

    4. Inheritance Tracking
       - Base class tracking
       - Mixin support
       - Abstract class handling
       - Interface implementation

Examples:
    >>> from earnorm.base.model.meta import ModelMeta
    >>> from earnorm.fields import StringField, IntegerField

    >>> # Define model with metaclass
    >>> class User(metaclass=ModelMeta):
    ...     _name = 'data.user'
    ...     name = StringField()
    ...     age = IntegerField()

    >>> # Access model registry
    >>> User._model_info.name  # 'data.user'
    >>> User._model_info.fields  # {'name': StringField(), 'age': IntegerField()}

    >>> # Check field descriptors
    >>> isinstance(User.name, AsyncFieldDescriptor)  # True
    >>> isinstance(User.age, AsyncFieldDescriptor)  # True

Classes:
    ModelInfo:
        Data class holding model metadata.

        Attributes:
            name: Model name
            fields: Field definitions
            env: Environment instance
            bases: Base classes

    ModelMeta:
        Metaclass for database models.

        Methods:
            __new__: Create model class
            __init__: Initialize model class
            _build_slots: Create class slots
            _register_fields: Register model fields

Implementation Notes:
    1. The metaclass creates descriptors for all field instances
    2. Model names must be unique within an environment
    3. Abstract models are not registered with environment
    4. Field names cannot conflict with method names

See Also:
    - earnorm.base.model.base: BaseModel implementation
    - earnorm.base.model.descriptors: Field descriptors
    - earnorm.base.env: Environment management
"""

import logging
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncContextManager,
    ClassVar,
    Self,
    TypeVar,
    cast,
    overload,
)

from earnorm.base.database.transaction.base import Transaction
from earnorm.base.model.descriptors import AsyncFieldDescriptor
from earnorm.fields import BaseField
from earnorm.fields.relations.base import RelationField
from earnorm.types.models import ModelProtocol

if TYPE_CHECKING:
    from earnorm.base.env import Environment

__all__ = ["BaseModel", "ModelInfo"]

logger = logging.getLogger(__name__)

T = TypeVar("T")
ValueT = TypeVar("ValueT")
ModelT = TypeVar("ModelT", bound="BaseModel")

# Global registry for pending reverse relationships
_pending_reverse_relationships: list[tuple[str, str, str, str, dict]] = []

# Global registry for model classes (sync access)
_model_registry: dict[str, type["BaseModel"]] = {}


def register_reverse_relationship(source_model: str, target_model: str, field_name: str, related_name: str, field_options: dict) -> None:
    """Register a reverse relationship to be created later.

    Args:
        source_model: Name of the source model
        target_model: Name of the target model
        field_name: Name of the field on source model
        related_name: Name of the reverse field on target model
        field_options: Options for creating the reverse field
    """
    _pending_reverse_relationships.append((source_model, target_model, field_name, related_name, field_options))


def process_pending_reverse_relationships() -> None:
    """Process all pending reverse relationships and create them."""
    from earnorm.fields.relations.one_to_one import OneToOneField
    from earnorm.fields.relations.one_to_many import OneToManyField
    from earnorm.fields.relations.many_to_one import ManyToOneField

    processed = []

    for source_model, target_model, field_name, related_name, field_options in _pending_reverse_relationships:
        try:
            # Get target model class from registry (sync access)
            if target_model in _model_registry:
                target_class = _model_registry[target_model]

                # Check if reverse field already exists (sync check to avoid async descriptor issues)
                if related_name in target_class.__dict__ or any(related_name in base.__dict__ for base in target_class.__mro__[1:]):
                    logger.debug(f"Reverse field {related_name} already exists on {target_model}")
                    processed.append((source_model, target_model, field_name, related_name, field_options))
                    continue

                # Create reverse field based on original field type
                field_type = field_options.get('field_type', 'one2one')

                if field_type == 'one2one':
                    # OneToOne -> OneToOne (reverse)
                    reverse_field = OneToOneField(
                        source_model,
                        related_name=field_name,
                        on_delete=field_options.get('on_delete', 'CASCADE'),
                        required=False  # Reverse fields are typically not required
                    )
                elif field_type == 'many2one':
                    # ManyToOne -> OneToMany (reverse)
                    reverse_field = OneToManyField(
                        source_model,
                        related_name=field_name,
                        on_delete=field_options.get('on_delete', 'CASCADE')
                    )
                else:
                    logger.warning(f"Unsupported field type for reverse relationship: {field_type}")
                    continue

                # Set field name and model name
                reverse_field.name = related_name
                reverse_field.model_name = target_model

                # Set environment if target class has one
                if hasattr(target_class, '_env') and target_class._env:
                    reverse_field.env = target_class._env

                # For OneToOne fields, create proper descriptor
                if field_type == 'one2one':
                    from earnorm.base.model.descriptors import AsyncFieldDescriptor
                    descriptor = AsyncFieldDescriptor(reverse_field)
                    setattr(target_class, related_name, descriptor)
                else:
                    # For OneToMany fields, set field directly
                    setattr(target_class, related_name, reverse_field)

                # Add to __fields__ if it exists
                if hasattr(target_class, '__fields__'):
                    target_class.__fields__[related_name] = reverse_field

                logger.info(f"Created reverse relationship: {target_model}.{related_name} -> {source_model}")
                processed.append((source_model, target_model, field_name, related_name, field_options))

        except Exception as e:
            logger.error(f"Failed to create reverse relationship {target_model}.{related_name}: {e}")

    # Remove processed relationships
    for item in processed:
        if item in _pending_reverse_relationships:
            _pending_reverse_relationships.remove(item)


@dataclass
class ModelInfo:
    """Model metadata container.

    This class holds metadata about a model class including:
    - Model name and registry key
    - Field definitions and types
    - Environment instance
    - Base classes and mixins
    - Abstract status

    Args:
        name: Model name/registry key
        fields: Dictionary of field definitions
        env: Environment instance
        bases: List of base classes
        is_abstract: Whether model is abstract

    Examples:
        >>> info = ModelInfo(
        ...     name='data.user',
        ...     fields={'name': StringField()},
        ...     env=env,
        ...     bases=[BaseModel],
        ...     is_abstract=False
        ... )
        >>> info.name  # 'data.user'
        >>> info.fields  # {'name': StringField()}
    """

    name: str
    model_class: type["BaseModel"]
    is_abstract: bool
    parent_models: set[str]
    fields: dict[str, BaseField[Any]]


# Forward reference for BaseModel
class BaseModel(ModelProtocol):
    """Base class for all database models.

    This class implements ModelProtocol and defines the basic structure and behavior
    that all models must have. It includes:
    - Model name and fields
    - Environment access
    - Recordset attributes
    - Slots for memory efficiency

    Examples:
        >>> class User(BaseModel):
        ...     _name = 'res.users'
        ...     name = StringField()
        ...
        >>> user = User()
        >>> user.env  # Access environment
        >>> user.__fields__  # Access fields
    """

    # Class variables
    _store: ClassVar[bool]
    """Whether model supports storage."""

    _name: ClassVar[str]
    """Technical name of the model."""

    _description: ClassVar[str | None]
    """User-friendly description."""

    _table: ClassVar[str | None]
    """Database table name."""

    _sequence: ClassVar[str | None]
    """ID sequence name."""

    _skip_default_fields: ClassVar[bool]
    """Whether to skip adding default fields."""

    _abstract: ClassVar[bool] = False
    """Whether model is abstract."""

    __fields__: ClassVar[dict[str, BaseField[Any]]]
    """Model fields dictionary."""

    fields: dict[str, BaseField[Any]]
    """Model fields dictionary (alias for __fields__)."""

    # Instance variables
    __slots__ = (
        "_env",  # Environment instance
        "_ids",  # Record IDs
        "_name",  # Model name
    )

    id: str
    """Record ID."""

    _env: "Environment"
    """Environment instance."""

    # Protocol methods
    @classmethod
    async def browse(cls, ids: str | list[str]) -> "BaseModel":
        """Browse records by IDs.

        Args:
            ids: Record ID or list of record IDs

        Returns:
            Recordset containing the records
        """
        ...

    async def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary.

        Returns:
            Dictionary representation of model
        """
        ...

    def from_dict(self, data: dict[str, Any]) -> None:
        """Update model from dictionary.

        Args:
            data: Dictionary data to update from
        """
        ...

    @classmethod
    @overload
    async def create(cls) -> Self: ...

    @classmethod
    @overload
    async def create(cls, values: dict[str, Any]) -> Self: ...

    @classmethod
    @overload
    async def create(cls, values: list[dict[str, Any]]) -> list[Self]: ...

    @classmethod
    async def create(
        cls, values: dict[str, Any] | list[dict[str, Any]] | None = None
    ) -> Self | list[Self]:
        """Create one or multiple records.

        Args:
            values: Field values to create record(s) with. Can be:
                - None: Creates record with default values
                - Dict: Creates single record with provided values
                - List[Dict]: Creates multiple records with provided values

        Returns:
            - Single record if values is None or Dict
            - List of records if values is List[Dict]

        Examples:
            >>> # Create single record with values
            >>> user = await User.create({
            ...     "name": "John Doe",
            ...     "email": "john@example.com",
            ...     "age": 25,
            ...     "status": "active",
            ... })
            >>> print(user.name)  # John Doe

            >>> # Create multiple records
            >>> users = await User.create([
            ...     {"name": "John", "email": "john@example.com"},
            ...     {"name": "Jane", "email": "jane@example.com"}
            ... ])
            >>> print(len(users))  # 2

            >>> # Create with defaults
            >>> user = await User.create()
            >>> print(user.name)  # None
        """
        if values is None:
            values = {}

        if isinstance(values, list):
            # Create multiple records
            return await super().create_multi(values)  # type: ignore
        else:
            # Create single record
            return await super().create(values)  # type: ignore

    async def write(self, values: dict[str, Any]) -> "BaseModel":
        """Update record with values.

        Args:
            values: Field values to update

        Returns:
            Updated record
        """
        ...

    async def unlink(self) -> bool:
        """Delete record from database.

        Returns:
            True if record was deleted
        """
        ...

    async def with_transaction(
        self,
    ) -> AsyncContextManager[Transaction["BaseModel"]]:
        """Get transaction context manager.

        Returns:
            Transaction context manager
        """
        ...


class ModelMeta(type):
    """Metaclass for model classes.

    This metaclass:
    1. Sets up __fields__ dictionary from class attributes
    2. Injects default fields (id, created_at, updated_at)
    3. Injects environment from container
    4. Validates model configuration
    5. Registers field descriptors

    Examples:
        >>> class User(metaclass=ModelMeta):
        ...     _name = "user"
        ...     name = fields.StringField()
    """

    @classmethod
    def _validate_model(cls, model_cls: type[ModelT]) -> None:
        """Validate model before registration.

        Args:
            model_cls: Model class to validate

        Raises:
            ValueError: If validation fails
            TypeError: If type validation fails
        """
        try:
            # 1. Validate model name
            if not hasattr(model_cls, "_name"):
                raise ValueError(f"Model {model_cls.__name__} must define _name attribute")

            model_name = model_cls._name
            if not isinstance(model_name, str):
                raise TypeError(f"Model {model_cls.__name__}._name must be string, got {type(model_name)}")

            if not model_name:
                raise ValueError(f"Model {model_cls.__name__}._name cannot be empty")

            # 2. Validate fields
            fields_dict = getattr(model_cls, "__fields__", {})
            if not isinstance(fields_dict, dict):
                raise TypeError(f"Model {model_cls.__name__}.__fields__ must be dict")

            for field_name, field in fields_dict.items():
                # 2.1. Field name validation
                if not isinstance(field_name, str):
                    raise TypeError(f"Field name must be string, got {type(field_name)}")

                if not field_name:
                    raise ValueError("Field name cannot be empty")

                # 2.2. Field type validation
                if not isinstance(field, BaseField):
                    raise TypeError(f"Field {field_name} must be instance of BaseField, got {type(field)}")

                # 2.3. Required fields validation
                # Skip validation for system fields that have auto-generation logic
                is_auto_generated = (
                    getattr(field, "auto_now_add", False) or  # Auto-set on create
                    getattr(field, "auto_now", False) or      # Auto-update on write
                    getattr(field, "system", False) and field_name == "id"  # ID is auto-generated
                )

                if (
                    field.required
                    and field.default is None
                    and not is_auto_generated
                    and not getattr(field, "system", False)  # Don't warn for system fields
                ):
                    logger.warning(f"Field {field_name} in {model_cls.__name__} is required but has no default value")

                # 2.4. Relation field validation
                if isinstance(field, RelationField):
                    target_model = getattr(field, "model_ref", None)  # type: ignore
                    if not target_model:
                        raise ValueError(f"Relation field {field_name} must define target model")

                    # Check self-referential relations
                    if target_model == model_name:
                        logger.info(f"Self-referential relation detected: {model_name}.{field_name}")

            # 3. Validate unique constraints
            unique_fields = [f.name for f in fields_dict.values() if getattr(f, "unique", False)]
            if len(unique_fields) != len(set(unique_fields)):
                raise ValueError(f"Duplicate unique field names in {model_cls.__name__}: {unique_fields}")

            # 4. Validate field dependencies
            for field_name, field in fields_dict.items():
                if hasattr(field, "depends_on"):
                    depends_on = field.depends_on
                    if depends_on and not all(f in fields_dict for f in depends_on):
                        raise ValueError(f"Field {field_name} depends on non-existent fields: {depends_on}")

            # 5. Validate model inheritance
            if hasattr(model_cls, "_inherit"):
                inherit = model_cls._inherit
                if not isinstance(inherit, (str, list)):
                    raise TypeError(f"Model {model_cls.__name__}._inherit must be string or list")

            # 6. Validate abstract status
            if getattr(model_cls, "_abstract", False):
                if not fields_dict:
                    logger.warning(f"Abstract model {model_cls.__name__} has no fields")

            # 7. Validate field name conflicts with reserved names
            reserved_names = {"id", "ids", "env", "fields"}
            for field_name, field in fields_dict.items():
                # Skip system fields when checking reserved names
                if not getattr(field, "system", False) and field_name in reserved_names:
                    raise ValueError(f"Field name '{field_name}' conflicts with reserved name in {model_cls.__name__}")

        except Exception as e:
            logger.error(f"Model validation failed for {model_cls.__name__}: {e!s}")
            raise

    def __new__(mcs, name: str, bases: tuple[type[Any], ...], attrs: dict[str, Any]) -> type[BaseModel]:
        """Create new model class with automatic registration.

        Args:
            name: Class name
            bases: Base classes
            attrs: Class attributes

        Returns:
            New model class
        """
        # Skip for BaseModel
        if name == "BaseModel":
            return cast(type[BaseModel], super().__new__(mcs, name, bases, attrs))

        # Get fields from class attributes
        fields_dict: dict[str, BaseField[Any]] = {}

        # Don't wrap slot attributes and properties
        skip_wrap = set(attrs.get("__slots__", ())) | {"id", "ids"}

        # Get model name
        model_name = attrs.get("_name", "")
        if not model_name:
            raise ValueError(f"Model {name} must define _name attribute")

        # Wrap fields with AsyncFieldDescriptor and setup fields
        for key, value in list(attrs.items()):
            if isinstance(value, BaseField) and key not in skip_wrap:
                # Skip ManyToManyField from AsyncFieldDescriptor wrapping
                # as it has its own descriptor system
                from earnorm.fields.relations.many_to_many import ManyToManyField
                if isinstance(value, ManyToManyField):
                    # Let ManyToManyField handle its own descriptor setup
                    value.name = key
                    value.model_name = model_name
                    fields_dict[key] = value
                    # Mark for later descriptor setup
                    attrs[f"_m2m_field_{key}"] = value
                else:
                    attrs[key] = AsyncFieldDescriptor(value)  # type: ignore
                    value.name = key
                    value.model_name = model_name  # Set model_name directly
                    fields_dict[key] = value

                    # Register reverse relationship if this is a relation field
                    if isinstance(value, RelationField) and value.related_name:
                        # Get target model name
                        if isinstance(value._model_ref, str):
                            target_model_name = value._model_ref
                        else:
                            target_model_name = getattr(value._model_ref, '_name', '')

                        register_reverse_relationship(
                            source_model=model_name,
                            target_model=target_model_name,
                            field_name=key,
                            related_name=value.related_name,
                            field_options={
                                'field_type': value.field_type,
                                'on_delete': value.on_delete,
                            }
                        )

        # Add default fields if not skipped
        skip_defaults = attrs.get("_skip_default_fields", False)
        if not skip_defaults:
            from earnorm.fields import DatetimeField, StringField

            # Add id field as system field
            id_field = StringField(
                required=True,
                readonly=True,
                help="Unique identifier for the record",
                system=True,
                immutable=True,
                internal=True,
            )
            id_field.name = "id"
            id_field.model_name = model_name  # Set model_name for id field
            fields_dict["id"] = id_field

            # Add other default fields as system fields
            created_at = DatetimeField(
                required=True,
                readonly=True,
                help="Record creation timestamp",
                auto_now_add=True,
                system=True,
                immutable=True,
            )
            created_at.name = "created_at"
            created_at.model_name = model_name  # Set model_name for created_at
            updated_at = DatetimeField(required=True, help="Last update timestamp", auto_now=True, system=True)
            updated_at.name = "updated_at"
            updated_at.model_name = model_name  # Set model_name for updated_at

            fields_dict["created_at"] = created_at
            fields_dict["updated_at"] = updated_at

            if "created_at" not in skip_wrap:
                attrs["created_at"] = AsyncFieldDescriptor(created_at)
            if "updated_at" not in skip_wrap:
                attrs["updated_at"] = AsyncFieldDescriptor(updated_at)
        else:
            # Even if defaults are skipped, ensure id field exists as system field
            from earnorm.fields import StringField

            if "id" not in fields_dict:
                id_field = StringField(
                    required=True,
                    readonly=True,
                    help="Unique identifier for the record",
                    system=True,
                    immutable=True,
                    internal=True,
                )
                id_field.name = "id"
                id_field.model_name = model_name  # Set model_name for id field
                fields_dict["id"] = id_field
                attrs["id"] = AsyncFieldDescriptor(id_field)

        # Set __fields__ class variable
        attrs["__fields__"] = fields_dict

        # Create class
        cls = cast(type[BaseModel], super().__new__(mcs, name, bases, attrs))

        # Setup M2M descriptors after class creation
        for attr_name, attr_value in list(attrs.items()):
            if attr_name.startswith("_m2m_field_"):
                field_name = attr_name[11:]  # Remove "_m2m_field_" prefix
                m2m_field = attr_value
                if hasattr(m2m_field, '__set_name__'):
                    m2m_field.__set_name__(cls, field_name)
                # Clean up temporary attribute
                delattr(cls, attr_name)

        try:
            # Skip registration for abstract models
            if getattr(cls, "_abstract", False):
                logger.debug(f"Skipping registration for abstract model {name}")
                return cls

            # Validate model
            mcs._validate_model(cls)

            # Register model with improved error handling
            mcs._register_model_safely(cls, fields_dict)

        except Exception as e:
            logger.error(f"Failed to register model {name}: {e!s}")
            # Continue with class creation even if registration fails
            # This ensures the class is still usable for testing/development

        return cls

    @classmethod
    def _register_model_safely(mcs, cls: type[BaseModel], fields_dict: dict[str, BaseField[Any]]) -> None:
        """Safely register model with proper error handling and validation.

        Args:
            cls: Model class to register
            fields_dict: Dictionary of field definitions

        Raises:
            ValueError: If model configuration is invalid
            RuntimeError: If registration fails
        """
        from earnorm.base.env import Environment
        from earnorm.di import container

        # Validate model has required attributes
        if not hasattr(cls, "_name") or not cls._name:
            raise ValueError(f"Model {cls.__name__} must define _name attribute")

        model_name = cls._name

        # Always register in model registry first (for deferred registration)
        if model_name in _model_registry:
            existing_cls = _model_registry[model_name]
            if existing_cls is not cls:
                logger.warning(f"Model {model_name} already registered with different class. Skipping.")
                return
        else:
            # Add to registry immediately for deferred registration
            _model_registry[model_name] = cls
            logger.debug(f"Added model {model_name} to registry for deferred registration")

        # Get environment instance safely
        env = Environment.get_instance()
        if not env:
            logger.warning(f"Environment not available for model {model_name}. Deferring registration.")
            return

        # Check if environment is initialized
        if not getattr(env, "_initialized", False):
            logger.warning(f"Environment not initialized for model {model_name}. Deferring registration.")
            return

        try:
            # Register model class in container if not already registered
            container_key = f"model.{model_name}"
            if not container.has(container_key):
                # Create factory function that returns the class
                def model_factory(model_cls=cls):
                    return model_cls

                container.register_factory(container_key, model_factory)
                logger.info(f"Registered model {model_name} in container")

            # Model already in registry, just update status
            logger.debug(f"Model {model_name} already in registry, completing registration")

            # Set environment reference
            cls._env = env

            # Set environment for all fields with error handling
            for field_name, field in fields_dict.items():
                try:
                    field.env = env
                except Exception as e:
                    logger.warning(f"Failed to set environment for field {field_name}: {e}")

            # Process pending reverse relationships safely
            try:
                process_pending_reverse_relationships()
            except Exception as e:
                logger.warning(f"Failed to process pending relationships for {model_name}: {e}")

        except Exception as e:
            # Cleanup on failure to prevent inconsistent state
            mcs._cleanup_failed_registration(model_name)
            raise RuntimeError(f"Failed to register model {model_name}: {e}") from e

    @classmethod
    def _cleanup_failed_registration(mcs, model_name: str) -> None:
        """Cleanup failed model registration to prevent inconsistent state.

        Args:
            model_name: Name of the model to cleanup
        """
        from earnorm.di import container

        try:
            # Remove from model registry
            if model_name in _model_registry:
                del _model_registry[model_name]
                logger.debug(f"Cleaned up model registry for {model_name}")

            # Remove from container
            container_key = f"model.{model_name}"
            if container.has(container_key):
                try:
                    container.unregister(container_key)
                    logger.debug(f"Cleaned up container registration for {model_name}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup container for {model_name}: {e}")

        except Exception as e:
            logger.warning(f"Failed to cleanup registration for {model_name}: {e}")

    @classmethod
    def register_deferred_models(mcs) -> None:
        """Register models that were deferred due to uninitialized environment.

        This method should be called after environment initialization to register
        models that couldn't be registered during class creation.
        """
        from earnorm.base.env import Environment

        logger.info(f"Starting deferred model registration. Registry has {len(_model_registry)} models")

        env = Environment.get_instance()
        if not env or not getattr(env, "_initialized", False):
            logger.warning("Environment not available for deferred model registration")
            return

        # Re-register all models in the registry
        registered_count = 0
        for model_name, model_cls in list(_model_registry.items()):
            try:
                logger.debug(f"Checking model {model_name}, has _env: {hasattr(model_cls, '_env')}")
                if hasattr(model_cls, "_env"):
                    logger.debug(f"Model {model_name} _env value: {model_cls._env}")
                    logger.debug(f"Model {model_name} _env type: {type(model_cls._env)}")

                # Check if _env is None or not a proper Environment instance
                needs_registration = (
                    not hasattr(model_cls, "_env") or
                    model_cls._env is None or
                    not hasattr(model_cls._env, "adapter")  # Check if it's a proper Environment
                )

                if needs_registration:
                    logger.info(f"Re-registering deferred model: {model_name}")

                    # Set environment
                    model_cls._env = env

                    # Register in DI container if not already registered
                    from earnorm.di import container
                    container_key = f"model.{model_name}"
                    if not container.has(container_key):
                        # Create factory function that returns the class
                        def model_factory(model_cls=model_cls):
                            return model_cls

                        container.register_factory(container_key, model_factory)
                        logger.debug(f"Registered model {model_name} in container during deferred registration")

                    # Set environment for fields
                    if hasattr(model_cls, "__fields__"):
                        for field_name, field in model_cls.__fields__.items():
                            try:
                                field.env = env
                            except Exception as e:
                                logger.warning(f"Failed to set environment for field {field_name}: {e}")

                    registered_count += 1
                    logger.info(f"Successfully re-registered model: {model_name}")
                else:
                    logger.debug(f"Model {model_name} already has environment")

            except Exception as e:
                logger.error(f"Failed to re-register model {model_name}: {e}")

        logger.info(f"Deferred model registration completed. Registered {registered_count} models")

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        """Create model instance with injected env.

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Model instance
        """
        # Get env from container if not provided
        if "env" not in kwargs:
            try:
                from earnorm.base.env import Environment

                env = Environment.get_instance()
                if env:
                    kwargs["env"] = env
            except Exception as e:
                logger.error(f"Failed to inject environment: {e}")

        return super().__call__(*args, **kwargs)
