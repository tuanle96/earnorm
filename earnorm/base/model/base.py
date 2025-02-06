"""Base model class for database records.

This module provides the base model class for all database models in EarnORM.
It includes features such as:

1. Field validation
2. CRUD operations
3. Multiple database support
4. Lazy loading
5. Event system

Examples:
    >>> # Define a model
    >>> class User(BaseModel):
    ...     _name = "users"
    ...     name = StringField(required=True)
    ...     age = IntegerField()
    ...     email = EmailField(unique=True)
    ...     status = SelectField(choices=["active", "inactive"])
    ...     created_at = DateTimeField(readonly=True)
    ...     updated_at = DateTimeField(readonly=True)

    >>> # Create a record
    >>> user = await User.create({
    ...     "name": "John Doe",
    ...     "age": 30,
    ...     "email": "john@example.com",
    ...     "status": "active"
    ... })

    >>> # Search records
    >>> users = await User.search([
    ...     ("age", ">=", 18),
    ...     ("status", "=", "active")
    ... ]).limit(10).execute()

    >>> # Update records
    >>> await users.write({
    ...     "status": "inactive"
    ... })

    >>> # Delete records
    >>> await users.unlink()

    >>> # Aggregate queries
    >>> stats = await User.aggregate()\\
    ...     .group_by("status")\\
    ...     .count("total")\\
    ...     .avg("age", "avg_age")\\
    ...     .having(total__gt=100)\\
    ...     .execute()

    >>> # Join queries
    >>> posts = await User.join(
    ...     "posts",
    ...     on={"id": "user_id"},
    ...     join_type="left"
    ... ).select(
    ...     "name",
    ...     "posts.title",
    ...     "posts.content"
    ... ).where(
    ...     posts__likes__gt=10
    ... ).execute()

    >>> # Group queries
    >>> order_stats = await Order.group()\\
    ...     .by("status", "category")\\
    ...     .count("total_orders")\\
    ...     .sum("amount", "total_amount")\\
    ...     .having(total_orders__gt=10)\\
    ...     .execute()
"""

import logging
from datetime import UTC, datetime
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncContextManager,
    Callable,
    ClassVar,
    Dict,
    List,
    Optional,
    Protocol,
    Self,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
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
from earnorm.base.model.descriptors import FieldsDescriptor
from earnorm.base.model.meta import ModelMeta
from earnorm.constants import FIELD_MAPPING
from earnorm.di import Container
from earnorm.exceptions import DatabaseError, FieldValidationError, ValidationError
from earnorm.fields.base import BaseField
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


