"""Base model for EarnORM.

This module provides the internal base model class that all ORM models inherit from.
It handles record management, field access, and common functionality.
This is an internal implementation and should not be used directly.

Examples:
    >>> from earnorm.base.model import StoredModel, AbstractModel
    >>>
    >>> class User(StoredModel):
    ...     _name = 'data.user'
    ...     name = StringField()
    ...
    >>> class UserService(AbstractModel):
    ...     _name = 'service.user'
    ...     async def authenticate(self, user_id: int):
    ...         pass
"""

from __future__ import annotations

from typing import (
    Any,
    ClassVar,
    Dict,
    ForwardRef,
    Generic,
    List,
    Optional,
    Protocol,
    Set,
    Tuple,
    Type,
    TypeAlias,
    TypeVar,
    Union,
    cast,
    overload,
    runtime_checkable,
)

from earnorm.base.database.adapters.mongo import MongoQuery
from earnorm.base.database.query.base.query import Query
from earnorm.base.database.transaction.base import DatabaseTransaction
from earnorm.base.domain.converters.mongo import MongoConverter
from earnorm.base.domain.expression import DomainExpression
from earnorm.base.domain.operators import DomainOperator, LogicalOp
from earnorm.base.domain.types import ValueType
from earnorm.base.env import Environment
from earnorm.base.model.meta import ModelMetaclass, RecordSetType
from earnorm.di import container
from earnorm.fields.base import Field
from earnorm.types import JsonDict, ModelProtocol
from earnorm.validators.base import ValidationError

# Type variables for model types
ModelT = TypeVar("ModelT", bound="BaseModel[Any]")
Self = TypeVar("Self", bound="BaseModel[Any]")

T = TypeVar("T", bound="ModelProtocol")
V = TypeVar("V")

# Type variables for protocols
T_model = TypeVar("T_model", bound=ModelProtocol, contravariant=True)
T_contra = TypeVar("T_contra", bound=ModelProtocol, contravariant=True)

# Forward references
BaseModelRef = ForwardRef("BaseModel")

# Domain expression types
DomainTerm = Tuple[str, DomainOperator, Any]
DomainValue = Union[str, int, float, bool, List[Any], Dict[str, Any], None]

# Class level environment
T_model = TypeVar("T_model", bound=ModelProtocol)

# Type aliases
ModelType: TypeAlias = Type[ModelProtocol]
QueryType: TypeAlias = Query[ModelProtocol]
TransactionType: TypeAlias = DatabaseTransaction[ModelProtocol]


@runtime_checkable
class FieldProvider(Protocol):
    """Protocol for field access."""

    __fields__: ClassVar[Dict[str, Field[Any]]]
    _name: ClassVar[str]


@runtime_checkable
class RelatedFieldProvider(Protocol):
    """Protocol for related field access."""

    name: str
    relational: bool
    comodel_name: str
    inverse_name: str


@runtime_checkable
class ModelRegistryProvider(Protocol):
    """Protocol for model registration."""

    async def get_model(self, name: str) -> Type[ModelProtocol]:
        """Get model by name."""
        ...

    async def register_model(self, name: str, model: Type[ModelProtocol]) -> None:
        """Register model."""
        ...


@runtime_checkable
class EnvironmentProvider(Protocol):
    """Protocol for environment access."""

    @classmethod
    def get_class_env(cls) -> Optional[Environment]:
        """Get class level environment."""
        ...

    @classmethod
    def set_class_env(cls, env: Environment) -> None:
        """Set class level environment."""
        ...

    def get_instance_env(self) -> Environment:
        """Get instance environment."""
        ...


@runtime_checkable
class CacheProvider(Protocol):
    """Protocol for cache access."""

    async def get_cached(self, model: str, record_id: int) -> Optional[Dict[str, Any]]:
        """Get cached record."""
        ...

    async def set_cached(
        self, model: str, record_id: int, data: Dict[str, Any]
    ) -> None:
        """Set cached record."""
        ...


@runtime_checkable
class DatabaseRecord(Protocol):
    """Protocol for database record."""

    id: int


@runtime_checkable
class DatabaseAdapterProvider(Protocol):
    """Protocol for database adapter."""

    async def query(self, model_type: ModelType) -> QueryType:
        """Get query builder."""
        ...

    async def create(
        self, model_type: ModelType, values: Dict[str, Any]
    ) -> DatabaseRecord:
        """Create new record."""
        ...

    async def transaction(self, model_type: ModelType) -> TransactionType:
        """Start transaction."""
        ...


