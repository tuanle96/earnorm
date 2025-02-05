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

import asyncio
import logging
from datetime import UTC, datetime, timezone
from typing import (
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

from earnorm.base.database.query.interfaces.domain import DomainExpression
from earnorm.base.database.query.interfaces.domain import DomainOperator as Operator
from earnorm.base.database.query.interfaces.domain import LogicalOperator as LogicalOp
from earnorm.base.database.query.interfaces.operations.aggregate import (
    AggregateProtocol as AggregateQuery,
)
from earnorm.base.database.query.interfaces.operations.join import (
    JoinProtocol as JoinQuery,
)
from earnorm.base.database.query.interfaces.query import QueryProtocol as AsyncQuery
from earnorm.base.database.transaction.base import Transaction
from earnorm.base.env import Environment
from earnorm.base.model.data_store import ModelDataStore
from earnorm.base.model.descriptors import FieldsDescriptor
from earnorm.base.model.meta import ModelMeta
from earnorm.di import Container
from earnorm.exceptions import (
    DatabaseError,
    FieldValidationError,
    UniqueConstraintError,
)
from earnorm.fields.base import BaseField
from earnorm.fields.relation.base import RelationField
from earnorm.types import DatabaseModel, ValueType
from earnorm.types.models import ModelProtocol

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
        "_data_store",  # Data store instance
        "_deleted",  # Deletion flag
        "_ids",  # Record IDs
        "_prefetch_ids",  # Prefetch IDs
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

    # Instance variables with type hints
    _ids: Tuple[str, ...]
    _data_store: "ModelDataStore[Self]"  # Use Self type
    _deleted: bool
    _prefetch_ids: Tuple[str, ...]

    def __init__(self, env: Optional[Environment] = None) -> None:
        """Initialize base model."""
        env_instance = env if env is not None else self._get_default_env()
        if not env_instance:
            raise RuntimeError(
                "Environment not initialized. Make sure earnorm.init() is called first"
            )
        object.__setattr__(self, "_env", env_instance)
        object.__setattr__(self, "_data_store", ModelDataStore(self))
        object.__setattr__(self, "_deleted", False)
        object.__setattr__(self, "_ids", ())
        object.__setattr__(self, "_prefetch_ids", ())
        # Initialize id field
        self._data_store.set_field("id", "")

        if not self._name:
            raise ValueError("Model must define _name attribute")

    @classmethod
    def _get_default_env(cls) -> Optional[Environment]:
        """Get default environment from container.

        Returns:
            Optional[Environment]: Environment instance or None
        """
        try:
            # Get singleton instance
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
    def _data(self) -> Dict[str, Any]:
        """Get record data."""
        return self._data_store.get_data()

    @_data.setter
    def _data(self, value: Dict[str, Any]) -> None:
        """Set record data."""
        self._data_store.set_data(value)

    @property
    def _changed(self) -> Set[str]:
        """Get changed fields."""
        return self._data_store.get_changed()

    @property
    def _has_data(self) -> bool:
        """Check if record has data loaded."""
        return self._data_store.has_data()

    @property
    def _record_data(self) -> Dict[str, Any]:
        """Get record data."""
        return self._data_store.get_data()

    @_record_data.setter
    def _record_data(self, value: Dict[str, Any]) -> None:
        """Set record data."""
        self._data_store.set_data(value)

    @classmethod
    def _browse(
        cls,
        env: Environment,
        ids: Sequence[str],
        prefetch_ids: Optional[Sequence[str]] = None,
    ) -> Self:
        """Create recordset instance."""
        records = object.__new__(cls)

        # Initialize required attributes
        object.__setattr__(records, "_env", env)
        object.__setattr__(records, "_data_store", ModelDataStore(records))
        object.__setattr__(records, "_deleted", False)
        object.__setattr__(records, "_name", cls._get_instance_name())

        # Validate and convert IDs
        validated_ids: List[str] = []
        for id_value in ids:
            if not id_value:
                continue
            try:
                # Ensure ID is string and valid
                str_id = str(id_value).strip()
                if not str_id:
                    continue
                validated_ids.append(str_id)
            except Exception as e:
                logger.warning(f"Invalid ID skipped: {id_value} - {str(e)}")
                continue

        object.__setattr__(records, "_ids", tuple(validated_ids))

        # Handle prefetch IDs
        if prefetch_ids:
            validated_prefetch: List[str] = []
            for pid in prefetch_ids:
                if not pid:
                    continue
                try:
                    str_pid = str(pid).strip()
                    if not str_pid:
                        continue
                    validated_prefetch.append(str_pid)
                except Exception as e:
                    logger.warning(f"Invalid prefetch ID skipped: {pid} - {str(e)}")
                    continue
            object.__setattr__(records, "_prefetch_ids", tuple(validated_prefetch))
        else:
            object.__setattr__(records, "_prefetch_ids", records._ids)

        # Set id field in _data
        records._data_store.set_field("id", records._ids[0] if records._ids else "")
        return records

    @classmethod
    async def browse(cls, ids: Union[str, List[str]]) -> Self:
        """Browse records by IDs.

        This method always returns a recordset instance, whether browsing a single ID
        or multiple IDs.

        Args:
            ids: Record ID or list of record IDs

        Returns:
            Self: A recordset containing the records with the given IDs

        Examples:
            >>> # Browse single record
            >>> user = await User.browse("123")
            >>> print(user.name)

            >>> # Browse multiple records
            >>> users = await User.browse(["123", "456"])
            >>> for user in users:
            ...     print(user.name)
        """
        if isinstance(ids, str):
            return cls._browse(cls._env, [ids])
        return cls._browse(cls._env, ids)

    @classmethod
    async def _where_calc(
        cls, domain: Sequence[Union[Tuple[str, str, Any], str]]
    ) -> AsyncQuery[ModelProtocol]:
        """Build query from domain.

        Args:
            domain: Search domain

        Returns:
            Query instance
        """
        query = await cls._env.adapter.query(cast(Type[ModelProtocol], cls))
        if domain:
            expr = DomainExpression(cast(List[Any], list(domain)))
            query = query.filter(expr.to_list())
        return cast(AsyncQuery[ModelProtocol], query)

    @classmethod
    async def _apply_ir_rules(cls, query: AsyncQuery[DatabaseModel], mode: str) -> None:
        """Apply access rules to query.

        Args:
            query: Query to modify
            mode: Access mode (read/write/create/unlink)
        """
        # TODO: Implement access rules
        pass

    @classmethod
    async def search(
        cls,
        domain: Optional[
            List[Union[Tuple[str, Operator, ValueType], LogicalOp]]
        ] = None,
        offset: int = 0,
        limit: Optional[int] = None,
        order: Optional[str] = None,
        use_cache: bool = True,
        prefetch_fields: Optional[List[str]] = None,
    ) -> Self:
        """Search records matching domain.

        Args:
            domain: Search domain
            offset: Number of records to skip
            limit: Maximum number of records to return
            order: Sort order
            use_cache: Whether to use cache
            prefetch_fields: Fields to prefetch

        Returns:
            Recordset containing matching records

        Examples:
            >>> users = await User.search([("age", ">", 18)])
            >>> print(len(users))  # Number of adult users
        """
        try:
            # Try get from cache first
            if use_cache:
                logger.debug("Trying to get results from cache")
                cache_manager = await cls._env.cache_manager
                cache_key = f"query:{cls._name}:{hash(str(domain))}"
                if limit:
                    cache_key += f":limit={limit}"
                if offset:
                    cache_key += f":offset={offset}"
                if order:
                    cache_key += f":order={order}"

                cached_result = await cache_manager.get(cache_key)
                if cached_result:
                    logger.debug("Found cached results")
                    return cls._browse(
                        await cls._get_env(),
                        [
                            str(doc.get("id"))  # type: ignore
                            for doc in cached_result
                            if isinstance(doc, dict) and "id" in doc
                        ],
                        prefetch_fields,
                    )

            # Calculate where clause
            logger.debug("Building query from domain: %s", domain)
            query = await cls._where_calc(domain or [])

            # Add options
            if offset:
                query.offset(offset)
            if limit is not None:
                query.limit(limit)
            if order:
                query.order_by(order)

            # Execute query with timeout
            logger.debug("Executing query")
            docs = await asyncio.wait_for(
                query.execute(), timeout=30.0  # 30 seconds timeout
            )
            logger.debug("Search found %d records", len(docs))
            logger.debug("Raw docs: %s", docs)

            # Cache query result
            if use_cache:
                logger.debug("Caching query results")
                # Convert docs to serializable format before caching
                serializable_docs: List[Dict[str, Any]] = []
                for doc in docs:
                    if isinstance(doc, dict):
                        # If doc is already a dict, use it
                        serializable_docs.append(
                            {k: v for k, v in doc.items() if not isinstance(v, type)}  # type: ignore
                        )
                    else:
                        # If doc is a model instance, convert to dict
                        serializable_docs.append(
                            {
                                k: v
                                for k, v in doc._data.items()  # type: ignore
                                if not isinstance(v, type)
                            }
                        )
                logger.debug("Serializable docs: %s", serializable_docs)
                cache_manager = await cls._env.cache_manager
                cache_key = f"query:{cls._name}:{hash(str(domain))}"
                await cache_manager.set(
                    cache_key, serializable_docs, ttl=300
                )  # Cache for 5 minutes

            # Create recordset
            logger.debug("Creating recordset from docs")
            recordset = cls._browse(
                await cls._get_env(),
                [
                    str(doc.id if hasattr(doc, "id") else doc.get("id"))  # type: ignore
                    for doc in docs
                    if (isinstance(doc, dict) and "id" in doc)
                    or (hasattr(doc, "id") and doc.id)
                ],
                prefetch_fields,
            )
            logger.debug("Created recordset with %d records", len(recordset))

            # Batch load data
            logger.debug("Batch loading data for search results")
            await recordset._batch_load_data([recordset])  # Convert to list

            # Prefetch fields
            if prefetch_fields:
                logger.debug("Prefetching fields: %s", prefetch_fields)
                await recordset.prefetch(*prefetch_fields)

            return recordset

        except Exception as e:
            logger.error("Search failed: %s", str(e), exc_info=True)
            backend = cls._env.adapter.backend_type
            raise DatabaseError(
                message=f"Search failed: {str(e)}",
                backend=backend,
            ) from e

    async def _validate_create(self, vals: Dict[str, Any]) -> None:
        """Validate record creation.

        This method performs the following validations:
        1. Check required fields
        2. Check field types and constraints
        3. Check unique constraints
        4. Apply custom validation rules

        Args:
            vals: Field values to validate

        Raises:
            FieldValidationError: If validation fails
            ValidationError: If custom validation fails
        """
        logger.debug("Validating create values: %s", vals)

        try:
            # Check required fields
            for name, field in self.__fields__.items():
                if (
                    field.required
                    and not field.readonly
                    and name not in vals
                    and field.default is None
                ):
                    raise FieldValidationError(
                        message=f"Field '{name}' is required",
                        field_name=name,
                    )

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

            # Check unique constraints
            await self._check_unique_constraints(vals)

            # Apply custom validation rules
            await self._validate_create_rules(vals)

        except Exception as e:
            logger.error("Validation failed: %s", str(e))
            raise

    async def _validate_write(self, vals: Dict[str, Any]) -> None:
        """Validate record update.

        Args:
            vals: Field values to validate

        Raises:
            FieldValidationError: If validation fails
            ValidationError: If custom validation fails
            ValueError: If records don't exist
        """
        try:
            if not self._ids:
                logger.error("No records to update - IDs are empty")
                raise ValueError("No records to update")

            # Validate field values
            for name, value in vals.items():
                logger.debug("Validating field '%s' with value: %s", name, value)

                if name not in self.__fields__:
                    logger.error("Invalid field name: %s", name)
                    raise FieldValidationError(
                        message=f"Field '{name}' does not exist",
                        field_name=name,
                    )

                field = self.__fields__[name]
                if field.readonly:
                    logger.error("Attempt to modify readonly field: %s", name)
                    raise FieldValidationError(
                        message=f"Field '{name}' is readonly",
                        field_name=name,
                    )

                try:
                    await field.validate(value)
                    logger.debug("Field '%s' validation passed", name)
                except ValueError as e:
                    logger.error("Field '%s' validation failed: %s", name, str(e))
                    raise FieldValidationError(
                        message=str(e),
                        field_name=name,
                    ) from e

            # Check unique constraints
            logger.debug("Checking unique constraints")
            await self._check_unique_constraints(vals)

            # Apply custom validation rules
            logger.debug("Applying custom validation rules")
            await self._validate_write_rules(vals)

        except Exception as e:
            logger.error("Write validation failed: %s", str(e), exc_info=True)
            raise

    async def _validate_unlink(self) -> None:
        """Validate record deletion.

        This method performs the following validations:
        1. Check if records exist
        2. Check if records can be deleted (not readonly)
        3. Check if records have no dependent records
        4. Apply custom validation rules

        Raises:
            FieldValidationError: If deletion is not allowed
            ValidationError: If custom validation fails
            ValueError: If records don't exist
        """
        logger.debug("Validating deletion for records: %s", self._ids)

        try:
            if not self._ids:
                raise ValueError("No records to delete")

            # Check if records exist in database
            domain_tuple = cast(
                Tuple[str, Operator, ValueType],
                ("id", "in", list(self._ids)),
            )
            query = await self._where_calc([domain_tuple])
            count = await query.count()
            if count != len(self._ids):
                raise ValueError("Some records do not exist")

            # Check if model allows deletion
            if getattr(self, "_allow_unlink", None) is False:
                raise FieldValidationError(
                    message="Deletion is not allowed for this model",
                    field_name="id",
                )

            # Check for dependent records
            await self._check_dependencies()

            # Apply custom validation rules
            await self._validate_unlink_rules()

        except Exception as e:
            logger.error("Validation failed: %s", str(e))
            raise

    async def _check_dependencies(self) -> None:
        """Check for dependent records.

        This method checks if there are any records in other models
        that depend on the records being deleted.

        Raises:
            ValidationError: If dependent records exist
        """
        # To be implemented
        pass

    async def _validate_unlink_rules(self) -> None:
        """Apply custom validation rules for deletion.

        This method can be overridden by subclasses to add custom validation rules.
        By default, it does nothing.

        Raises:
            FieldValidationError: If validation fails
        """
        pass

    def _serialize_value(self, value: Any) -> Any:
        """Serialize value for caching.

        Args:
            value: Value to serialize

        Returns:
            Serialized value that can be stored in cache

        Examples:
            >>> _serialize_value(datetime(2024, 1, 1))
            '2024-01-01T00:00:00+00:00'
            >>> _serialize_value({"date": datetime(2024, 1, 1)})
            {'date': '2024-01-01T00:00:00+00:00'}
        """
        if isinstance(value, datetime):
            # Convert to UTC and format as ISO string
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value.isoformat()
        elif isinstance(value, dict):
            return {
                str(key): self._serialize_value(val)
                for key, val in cast(Dict[Any, Any], value).items()
            }
        elif isinstance(value, (list, tuple)):
            return [
                self._serialize_value(item)
                for item in cast(Union[List[Any], Tuple[Any, ...]], value)
            ]
        return value

    async def _create(self, vals: Dict[str, Any]) -> None:
        """Create record in database.

        Args:
            vals: Values to create record with

        Raises:
            DatabaseError: If record creation fails
        """
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

            # Store all record data including original values and converted values
            self._data = {
                **vals,  # Original values from user
                **db_vals,  # Converted values including any transformations
                "id": str_id,
                "created_at": now,
                "updated_at": now,
            }

        except Exception as e:
            raise DatabaseError(
                message=f"Failed to create record: {e}", backend=backend
            ) from e

        # Update cache for new record
        try:
            cache_manager = await self._env.cache_manager
            for field_name, value in self._data.items():
                # Serialize value before caching
                serialized_value = self._serialize_value(value)
                await cache_manager.set(
                    f"{self._name}:{field_name}:{str_id}",
                    serialized_value,
                    ttl=3600,  # Cache for 1 hour
                )
        except Exception as e:
            logger.warning(f"Failed to update cache for new record: {e}")
            # Don't raise exception as the record was created successfully

    async def _write(self, vals: Dict[str, Any]) -> None:
        """Write values to database.

        This method updates records in the database with the given values.
        It ensures all IDs are valid strings.

        Args:
            vals: Field values to update

        Raises:
            DatabaseError: If database operation fails
            ValueError: If any ID is invalid
        """
        try:
            # Validate write operation
            await self._validate_write(vals)

            # Convert values for backend
            db_vals = await self._convert_to_db(vals)

            # Create update operations
            updates: List[Dict[str, Any]] = []

            # Process each model ID
            for model_id in self._ids:
                # Ensure model_id is valid
                if not model_id:
                    raise ValueError("Empty ID is not allowed")

                try:
                    str_id = str(model_id).strip()
                    if not str_id:
                        raise ValueError("Empty ID after conversion")
                except Exception as e:
                    raise ValueError(f"Invalid ID format: {model_id}") from e

                logger.debug("Processing model with ID: %s", model_id)

                # Create update operation
                update_op = {"filter": {"id": str_id}, "update": {"$set": db_vals}}
                logger.debug("Created update operation: %s", update_op)

                updates.append(update_op)

            if not updates:
                logger.warning("No valid records to update")
                return

            logger.debug("Attempting bulk update with %d operations", len(updates))
            result = await self._env.adapter.bulk_write(self._name, updates)
            logger.debug("Bulk update completed successfully: %s", result)

            # Update cache with new values
            cache_manager = await self._env.cache_manager
            for field_name, value in vals.items():
                for record_id in self._ids:
                    await cache_manager.set(
                        f"{self._name}:{field_name}:{record_id}", value
                    )

        except ValueError as e:
            logger.error("Invalid ID error: %s", str(e), exc_info=True)
            raise DatabaseError(
                backend=self._env.adapter.backend_type,
                message=str(e),
            ) from e
        except Exception as e:
            logger.error("Failed to update records: %s", str(e), exc_info=True)
            raise DatabaseError(
                backend=self._env.adapter.backend_type,
                message=f"Failed to update records: {str(e)}",
            ) from e

    async def _unlink(self) -> bool:
        """Delete records in recordset."""
        if not self._ids:
            return False

        try:
            # Convert all IDs to string format
            delete_ids = [str(model_id) for model_id in self._ids]

            # Delete records using adapter's interface
            result = await self._env.adapter.delete_many_by_filter(
                self._name,
                {"id": {"in": delete_ids}},  # Use database-agnostic filter format
            )

            # Clear recordset
            self._ids = ()
            self._prefetch_ids = ()

            return bool(result)

        except Exception as e:
            logger.error("Failed to delete records: %s", str(e), exc_info=True)
            raise DatabaseError(
                message=f"Failed to delete records: {e}",
                backend=self._env.adapter.backend_type,
            ) from e

    async def write(self, values: Dict[str, Any]) -> Self:
        """Update records in recordset.

        Args:
            values: Field values to update

        Returns:
            Self: Same recordset with updated values

        Examples:
            >>> user = await User.search([("email", "=", "john@example.com")])
            >>> updated_user = await user.write({"age": 26})
            >>> print(updated_user.age)  # 26
        """
        await self._write(values)
        return self

    async def unlink(self) -> bool:
        """Delete records in recordset.

        Returns:
            bool: True if records were deleted successfully

        Examples:
            >>> user = await User.search([("email", "=", "john@example.com")])
            >>> success = await user.unlink()
            >>> print(success)  # True
        """
        await self._unlink()
        self._ids = ()
        self._prefetch_ids = ()
        return True

    def __iter__(self):
        """Iterate through records in recordset."""
        for _id in self._ids:
            yield self._browse(self._env, [_id], self._prefetch_ids)

    def __len__(self):
        """Return number of records in recordset."""
        return len(self._ids)

    def __getitem__(self, key: Union[int, slice]) -> Self:
        """Get record(s) by index/slice."""
        if isinstance(key, slice):
            ids = self._ids[key]
        else:
            ids = [self._ids[key]]
        return self._browse(self._env, ids, self._prefetch_ids)

    @property
    def ids(self):
        """Return record IDs."""
        return self._ids

    def _filter_func(self, rec: Self, name: str) -> bool:
        """Filter function for filtered method."""
        return any(rec.mapped(name))

    def filtered(self, func: Union[str, Callable[[Self], bool]]) -> Self:
        """Filter records in recordset.

        Args:
            func: Filter function or field name

        Returns:
            Filtered recordset
        """
        if isinstance(func, str):
            name = func

            def filter_func(rec: Self) -> bool:
                return self._filter_func(rec, name)

            func = filter_func

        return self._browse(
            self._env, [rec.id for rec in self if func(rec)], self._prefetch_ids  # type: ignore
        )

    def mapped(self, func: Union[str, Callable[[Self], Any]]) -> Any:
        """Apply function to records in recordset.

        Args:
            func: Mapping function or field name

        Returns:
            Result of mapping
        """
        if isinstance(func, str):
            field = self.__fields__[func]
            # pylint: disable=unnecessary-dunder-call
            return field.__get__(
                self, type(self)
            )  # pylint: disable=unnecessary-dunder-call
        return [func(rec) for rec in self]  # type: ignore

    def _sort_key(self, rec: Self, field: BaseField[Any]) -> Any:
        """Sort key function for sorted method."""
        # pylint: disable=unnecessary-dunder-call
        return cast(Any, field.__get__(rec, type(rec)))

    def sorted(
        self,
        key: Optional[Union[str, Callable[[Self], Any]]] = None,
        reverse: bool = False,
    ) -> Self:
        """Sort records in recordset.

        Args:
            key: Sort key function or field name
            reverse: Reverse sort order

        Returns:
            Sorted recordset
        """
        records = list(self)
        if key is not None:
            if isinstance(key, str):
                name = key
                field = self.__fields__[name]

                def sort_key(rec: Self) -> Any:
                    return self._sort_key(rec, field)

                key = sort_key
            records.sort(key=cast(Callable[[Self], Any], key), reverse=reverse)
        else:
            records.sort(reverse=reverse)  # type: ignore[call-overload]
        return self._browse(self._env, [rec.id for rec in records], self._prefetch_ids)

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

    async def _check_unique_constraints(self, vals: Dict[str, Any]) -> None:
        """Check unique constraints.

        Args:
            vals: Field values to check

        Raises:
            UniqueConstraintError: If unique constraint would be violated
        """
        for name, value in vals.items():
            field = self.__fields__[name]
            if not getattr(field, "unique", False):
                continue

            # Build domain for unique check
            domain = [
                (name, "=", value),
                "!",
                ("id", "in", list(self._ids)) if self._ids else ("id", "!=", 0),
            ]

            # Check if value exists
            query = await self._where_calc(domain)
            exists = await query.exists()
            if exists:
                raise UniqueConstraintError(
                    message="Value already exists",
                    field_name=name,
                    value=value,
                )

    async def _validate_create_rules(self, vals: Dict[str, Any]) -> None:
        """Apply custom validation rules for creation.

        This method can be overridden by subclasses to add custom validation rules.
        By default, it does nothing.

        Args:
            vals: Field values to validate

        Raises:
            ValidationError: If validation fails
        """
        pass

    async def _validate_write_rules(self, vals: Dict[str, Any]) -> None:
        """Apply custom validation rules for update.

        This method can be overridden by subclasses to add custom validation rules.
        By default, it does nothing.

        Args:
            vals: Field values to validate

        Raises:
            ValidationError: If validation fails
        """
        pass

    @classmethod
    async def create(cls, values: Dict[str, Any]) -> Self:
        """Create a new record.

        This method creates a new record in the database with the given values.
        It performs the following steps:
        1. Create a new instance of the model
        2. Validate the values
        3. Convert values to database format
        4. Insert into database
        5. Return the new record

        Args:
            values: Field values to create record with

        Returns:
            Self: A recordset containing the newly created record

        Raises:
            FieldValidationError: If validation fails
            DatabaseError: If database operation fails
            UniqueConstraintError: If unique constraint is violated

        Examples:
            >>> user = await User.create({
            ...     "name": "John Doe",
            ...     "email": "john@example.com",
            ...     "age": 30
            ... })
            >>> print(user.name)  # Access as recordset
        """
        # Create new instance
        record = cls._browse(cls._env, [], [])

        # Create record
        await record._create(values)

        return record

    async def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary.

        This method converts all fields to their Python format, handling:
        1. Loading data from database/cache if needed
        2. Converting database format to Python format
        3. Error handling for each field
        4. Caching converted results

        Returns:
            Dictionary representation of model

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            # Try get from cache first
            cache_manager = await self._env.cache_manager
            cache_key = f"{self._name}:dict:{self.id}"
            cached_dict = await cache_manager.get(cache_key)
            if isinstance(cached_dict, dict):
                logger.debug(f"Got cached dict for {self._name}:{self.id}")
                return cached_dict

            # Ensure data is loaded
            if not self._has_data and self.id:
                logger.debug(f"Loading data for {self._name}:{self.id}")
                await self._ensure_data_loaded()

            if not self._has_data:
                logger.warning(f"No data found for {self._name}:{self.id}")
                return {name: None for name in self.__fields__}

            # Get database backend
            backend = self._env.adapter.backend_type
            logger.debug(
                f"Converting fields for {self._name}:{self.id} using {backend} backend"
            )

            # Convert fields
            result: Dict[str, Any] = {}
            for name, field in self.__fields__.items():
                raw_value = self._data.get(name)
                try:
                    value = await self._convert_field_value(field, raw_value, backend)
                    result[name] = value
                except Exception as e:
                    logger.error(f"Failed to convert field {name}: {e}")
                    result[name] = None

            # Cache converted dict
            logger.debug(f"Caching dict for {self._name}:{self.id}")
            await cache_manager.set(cache_key, result)

            return result

        except DatabaseError:
            # Re-raise database errors
            raise

        except Exception as e:
            logger.error(f"Failed to convert model to dict: {e}", exc_info=True)
            # Return empty values as fallback
            return {name: None for name in self.__fields__}

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Update model from dictionary.

        Args:
            data: Dictionary data to update from
        """
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

    async def _convert_to_db(self, vals: Dict[str, Any]) -> Dict[str, Any]:
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
        backend = self._env.adapter.backend_type

        # Convert user-provided values
        for name, value in vals.items():
            field = self.__fields__[name]
            if not field.readonly:  # Skip readonly fields
                db_vals[name] = await field.to_db(value, backend)

        # Add system fields
        db_vals["updated_at"] = datetime.now(UTC)

        return db_vals

    async def _read_from_cache(self, field_name: str) -> Any:
        """Read field value from cache.

        Args:
            field_name: Name of the field to read

        Returns:
            Any: Cached value or None if not found

        Examples:
            >>> user = User.browse(1)
            >>> name = await user._read_from_cache("name")
            >>> print(name)  # "John" or None if not cached
        """
        cache_manager = await self._env.cache_manager
        key = f"{self._name}:{field_name}:{self.id}"
        return await cache_manager.get(key)

    async def _write_to_cache(
        self,
        field_name: str,
        value: Any,
        ttl: Optional[int] = None,
        strategy: str = "write-through",
    ) -> None:
        """Write field value to cache.

        Args:
            field_name: Name of the field to write
            value: Value to cache
            ttl: Cache TTL in seconds
            strategy: Cache strategy (write-through/write-behind)
        """
        cache_manager = await self._env.cache_manager
        key = f"{self._name}:{field_name}:{self.id}"

        if strategy == "write-through":
            # Write to cache immediately
            await cache_manager.set(key, value, ttl=ttl or 3600)
        else:
            # Write-behind: Queue write for batch processing
            await cache_manager.queue_write(key, value, ttl=ttl or 3600)

    async def _invalidate_cache(
        self, field_names: Optional[List[str]] = None, invalidate_related: bool = True
    ) -> None:
        """Invalidate cache for specified fields.

        Args:
            field_names: List of field names to invalidate, or None to invalidate all
            invalidate_related: Whether to invalidate related records
        """
        cache_manager = await self._env.cache_manager

        # Get fields to invalidate
        if field_names is None:
            field_names = list(self.__fields__.keys())

        # Collect all keys to invalidate
        keys_to_invalidate: Set[str] = set()

        # Add direct field keys
        for field_name in field_names:
            for record_id in self._ids:
                keys_to_invalidate.add(f"{self._name}:{field_name}:{record_id}")

        # Add computed field keys that depend on these fields
        for compute_field in self.__fields__.values():
            if hasattr(compute_field, "depends"):
                if any(dep in field_names for dep in compute_field.depends):
                    for record_id in self._ids:
                        keys_to_invalidate.add(
                            f"{self._name}:{compute_field.name}:{record_id}"
                        )

        # Add related record keys if requested
        if invalidate_related:
            for field_name in field_names:
                field = self.__fields__.get(field_name)
                if isinstance(field, RelationField):
                    # Get related record IDs
                    related_ids: Set[str] = set()
                    for record_id in self._ids:
                        value = await self._read_from_cache(field_name)
                        if isinstance(value, (list, tuple)):
                            related_ids.update(str(v) for v in value if v)  # type: ignore
                        elif value:
                            related_ids.add(str(value))

                    # Add related record keys
                    for related_id in related_ids:
                        keys_to_invalidate.add(f"{field.model_ref}:data:{related_id}")

        # Batch invalidate all keys
        if keys_to_invalidate:
            await cache_manager.delete_many(list(keys_to_invalidate))
            logger.debug(f"Invalidated {len(keys_to_invalidate)} cache keys")

    async def _prefetch_fields(self, field_names: List[str]) -> None:
        """Prefetch field values for recordset.

        This method prefetches values for specified fields and their related fields.
        It helps reduce the number of database queries by loading data in batches.

        Args:
            field_names: List of field names to prefetch

        Examples:
            >>> users = User.search([("age", ">", 18)])
            >>> await users._prefetch_fields(["company_id", "role_ids"])
        """
        cache_manager = await self._env.cache_manager

        # Group fields by model
        field_groups: Dict[str, List[str]] = {}
        for field_name in field_names:
            field = self.__fields__[field_name]
            if isinstance(field, RelationField):
                model_name = field.model_ref
                if isinstance(model_name, str):
                    if model_name not in field_groups:
                        field_groups[model_name] = []
                    field_groups[model_name].append(field_name)

        # Prefetch each group
        for model_name, model_fields in field_groups.items():
            # Get related record IDs
            related_ids: Set[str] = set()
            for field_name in model_fields:
                cached_values: List[Any] = await asyncio.gather(
                    *(self._read_from_cache(field_name) for _ in self._ids),
                    return_exceptions=True,
                )
                for value in cached_values:
                    if value is not None:
                        if isinstance(value, (list, tuple)):
                            # Handle list/tuple of IDs
                            for item in value:  # type: ignore
                                try:
                                    # Convert any value to string safely
                                    str_id = str(item) if item is not None else None  # type: ignore
                                    if str_id is not None:
                                        related_ids.add(str_id)
                                except (ValueError, TypeError):
                                    continue
                        else:
                            try:
                                # Handle single ID value
                                str_id = str(value) if value is not None else None
                                if str_id is not None:
                                    related_ids.add(str_id)
                            except (ValueError, TypeError):
                                continue

            if related_ids:
                # Get related model class
                model_cls = await self._env.get_model(model_name)
                if model_cls:
                    model_cls = cast(Type[BaseModel], model_cls)
                    # Load related records
                    related_records = await model_cls.browse(list(related_ids))
                    records_list = (
                        [related_records]
                        if not isinstance(related_records, list)
                        else related_records
                    )

                    # Cache related records
                    for record in records_list:
                        record_data = await record.to_dict()
                        for fname, value in record_data.items():
                            await cache_manager.set(
                                f"{model_name}:{fname}:{record.id}", value, ttl=3600
                            )

    async def prefetch(self, *fields: str) -> None:
        """Prefetch specified fields.

        This is a convenience method that calls _prefetch_fields internally.

        Args:
            *fields: Field names to prefetch

        Examples:
            >>> users = User.search([("age", ">", 18)])
            >>> await users.prefetch("company_id", "role_ids")
        """
        await self._prefetch_fields(list(fields))

    @property
    def id(self) -> str:
        """Get ID of first record in recordset.

        Returns:
            str: ID of first record or empty string if recordset is empty.
                 Always returns a string, converting from ObjectId if needed.

        Examples:
            >>> user = await User.browse("123")
            >>> print(user.id)  # "123"
            >>> users = await User.search([])
            >>> print(users.id)  # ""
        """
        raw_id = self._data.get("id")
        if raw_id is None:
            return ""
        return str(raw_id)

    @id.setter
    def id(self, value: str) -> None:
        """Set ID of first record in recordset.

        Args:
            value: ID value to set. Must be a string or convertible to string.

        Examples:
            >>> user = User()
            >>> user.id = "123"
            >>> print(user.id)  # "123"
        """
        self._data["id"] = str(value) if value else ""

    async def _validate_id(self, id_value: Any) -> Optional[str]:
        """Validate and convert ID value.

        Args:
            id_value: Value to validate as ID

        Returns:
            Optional[str]: Validated ID as string or None if invalid

        Examples:
            >>> await model._validate_id("123")
            "123"
            >>> await model._validate_id(model)  # model instance
            "123"
            >>> await model._validate_id(None)
            None
        """
        try:
            # Handle model instance
            if isinstance(id_value, self.__class__):
                id_attr = getattr(id_value, "id", None)
                return str(id_attr) if id_attr else None

            # Handle string
            if isinstance(id_value, str):
                return id_value

            # Handle objects with id attribute
            if hasattr(id_value, "id"):
                id_attr = getattr(id_value, "id", None)
                return str(id_attr) if id_attr else None

            return None
        except Exception as e:
            self.logger.warning(
                f"Invalid ID validation: {e} for value type {type(id_value)}",
                exc_info=True,
            )
            return None

    def _set_data(self, data: Dict[str, Any]) -> None:
        """Set record data safely.

        Args:
            data: Data to set
        """
        self.__dict__["_data"] = data

    async def _batch_load_data(
        self, records: List[Self], batch_size: int = 100
    ) -> None:
        """Load data for multiple records in one query.

        Args:
            records: Records to load data for
            batch_size: Number of records to load in one batch
        """
        try:
            # Get IDs of records that need data
            ids_to_load = [rec.id for rec in records if rec.id and not rec._has_data]

            if not ids_to_load:
                logger.debug("No records need data loading")
                return

            logger.debug(f"Loading data for {len(ids_to_load)} records")

            # Get cache manager
            cache_manager = await self._env.cache_manager

            # Try get from cache first in batches
            cached_data: Dict[str, Dict[str, Any]] = {}
            cache_keys = [f"{self._name}:data:{rid}" for rid in ids_to_load]

            # Batch get from cache
            cached_values = await cache_manager.get_many(cache_keys)
            for key, value in zip(cache_keys, cached_values):
                if isinstance(value, dict):
                    record_id = key.split(":")[-1]
                    cached_data[record_id] = value
                    logger.debug(f"Got cached data for {self._name}:{record_id}")

            # Remove cached IDs
            ids_to_load = [id for id in ids_to_load if id not in cached_data]

            if ids_to_load:
                # Process in batches
                for i in range(0, len(ids_to_load), batch_size):
                    batch_ids = ids_to_load[i : i + batch_size]
                    logger.debug(
                        f"Querying database for batch of {len(batch_ids)} records"
                    )

                    # Batch query for remaining IDs
                    query = await self._env.adapter.query(
                        cast(Type[ModelProtocol], type(self))
                    )
                    query.filter([("id", "in", batch_ids)])

                    # Add prefetch fields if defined
                    if hasattr(self, "_prefetch_fields"):
                        query.prefetch(getattr(self, "_prefetch_fields", []))

                    docs = await query.execute()

                    # Cache new data in batch
                    cache_ops: List[Tuple[str, Dict[str, Any]]] = []
                    for doc in docs:
                        if isinstance(doc, dict) and "id" in doc:
                            doc_id_value = cast(Optional[str], doc.get("id"))  # type: ignore
                            if doc_id_value is not None:
                                try:
                                    doc_id = str(doc_id_value)
                                    cache_key = f"{self._name}:data:{doc_id}"
                                    cache_ops.append((cache_key, doc))
                                    cached_data[doc_id] = doc
                                except (ValueError, TypeError) as e:
                                    logger.warning(
                                        f"Failed to convert document ID: {e}"
                                    )
                                    continue

                    if cache_ops:
                        # Batch set to cache
                        await cache_manager.set_many(
                            {k: (v, 3600) for k, v in cache_ops}  # 1 hour TTL
                        )
                        logger.debug(f"Cached {len(cache_ops)} records")

            # Update records
            for record in records:
                if record.id in cached_data:
                    record._data = cached_data[record.id]
                    logger.debug(f"Updated data for {self._name}:{record.id}")

        except Exception as e:
            logger.error(f"Failed to batch load data: {e}", exc_info=True)

    async def _ensure_data_loaded(self) -> None:
        """Ensure record data is loaded."""
        if not self._has_data and self.id:
            try:
                logger.debug(f"Loading data for {self._name}:{self.id}")
                # Try cache first
                cache_manager = await self._env.cache_manager
                cache_key = f"{self._name}:data:{self.id}"
                cached_data = await cache_manager.get(cache_key)

                if isinstance(cached_data, dict):
                    logger.debug(f"Got cached data for {self._name}:{self.id}")
                    self._data = cached_data
                else:
                    # Query database
                    logger.debug(f"Querying database for {self._name}:{self.id}")
                    raw_data = await self._env.adapter.find_by_id(self._name, self.id)
                    if isinstance(raw_data, dict):
                        self._data = raw_data
                        # Cache for next time
                        logger.debug(f"Caching data for {self._name}:{self.id}")
                        await cache_manager.set(cache_key, raw_data)
                    else:
                        logger.warning(f"No data found for {self._name}:{self.id}")

            except Exception as e:
                logger.error(f"Failed to load data: {e}", exc_info=True)

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
        try:
            if raw_value is None:
                return None
            return await field.from_db(raw_value, backend)
        except Exception as e:
            self.logger.warning(f"Failed to convert field {field.name}: {e}")
            return None
