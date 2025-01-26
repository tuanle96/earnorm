"""Model metaclass implementation.

This module provides the metaclass for all database models.
It handles:
- Field registration and validation
- Model registration with environment
- Slot creation
- Name generation
- Default fields injection
- Model registry management
- Inheritance tracking
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Set, Type, TypeVar, cast

from earnorm.fields.base import Field
from earnorm.fields.primitive import DateTimeField, StringField


@dataclass
class ModelInfo:
    """Model information container.

    Attributes:
        name: Technical name (e.g. res.users)
        model_class: Model class
        is_abstract: Whether model is abstract
        parent_models: Parent model names
        fields: All fields including inherited
    """

    name: str
    model_class: Type["BaseModel"]
    is_abstract: bool
    parent_models: Set[str]
    fields: Dict[str, Field[Any]]


# Forward reference for BaseModel
class BaseModel:
    """Base class for all database models.

    This class defines the basic structure and behavior that all models must have.
    It includes:
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

    # Required attributes
    _name: str
    fields: Dict[str, Field[Any]]

    # Abstract flag - not in slots because it's a class variable
    _abstract: bool = False

    # Recordset attributes
    _domain: List[Any]
    _limit: Optional[int]
    _offset: Optional[int]
    _order: Optional[str]
    _group_by: Optional[List[str]]
    _having: Optional[List[Any]]
    _distinct: bool
    _data: Dict[str, Any]
    _changed: Set[str]

    # Define slots for memory efficiency
    __slots__ = (
        "_name",
        "fields",
        "_domain",
        "_limit",
        "_offset",
        "_order",
        "_group_by",
        "_having",
        "_distinct",
        "_data",
        "_changed",
    )

    def __init__(self, **data: Any) -> None:
        """Initialize model instance.

        Args:
            **data: Initial values for fields
        """
        # Initialize recordset attributes
        self._domain = []
        self._limit = None
        self._offset = None
        self._order = None
        self._group_by = None
        self._having = None
        self._distinct = False
        self._data = {}
        self._changed = set()

        # Set initial data
        for key, value in data.items():
            setattr(self, key, value)


ValueT = TypeVar("ValueT")


