"""Model metaclass implementation.

This module provides the MetaModel metaclass for model registration and inheritance.
It includes:
- Model registration
- Field registration
- Method registration
- Inheritance handling
- Async method support
- RecordSet type creation

Examples:
    >>> from earnorm.base.model.meta import MetaModel
    >>>
    >>> class User(metaclass=MetaModel):
    ...     _name = "res.users"
    ...     _description = "Users"
    ...
    ...     name = StringField(required=True)
    ...     email = StringField()
    ...
    ...     @multi
    ...     async def write(self, values):
    ...         return await super().write(values)
"""

from typing import Any, Dict, Iterator, List, Optional, Set, Type, TypeVar, Union, cast

from earnorm.base.env import Environment
from earnorm.types import FieldProtocol

from .base import BaseModel

T = TypeVar("T", bound="BaseModel")


class RecordSetType(BaseModel):
    """Base type for RecordSet classes.

    A RecordSet is a collection of model records that behaves like both
    a list of records and a model instance. It inherits all model methods
    and attributes while providing list operations.
    """

    __annotations__ = {"_ids": List[int], "_prefetch": Dict[str, Set[int]]}

    def __init__(
        self,
        env: Environment,
        ids: Optional[Union[int, List[int]]] = None,
    ) -> None:
        """Initialize RecordSet.

        Args:
            env: Environment instance
            ids: Optional ID or list of IDs to initialize with
        """
        super().__init__(env=env)
        self._ids = self._normalize_ids(ids) if ids else []

    def __getitem__(self: T, index: Union[int, slice]) -> T:
        """Get record(s) at index."""
        if isinstance(index, slice):
            # Create new instance with sliced IDs
            instance = self.__class__(env=self._instance_env)
            instance._ids = self._ids[index]
            return instance
        else:
            # Create new instance with single ID
            instance = self.__class__(env=self._instance_env)
            instance._ids = [self._ids[index]]
            return instance

    def __len__(self) -> int:
        """Get number of records in set."""
        return len(self._ids)

    def __iter__(self: T) -> Iterator[T]:
        """Iterate over records."""
        for record_id in self._ids:
            instance = self.__class__(env=self._instance_env)
            instance._ids = [record_id]
            yield instance

    def __repr__(self) -> str:
        return f"{self._name}[{self._ids}]"

    def __str__(self) -> str:
        return f"{self._name}[{self._ids}]"


