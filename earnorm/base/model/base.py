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
    AsyncContextManager,
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

from earnorm import api
from earnorm.base.database.query.core.query import BaseQuery
from earnorm.base.database.query.interfaces.domain import DomainExpression
from earnorm.base.database.query.interfaces.domain import DomainOperator as Operator
from earnorm.base.database.query.interfaces.domain import LogicalOperator as LogicalOp
from earnorm.base.database.query.interfaces.operations.aggregate import AggregateProtocol as AggregateQuery
from earnorm.base.database.query.interfaces.operations.join import JoinProtocol as JoinQuery
from earnorm.base.database.transaction.base import Transaction
from earnorm.base.env import Environment
from earnorm.base.model.meta import ModelMeta
from earnorm.constants import FIELD_MAPPING
from earnorm.di import Container
from earnorm.exceptions import DatabaseError, FieldValidationError, ModelNotFoundError
from earnorm.fields import BaseField, RelationField
from earnorm.types import ValueType
from earnorm.types.models import ModelProtocol

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Define type variables
T = TypeVar("T")
V = TypeVar("V")


class ContainerProtocol(Protocol):
    """Protocol for Container class."""

    async def get(self, key: str) -> Any:
        """Get value from container by key."""
        ...

    async def get_environment(self) -> Optional[Environment]:
        """Get environment from container."""
        ...


