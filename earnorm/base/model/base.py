"""Base model implementation for EarnORM.

This module provides the base model class that all database models inherit from.
It implements core functionality for model definition, validation, and persistence.

Key Features:
    1. Model Definition
       - Field declarations
       - Model metadata
       - Inheritance support
       - Abstract models

    2. Field Management
       - Field validation
       - Type conversion
       - Default values
       - Computed fields

    3. CRUD Operations
       - Create records
       - Read/search records
       - Update records
       - Delete records

    4. Query Building
       - Domain expressions
       - Field selection
       - Sorting/ordering
       - Pagination

    5. Transaction Support
       - ACID compliance
       - Nested transactions
       - Savepoints
       - Error handling

    6. Event System
       - Pre/post hooks
       - Validation events
       - Change tracking
       - Custom events

Examples:
    >>> from earnorm.base.model import BaseModel
    >>> from earnorm.fields import StringField, IntegerField, DateTimeField

    >>> # Define model
    >>> class User(BaseModel):
    ...     _name = 'data.user'
    ...
    ...     name = StringField(required=True)
    ...     age = IntegerField()
    ...     email = StringField(unique=True)
    ...     created_at = DateTimeField(readonly=True)
    ...
    ...     async def validate(self):
    ...         '''Custom validation logic'''
    ...         if self.age < 0:
    ...             raise ValueError("Age cannot be negative")
    ...
    ...     @property
    ...     def is_adult(self):
    ...         '''Computed property'''
    ...         return self.age >= 18

    >>> # Create record
    >>> user = await User.create({
    ...     "name": "John Doe",
    ...     "age": 30,
    ...     "email": "john@example.com"
    ... })

    >>> # Search records
    >>> adults = await User.search([
    ...     ("age", ">=", 18),
    ...     ("email", "like", "%@example.com")
    ... ]).order_by("-created_at").limit(10)

    >>> # Update records
    >>> await adults.write({
    ...     "status": "active"
    ... })

    >>> # Delete records
    >>> await adults.unlink()

    >>> # Transaction
    >>> async with User.env.transaction() as txn:
    ...     user = await User.with_env(txn).create({
    ...         "name": "Jane Doe",
    ...         "age": 25
    ...     })
    ...     # Transaction commits if no errors

Classes:
    BaseModel:
        Base class for all database models.

        Class Attributes:
            _name: Model name/collection
            _env: Environment instance
            _fields: Field definitions

        Instance Attributes:
            id: Record ID
            _values: Field values
            _cache: Field cache

        Methods:
            create: Create records
            search: Search records
            write: Update records
            unlink: Delete records

Implementation Notes:
    1. Models use metaclass for initialization
    2. Fields are converted to descriptors
    3. Values are cached per-instance
    4. Transactions use context managers

See Also:
    - earnorm.fields: Field definitions
    - earnorm.database: Database adapters
    - earnorm.env: Environment management
"""

from __future__ import annotations

import logging
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Protocol,
    Self,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

from earnorm.base.database.query.backends.mongo.converter import MongoConverter
from earnorm.base.database.query.interfaces.domain import DomainOperator as Operator
from earnorm.base.database.query.interfaces.domain import LogicalOperator as LogicalOp
from earnorm.base.env import Environment
from earnorm.base.model.meta import ModelMeta
from earnorm.di import Container
from earnorm.exceptions import DatabaseError, ModelNotFoundError, ValidationError
from earnorm.fields import BaseField, RelationField
from earnorm.types import ValueType

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Define type variables
T = TypeVar("T", bound="BaseModel")
V = TypeVar("V")


class ContainerProtocol(Protocol):
    """Protocol for Container class."""

    async def get(self, key: str) -> Any:
        """Get value from container by key."""
        ...

    async def get_environment(self) -> Optional[Environment]:
        """Get environment from container."""
        ...


class FieldsDescriptor:
    """Descriptor for model fields.

    This descriptor handles:
    - Field registration
    - Field inheritance
    - Field access
    """

    def __get__(
        self, instance: Optional["BaseModel"], owner: Type["BaseModel"]
    ) -> Dict[str, BaseField[Any]]:
        """Get fields dictionary.

        Args:
            instance: Model instance
            owner: Model class

        Returns:
            Fields dictionary
        """
        return owner.__dict__.get("__fields__", {})