class MetaModel(type):
    """Metaclass for EarnORM models.

    This class handles:
    - Model registration
    - Field registration
    - Method registration
    - Inheritance handling
    - Async method support
    - RecordSet type creation

    Attributes:
        _name: Model name
        _description: Model description
        _table: Database table name
        _sequence: ID sequence name
        _inherit: Parent model names
        _inherits: Parent models to inherit fields from
        _order: Default order
        _fields: Model fields dictionary
        _constraints: Model constraints set
    """

    _fields: Dict[str, FieldProtocol[Any]] = {}
    _constraints: set[Any] = set()

    def __new__(
        mcs,
        name: str,
        bases: tuple[Type[Any], ...],
        attrs: Dict[str, Any],
        **kwargs: Any,
    ) -> Type[BaseModel]:
        """Create new model class.

        Args:
            name: Class name
            bases: Base classes
            attrs: Class attributes
            **kwargs: Additional arguments

        Returns:
            Model class

        Raises:
            ValueError: If model name is missing
        """
        # Skip registration for BaseModel
        if attrs.get("__module__") == "earnorm.base.model.base":
            return cast(Type[BaseModel], super().__new__(mcs, name, bases, attrs))

        # Get model name
        model_name = attrs.get("_name")
        if not model_name:
            raise ValueError(f"Model {name} must have _name attribute")

        # Setup model attributes
        mcs._setup_model_attributes(attrs, model_name)

        # Setup fields
        fields = mcs._setup_fields(bases, attrs)
        attrs["fields"] = fields

        # Create model class first
        model_class = super().__new__(mcs, name, bases, attrs)

        # Create RecordSet type that inherits from model class
        recordset_name = f"{name}RecordSet"
        recordset_cls = type(
            recordset_name,
            (RecordSetType, model_class),  # Add model_class as base
            {
                "_name": model_name,
                "_ids": [],
                "__annotations__": {"_ids": List[int], "model_name": str},
            },
        )

        # Add RecordSet type to attributes
        setattr(model_class, "_RecordSet", recordset_cls)

        # Register model if it has environment
        mcs._register_model(cast(Type[BaseModel], model_class))

        return cast(Type[BaseModel], model_class)

    @classmethod
    def _setup_model_attributes(cls, attrs: Dict[str, Any], model_name: str) -> None:
        """Setup model attributes.

        Args:
            attrs: Class attributes
            model_name: Model name
        """
        attrs["_table"] = attrs.get("_table") or model_name.replace(".", "_")
        attrs["_sequence"] = attrs.get("_sequence") or f"{attrs['_table']}_id_seq"
        attrs["_inherit"] = attrs.get("_inherit", [])
        attrs["_inherits"] = attrs.get("_inherits", {})
        attrs["_order"] = attrs.get("_order", "id")
        attrs["_constraints"] = set()
        attrs["_auto"] = attrs.get("_auto", True)
        attrs["_register"] = attrs.get("_register", True)
        attrs["_abstract"] = attrs.get("_abstract", False)
        attrs["_transient"] = attrs.get("_transient", False)

    @classmethod
    def _setup_fields(
        cls, bases: tuple[Type[Any], ...], attrs: Dict[str, Any]
    ) -> Dict[str, FieldProtocol[Any]]:
        """Setup model fields.

        Args:
            bases: Base classes
            attrs: Class attributes

        Returns:
            Dictionary of fields
        """
        # Get fields from bases
        fields: Dict[str, FieldProtocol[Any]] = {}
        for base in bases:
            if hasattr(base, "_fields"):
                base_fields = cast(
                    Dict[str, FieldProtocol[Any]], getattr(base, "_fields", {})
                )
                fields.update(base_fields)

        # Register new fields
        for key, value in attrs.items():
            if isinstance(value, FieldProtocol):
                fields[key] = value
                value.setup(cls)

        return fields

    @classmethod
    def _register_model(cls, model_class: Type[BaseModel]) -> None:
        """Register model in environment.

        Args:
            model_class: Model class to register
        """
        if hasattr(model_class, "env"):
            env: Environment = getattr(model_class, "env")
            model_name = cast(str, getattr(model_class, "_name"))
            env.add_model(model_name, model_class)

    def __init__(
        cls,
        name: str,
        bases: tuple[Type[Any], ...],
        attrs: Dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """Initialize model class.

        Args:
            name: Class name
            bases: Base classes
            attrs: Class attributes
            **kwargs: Additional arguments
        """
        super().__init__(name, bases, attrs, **kwargs)

        # Skip initialization for BaseModel
        if attrs.get("__module__") == "earnorm.base.model.base":
            return

        # Initialize fields
        cls._setup_field_triggers()

        # Initialize methods
        cls._setup_methods()

    @classmethod
    def _setup_field_triggers(cls) -> None:
        """Setup field triggers.

        This initializes field triggers for computed fields.
        """
        for field in cls._fields.values():
            field.setup_triggers()

    @classmethod
    def _setup_methods(cls) -> None:
        """Setup model methods.

        This:
        - Registers computed methods
        - Sets up method dependencies
        - Marks async methods
        """
        # Get all methods
        methods = cls._get_methods()

        # Setup method attributes
        for name, method in methods.items():
            cls._setup_method(name=name, method=method)

    @classmethod
    def _get_methods(cls) -> Dict[str, Any]:
        """Get all model methods.

        Returns:
            Dictionary of methods
        """
        methods: Dict[str, Any] = {}
        for name in dir(cls):
            if name.startswith("_"):
                continue
            value = getattr(cls, name)
            if callable(value):
                methods[name] = value
        return methods

    @classmethod
    def _setup_method(cls, name: str, method: Any) -> None:
        """Setup single method.

        Args:
            name: Method name
            method: Method object
        """
        # Mark async methods
        if hasattr(method, "_async"):
            setattr(cls, name, method)

        # Setup computed methods
        if hasattr(method, "_compute"):
            field = cls._fields.get(method._compute)  # pylint: disable=W0212
            if field:
                field.compute = method
                field.compute_depends = getattr(method, "_depends", set())  # type: ignore

    # getters fields
    @property
    def fields(cls) -> Dict[str, FieldProtocol[Any]]:
        """Get model fields dictionary."""
        return cls._fields