class MetaModel(type):
    """Metaclass for all database models.

    This metaclass handles:
    - Field registration and validation
    - Model registration with environment
    - Slot creation
    - Name generation
    - Default fields injection
    - Model registry management
    - Inheritance tracking

    Examples:
        >>> class User(BaseModel):
        ...     _name = 'res.users'
        ...     name = StringField(required=True)
        ...     email = EmailField(unique=True)
        ...
        >>> user = User(name="John")
        >>> user.id         # Default field
        >>> user.created_at # Default field
        >>> user.updated_at # Default field
        >>> User.__fields__ # Access all fields through class
        >>> user.__fields__ # Access all fields through instance
    """

    # Global registry for all models
    _registry: Dict[str, Type["BaseModel"]] = {}

    # Inheritance graph (parent -> children)
    _inherit_graph: Dict[str, Set[str]] = {}

    # Define default fields that every model should have
    DEFAULT_FIELDS: Dict[str, Field[Any]] = {
        "id": StringField(
            required=True,
            readonly=True,
            backend_options={"mongodb": {"field_name": "_id"}},  # Map to MongoDB's _id
        ),
        "created_at": DateTimeField(
            required=True, readonly=True, default=lambda: datetime.now(UTC)
        ),
        "updated_at": DateTimeField(
            required=True, readonly=True, default=lambda: datetime.now(UTC)
        ),
    }

    def __new__(
        mcs, name: str, bases: tuple[Type[Any], ...], attrs: Dict[str, Any]
    ) -> Type[BaseModel]:
        """Create new model class.

        Args:
            name: Class name
            bases: Base classes
            attrs: Class attributes

        Returns:
            New model class

        Raises:
            ValueError: If trying to override default field or invalid model name
        """
        # Create slots
        slots: Set[str] = set()
        for base in bases:
            slots.update(getattr(base, "__slots__", ()))

        # Collect fields from parent classes
        inherited_fields: Dict[str, Field[Any]] = {}
        for base in bases:
            if hasattr(base, "fields"):
                inherited_fields.update(getattr(base, "fields", {}))

        # Add default fields first
        fields: Dict[str, Field[Any]] = {}
        for field_name, field in mcs.DEFAULT_FIELDS.items():
            # Create a new instance of the field for each model
            new_field = field.__class__(**field.__dict__)
            fields[field_name] = new_field
            new_field.name = field_name
            slots.add(f"_{field_name}")

        # Add user-defined fields
        for key, value in attrs.items():
            if isinstance(value, Field):
                if key in fields:
                    raise ValueError(f"Cannot override default field '{key}'")
                slots.add(f"_{key}")
                fields[key] = value
                value.name = key

        # Add recordset slots
        recordset_slots = {
            "_domain",
            "_limit",
            "_offset",
            "_order",
            "_group_by",
            "_having",
            "_distinct",
            "_env",
            "_data",
            "_changed",
        }
        slots.update(recordset_slots)

        attrs["__slots__"] = tuple(slots)

        # Combine inherited and current fields
        all_fields = {**inherited_fields, **fields}
        attrs["fields"] = all_fields

        # Create new class
        cls = super().__new__(mcs, name, bases, attrs)

        # Set model name if not defined
        if "_name" not in attrs:
            attrs["_name"] = name.lower()

        # Validate model name
        model_name = attrs["_name"]
        mcs.validate_model_name(model_name)

        # Register model
        mcs._registry[model_name] = cls

        # Update inheritance graph
        for base in bases:
            if hasattr(base, "_name"):
                parent_name = base._name
                if parent_name not in mcs._inherit_graph:
                    mcs._inherit_graph[parent_name] = set()
                mcs._inherit_graph[parent_name].add(model_name)

        return cast(Type[BaseModel], cls)

    @classmethod
    def validate_model_name(cls, name: str) -> None:
        """Validate model name format.

        Args:
            name: Model name to validate

        Raises:
            ValueError: If model name is invalid
        """
        if not name or "." not in name:
            raise ValueError("Model name must be in format: 'module.model'")

    @classmethod
    def get_model(cls, name: str) -> Type["BaseModel"]:
        """Get model by name.

        Args:
            name: Model name

        Returns:
            Model class

        Raises:
            ValueError: If model not found
        """
        try:
            return cls._registry[name]
        except KeyError as exc:
            raise ValueError(f"Model {name} not found in registry") from exc

    @classmethod
    def get_inherited_models(cls, model_name: str) -> Set[str]:
        """Get all models that inherit from given model.

        Args:
            model_name: Parent model name

        Returns:
            Set of child model names
        """
        return cls._inherit_graph.get(model_name, set())

    @classmethod
    def get_parent_models(cls, model_name: str) -> Set[str]:
        """Get all parent models of given model.

        Args:
            model_name: Child model name

        Returns:
            Set of parent model names
        """
        model = cls._registry[model_name]
        parents: Set[str] = set()
        for base in model.__bases__:
            if hasattr(base, "_name"):
                parent_name = getattr(base, "_name")
                parents.add(parent_name)
        return parents

    @classmethod
    def list_models(cls) -> List[str]:
        """List all registered models.

        Returns:
            List of model names
        """
        return list(cls._registry.keys())

    @classmethod
    def list_concrete_models(cls) -> List[str]:
        """List only concrete models.

        Returns:
            List of concrete model names
        """
        return [
            name
            for name, model in cls._registry.items()
            if not getattr(model, "_abstract", False)
        ]

    @classmethod
    def get_model_info(cls, name: str) -> ModelInfo:
        """Get detailed info about a model.

        Args:
            name: Model name

        Returns:
            ModelInfo instance

        Raises:
            ValueError: If model not found
        """
        model = cls.get_model(name)
        return ModelInfo(
            name=name,
            model_class=model,
            is_abstract=getattr(model, "_abstract", False),
            parent_models=cls.get_parent_models(name),
            fields=getattr(model, "fields", {}),
        )