class BaseModel(metaclass=ModelMeta):
    """Base class for all database models.

    This class provides core functionality for model definition and persistence.
    All database models should inherit from this class.

    Class Attributes:
        _name: Model name/collection (required)
        _env: Environment instance
        _fields: Field definitions
        _model_info: Model metadata

    Instance Attributes:
        id: Record ID
        _values: Field values
        _cache: Field cache
        _modified: Modified fields

    Examples:
        >>> class User(BaseModel):
        ...     _name = 'data.user'
        ...     name = StringField()
        ...     age = IntegerField()

        >>> # Create record
        >>> user = await User.create({
        ...     "name": "John",
        ...     "age": 30
        ... })

        >>> # Access fields
        >>> print(user.name)  # "John"
        >>> print(user.age)  # 30

        >>> # Update fields
        >>> await user.write({
        ...     "age": 31
        ... })

        >>> # Delete record
        >>> await user.unlink()
    """

    # Define slots for memory efficiency and type safety
    __slots__ = (
        "_env",  # Environment instance
        "_name",  # Model name
        "_ids",  # Record IDs
        "_cache",  # Field value cache
    )

    # Class variables (metadata)
    _store: ClassVar[bool] = True
    _name: ClassVar[str]  # Set by metaclass
    _description: ClassVar[Optional[str]] = None
    _table: ClassVar[Optional[str]] = None
    _sequence: ClassVar[Optional[str]] = None
    _skip_default_fields: ClassVar[bool] = False
    _abstract: ClassVar[bool] = False
    _env: Environment  # Environment instance

    # Model fields (will be set by metaclass)
    __fields__ = FieldsDescriptor()

    def __init__(self, env: Optional[Environment] = None) -> None:
        """Initialize model instance.

        This method:
        1. Initializes instance attributes
        2. Sets up field cache
        3. Marks instance as new
        """
        env_instance = env if env is not None else self._get_default_env()
        if not env_instance:
            raise RuntimeError(
                "Environment not initialized. Make sure earnorm.init() is called first"
            )

        # Initialize all slots with default values
        object.__setattr__(self, "_env", env_instance)
        object.__setattr__(self, "_name", self._get_instance_name())
        object.__setattr__(self, "_ids", ())
        object.__setattr__(self, "_cache", {})  # Initialize empty cache dictionary

        if not self._name:
            raise ValueError("Model must define _name attribute")

    @classmethod
    def _get_default_env(cls) -> Optional[Environment]:
        """Get default environment from container."""
        try:
            env = Environment.get_instance()
            if not env._initialized:  # type: ignore
                return None
            return env
        except Exception:
            return None

    @property
    def env(self) -> Environment:
        """Get environment."""
        return self._env

    @property
    def _has_data(self) -> bool:
        """Check if record exists in database."""
        return bool(self._ids)

    async def __getattr__(self, name: str) -> Any:
        """Get attribute value.

        Args:
            name: Attribute name

        Returns:
            Attribute value
        """
        self.env.logger.info(f"Getting attribute {name} for {self._name}")

        # Get field
        field = self.__fields__.get(name)
        if not field:
            self.env.logger.warning(f"Field {name} not found")
            raise AttributeError(
                f"'{self.__class__.__name__}' has no attribute '{name}'"
            )

        self.env.logger.info(f"Found field {name} of type {type(field)}")

        # Get record ID
        record_id = self.id
        self.env.logger.info(f"Getting attribute {name} for {self._name}:{record_id}")

        # Get from cache first
        cache = getattr(self, "_cache", None)
        self.env.logger.info(f"Cache object: {cache}")

        if cache is not None:
            cached = cache.get(name)
            self.env.logger.info(f"Cached value for {name}: {cached}")
            if cached is not None:
                self.env.logger.info(f"Returning cached value for {name}")
                return cached

        # For relation fields, get related records
        if isinstance(field, RelationField):
            self.env.logger.info(
                f"Getting related records for {name} using get_related()"
            )
            value = await field.get_related(self)
            self.env.logger.info(f"Got related records: {value}")

            # Cache the value
            if isinstance(cache, dict):
                cache[name] = value
                self.env.logger.info(f"Cached relation value for {name}")
            return value

        # Direct database fetch using read method
        self.env.logger.info(f"Fetching from database for {name}")
        result = await self.env.adapter.read(self._name, record_id, [name])
        self.env.logger.info(f"Database result: {result}")

        if not result:
            self.env.logger.info(f"No result found for {name}")
            return None

        # Convert value using field object
        value = await field.from_db(result.get(name), self.env.adapter.backend_type)  # type: ignore
        self.env.logger.info(f"Converted value: {value}")

        # Cache and return the value
        if isinstance(cache, dict):
            cache[name] = value
            self.env.logger.info(f"Cached value for {name}")

        return value

    @classmethod
    def _browse(
        cls,
        env: Environment,
        records_or_ids: Union[List[Dict[str, Any]], List[str], Sequence[str]],
    ) -> Self:
        """Create a recordset from a list of records or IDs.

        This method is used internally to create recordsets from database records
        or record IDs. It ensures proper caching and type safety.

        Args:
            env: Environment instance
            records_or_ids: List of record dictionaries or record IDs

        Returns:
            Recordset containing the records

        Examples:
            >>> # From record dictionaries
            >>> records = [{'id': 1, 'name': 'John'}, {'id': 2, 'name': 'Jane'}]
            >>> employees = Employee._browse(env, records)
            >>> for emp in employees:
            ...     print(emp.name)  # Prints: John, Jane

            >>> # From record IDs
            >>> ids = ['1', '2']
            >>> employees = Employee._browse(env, ids)
            >>> for emp in employees:
            ...     print(emp.id)  # Prints: 1, 2
        """
        if not records_or_ids:
            # Return empty recordset
            recordset = cls()
            object.__setattr__(recordset, "_env", env)
            object.__setattr__(recordset, "_cache", {})
            return recordset

        # Create recordset
        recordset = cls()
        object.__setattr__(recordset, "_env", env)
        object.__setattr__(recordset, "_cache", {})

        # Handle record dictionaries
        if isinstance(records_or_ids[0], dict):
            records = cast(List[Dict[str, Any]], records_or_ids)
            object.__setattr__(recordset, "_records", records)
            # Cache records by ID
            for record in records:
                if record.get("id"):
                    recordset._cache[str(record["id"])] = record
        # Handle record IDs
        else:
            ids = [str(id_) for id_ in records_or_ids]
            object.__setattr__(recordset, "_ids", tuple(ids))

        return recordset

    @classmethod
    async def browse(cls, ids: Union[str, List[str]]) -> Self:
        """Browse records by IDs.

        Args:
            ids: Record ID or list of record IDs

        Returns:
            Self: A recordset containing the records with the given IDs
        """
        id_list = [ids] if isinstance(ids, str) else ids
        return cls._browse(cls._env, id_list)

    @classmethod
    async def search(
        cls,
        domain: Optional[
            List[Union[Tuple[str, Operator, ValueType], LogicalOp]]
        ] = None,
        offset: int = 0,
        limit: Optional[int] = None,
        order: Optional[str] = None,
    ) -> Self:
        """Search for records matching domain.

        Args:
            domain: Domain expression
            offset: Number of records to skip
            limit: Maximum number of records to return
            order: Sort order (field_name asc/desc)

        Returns:
            Recordset containing matching records

        Examples:
            >>> # Search with domain expression
            >>> users = await User.search(
            ...     domain=[("age", ">", 18), "&", ("status", "=", "active")]
            ... )

            >>> # Search with limit and offset
            >>> recent_users = await User.search(
            ...     order='create_date desc',
            ...     limit=10
            ... )
        """
        if not cls._env:
            raise RuntimeError("Environment not initialized")

        try:
            # Convert domain to MongoDB query using MongoConverter
            filter_dict: Dict[str, Any] = {}
            if domain:
                converter = MongoConverter()
                filter_dict = converter.convert(cast(List[Any], list(domain)))

            # Search records using adapter
            ids = await cls._env.adapter.search(
                store=str(cls._name),
                filter=filter_dict,
                fields=["_id"],  # Only get IDs
                offset=offset,
                limit=limit,
                order=order,
            )

            # Return recordset using browse
            return await cls.browse(ids)

        except ValueError as e:
            cls._env.logger.error("Invalid search parameters: %s", str(e))
            raise ValidationError(
                field_name="domain",
                code="invalid_domain",
                message=f"Invalid search parameters: {e}",
            ) from e

        except DatabaseError as e:
            cls._env.logger.error("Database error during search: %s", str(e))
            raise DatabaseError(
                f"Search failed: {e}", backend=cls._env.adapter.backend_type
            ) from e

        except Exception as e:
            cls._env.logger.error("Unexpected error during search: %s", str(e))
            raise RuntimeError(f"Search failed unexpectedly: {e}") from e

    async def write(self, vals: Dict[str, Any]) -> Self:
        """Update records with values.

        This method:
        1. Validates values before update
        2. Converts values to database format
        3. Updates records in database
        4. Invalidates cache for updated fields

        Args:
            vals: Values to update

        Returns:
            Self: Updated recordset

        Raises:
            DatabaseError: If update fails

        Examples:
            >>> user = await User.browse("123")
            >>> await user.write({"name": "John"})  # Updates and invalidates cache
        """
        if not self._ids:
            return self

        try:
            # Convert values to database format
            db_vals = await self._convert_to_db(vals)

            # Update records using IDs
            await self._env.adapter.update(
                store=str(type(self)._name),
                ids=list(self._ids),
                values=db_vals,
            )

            # Clear cache for each updated field
            for field_name in vals.keys():
                self._clear_cache(str(field_name))

            return self

        except Exception as e:
            logger.error(f"Failed to write values: {str(e)}", exc_info=True)
            raise DatabaseError(
                message=str(e), backend=self._env.adapter.backend_type
            ) from e

    @property
    def id(self) -> str:
        """Get record ID."""
        return self._ids[0] if self._ids else ""

    @id.setter
    def id(self, value: str) -> None:
        """Set record ID."""
        self._ids = (value,)

    @property
    def ids(self) -> Tuple[str, ...]:
        """Get record IDs."""
        return self._ids

    def __iter__(self):
        """Iterate through records.

        Returns:
            Iterator of recordsets, each containing a single record.

        Examples:
            >>> users = await User.search([("age", ">", 18)])
            >>> for user in users:  # No need for await
            ...     print(user.name)
        """
        return iter(self._browse(self._env, (id,)) for id in self._ids)

    def __len__(self):
        """Get number of records."""
        return len(self._ids)

    def __getitem__(self, key: Union[int, slice]) -> Self:
        """Get record by index."""
        if isinstance(key, slice):
            return self._browse(self._env, self._ids[key])
        return self._browse(self._env, (self._ids[key],))

    @overload
    @classmethod
    async def create(
        cls,
        values: None = None,
    ) -> Self: ...

    @overload
    @classmethod
    async def create(
        cls,
        values: Dict[str, Any],
    ) -> Self: ...

    @overload
    @classmethod
    async def create(
        cls,
        values: List[Dict[str, Any]],
    ) -> Self: ...

    @classmethod
    async def create(
        cls, values: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None
    ) -> Self:
        """Create one or multiple records.

        This method creates records in the database and returns a recordset containing
        all created record IDs. It supports three modes:
        1. Empty recordset (values=None)
        2. Single record (values=dict)
        3. Multiple records (values=list of dicts)

        Args:
            values: Values to create records with. Can be:
                   - None: Create empty recordset
                   - Dict: Create single record
                   - List[Dict]: Create multiple records

        Returns:
            Self: A recordset containing all created record IDs

        Raises:
            DatabaseError: If creation fails

        Examples:
            >>> # Create empty recordset
            >>> empty = await User.create()
            >>>
            >>> # Create single record
            >>> user = await User.create({
            ...     "name": "John",
            ...     "email": "john@example.com"
            ... })
            >>>
            >>> # Create multiple records
            >>> users = await User.create([
            ...     {"name": "Alice", "email": "alice@example.com"},
            ...     {"name": "Bob", "email": "bob@example.com"}
            ... ])
            >>> # Update all created records
            >>> await users.write({"status": "active"})
        """
        if values is None:
            values = {}

        try:
            # Get environment
            env = await cls._get_env()

            # Convert values to database format
            if isinstance(values, list):
                # Create multiple records
                db_vals_list: List[Dict[str, Any]] = []
                for vals in values:
                    db_vals = await cls._convert_to_db(vals)
                    db_vals_list.append(db_vals)

                # Create records and get IDs
                record_ids = await cls._env.adapter.create(
                    store=str(cls._name),
                    values=db_vals_list,
                )

                # Return single recordset with all IDs
                return cls._browse(env, [str(rid) for rid in record_ids])
            else:
                # Create single record
                db_vals = await cls._convert_to_db(values)
                record_id = await cls._env.adapter.create(
                    store=str(cls._name),
                    values=db_vals,
                )
                return cls._browse(env, [str(record_id)])

        except Exception as e:
            logger.error("Failed to create records: %s", str(e), exc_info=True)
            raise DatabaseError(
                message=str(e), backend=cls._env.adapter.backend_type
            ) from e

    async def to_dict(
        self, fields: Optional[List[str]] = None, exclude: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Convert model to dictionary.

        This method converts the current record to a dictionary format.
        It handles:
        1. Field selection and exclusion
        2. Type conversion from database to Python
        3. Error handling for each field
        4. Cache management

        Args:
            fields: List of field names to include (None for all fields)
            exclude: List of field names to exclude

        Returns:
            Dict[str, Any]: Dictionary containing field values

        Examples:
            >>> user = await User.browse("123")
            >>> # Get all fields
            >>> data = await user.to_dict()
            >>> print(data["name"])  # "John"
            >>>
            >>> # Get specific fields
            >>> data = await user.to_dict(fields=["name", "email"])
            >>> print(data.keys())  # ["name", "email"]
            >>>
            >>> # Exclude fields
            >>> data = await user.to_dict(exclude=["password"])
            >>> print("password" in data)  # False
        """
        result: Dict[str, Any] = {}

        try:
            # Determine fields to convert
            if not fields:
                fields = list(self.__fields__.keys())
            if exclude:
                fields = [f for f in fields if f not in exclude]

            # Get record data from database
            if self._ids:
                record_id = self._ids[0]
                db_result = await self._env.adapter.read(
                    store=str(self._name), id_or_ids=record_id, fields=fields
                )

                if isinstance(db_result, dict):
                    # Convert each field
                    for field_name in fields:
                        try:
                            if field_name in self.__fields__:
                                field_obj = self.__fields__[field_name]
                                db_value = db_result.get(field_name)
                                value = await field_obj.from_db(
                                    db_value, self._env.adapter.backend_type
                                )
                                result[field_name] = value
                        except Exception as e:
                            self.env.logger.error(
                                f"Error converting field {field_name}: {str(e)}"
                            )
                            result[field_name] = None

        except Exception as e:
            self.env.logger.error(f"Error converting record to dict: {str(e)}")
            # Return empty dict on error
            return {}

        return result

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Update model from dictionary."""
        for name, value in data.items():
            if name in self.__fields__ and not self.__fields__[name].readonly:
                setattr(self, name, value)

    @classmethod
    async def _get_env(cls) -> Environment:
        """Get environment instance from container.

        Returns:
            Environment: Environment instance from container

        Raises:
            RuntimeError: If environment is not found in container
        """
        try:
            container = cast(ContainerProtocol, Container())
            env = await container.get("environment")
            if not isinstance(env, Environment):
                # Try get default environment
                env = cls._get_default_env()
                if not env:
                    raise RuntimeError("Environment not found in container")
            return env
        except Exception as e:
            # Try get default environment
            env = cls._get_default_env()
            if not env:
                raise RuntimeError(f"Failed to get environment: {str(e)}")
            return env

    @classmethod
    def _get_instance_name(cls) -> str:
        """Get instance name from class.

        Returns:
            str: Instance name
        """
        return str(getattr(cls, "_name", ""))

    def _set_instance_name(self, name: str) -> None:
        """Set instance name.

        Args:
            name: Instance name
        """
        object.__setattr__(self, "_name", name)

    @classmethod
    async def _convert_to_db(cls, vals: Dict[str, Any]) -> Dict[str, Any]:
        """Convert values to database format.

        This method converts Python values to database-compatible format.
        It handles:
        1. Field type conversion
        2. ID conversion
        3. Special field handling
        4. Auto fields (created_at, updated_at)
        5. System fields validation and processing

        Args:
            vals: Values to convert

        Returns:
            Dict with converted values

        Examples:
            >>> user = User()
            >>> db_vals = await user._convert_to_db({"age": 25})
            >>> print(db_vals)  # {"age": 25, "updated_at": "2024-02-06T05:17:43.715Z"}
        """
        db_vals: Dict[str, Any] = {}
        backend = cls._env.adapter.backend_type

        # Convert fields that are in vals
        for name, value in vals.items():
            if name in cls.__fields__:
                field = cls.__fields__[name]
                # Skip readonly and system fields unless explicitly allowed
                if not field.readonly or getattr(field, "system", False):
                    db_vals[name] = await field.to_db(value, backend)

        # Handle system fields and auto fields
        for name, field in cls.__fields__.items():
            if name not in db_vals and getattr(field, "system", False):
                # Handle auto timestamp fields
                if getattr(field, "auto_now_add", False) or getattr(
                    field, "auto_now", False
                ):
                    from earnorm.fields.primitive import DateTimeField

                    if isinstance(field, DateTimeField):
                        db_vals[name] = await field.to_db(None, backend)

        return db_vals

    async def unlink(self) -> bool:
        """Delete records from database.

        This method deletes the current recordset from the database.
        It handles:
        1. Building delete query with proper filters
        2. Executing delete operation
        3. Clearing cache and recordset data
        4. Error handling and logging

        Returns:
            bool: True if records were deleted successfully, False otherwise

        Raises:
            DatabaseError: If deletion fails due to database error

        Examples:
            >>> # Delete single record
            >>> user = await User.browse("123")
            >>> success = await user.unlink()
            >>>
            >>> # Delete multiple records
            >>> users = await User.search([("active", "=", False)])
            >>> success = await users.unlink()
        """
        try:
            if not self._ids:
                return True

            # Execute delete operation using IDs
            result = await self._env.adapter.delete(
                store=str(self._name),
                ids=list(self._ids),
            )

            # Check deletion count
            deleted_count = result or 0
            if deleted_count != len(self._ids):
                self.env.logger.warning(
                    f"Deleted {deleted_count} records out of {len(self._ids)}"
                )

            # Clear cache before clearing recordset data
            self._clear_cache()  # Clear all cache when record is deleted

            # Clear recordset data
            self._ids = ()

            return True

        except Exception as e:
            self.env.logger.error(f"Failed to delete {self._name} records: {str(e)}")
            raise DatabaseError(
                message=f"Failed to delete records: {str(e)}",
                backend=self._env.adapter.backend_type,
            ) from e

    def ensure_one(self) -> Self:
        """Ensure recordset contains exactly one record.

        This method validates that the current recordset contains exactly one record.
        It is useful when you expect a single record from a search or browse operation.

        Returns:
            Self: The current recordset if it contains exactly one record

        Raises:
            ValueError: If recordset contains zero or multiple records

        Examples:
            >>> # Get single user by email
            >>> user = await User.search([("email", "=", "john@example.com")]).ensure_one()
            >>> print(user.name)
            >>>
            >>> # Will raise ValueError if no user found
            >>> user = await User.search([("email", "=", "notfound@example.com")]).ensure_one()
            >>>
            >>> # Will raise ValueError if multiple users found
            >>> users = await User.search([("age", ">", 18)]).ensure_one()
        """
        if len(self._ids) == 0:
            raise ValueError(f"No {self._name} record found")
        if len(self._ids) > 1:
            raise ValueError(
                f"Expected single {self._name} record, got {len(self._ids)} records"
            )
        return self

    def _clear_cache(self, field_name: Optional[str] = None) -> None:
        """Clear cached values.

        Args:
            field_name: Name of field to clear, or None to clear all
        """
        if not hasattr(self, "_cache"):
            object.__setattr__(self, "_cache", {})
        if field_name:
            self._cache.pop(field_name, None)
        else:
            self._cache.clear()

    def __init_subclass__(cls, **kwargs):  # type: ignore
        """Initialize model subclass.

        This method is called when a model class is defined.
        It handles:
        - Model registration via ModelMeta
        - Field setup
        - Relationship resolution
        """
        super().__init_subclass__(**kwargs)

        # Setup fields and track dependencies
        for name, field in cls.__dict__.items():
            if isinstance(field, RelationField):
                # Setup field
                field.setup(name, cls._name)  # type: ignore

    @classmethod
    async def get_model(cls, name: str) -> Optional[Type["BaseModel"]]:
        """Get model class by name.

        Args:
            name: Model name

        Returns:
            Optional[Type[BaseModel]]: Model class if found, None otherwise
        """
        env = cls._env
        return await env.get_model(name)  # type: ignore

    @classmethod
    async def get_model_or_raise(cls, name: str) -> Type["BaseModel"]:
        """Get model class by name or raise error.

        Args:
            name: Model name

        Returns:
            Type[BaseModel]: Model class

        Raises:
            ModelNotFoundError: If model is not found
        """
        model = await cls.get_model(name)
        if model is None:
            raise ModelNotFoundError(f"Model '{name}' not found", field_name=name)
        return model

    def _get_cache(self, field_name: str) -> Optional[Any]:
        """Get cached value for a field.

        Args:
            field_name: Name of the field

        Returns:
            Cached value or None if not cached
        """
        if not hasattr(self, "_cache"):
            object.__setattr__(self, "_cache", {})
        return self._cache.get(field_name)  # type: ignore

    def _set_cache(self, field_name: str, value: Any) -> None:
        """Set cached value for a field.

        Args:
            field_name: Name of the field
            value: Value to cache
        """
        if not hasattr(self, "_cache"):
            object.__setattr__(self, "_cache", {})
        self._cache[field_name] = value