class BaseModel(metaclass=ModelMeta):
    """Base model class with auto env injection.

    This class provides:
    - Automatic env injection from container
    - Basic CRUD operations
    - Field validation and type checking
    - Implementation of ModelProtocol methods

    Examples:
        >>> class User(BaseModel):
        ...     _name = "user"
        ...     name = fields.StringField()
        >>> user = User()  # env auto-injected
        >>> new_user = await user.create({"name": "John"})
    """

    # Define slots for memory efficiency and type safety
    __slots__ = (
        "_env",  # Environment instance
        "_name",  # Model name
        "_ids",  # Record IDs
        "_prefetch_ids",  # IDs for prefetching
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
    # id field is defined in ModelMeta.DEFAULT_FIELDS as StringField

    def __init__(self, env: Optional[Environment] = None) -> None:
        """Initialize base model."""
        env_instance = env if env is not None else self._get_default_env()
        if not env_instance:
            raise RuntimeError(
                "Environment not initialized. Make sure earnorm.init() is called first"
            )
        object.__setattr__(self, "_env", env_instance)
        object.__setattr__(self, "_name", self._get_instance_name())
        object.__setattr__(self, "_ids", ())
        object.__setattr__(self, "_prefetch_ids", ())

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
        """Get attribute value, loading from cache or database if needed."""
        logger.info(f"Getting attribute {name} for {self._name}")
        try:
            # Check if field exists
            if name not in self.__fields__:
                logger.info(f"Field '{name}' not found in {self._name}")
                raise AttributeError(
                    f"'{self.__class__.__name__}' has no attribute '{name}'"
                )

            # Get first record ID
            if not self._ids:
                logger.info(f"No records in recordset for {self._name}")
                return None

            record_id = self._ids[0]
            logger.info(f"Getting attribute {name} for {self._name}:{record_id}")

            # Check cache first
            if self._env.is_field_loaded(self._name, record_id, name):
                value = self._env.get_field_value(self._name, record_id, name)
                logger.info(
                    f"Got cached value {value} for {name} of {self._name}:{record_id}"
                )
                return value

            # Load from database
            logger.info(
                f"Cache miss for {name} of {self._name}:{record_id}, loading from database"
            )
            await self._prefetch_records([name])

            value = self._env.get_field_value(self._name, record_id, name)
            logger.info(
                f"Loaded value {value} for {name} of {self._name}:{record_id} from database"
            )
            return value

        except Exception as e:
            logger.error(f"Failed to get attribute {name} for {self._name}: {str(e)}")
            raise

    async def _get_field_value(self, field: str) -> Any:
        """Get field value from cache or database."""
        if not self._ids:
            return None

        record_id = self._ids[0]

        # Check cache
        if self._env.is_field_loaded(self._name, record_id, field):
            return self._env.get_field_value(self._name, record_id, field)

        # Load from database
        await self._prefetch_records([field])
        return self._env.get_field_value(self._name, record_id, field)

    @classmethod
    def _browse(
        cls,
        env: Environment,
        ids: Sequence[str],
        prefetch_ids: Sequence[str] = (),
    ) -> Self:
        """Create recordset instance."""
        records = object.__new__(cls)

        # Initialize required attributes
        object.__setattr__(records, "_env", env)
        object.__setattr__(records, "_name", cls._get_instance_name())
        object.__setattr__(records, "_ids", tuple(ids))
        object.__setattr__(records, "_prefetch_ids", tuple(prefetch_ids))
        return records

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
        """Update record with values.

        Args:
            vals: Field values to update

        Returns:
            Updated record
        """
        await self._write(vals)
        return self

    async def _write(self, vals: Dict[str, Any]) -> None:
        """Update record in database.

        Args:
            vals: Field values to update

        Raises:
            FieldValidationError: If validation fails
            DatabaseError: If database operation fails
        """
        # Validate values
        await self._validate_write(vals)

        # Convert values to database format
        db_vals: Dict[str, Any] = {}
        backend = self._env.adapter.backend_type

        # Convert user-provided values
        for name, value in vals.items():
            field = self.__fields__[name]
            if not field.readonly:  # Skip readonly fields
                db_vals[name] = await field.to_db(value, backend)

        # Add system fields
        now = datetime.now(UTC)
        db_vals["updated_at"] = now

        # Update records
        try:
            # Convert to model objects
            models = [
                self._browse(self._env, [id], self._prefetch_ids) for id in self._ids
            ]

            # Update each model
            for model in models:
                for field, value in db_vals.items():
                    setattr(model, field, value)

            # Bulk update
            await self._env.adapter.update_many(cast(List[ModelProtocol], models))

        except Exception as e:
            raise DatabaseError(
                message=f"Failed to update records: {e}", backend=backend
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
        logger.debug("Validating write values: %s", vals)

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

            # Validate field values
            for name, value in vals.items():
                if name not in self.__fields__:
                    raise FieldValidationError(
                        message=f"Field '{name}' does not exist",
                        field_name=name,
                    )
                field = self.__fields__[name]
                if field.readonly:
                    raise FieldValidationError(
                        message=f"Field '{name}' is readonly",
                        field_name=name,
                    )
                try:
                    await field.validate(value)
                except ValueError as e:
                    raise FieldValidationError(
                        message=str(e),
                        field_name=name,
                    ) from e

        except Exception as e:
            logger.error("Validation failed: %s", str(e))
            raise

    @property
    def id(self) -> str:
        """Get record ID."""
        return self._ids[0] if self._ids else ""

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
        logger.debug(
            "Creating join query for model %s with %s",
            cls._name,
            model,
        )
        query = await cls._env.adapter.get_join_query(cast(Type[ModelProtocol], cls))
        return query.join(model, on, join_type)

    @classmethod
    async def group(cls) -> AggregateQuery[ModelProtocol]:
        """Create group query.

        Returns:
            Group query builder
        """
        logger.debug("Creating group query for model: %s", cls._name)
        query = await cls._env.adapter.get_group_query(cast(Type[ModelProtocol], cls))
        return query

    @api.model
    async def create(cls, vals: Dict[str, Any]) -> Self:
        """Create a new record.

        Args:
            vals: Field values

        Returns:
            Created record

        Raises:
            DatabaseError: If database operation fails
            ValidationError: If validation fails
        """
        env = None
        try:
            # Create record
            logger.info(f"Creating {cls._name} record with values: {vals}")

            # Get environment
            env = await cls._get_env()

            # Convert values to database format
            db_vals = await cls._convert_to_db(vals)
            logger.info(f"Converted values for DB: {db_vals} with cls {cls}")

            # Get table name
            table_name = cls._table or cls._name
            logger.info(f"Table name: {table_name}")
            if not table_name:
                raise ValueError(f"Model {cls.__name__} has no table or name defined")

            logger.info(f"Creating {cls._name} record with values: {db_vals}")

            # Insert into database
            record_id = await env.adapter.create(cast(Type[ModelProtocol], cls), db_vals)
            logger.info(f"Created {cls._name} record with ID: {record_id}")

            # Create recordset
            record = cls._browse(env, [record_id])

            # Cache the created values immediately
            logger.debug(f"Caching values for {cls._name}:{record_id}")
            for field, value in vals.items():
                try:
                    # Convert value from DB format if needed
                    field_obj = cls.__fields__[field]
                    converted_value = await field_obj.from_db(
                        value, env.adapter.backend_type
                    )
                    env.set_field_value(cls._name, record_id, field, converted_value)
                    logger.debug(
                        f"Cached field {field}={converted_value} for {cls._name}:{record_id}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to cache field {field} for {cls._name}:{record_id}: {str(e)}"
                    )

            return record

        except ValidationError as e:
            logger.error(f"Validation failed for {cls._name} record: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to create {cls._name} record: {str(e)}")
            # Get backend type safely
            backend = "unknown"
            if env is not None:
                try:
                    backend = env.adapter.backend_type
                except Exception:
                    pass
            raise DatabaseError(
                message=f"Failed to create record: {str(e)}",
                backend=backend,
            ) from e

    @api.one
    async def to_dict(self, fields: Optional[List[str]] = ["id"]) -> Dict[str, Any]:
        """Convert model to dictionary."""
        result: Dict[str, Any] = {}

        if not fields:
            fields = list(self.__fields__.keys())

        logger.info(f"Getting fields: {self.__fields__}")

        for field in fields:
            try:
                value = await self._get_field_value(field)

                # Handle awaitable values
                if value is not None and hasattr(value, "__await__"):
                    value = await value

                result[field] = value

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
        4. System fields

        Args:
            vals: Values to convert

        Returns:
            Dict with converted values

        Examples:
            >>> user = User()
            >>> db_vals = await user._convert_to_db({"age": 25})
            >>> print(db_vals)  # {"age": 25, "updated_at": datetime(...)}
        """
        db_vals: Dict[str, Any] = {}
        backend = cls._env.adapter.backend_type

        # Convert user-provided values
        for name, value in vals.items():
            field = cls.__fields__[name]
            if not field.readonly:  # Skip readonly fields
                db_vals[name] = await field.to_db(value, backend)

        # Add system fields
        db_vals["updated_at"] = datetime.now(UTC)

        return db_vals

    async def _convert_field_value(
        self, field: BaseField[Any], raw_value: Any, backend: str
    ) -> Any:
        """Convert field value from database format.

        Args:
            field: Field instance
            raw_value: Raw value from database
            backend: Database backend type

        Returns:
            Any: Converted value
        """
        self.logger.debug(
            f"Converting fields for {self._name}:{self.id} using {backend} backend"
        )

        # If raw value is None, return None
        if raw_value is None:
            self.logger.debug("Raw value is None, returning None")
            return None

        try:
            # Convert from database format
            value = await field.from_db(raw_value, backend)
            self.logger.debug(f"Converted value from DB: {value}")

            # Validate the converted value
            try:
                await field.validate(value)
                self.logger.debug(f"Validation successful, value: {value}")
                return value
            except FieldValidationError as e:
                self.logger.warning(
                    f"Field validation failed for {field.name}: {str(e)}"
                )
                return None

        except Exception as e:
            self.logger.error(f"Error converting field {field.name} value: {str(e)}")
            return None

    async def _create(self, vals: Dict[str, Any]) -> None:
        """Create record in database."""
        # Get database backend
        backend = self._env.adapter.backend_type

        # Convert values to database format
        db_vals = await self._convert_to_db(vals)

        # Add timestamps
        now = datetime.now(UTC)
        db_vals["created_at"] = now
        db_vals["updated_at"] = now

        # Insert record
        try:
            record_id = await self._env.adapter.insert_one(
                self._name, db_vals  # Collection name from model
            )
            # Convert ID to string if needed
            str_id = str(record_id) if record_id else None
            if not str_id:
                raise ValueError("Failed to get record ID after creation")
            self._ids = (str_id,)

        except Exception as e:
            raise DatabaseError(
                message=f"Failed to create record: {e}", backend=backend
            ) from e

    async def filtered(self, func: Callable[[Self], bool]) -> Self:
        """Filter recordset using a function.

        This method filters the current recordset by applying a function to each record
        and keeping only those records for which the function returns True.

        Args:
            func: Function that takes a record and returns a boolean

        Returns:
            Self: A new recordset containing only records that match the filter

        Examples:
            >>> # Filter users over 18
            >>> adults = await users.filtered(lambda user: user.age >= 18)
            >>>
            >>> # Filter active users
            >>> active = await users.filtered(lambda user: user.status == 'active')
            >>>
            >>> # Combine multiple conditions
            >>> active_adults = await users.filtered(
            ...     lambda user: user.age >= 18 and user.status == 'active'
            ... )
        """
        filtered_ids: List[str] = []
        for record in self:
            try:
                if func(record):
                    filtered_ids.append(record.id)
            except Exception as e:
                self.logger.warning(f"Error filtering record: {str(e)}")
                continue
        return self._browse(self._env, filtered_ids)

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

            # Clear recordset data
            self._ids = ()
            self._prefetch_ids = ()

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

    async def _prefetch_records(self, fields: List[str]) -> None:
        """Prefetch records efficiently using cache.

        This method loads the specified fields for all records in the current recordset
        in a single batch operation. It uses cache when available and loads from
        database only for uncached values.

        Args:
            fields: List of field names to prefetch
        """
        try:
            # Get uncached fields for each record
            uncached_fields: Dict[str, List[str]] = {}
            for record_id in self._ids:
                uncached = [
                    field
                    for field in fields
                    if not self._env.is_field_loaded(self._name, record_id, field)
                ]
                if uncached:
                    uncached_fields[record_id] = uncached

            if not uncached_fields:
                return

            # Get all unique field names
            all_fields: Set[str] = set()
            for field_list in uncached_fields.values():
                all_fields.update(field_list)

            # Fetch records from database
            results: List[Dict[str, Any]] = await self._env.adapter.fetch_all(
                self._name,
                list(uncached_fields.keys()),
                list(all_fields),
            )

            # Process results
            for result in results:
                # Skip invalid results
                if not result:
                    continue

                try:
                    record_id_raw = result.get("id")
                    if not isinstance(record_id_raw, (str, int)):
                        logger.warning(
                            f"Invalid ID type in result for {self._name}: {type(record_id_raw)}"
                        )
                        continue

                    record_id = str(record_id_raw)
                    logger.debug(f"Processing record {self._name}:{record_id}")

                    for field in fields:
                        if field not in result:
                            logger.debug(
                                f"Field {field} not found in result for {self._name}:{record_id}"
                            )
                            continue

                        try:
                            # Get raw value with type checking
                            raw_value: Any = result[field]

                            # Convert value from DB format
                            field_obj = self.__fields__[field]
                            converted_value: Any = await field_obj.from_db(
                                raw_value, self._env.adapter.backend_type
                            )

                            # Cache the value
                            self._env.set_field_value(
                                self._name, record_id, field, converted_value
                            )

                            logger.debug(
                                f"Cached {field}={converted_value} for {self._name}:{record_id}"
                            )
                        except Exception as e:
                            logger.warning(
                                f"Failed to process field {field} for {self._name}:{record_id}: {str(e)}"
                            )
                            continue

                except Exception as e:
                    logger.warning(
                        f"Failed to process record for {self._name}: {str(e)}"
                    )
                    continue

        except Exception as e:
            logger.error(f"Failed to prefetch records for {self._name}: {str(e)}")
            raise DatabaseError(
                message=f"Failed to prefetch records: {str(e)}",
                backend=self._env.adapter.backend_type,
            ) from e

    async def prefetch(self, *fields: str) -> "BaseModel":
        """Prefetch specified fields for all records in the recordset.

        Args:
            *fields: Field names to prefetch

        Returns:
            self: Returns self for method chaining
        """
        if not fields:
            return self

        # Validate fields exist
        invalid_fields = [f for f in fields if f not in self.__fields__]
        if invalid_fields:
            raise ValueError(f"Invalid fields to prefetch: {invalid_fields}")

        # Prefetch records
        await self._prefetch_records(list(fields))
        return self

    async def load_related(self, *fields: str) -> "BaseModel":
        """Prefetch related records for specified relation fields.

        Args:
            *fields: Names of relation fields to prefetch

        Returns:
            self: Returns self for method chaining

        Raises:
            ValueError: If any field is not a relation field
        """
        if not fields:
            return self

        # Validate fields are relations
        invalid_fields: List[str] = []
        for field in fields:
            if field not in self.__fields__:
                invalid_fields.append(field)
                continue

            field_obj = self.__fields__[field]
            field_type = field_obj.adapters[
                self._env.adapter.backend_type
            ].get_field_type()

            if not field_type.startswith("many2") and not field_type.startswith("one2"):
                invalid_fields.append(field)

        if invalid_fields:
            raise ValueError(f"Invalid relation fields to load: {invalid_fields}")

        # Mark fields for prefetching
        for field in fields:
            self._env.mark_for_prefetch(f"{self._name}.{field}", list(self._ids))

        return self

    async def _prefetch_related_records(self, field_name: str) -> None:
        """Prefetch related records for a relation field.

        This method loads related records for a relation field efficiently using batch loading.
        It supports both many2one and one2many/many2many relations.

        Args:
            field_name: Name of the relation field to prefetch

        Raises:
            ValueError: If field is not a relation field
            DatabaseError: If database operation fails
        """
        # Get field object
        field = self.__fields__[field_name]
        field_type = field.adapters[self._env.adapter.backend_type].get_field_type()

        # Validate field type
        if not field_type.startswith("many2") and not field_type.startswith("one2"):
            raise ValueError(f"Field {field_name} is not a relation field")

        # Get related model class
        if not hasattr(field, "model_ref"):
            raise ValueError(f"Field {field_name} has no model reference")

        model_ref = getattr(field, "model_ref")
        if not isinstance(model_ref, str):
            raise ValueError(f"Invalid model reference for field {field_name}")

        related_model = await self._env.get_model(model_ref)
        if not related_model:
            raise ValueError(f"Related model {model_ref} not found")

        # Get related IDs based on field type
        if field_type.startswith("many2one"):
            # Get single ID for each record
            related_ids: Set[str] = set()
            for record_id in self._ids:
                if self._env.is_field_loaded(self._name, record_id, field_name):
                    value = self._env.get_field_value(self._name, record_id, field_name)
                    if isinstance(value, (str, int)):
                        related_ids.add(str(value))
        else:
            # Get multiple IDs for each record
            related_ids: Set[str] = set()
            for record_id in self._ids:
                if self._env.is_field_loaded(self._name, record_id, field_name):
                    values = self._env.get_field_value(
                        self._name, record_id, field_name
                    )
                    if isinstance(values, (list, tuple)):
                        for value in values:  # type: ignore
                            if isinstance(value, (str, int)):
                                related_ids.add(str(value))

        # Prefetch related records if any found
        if related_ids:
            try:
                records = await related_model.browse(list(related_ids))
                # Prefetch all fields for related records
                fields_to_prefetch = list(related_model.__fields__.keys())
                await records._prefetch_records(fields_to_prefetch)  # type: ignore
            except Exception as e:
                self.logger.error(
                    f"Failed to prefetch records for {field_name}: {str(e)}"
                )
                raise DatabaseError(
                    message=f"Failed to prefetch related records: {str(e)}",
                    backend=self._env.adapter.backend_type,
                ) from e

    async def _cleanup_cache(self) -> None:
        """Cleanup cache for current recordset.

        This method invalidates cache entries for all records in the current recordset.
        It is useful when you want to force reload of record data from database.

        Examples:
            >>> users = await User.browse([1, 2, 3])
            >>> await users._cleanup_cache()  # Clear cache for users 1,2,3
        """
        try:
            for id_ in self._ids:
                # Invalidate entire record
                self._env.invalidate_record(self._name, id_)
                self.logger.debug(f"Cleared cache for {self._name}:{id_}")
        except Exception as e:
            self.logger.error(f"Failed to cleanup cache: {str(e)}")

    async def batch_get(self, field: str) -> Dict[str, Any]:
        """Get field value for multiple records efficiently.

        This method retrieves field values for all records in the current recordset
        in a single batch operation. It uses cache when available and loads from
        database only for uncached values.

        Args:
            field: Field name to get

        Returns:
            Dict mapping record ID to field value

        Raises:
            ValueError: If field does not exist
            DatabaseError: If database operation fails

        Examples:
            >>> users = await User.browse([1, 2, 3])
            >>> names = await users.batch_get("name")
            >>> print(names)  # {"1": "John", "2": "Jane", "3": "Bob"}
        """
        # Validate field exists
        if field not in self.__fields__:
            raise ValueError(f"Field {field} does not exist")

        # Prefetch field if needed
        await self._prefetch_records([field])

        # Get values from cache
        try:
            return {
                id_: self._env.get_field_value(self._name, id_, field)
                for id_ in self._ids
            }
        except Exception as e:
            self.logger.error(f"Failed to get batch values: {str(e)}")
            raise DatabaseError(
                message=f"Failed to get batch values: {str(e)}",
                backend=self._env.adapter.backend_type,
            ) from e

    async def batch_write(self, values: Dict[str, Dict[str, Any]]) -> None:
        """Update multiple records with different values.

        This method updates multiple records with different values in a single
        batch operation. It is more efficient than updating records one by one.

        Args:
            values: Dict mapping record ID to update values

        Raises:
            ValueError: If any record ID is invalid
            DatabaseError: If database operation fails

        Examples:
            >>> users = await User.browse([1, 2])
            >>> await users.batch_write({
            ...     "1": {"name": "John", "age": 30},
            ...     "2": {"name": "Jane", "age": 25}
            ... })
        """
        # Validate record IDs
        invalid_ids = set(values.keys()) - set(self._ids)
        if invalid_ids:
            raise ValueError(f"Invalid record IDs: {invalid_ids}")

        try:
            # Update each record
            for record_id, vals in values.items():
                record = self._browse(self._env, [record_id])
                await record.write(vals)

            self.logger.debug(f"Batch updated {len(values)} records")

        except Exception as e:
            self.logger.error(f"Failed to batch write: {str(e)}")
            raise DatabaseError(
                message=f"Failed to batch write: {str(e)}",
                backend=self._env.adapter.backend_type,
            ) from e

    async def optimize_memory(self, max_records: int = 1000) -> None:
        """Optimize memory usage by clearing cache if needed.

        This method helps manage memory usage by clearing cache for recordsets
        that exceed a certain size threshold. It is useful for large recordsets
        where keeping all records in cache may consume too much memory.

        Args:
            max_records: Maximum number of records to keep in cache

        Examples:
            >>> users = await User.search([])  # Get all users
            >>> await users.optimize_memory(1000)  # Clear cache if > 1000 records
        """
        if len(self._ids) > max_records:
            self.logger.info(
                f"Clearing cache for {self._name} - {len(self._ids)} records exceed limit of {max_records}"
            )
            await self._cleanup_cache()

    def mark_for_prefetch(self, fields: List[str]) -> None:
        """Mark fields for prefetching.

        This method marks fields to be prefetched later when execute_prefetch is called.
        It is useful when you want to batch multiple prefetch operations together
        for better performance.

        Args:
            fields: List of field names to prefetch

        Raises:
            ValueError: If any field does not exist

        Examples:
            >>> users = await User.browse([1, 2, 3])
            >>> users.mark_for_prefetch(["posts", "comments"])
            >>> await users.execute_prefetch()  # Prefetch all marked fields
        """
        # Validate fields exist
        invalid_fields = [f for f in fields if f not in self.__fields__]
        if invalid_fields:
            raise ValueError(f"Invalid fields to prefetch: {invalid_fields}")

        # Mark fields for prefetching
        for field in fields:
            self._env.mark_for_prefetch(f"{self._name}.{field}", list(self._ids))
            self.logger.debug(f"Marked {field} for prefetch on {self._name}")

    async def execute_prefetch(self) -> None:
        """Execute all pending prefetch operations.

        This method executes all prefetch operations that were previously marked
        using mark_for_prefetch. It batches multiple prefetch operations together
        for better performance.

        Raises:
            DatabaseError: If database operation fails

        Examples:
            >>> users = await User.browse([1, 2, 3])
            >>> users.mark_for_prefetch(["posts"])
            >>> users.mark_for_prefetch(["comments"])
            >>> await users.execute_prefetch()  # Prefetch both posts and comments
        """
        try:
            await self._env.prefetch_all_pending()
            self.logger.debug(f"Executed prefetch for {self._name}")
        except Exception as e:
            self.logger.error(f"Failed to execute prefetch: {str(e)}")
            raise DatabaseError(
                message=f"Failed to execute prefetch: {str(e)}",
                backend=self._env.adapter.backend_type,
            ) from e

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for current recordset.

        This method returns statistics about the cache usage for the current recordset,
        including:
        - Total number of records
        - Number of cached fields per record
        - Total memory usage estimate

        Returns:
            Dict containing cache stats:
            - total_records: Total number of records in recordset
            - cached_fields: Dict mapping record ID to number of cached fields
            - memory_usage: Rough estimate of memory usage in bytes
        """
        try:
            # Get basic stats
            stats: Dict[str, Any] = {
                "total_records": len(self._ids),
                "cached_fields": {},
                "memory_usage": 0,
            }

            # Get cached fields count
            cached_fields: Dict[str, int] = {}
            for id_ in self._ids:
                loaded = (
                    getattr(self._env, "_loaded_fields", {})
                    .get(self._name, {})
                    .get(id_, set())
                )
                cached_fields[id_] = len(loaded) if loaded else 0
            stats["cached_fields"] = cached_fields

            # Estimate memory usage
            total_memory: int = 0
            for id_ in self._ids:
                cache_data = (
                    getattr(self._env, "_cache", {}).get(self._name, {}).get(id_, {})
                )
                total_memory += len(str(cache_data)) if cache_data else 0
            stats["memory_usage"] = total_memory

            return stats

        except Exception as e:
            logger.error(f"Failed to get cache stats: {str(e)}")
            return {
                "total_records": len(self._ids),
                "cached_fields": {},
                "memory_usage": 0,
            }

    async def _before_write(self, values: Dict[str, Any]) -> None:
        """Hook called before write operation.

        This method is called before a write operation to handle cache invalidation
        for dependent fields. It ensures that computed fields that depend on the
        fields being written are properly invalidated.

        Args:
            values: Values to write

        Examples:
            >>> class User(BaseModel):
            ...     age = IntegerField()
            ...     is_adult = BooleanField(compute="_compute_is_adult")
            ...
            ...     @depends("age")
            ...     def _compute_is_adult(self):
            ...         return self.age >= 18
            ...
            >>> user = await User.browse(1)
            >>> await user.write({"age": 20})  # Invalidates is_adult
        """
        try:
            # Get dependent fields
            dependent_fields: Set[str] = set()
            for field_name in values:
                field = self.__fields__[field_name]
                if hasattr(field, "depends"):
                    depends = getattr(field, "depends", [])
                    if isinstance(depends, (list, tuple, set)):
                        dependent_fields.update(depends)

            # Invalidate dependent fields
            for id_ in self._ids:
                for field in dependent_fields:
                    # Invalidate specific dependent field
                    self._env.invalidate_record(self._name, id_, field)
                    self.logger.debug(
                        f"Invalidated dependent field {field} for {self._name}:{id_}"
                    )

        except Exception as e:
            self.logger.error(f"Failed to process before write hook: {str(e)}")

    async def _after_write(self, values: Dict[str, Any]) -> None:
        """Hook called after write operation.

        This method is called after a write operation to handle cache invalidation
        for computed fields. It ensures that all computed fields are properly
        invalidated after a write operation.

        Args:
            values: Written values

        Examples:
            >>> class User(BaseModel):
            ...     name = StringField()
            ...     full_name = StringField(compute="_compute_full_name")
            ...
            ...     @depends("name")
            ...     def _compute_full_name(self):
            ...         return f"Mr/Ms {self.name}"
            ...
            >>> user = await User.browse(1)
            >>> await user.write({"name": "John"})  # Invalidates full_name
        """
        try:
            # Get computed fields
            computed_fields = [
                f
                for f, field in self.__fields__.items()
                if hasattr(field, "compute") and getattr(field, "compute", None)
            ]

            # Invalidate computed fields
            for id_ in self._ids:
                for field in computed_fields:
                    # Invalidate specific computed field
                    self._env.invalidate_record(self._name, id_, field)
                    self.logger.debug(
                        f"Invalidated computed field {field} for {self._name}:{id_}"
                    )

        except Exception as e:
            self.logger.error(f"Failed to process after write hook: {str(e)}")
