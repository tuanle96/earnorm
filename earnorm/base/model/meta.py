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

from __future__ import annotations

from typing import (
    Any,
    ClassVar,
    Dict,
    Iterator,
    List,
    Optional,
    Protocol,
    Set,
    Type,
    TypeVar,
    Union,
    cast,
    runtime_checkable,
)

from earnorm.base.env import Environment
from earnorm.types import FieldProtocol, ModelProtocol

T = TypeVar("T", bound="BaseModel")
Self = TypeVar("Self", bound="RecordSetType")


@runtime_checkable
class BaseModel(Protocol):
    """Protocol for base model functionality."""

    _name: ClassVar[str]
    _fields: ClassVar[Dict[str, FieldProtocol[Any]]]
    _instance_env: Environment

    def _normalize_ids(self, ids: Union[int, List[int]]) -> List[int]:
        """Normalize record IDs."""
        ...


class BaseModelMetaclass(type):
    """Base metaclass for all model types."""

    def __new__(
        mcs,
        name: str,
        bases: tuple[Type[Any], ...],
        attrs: Dict[str, Any],
        **kwargs: Any,
    ) -> Type[Any]:
        """Create new model class."""
        return super().__new__(mcs, name, bases, attrs)


class RecordSetMetaclass(BaseModelMetaclass):
    """Metaclass for RecordSet types."""

    pass


class ModelMetaclass(BaseModelMetaclass):
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

    async def __new__(
        mcs,
        name: str,
        bases: tuple[Type[Any], ...],
        attrs: Dict[str, Any],
        **kwargs: Any,
    ) -> Type[ModelProtocol]:
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
            return cast(Type[ModelProtocol], super().__new__(mcs, name, bases, attrs))

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
            metaclass=RecordSetMetaclass,  # Use RecordSet metaclass
        )

        # Add RecordSet type to attributes
        setattr(model_class, "_RecordSet", recordset_cls)

        # Register model if it has environment
        await mcs._register_model(cast(Type[ModelProtocol], model_class))

        return cast(Type[ModelProtocol], model_class)

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
    async def _register_model(cls, model_class: Type[ModelProtocol]) -> None:
        """Register model in environment.

        Args:
            model_class: Model class to register
        """
        if hasattr(model_class, "_instance_env"):
            env = cast(Environment, getattr(model_class, "_instance_env"))
            model_name = cast(str, getattr(model_class, "_name"))
            await env.register_model(model_name, model_class)


class RecordSetType:
    """Base type for RecordSet classes.

    A RecordSet is a collection of model records that behaves like both
    a list of records and a model instance. It inherits all model methods
    and attributes while providing list operations.
    """

    _name: ClassVar[str]
    _instance_env: Environment
    _ids: List[int]
    _prefetch: Dict[str, Set[int]]

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
        self._instance_env = env
        self._ids = self._normalize_ids(ids) if ids else []
        self._prefetch = {}

    def __getitem__(self: Self, index: Union[int, slice]) -> Self:
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

    def __iter__(self: Self) -> Iterator[Self]:
        """Iterate over records."""
        for record_id in self._ids:
            instance = self.__class__(env=self._instance_env)
            instance._ids = [record_id]
            yield instance

    def __repr__(self) -> str:
        return f"{self._name}[{self._ids}]"

    def __str__(self) -> str:
        return f"{self._name}[{self._ids}]"

    def _normalize_ids(self, ids: Optional[Union[int, List[int]]]) -> List[int]:
        """Normalize record IDs.

        Args:
            ids: ID or list of IDs

        Returns:
            Normalized list of IDs
        """
        if ids is None:
            return []
        if isinstance(ids, int):
            return [ids]
        return list(ids)