@runtime_checkable
class DatabaseTransaction(Protocol[T_contra]):
    """Protocol for database transaction."""

    async def __aenter__(self) -> "DatabaseTransaction[T_contra]":
        """Enter transaction context."""
        ...

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit transaction context."""
        ...

    async def insert(self, record: T_contra) -> DatabaseRecord:
        """Insert record."""
        ...

    async def update(self, record: T_contra, values: Dict[str, Any]) -> DatabaseRecord:
        """Update record."""
        ...

    async def delete(self, record: T_contra) -> bool:
        """Delete record."""
        ...


class EnvironmentDescriptor:
    """Descriptor for accessing environment.

    Provides unified access to environment for both instance and class.
    """

    @overload
    async def __get__(
        self, instance: None, owner: Type[EnvironmentProvider]
    ) -> Environment: ...

    @overload
    async def __get__(
        self,
        instance: EnvironmentProvider,
        owner: Optional[Type[EnvironmentProvider]] = None,
    ) -> Environment: ...

    async def __get__(
        self,
        instance: Optional[EnvironmentProvider],
        owner: Optional[Type[EnvironmentProvider]] = None,
    ) -> Environment:
        """Get environment instance.

        Args:
            instance: Model instance or None for class access
            owner: Model class

        Returns:
            Environment instance

        Raises:
            ValidationError: If no environment available
        """
        if instance is not None:
            # Instance access
            return instance.get_instance_env()

        # Class access or fallback
        if not owner:
            raise ValidationError("No environment available")

        class_env = owner.get_class_env()
        if class_env is None:
            # Try to get from container
            env = await container.get("env")
            if env is None:
                raise ValidationError("No environment available")
            owner.set_class_env(env)
            class_env = env

        return class_env


class BaseModel(
    ModelProtocol,
    Generic[T],
    EnvironmentProvider,
    FieldProvider,
    ModelRegistryProvider,
    metaclass=ModelMetaclass,
):
    """Internal base class for all ORM models.

    This class provides core functionality for:
    - Field definitions and validation
    - Model metadata management
    - Basic record operations
    - Common utilities and type definitions

    This is an internal implementation and should not be used directly.
    Use StoredModel or AbstractModel instead.

    Attributes:
        _name: Technical name of the model
        _description: User-friendly description
        _internal: Marker for internal implementation
        _store: Whether model supports storage (must be defined by subclasses)
        _instance_env: Environment instance for this model instance
        _ids: List of record IDs this instance represents
        _prefetch: Dictionary mapping field names to sets of prefetched record IDs
    """

    __slots__ = ["_instance_env", "_ids", "_prefetch"]

    # Model metadata
    _name: ClassVar[str]
    _description: ClassVar[Optional[str]] = None
    _internal: ClassVar[bool] = True  # Mark as internal
    _table: ClassVar[Optional[str]] = None
    _sequence: ClassVar[Optional[str]] = None
    _inherit: ClassVar[Optional[Union[str, List[str]]]] = None
    _inherits: ClassVar[Dict[str, str]] = {}
    _order: ClassVar[str] = "id"
    _rec_name: ClassVar[Optional[str]] = None
    _RecordSet: ClassVar[Type[RecordSetType]]

    # Field definitions
    __fields__: ClassVar[Dict[str, Field[Any]]] = {}

    # Model type flags
    _auto: ClassVar[bool] = True
    _register: ClassVar[bool] = True
    _abstract: ClassVar[bool] = False
    _transient: ClassVar[bool] = False

    # Class level environment
    _class_env: ClassVar[Optional[Environment]] = None

    # Environment descriptor
    env: EnvironmentDescriptor = EnvironmentDescriptor()

    # Instance attributes
    _instance_env: Environment
    _ids: List[int]
    _prefetch: Dict[str, Set[int]]

    # Database adapter
    _adapter: DatabaseAdapterProvider

    @classmethod
    def get_class_env(cls) -> Optional[Environment]:
        """Get class level environment.

        Returns:
            Class level environment or None
        """
        return cls._class_env

    @classmethod
    def set_class_env(cls, env: Environment) -> None:
        """Set class level environment.

        Args:
            env: Environment instance
        """
        cls._class_env = env

    def get_instance_env(self) -> Environment:
        """Get instance environment.

        Returns:
            Instance environment
        """
        return self._instance_env

    async def get_model(self, name: str) -> Type[ModelProtocol]:
        """Get model by name.

        Args:
            name: Model name

        Returns:
            Model class

        Raises:
            KeyError: If model not found
            ValidationError: If name is None or invalid
        """
        if not name:
            raise ValidationError("Model name cannot be None or empty")

        env = cast(ModelRegistryProvider, await self.env)
        model = await env.get_model(name)
        if not isinstance(model, type):
            raise ValidationError(f"Invalid model type for {name}")

        # Check if model implements ModelProtocol
        if not hasattr(model, "_name") or not hasattr(model, "_fields"):
            raise ValidationError(f"Invalid model type for {name}")

        return model

    async def register_model(self, name: str, model: Type[ModelProtocol]) -> None:
        """Register model.

        Args:
            name: Model name
            model: Model class

        Raises:
            ValueError: If model already registered
            ValidationError: If name is None or invalid
        """
        if not name:
            raise ValidationError("Model name cannot be None or empty")

        env = await self.env
        await env.register_model(name, model)

    @classmethod
    def _validate_model_type(cls: Type[ModelT]) -> None:
        """Validate model type configuration.

        Raises:
            TypeError: If _store attribute is not defined
        """
        if not hasattr(cls, "_store"):
            raise TypeError(f"Model {cls.__name__} must declare _store attribute")

    def __init_subclass__(cls: Type[ModelT]) -> None:
        """Initialize model subclass.

        This method is called when a class inherits from BaseModel.
        It validates the model configuration.

        Raises:
            TypeError: If model configuration is invalid
        """
        super().__init_subclass__()
        cls._validate_model_type()

    def __init__(
        self,
        env: Optional[Environment] = None,
        ids: Optional[Union[int, List[int]]] = None,
    ) -> None:
        """Initialize a new model instance.

        Args:
            env: Environment instance
            ids: Optional ID or list of IDs to initialize with

        Raises:
            ValidationError: If env is None and no class environment
        """
        # Use provided env or class env
        if env is not None:
            self._instance_env = env
        else:
            if not self.__class__._class_env:
                raise ValidationError("No environment available")
            self._instance_env = self.__class__._class_env

        self._ids = []
        self._prefetch = {}

        if ids is not None:
            self._ids = self._normalize_ids(ids)

    async def __getattr__(self, name: str) -> Any:
        """Lazy load field values.

        This method implements lazy loading by only loading field values
        when they are accessed. It checks the cache first and only loads
        from database if needed.

        Args:
            name: Name of the field to access

        Returns:
            Field value

        Raises:
            AttributeError: If field does not exist
        """
        # Check if field exists
        field = self.__fields__.get(name)
        if field is None:
            raise AttributeError(f"Field {name} does not exist on {self._name}")

        # Check cache first
        env = cast(CacheProvider, await self.env)
        cached = await env.get_cached(self._name, self._ids[0])
        if cached and name in cached:
            return cached[name]

        # Load from database if not in cache
        await self._read([field.name])
        cached = await env.get_cached(self._name, self._ids[0])
        if cached and name in cached:
            return cached[name]

        raise AttributeError(f"Field {name} not found in cache or database")

    async def _read(self, fields: List[str]) -> None:
        """Read field values from database.

        Args:
            fields: List of field names to read
        """
        # Get adapter
        adapter = await self._get_adapter()

        # Build query to get records
        query = await adapter.query(cast(Type[T], self.__class__))
        filter_dict = cast(JsonDict, {"_id": {"$in": self._ids}})
        records = await query.filter(filter_dict).execute_async()

        # Update cache
        env = cast(CacheProvider, await self.env)
        for record in records:
            record_values = {field: getattr(record, field) for field in fields}
            await env.set_cached(self._name, record.id, record_values)

    async def _prefetch_field(self, field: Field[Any]) -> None:
        """Setup prefetching for field.

        This method sets up prefetching for a field and its related fields.
        It adds records to the prefetch queue and handles related records.

        Args:
            field: Field to prefetch
        """
        if not field.prefetch or not self._ids:
            return

        if not isinstance(field, RelatedFieldProvider):
            return

        # Get related records
        env = cast(CacheProvider, await self.env)
        cached = await env.get_cached(self._name, self._ids[0])
        if cached and field.name in cached:
            return

        # Load from database
        await self._read([field.name])

    async def _prefetch_related(self, field: Field[Any]) -> None:
        """Prefetch related records.

        This method prefetches records related through a relation field.
        It handles both forward and backward relations.

        Args:
            field: Relation field to prefetch
        """
        if not field.prefetch or not self._ids:
            return

        if not isinstance(field, RelatedFieldProvider):
            return

        # Get related model
        env = cast(ModelRegistryProvider, await self.env)
        related_model = await env.get_model(field.comodel_name)
        if not related_model:
            return

        # Get related records
        adapter = await self._get_adapter()
        query = await adapter.query(cast(Type[T], related_model))
        filter_dict: JsonDict = {field.inverse_name: {"$in": self._ids}}
        records = await query.filter(filter_dict).execute_async()

        # Update cache
        cache_env = cast(CacheProvider, await self.env)
        for record in records:
            record_values = {field.name: getattr(record, field.name)}
            if field.comodel_name:
                await cache_env.set_cached(field.comodel_name, record.id, record_values)

                # Add to prefetch queue
                self._prefetch.setdefault(field.comodel_name, set()).add(record.id)

    async def _prefetch_setup(self) -> None:
        """Setup prefetching for all fields."""
        for field in self.__fields__.values():
            await self._prefetch_field(field)

    async def clear_prefetch(self) -> None:
        """Clear prefetch queue."""
        self._prefetch.clear()

    @classmethod
    async def browse(
        cls: Type[ModelT], ids: Optional[Union[int, List[int]]] = None
    ) -> ModelT:
        """Browse records by ID.

        Args:
            ids: Optional ID or list of IDs

        Returns:
            RecordSet instance
        """
        instance = cls(env=await cls.env, ids=ids)
        return instance

    @classmethod
    async def create(cls: Type[ModelT], values: Dict[str, Any]) -> ModelT:
        """Create new record.

        Args:
            values: Field values

        Returns:
            New record instance
        """
        instance = cls(env=await cls.env)
        await instance._create(values)
        return instance

    @classmethod
    async def search(cls: Type[ModelT], domain: Optional[List[Any]] = None) -> ModelT:
        """Search records.

        Args:
            domain: Search domain

        Returns:
            RecordSet instance
        """
        instance = cls(env=await cls.env)
        await instance._search(domain)
        return instance

    async def write(self, values: Dict[str, Any]) -> "BaseModel[T]":
        """Write values to record.

        Args:
            values: Field values

        Returns:
            Updated record instance
        """
        await self._write(values)
        return self

    async def unlink(self) -> bool:
        """Delete record.

        Returns:
            True if successful
        """
        return await self._unlink()

    async def _browse(
        self, ids: Optional[Union[int, List[int]]] = None
    ) -> "BaseModel[T]":
        """Internal browse implementation."""
        return self.__class__(env=await self.env, ids=ids)

    async def _create(self, values: Dict[str, Any]) -> None:
        """Create new record.

        Args:
            values: Field values
        """
        # Get adapter
        adapter = await self._get_adapter()

        # Create record
        async with await adapter.transaction(
            cast(Type[T], self.__class__)
        ) as transaction:
            record = await transaction.insert(cast(T, self))
            self._ids = [record.id]

            # Update cache
            env = cast(CacheProvider, await self.env)
            await env.set_cached(self._name, record.id, values)

    async def _write(self, values: Dict[str, Any]) -> None:
        """Internal write implementation."""
        # Validate values
        await self._validate_values(values)

        # Get adapter
        adapter = await self._get_adapter()

        # Update record
        async with await adapter.transaction(
            cast(Type[T], self.__class__)
        ) as transaction:
            record = await transaction.update(cast(T, self), values)
            self._ids = [record.id]

            # Update cache
            env = cast(CacheProvider, await self.env)
            await env.set_cached(self._name, record.id, values)

    async def _search(self, domain: Optional[List[Any]] = None) -> None:
        """Search records matching domain.

        Args:
            domain: Search domain
        """
        # Get adapter
        adapter = await self._get_adapter()

        # Build query
        query = cast(MongoQuery[T], await adapter.query(cast(Type[T], self.__class__)))
        if domain:
            # Convert domain to MongoDB filter
            filter_dict = self._domain_to_query(domain)
            converter = MongoConverter()
            mongo_filter = cast(JsonDict, converter.convert(filter_dict.root))
            query._raw_filter = mongo_filter

        # Execute query
        records = cast(List[T], await query.execute_async())
        self._ids = []
        for record in records:
            if hasattr(record, "id"):
                self._ids.append(cast(int, getattr(record, "id")))

    async def _unlink(self) -> bool:
        """Internal unlink implementation."""
        # Get adapter
        adapter = await self._get_adapter()

        # Delete record
        async with await adapter.transaction(
            cast(Type[T], self.__class__)
        ) as transaction:
            return await transaction.delete(cast(T, self))

    def _domain_to_query(self, domain: List[Any]) -> DomainExpression[ValueType]:
        """Convert domain to query expression.

        Args:
            domain: Domain list to convert

        Returns:
            Domain expression
        """
        if isinstance(domain, dict):
            # Convert dict to domain list
            domain_list = []
            for key, value in domain.items():
                if isinstance(value, dict):
                    for op, val in value.items():
                        if op == "$in":
                            domain_list.append((key, "in", val))
                        elif op == "$gt":
                            domain_list.append((key, ">", val))
                        elif op == "$gte":
                            domain_list.append((key, ">=", val))
                        elif op == "$lt":
                            domain_list.append((key, "<", val))
                        elif op == "$lte":
                            domain_list.append((key, "<=", val))
                        elif op == "$ne":
                            domain_list.append((key, "!=", val))
                else:
                    domain_list.append((key, "=", value))
            domain = domain_list
        return DomainExpression(
            cast(List[Union[Tuple[str, DomainOperator, ValueType], LogicalOp]], domain)
        )

    @classmethod
    async def _validate_values(cls, values: Dict[str, Any]) -> None:
        """Validate field values.

        Args:
            values: Field values to validate

        Raises:
            ValidationError: If validation fails
        """
        for field in cls.__fields__.values():
            await field.validate(values.get(field.name))

    @classmethod
    def _to_db_values(cls, values: JsonDict) -> JsonDict:
        """Convert values to database format.

        Args:
            values: Values to convert

        Returns:
            Converted values
        """
        db_values: JsonDict = {}
        for field in cls.__fields__.values():
            if field.name in values:
                db_values[field.name] = field.to_db(values[field.name])
        return db_values

    async def _get_adapter(self) -> DatabaseAdapterProvider:
        """Get database adapter.

        Returns:
            Database adapter
        """
        if not hasattr(self, "_adapter"):
            env = await self.env
            self._adapter = await env.get_adapter()
        return self._adapter

    def _normalize_ids(self, ids: Union[int, List[int]]) -> List[int]:
        """Normalize record IDs.

        Args:
            ids: ID or list of IDs

        Returns:
            Normalized list of IDs
        """
        if isinstance(ids, int):
            return [ids]
        return list(ids)

    async def _before_create(self, values: Dict[str, Any]) -> None:
        """Hook before record creation."""
        pass

    async def _after_create(self, values: Dict[str, Any]) -> None:
        """Hook after record creation."""
        pass

    async def _before_write(self, values: Dict[str, Any]) -> None:
        """Hook before record write."""
        pass

    async def _after_write(self, values: Dict[str, Any]) -> None:
        """Hook after record write."""
        pass

    async def _before_unlink(self) -> None:
        """Hook before record deletion."""
        pass

    async def _after_unlink(self) -> None:
        """Hook after record deletion."""
        pass

    def __str__(self) -> str:
        return f"{self._name}[{self._ids}]"

    @classmethod
    async def _internal_create(cls: Type[ModelT], values: JsonDict) -> ModelT:
        """Internal create method for database adapter.

        Args:
            values: Field values

        Returns:
            Created record
        """
        instance = cls(env=await cls.env)
        await instance._create(values)
        return instance

    @classmethod
    async def _internal_read(cls: Type[ModelT], ids: List[int]) -> List[ModelT]:
        """Internal read method for database adapter.

        Args:
            ids: Record IDs

        Returns:
            List of records
        """
        instance = cls(env=await cls.env)
        await instance._search([("id", "in", ids)])
        return [cls(env=await cls.env, ids=[id]) for id in instance._ids]

    @classmethod
    async def _internal_update(
        cls: Type[ModelT], ids: List[int], values: JsonDict
    ) -> List[ModelT]:
        """Internal update method for database adapter.

        Args:
            ids: Record IDs
            values: Field values

        Returns:
            List of updated records
        """
        instances = []
        for id in ids:
            instance = cls(env=await cls.env, ids=[id])
            await instance._write(values)
            instances.append(instance)
        return instances

    @classmethod
    async def _internal_delete(cls: Type[ModelT], ids: List[int]) -> bool:
        """Internal delete method for database adapter.

        Args:
            ids: Record IDs

        Returns:
            True if successful
        """
        instance = cls(env=await cls.env, ids=ids)
        return await instance._unlink()

    async def prefetch_field(self, field: Field[Any]) -> None:
        """Prefetch field values.

        Args:
            field: Field to prefetch
        """
        await self._prefetch_field(field)
