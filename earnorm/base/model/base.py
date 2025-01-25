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

from typing import (
    Any,
    ClassVar,
    Dict,
    Generic,
    List,
    Literal,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

from earnorm.base.database.adapter import DatabaseAdapter
from earnorm.base.database.query.backends.mongo.query import MongoQuery
from earnorm.base.domain.expression import DomainExpression
from earnorm.base.env import Environment
from earnorm.base.model.meta import MetaModel, RecordSetType
from earnorm.di import container
from earnorm.fields.base import Field
from earnorm.types import JsonDict, ModelProtocol, ValueType
from earnorm.validators.base import ValidationError

# Type variables for model types
ModelT = TypeVar("ModelT", bound="BaseModel")
Self = TypeVar("Self", bound="BaseModel")

# Domain expression types
DomainOperator = Literal[
    "=", "!=", "<", "<=", ">", ">=", "in", "not in", "like", "ilike"
]
DomainTerm = Tuple[str, DomainOperator, Any]
Domain = List[Union[DomainTerm, List[DomainTerm]]]

T = TypeVar("T", bound=ModelProtocol)
V = TypeVar("V")


class EnvironmentDescriptor:
    """Descriptor for accessing environment.

    Provides unified access to environment for both instance and class.
    """

    async def __get__(self, instance: Any, owner: Any = None) -> Environment:
        if instance is not None:
            # Instance access
            if hasattr(instance, "_instance_env"):
                return instance._instance_env
        # Class access or fallback
        if owner._class_env is None:
            # Try to get from container
            env = await container.get("env")
            if env is None:
                raise ValidationError("No environment available")
            owner._class_env = env
        return owner._class_env


class BaseModel(ModelProtocol, Generic[T], metaclass=MetaModel):
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
    env = EnvironmentDescriptor()

    # Database adapter
    _adapter: DatabaseAdapter[T]

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
            self._instance_env = self.__class__._class_env

        if self._instance_env is None:
            raise ValidationError("No environment available")

        self._ids: List[int] = []
        self._prefetch: Dict[str, Set[int]] = {}

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
        env = await self.env
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
        filter_dict: JsonDict = {"_id": {"$in": self._ids}}
        records = await cast(MongoQuery[T], query).filter(filter_dict).execute_async()

        # Update cache
        env = await self.env
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

        # Add to prefetch queue
        env = await self.env
        env.add_to_prefetch(self._name, set(self._ids))

        # Setup related fields prefetch
        if field.relational:
            await self._prefetch_related(field)

    async def _prefetch_related(self, field: Field[Any]) -> None:
        """Setup prefetching for related fields.

        This method handles prefetching of related records by:
        1. Getting the related model
        2. Collecting related record IDs
        3. Adding them to prefetch queue

        Args:
            field: Related field to prefetch
        """
        if not field.comodel_name:
            return

        env = await self.env
        comodel = cast(Type[BaseModel[T]], env[field.comodel_name])

        # Get related record IDs
        related_ids: Set[int] = set()
        for record_id in self._ids:
            cached = await env.get_cached(self._name, record_id)
            if cached and field.name in cached:
                value = cached[field.name]
                if value:
                    if isinstance(value, (list, tuple)):
                        related_ids.update(cast(List[int], value))
                    else:
                        related_ids.add(cast(int, value))

        # Add to prefetch queue
        if related_ids:
            browsed = await comodel.browse(list(related_ids))
            await browsed.prefetch_field(field)

    async def _prefetch_setup(self) -> None:
        """Setup prefetch registry.

        This method initializes the prefetch registry for the model.
        It tracks which records should be prefetched.
        """
        env = await self.env
        env.add_to_prefetch(self._name, set(self._ids))

    async def clear_prefetch(self) -> None:
        """Clear prefetch registry.

        This method clears the prefetch registry for the model.
        """
        env = await self.env
        env.clear_prefetch()

    # Public CRUD Methods
    @classmethod
    async def browse(
        cls: Type[Self], ids: Optional[Union[int, List[int]]] = None
    ) -> Self:
        """Browse records by ID.

        Args:
            ids: Optional ID or list of IDs to browse. If None, use current IDs.

        Returns:
            Model instance containing the records

        Examples:
            >>> users = await User.browse([1, 2, 3])  # Returns User instance
            >>> for user in users:  # user is also User instance
            ...     print(user.name)
        """
        env = await cls.env
        instance = cls(env=env)
        return await instance._browse(ids)

    @classmethod
    async def create(cls: Type[Self], values: Dict[str, Any]) -> Self:
        """Create a new record.

        Args:
            values: Field values for the new record

        Returns:
            Model instance containing the new record

        Examples:
            >>> user = await User.create({"name": "John", "age": 30})  # Returns User instance
            >>> print(user.name)
        """
        # Validate values
        cls._validate_values(values)

        env = await cls.env
        instance = cls(env=env)
        return await instance._create(values)

    @classmethod
    async def search(cls: Type[Self], domain: Optional[List[Any]] = None) -> Self:
        """Search records matching domain.

        Args:
            domain: Search domain

        Returns:
            Instance of the concrete model class containing matching records

        Examples:
            >>> users = await User.search([("age", ">", 18)])  # Returns User instance
            >>> print(users[0].name)  # User instance
            >>> print(users[1:3])  # User instance
        """
        env = await cls.env
        instance = cls(env=env)

        # Transform domain to query if needed
        query = instance._domain_to_query(domain) if domain else None

        return await instance._search(query)

    async def write(self, values: Dict[str, Any]) -> Self:
        """Update record with values.

        Args:
            values: Field values to update

        Returns:
            Updated record instance

        Examples:
            >>> user = await User.browse(1)
            >>> await user.write({"name": "Jane"})
        """
        # Validate values
        self._validate_values(values)
        return await self._write(values)

    async def unlink(self) -> bool:
        """Delete record from database.

        Returns:
            True if records were deleted

        Examples:
            >>> user = await User.browse(1)
            >>> await user.unlink()
        """
        if not self._ids:
            return False
        return await self._unlink()

    # Private CRUD Methods
    async def _browse(self, ids: Optional[Union[int, List[int]]] = None) -> Self:
        """Internal browse implementation."""
        if ids is not None:
            self._ids = self._normalize_ids(ids)
        return cast(Self, self)

    async def _create(self, values: Dict[str, Any]) -> Self:
        """Internal create implementation."""
        adapter = await self._get_adapter()

        # Create model instance with values
        instance = self.__class__(env=self._instance_env)
        for name, value in values.items():
            setattr(instance, name, value)

        async with await adapter.transaction(self.__class__) as txn:
            await self._before_create(values)
            created = await adapter.insert(instance)
            await self._after_create(values)

        return cast(Self, created)

    async def _write(self, values: Dict[str, Any]) -> Self:
        """Internal write implementation."""
        if not self._ids:
            return cast(Self, self)

        adapter = await self._get_adapter()

        # Update values on instance
        for name, value in values.items():
            setattr(self, name, value)

        async with await adapter.transaction(self.__class__) as txn:
            await self._before_write(values)
            updated = await adapter.update(self)
            await self._after_write(values)

        return cast(Self, updated)

    async def _search(self, query: Any = None) -> Self:
        """Internal search implementation."""
        adapter = await self._get_adapter()
        result = await adapter.query(self.__class__).filter(query).all()
        return cast(Self, result)

    async def _unlink(self) -> bool:
        """Internal unlink implementation."""
        if not self._ids:
            return False

        adapter = await self._get_adapter()

        async with await adapter.transaction(cast(Type[T], self.__class__)) as txn:
            await self._before_unlink()
            await adapter.delete(self)
            await self._after_unlink()

        return True

    # Helper Methods
    def _domain_to_query(self, domain: List[Any]) -> DomainExpression[ValueType]:
        """Convert domain to database query."""
        return DomainExpression(domain)

    @classmethod
    async def _validate_values(cls, values: Dict[str, Any]) -> None:
        """Validate field values."""
        for field_name, value in values.items():
            field = cls.__fields__.get(field_name)
            if field is None:
                raise ValidationError(f"Unknown field {field_name}")
            await field.validate(value)

    @classmethod
    def _to_db_values(cls, values: JsonDict) -> JsonDict:
        db_values = {}
        for name, value in values.items():
            field = cls.__fields__.get(name)
            if field is not None:
                db_values[name] = field.to_db(value, "mongo")
        return db_values

    async def _get_adapter(self) -> DatabaseAdapter[T]:
        """Get database adapter for model.

        Returns:
            Database adapter instance
        """
        env = await self.env
        adapter = await env.get_adapter()
        return cast(DatabaseAdapter[T], adapter)

    def _normalize_ids(self, ids: Union[int, List[int]]) -> List[int]:
        """Convert ID or list of IDs to list."""
        if isinstance(ids, int):
            return [ids]
        return list(ids)

    # Lifecycle hooks
    async def _before_create(self, values: Dict[str, Any]) -> None:
        """Hook called before record creation."""
        pass

    async def _after_create(self, values: Dict[str, Any]) -> None:
        """Hook called after record creation."""
        pass

    async def _before_write(self, values: Dict[str, Any]) -> None:
        """Hook called before record update."""
        pass

    async def _after_write(self, values: Dict[str, Any]) -> None:
        """Hook called after record update."""
        pass

    async def _before_unlink(self) -> None:
        """Hook called before record deletion."""
        pass

    async def _after_unlink(self) -> None:
        """Hook called after record deletion."""
        pass

    def __str__(self) -> str:
        """String representation showing model name and record IDs.

        Examples:
            >>> str(users)  # 'User(1,2,3)'
            >>> str(users[0])  # 'User(1)'
        """
        model_name = self.__class__.__name__
        ids = ",".join(str(id) for id in self._ids)
        return f"{model_name}({ids})"

    @classmethod
    async def _internal_create(cls: Type[T], values: JsonDict) -> T:
        adapter = cls._adapter
        async with await adapter.transaction(cls) as transaction:
            db_values = cls._to_db_values(values)
            created = await transaction.insert(db_values)
            return cast(T, created)

    @classmethod
    async def _internal_read(cls: Type[T], ids: List[int]) -> List[T]:
        adapter = cls._adapter
        query = await adapter.query(cls)
        domain = DomainExpression[ValueType]("id", "in", ids)
        query = cast(MongoQuery[T], query).filter(domain)
        return await query.execute_async()

    @classmethod
    async def _internal_update(
        cls: Type[T], ids: List[int], values: JsonDict
    ) -> List[T]:
        adapter = cls._adapter
        async with await adapter.transaction(cls) as transaction:
            db_values = cls._to_db_values(values)
            updated = await transaction.update(ids, db_values)
            return cast(List[T], updated)

    @classmethod
    async def _internal_delete(cls: Type[T], ids: List[int]) -> bool:
        adapter = cls._adapter
        async with await adapter.transaction(cls) as transaction:
            await transaction.delete(ids)
            return True

    async def prefetch_field(self, field: Field[Any]) -> None:
        """Setup prefetching for field.

        Args:
            field: Field to prefetch
        """
        await self._prefetch_field(field)