class LoggerProtocol(Protocol):
    """Protocol for logger interface."""

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def error(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None: ...
    def info(self, msg: str, *args: Any, **kwargs: Any) -> None: ...


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
    logger: LoggerProtocol = logging.getLogger(__name__)

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
        self.logger.info(f"Getting attribute {name} for {self._name}")

        # Get field
        field = self.__fields__.get(name)
        if not field:
            self.logger.warning(f"Field {name} not found")
            raise AttributeError(
                f"'{self.__class__.__name__}' has no attribute '{name}'"
            )

        self.logger.info(f"Found field {name} of type {type(field)}")

        # Get record ID
        record_id = self.id
        self.logger.info(f"Getting attribute {name} for {self._name}:{record_id}")

        # Get from cache first
        cache = getattr(self, "_cache", None)
        self.logger.info(f"Cache object: {cache}")

        if cache is not None:
            cached = cache.get(name)
            self.logger.info(f"Cached value for {name}: {cached}")
            if cached is not None:
                self.logger.info(f"Returning cached value for {name}")
                return cached

        # For relation fields, get related records
        if isinstance(field, RelationField):
            self.logger.info(f"Getting related records for {name} using get_related()")
            value = await field.get_related(self)
            self.logger.info(f"Got related records: {value}")

            # Cache the value
            if isinstance(cache, dict):
                cache[name] = value
                self.logger.info(f"Cached relation value for {name}")
            return value

        # Direct database fetch using read method
        self.logger.info(f"Fetching from database for {name}")
        result = await self.env.adapter.read(self._name, record_id, [name])
        self.logger.info(f"Database result: {result}")

        if not result:
            self.logger.info(f"No result found for {name}")
            return None

        # Convert value using field object
        value = await field.from_db(result.get(name), self.env.adapter.backend_type)
        self.logger.info(f"Converted value: {value}")

        # Cache and return the value
        if isinstance(cache, dict):
            cache[name] = value
            self.logger.info(f"Cached value for {name}")

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
    async def _where_calc(
        cls, domain: Sequence[Union[Tuple[str, str, Any], str]]
    ) -> BaseQuery[ModelProtocol]:
        """Build query from domain."""
        query = await cls._env.adapter.query(cast(Type[ModelProtocol], cls))
        query.reset()
        if domain:
            expr = DomainExpression(cast(List[Any], list(domain)))
            query = query.filter(expr.to_list())
        return cast(BaseQuery[ModelProtocol], query)

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
        """Search records matching domain.

        Args:
            domain: Search domain expression
            offset: Number of records to skip
            limit: Maximum number of records to return
            order: Order by expression

        Returns:
            Self: Recordset containing matching records

        Raises:
            DatabaseError: If search operation fails
        """
        try:
            # Log search parameters
            logger.info(
                "Searching %s with domain=%s, offset=%s, limit=%s, order=%s",
                cls._name,
                domain,
                offset,
                limit,
                order,
            )

            # Calculate where clause
            query = await cls._where_calc(domain or [])
            logger.info("Generated query: %s", query)

            # Add options
            if offset:
                query.offset(offset)
            if limit is not None:
                query.limit(limit)
            if order:
                query.order_by(order)

            # Get backend type and field mapping
            backend_type = cls._env.adapter.backend_type
            id_field = FIELD_MAPPING.get(backend_type, {}).get("id", "id")
            logger.info(
                "Using backend %s with id_field %s",
                backend_type,
                id_field,
            )

            # Select ID field based on backend
            query.select(id_field)

            # Execute query and get raw data
            result = await query.to_raw_data()
            logger.info("Query raw result: %s", result)

            # Extract IDs using both id and _id fields
            ids = []
            for doc in result:
                if id_field in doc:
                    ids.append(str(doc[id_field]))  # type: ignore
                elif "id" in doc:
                    ids.append(str(doc["id"]))  # type: ignore
            logger.info("Extracted IDs: %s", ids)  # type: ignore

            return cls._browse(cls._env, tuple(ids))  # type: ignore

        except Exception as e:
            logger.error("Search failed: %s", str(e), exc_info=True)
            raise DatabaseError(
                message=f"Search failed: {str(e)}",
                backend=cls._env.adapter.backend_type,
            ) from e

    @api.multi
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
            # Validate values before update
            await self._validate_write(vals)

            # Convert values to database format
            db_vals = await self._convert_to_db(vals)

            # Create domain expression for id filter
            domain_expr = DomainExpression([("id", "in", list(self._ids))])

            # Update records
            await self._env.adapter.update(
                cast(Type[ModelProtocol], type(self)),
                domain_expr,
                db_vals,
            )

            # Clear cache for updated fields
            self._clear_cache(list(vals.keys()))  # type: ignore

            return self

        except Exception as e:
            logger.error(f"Failed to write values: {str(e)}", exc_info=True)
            raise DatabaseError(
                message=str(e), backend=self._env.adapter.backend_type
            ) from e

    async def _validate_write(self, vals: Dict[str, Any]) -> None:
        """Validate record update.

        This method performs the following validations:
                1. Check if records exist
                2. Check field types and constraints
                3. Check unique constraints
                4. Apply custom validation rules

                Args:
                    vals: Field values to validate

                Raises:
                    FieldValidationError: If validation fails
                    ValidationError: If custom validation fails
                    ValueError: If records don't exist
        """
        logger.info("Validating write values: %s", vals)

        try:
            if not self._ids:
                raise ValueError("No records to update")

            # Check if records exist in database
            domain_tuple = cast(
                Tuple[str, Operator, ValueType],
                ("id", "in", list(self._ids)),
            )
            query = await self._where_calc([domain_tuple])
            count = await query.count()
            if count != len(self._ids):
                raise ValueError("Some records do not exist")

            # Create validation context
            context = {
                "model": self,
                "env": self._env,
                "operation": "write",
                "values": vals,
            }

            # Validate field values
            for name, value in vals.items():
                if name not in self.__fields__:
                    raise FieldValidationError(
                        message=f"Field '{name}' does not exist",
                        field_name=name,
                        code="field_not_found",
                    )
                field = self.__fields__[name]
                if field.readonly:
                    raise FieldValidationError(
                        message=f"Field '{name}' is readonly",
                        field_name=name,
                        code="field_readonly",
                    )
                try:
                    field_context = {**context, "field_name": name}
                    await field.validate(value, context=field_context)
                except ValueError as e:
                    raise FieldValidationError(
                        message=str(e),
                        field_name=name,
                        code="field_validation_error",
                    ) from e

        except Exception as e:
            logger.error("Validation failed: %s", str(e))
            raise

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

    @classmethod
    async def aggregate(cls) -> AggregateQuery[ModelProtocol]:
        """Create aggregate query.

        Returns:
            AggregateQuery: Aggregate query builder
        """
        query = await cls._env.adapter.get_aggregate_query(
            cast(Type[ModelProtocol], cls)
        )
        return query

    @classmethod
    async def join(
        cls,
        model: str,
        on: Dict[str, str],
        join_type: str = "inner",
    ) -> JoinQuery[ModelProtocol, Any]:
        """Create join query.

        Args:
            model: Model to join with
            on: Join conditions {local_field: foreign_field}
            join_type: Join type (inner, left, right)

        Returns:
            Join query builder
        """
        logger.info(
            "Creating join query for model %s with %s",
            cls._name,
            model,
        )
        query = await cls._env.adapter.get_join_query(cast(Type[ModelProtocol], cls))
        return query.join(model, on, join_type)

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
                    cast(Type[ModelProtocol], cls),
                    db_vals_list,
                )

                # Return single recordset with all IDs
                return cls._browse(env, [str(rid) for rid in record_ids])
            else:
                # Create single record
                db_vals = await cls._convert_to_db(values)
                record_id = await cls._env.adapter.create(
                    cast(Type[ModelProtocol], cls),
                    db_vals,
                )
                return cls._browse(env, [str(record_id)])

        except Exception as e:
            logger.error("Failed to create records: %s", str(e), exc_info=True)
            raise DatabaseError(
                message=str(e), backend=cls._env.adapter.backend_type
            ) from e

    @api.one
    async def to_dict(
        self, fields: Optional[List[str]] = None, exclude: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Convert model to dictionary."""
        result: Dict[str, Any] = {}

        if not fields:
            fields = list(self.__fields__.keys())

        logger.info(f"Getting fields: {self.__fields__}")

        for field in fields:
            try:
                # Direct database fetch for each field
                if self._ids:
                    record_id = self._ids[0]
                    db_result = await self._env.adapter.read(
                        cast(Type[ModelProtocol], type(self)), record_id, [field]
                    )
                    if db_result:
                        field_obj = self.__fields__[field]
                        value = await field_obj.from_db(
                            db_result.get(field), self._env.adapter.backend_type
                        )
                        result[field] = value
                    else:
                        result[field] = None
                else:
                    result[field] = None

            except Exception as e:
                logger.error(f"Error converting field {field}: {str(e)}")
                result[field] = None

        return result

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Update model from dictionary."""
        for name, value in data.items():
            if name in self.__fields__ and not self.__fields__[name].readonly:
                setattr(self, name, value)

    async def with_transaction(
        self,
    ) -> AsyncContextManager[Transaction[ModelProtocol]]:
        """Get transaction context manager.

        Returns:
            Transaction context manager
        """
        return await self._env.adapter.transaction(
            model_type=cast(Type[ModelProtocol], type(self))
        )

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

    async def _create(self, vals: Dict[str, Any]) -> None:
        """Create record in database.

        Args:
            vals: Values to create record with
        """
        # Convert values to database format
        db_vals = await self._convert_to_db(vals)

        # Create record in database
        record_id = await self._env.adapter.create(
            cast(Type[ModelProtocol], type(self)), db_vals
        )

        # Set record ID
        self._ids = (record_id,)

    @api.multi
    async def unlink(self) -> bool:
        """Delete record from database.

        Returns:
            True if record was deleted
        """
        try:
            await self._unlink()
            return True
        except Exception as e:
            logger.error(f"Failed to delete {self._name} records: {str(e)}")
            return False

    async def _unlink(self) -> None:
        """Delete records from database."""
        try:
            # Build delete query
            query = await self._where_calc([("id", "in", list(self._ids))])

            # Execute delete
            result = cast(Dict[str, int], await query.delete())
            deleted_count = result.get("deleted_count", 0)

            if deleted_count != len(self._ids):
                self.logger.warning(
                    f"Deleted {deleted_count} records out of {len(self._ids)}"
                )

            # Clear cache before clearing recordset data
            self._clear_cache()  # Clear all cache when record is deleted

            # Clear recordset data
            self._ids = ()

        except Exception as e:
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

    @classmethod
    async def read(
        cls, record_id: str, fields: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Read a single record.

        Args:
            record_id: Record ID to read
            fields: Optional list of fields to read

        Returns:
            Dict containing record data if found, None otherwise

        Raises:
            DatabaseError: If read operation fails
        """
        try:
            return await cls._env.adapter.read(
                cast(Type[ModelProtocol], cls),
                record_id,
                fields,
            )
        except Exception as e:
            logger.error("Failed to read record: %s", str(e), exc_info=True)
            raise DatabaseError(
                message=str(e), backend=cls._env.adapter.backend_type
            ) from e

    @classmethod
    async def update(cls, record_id: str, values: Dict[str, Any]) -> int:
        """Update a single record.

        Args:
            record_id: Record ID to update
            values: Values to update

        Returns:
            Number of records updated

        Raises:
            DatabaseError: If update fails
        """
        try:
            return await cls._env.adapter.update(
                cast(Type[ModelProtocol], cls),
                {"id": record_id},
                values,
            )
        except Exception as e:
            logger.error("Failed to update record: %s", str(e), exc_info=True)
            raise DatabaseError(
                message=str(e), backend=cls._env.adapter.backend_type
            ) from e

    @classmethod
    async def delete(cls, record_id: str) -> Optional[int]:
        """Delete a single record.

        Args:
            record_id: Record ID to delete

        Returns:
            Number of records deleted

        Raises:
            DatabaseError: If deletion fails
        """
        try:
            return await cls._env.adapter.delete(
                cast(Type[ModelProtocol], cls),
                {"id": record_id},
            )
        except Exception as e:
            logger.error("Failed to delete record: %s", str(e), exc_info=True)
            raise DatabaseError(
                message=str(e), backend=cls._env.adapter.backend_type
            ) from e

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
