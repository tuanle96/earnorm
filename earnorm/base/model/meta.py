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
    Dict,
    List,
    Optional,
    Self,
    Set,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

from earnorm.base.database.transaction.base import Transaction
from earnorm.base.model.descriptors import AsyncFieldDescriptor
from earnorm.fields import BaseField
from earnorm.types.models import ModelProtocol

if TYPE_CHECKING:
    from earnorm.base.env import Environment

__all__ = ["BaseModel", "ModelInfo"]

logger = logging.getLogger(__name__)

T = TypeVar("T")
ValueT = TypeVar("ValueT")


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
    model_class: Type["BaseModel"]
    is_abstract: bool
    parent_models: Set[str]
    fields: Dict[str, BaseField[Any]]


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

    _description: ClassVar[Optional[str]]
    """User-friendly description."""

    _table: ClassVar[Optional[str]]
    """Database table name."""

    _sequence: ClassVar[Optional[str]]
    """ID sequence name."""

    _skip_default_fields: ClassVar[bool]
    """Whether to skip adding default fields."""

    _abstract: ClassVar[bool] = False
    """Whether model is abstract."""

    __fields__: ClassVar[Dict[str, BaseField[Any]]]
    """Model fields dictionary."""

    fields: Dict[str, BaseField[Any]]
    """Model fields dictionary (alias for __fields__)."""

    # Instance variables
    __slots__ = (
        "_env",  # Environment instance
        "_name",  # Model name
        "_ids",  # Record IDs
    )

    id: str
    """Record ID."""

    _env: "Environment"
    """Environment instance."""

    # Protocol methods
    @classmethod
    async def browse(cls, ids: Union[str, List[str]]) -> "BaseModel":
        """Browse records by IDs.

        Args:
            ids: Record ID or list of record IDs

        Returns:
            Recordset containing the records
        """
        ...

    async def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary.

        Returns:
            Dictionary representation of model
        """
        ...

    def from_dict(self, data: Dict[str, Any]) -> None:
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
    async def create(cls, values: Dict[str, Any]) -> Self: ...

    @classmethod
    @overload
    async def create(cls, values: List[Dict[str, Any]]) -> List[Self]: ...

    @classmethod
    async def create(
        cls, values: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None
    ) -> Union[Self, List[Self]]:
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

    async def write(self, values: Dict[str, Any]) -> "BaseModel":
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

    def __new__(
        mcs, name: str, bases: tuple[Type[Any], ...], attrs: Dict[str, Any]
    ) -> Type[object]:
        """Create new model class.

        Args:
            name: Class name
            bases: Base classes
            attrs: Class attributes

        Returns:
            New model class
        """
        # Skip for BaseModel
        if name == "BaseModel":
            return cast(Type[object], super().__new__(mcs, name, bases, attrs))

        # Get fields from class attributes
        fields_dict: Dict[str, BaseField[Any]] = {}

        # Don't wrap slot attributes and properties
        skip_wrap = set(attrs.get("__slots__", ())) | {"id", "ids"}

        # Wrap fields with AsyncFieldDescriptor
        for key, value in list(attrs.items()):
            if isinstance(value, BaseField) and key not in skip_wrap:
                attrs[key] = AsyncFieldDescriptor(value)  # type: ignore
                value.name = key  # Set field name
                fields_dict[key] = value

        # Add default fields if not skipped
        skip_defaults = attrs.get("_skip_default_fields", False)
        if not skip_defaults:
            from earnorm.fields import DatetimeField, StringField

            # Add id field to fields_dict but don't wrap with AsyncFieldDescriptor
            id_field = StringField(
                required=True, readonly=True, help="Unique identifier for the record"
            )
            id_field.name = "id"  # Set field name
            fields_dict["id"] = id_field
            # Don't wrap id with AsyncFieldDescriptor
            # attrs["id"] remains as property from BaseModel

            # Add other default fields
            created_at = DatetimeField(
                required=True,
                readonly=True,
                help="Record creation timestamp",
                auto_now_add=True,
            )
            created_at.name = "created_at"
            updated_at = DatetimeField(
                required=True, help="Last update timestamp", auto_now=True
            )
            updated_at.name = "updated_at"

            fields_dict["created_at"] = created_at
            fields_dict["updated_at"] = updated_at

            # Only wrap non-id fields with AsyncFieldDescriptor
            if "created_at" not in skip_wrap:
                attrs["created_at"] = AsyncFieldDescriptor(created_at)
            if "updated_at" not in skip_wrap:
                attrs["updated_at"] = AsyncFieldDescriptor(updated_at)
        else:
            # Even if defaults are skipped, ensure id field exists
            from earnorm.fields import StringField

            if "id" not in fields_dict:
                id_field = StringField(
                    required=True,
                    readonly=True,
                    help="Unique identifier for the record",
                )
                id_field.name = "id"  # Set field name
                fields_dict["id"] = id_field
                attrs["id"] = AsyncFieldDescriptor(id_field)

        # Set __fields__ class variable
        attrs["__fields__"] = fields_dict

        # Create class
        cls = cast(Type[object], super().__new__(mcs, name, bases, attrs))

        # Get environment from container
        try:
            from earnorm.base.env import Environment

            env = Environment.get_instance()
            if env:
                setattr(cls, "_env", env)
        except Exception as e:
            logger.error(f"Failed to inject environment: {e}")

        return cls

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
