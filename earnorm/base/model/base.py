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
    Any,
    AsyncContextManager,
    Callable,
    ClassVar,
    Dict,
    List,
    Optional,
    Self,
    Sequence,
    Set,
    Tuple,
    TypeVar,
    Union,
    cast,
)

from bson import ObjectId

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
from earnorm.base.model.descriptors import FieldsDescriptor
from earnorm.base.model.meta import ModelMeta
from earnorm.di import Container
from earnorm.exceptions import (
    DatabaseError,
    FieldValidationError,
    UniqueConstraintError,
)
from earnorm.fields import BaseField
from earnorm.types import DatabaseModel, ValueType
from earnorm.types.models import ModelProtocol

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=ModelProtocol)


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
        "_data",  # Record data
        "_changed",  # Changed fields
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

    # Model fields (will be set by metaclass)
    __fields__ = FieldsDescriptor()  # Descriptor for accessing fields
    id: int = 0  # Record ID with default value

    _ids: Tuple[Any, ...]  # Record IDs with proper type
    _changed: Set[str]  # Changed fields with proper type

    def __init__(self, env: Optional[Environment] = None) -> None:
        """Initialize model with injected env."""
        # Initialize all slots with default values
        env_instance = env if env is not None else self._get_default_env()
        if not env_instance:
            raise RuntimeError(
                "Environment not initialized. Make sure earnorm.init() is called first"
            )
        object.__setattr__(self, "_env", env_instance)
        self._set_instance_name(self._get_instance_name())
        object.__setattr__(self, "_data", {})
        object.__setattr__(self, "_changed", set())
        object.__setattr__(self, "_deleted", False)
        object.__setattr__(self, "_ids", ())
        object.__setattr__(self, "_prefetch_ids", ())

        if not self._name:
            raise ValueError("Model must define _name attribute")

    @classmethod
    def _get_default_env(cls) -> Optional[Environment]:
        """Get default environment from container.

        Returns:
            Optional[Environment]: Environment instance or None
        """
        try:
            from earnorm.di import container

            env = container.get("environment")
            return env if isinstance(env, Environment) else None
        except Exception:
            return None

    @property
    def env(self) -> Environment:
        """Get environment."""
        return self._env

    @classmethod
    def _browse(
        cls,
        env: Environment,
        ids: Sequence[int],
        prefetch_ids: Optional[Sequence[int]] = None,
    ) -> Self:
        """Create recordset instance.

        Args:
            env: Environment instance
            ids: Record IDs
            prefetch_ids: IDs to prefetch

        Returns:
            Self: New recordset instance
        """
        records = object.__new__(cls)
        records._env = env
        records._ids = tuple(ids)
        records._prefetch_ids = tuple(prefetch_ids or ids)
        records._data = {}
        records._changed = set()
        records._deleted = False
        records._set_instance_name(cls._get_instance_name())
        return records

    @classmethod
    async def browse(
        cls, ids: Union[int, List[int]]
    ) -> Union[DatabaseModel, List[DatabaseModel]]:
        """Browse records by IDs.

        Args:
            ids: Record ID or list of record IDs

        Returns:
            Single record or list of records
        """
        if isinstance(ids, int):
            return cls._browse(cls._env, [ids])
        return [cls._browse(cls._env, [id]) for id in ids]

    @classmethod
    async def _where_calc(
        cls, domain: Sequence[Union[Tuple[str, str, Any], str]]
    ) -> AsyncQuery[DatabaseModel]:
        """Build query from domain.

        Args:
            domain: Search domain

        Returns:
            Query instance
        """
        query = await cls._env.adapter.query(cls)
        if domain:
            expr = DomainExpression(cast(List[Any], list(domain)))
            query = query.filter(expr.to_list())
        return query

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
    ) -> Self:
        """Search records matching domain.

        Args:
            domain: Search domain
            offset: Number of records to skip
            limit: Maximum number of records to return
            order: Sort order

        Returns:
            Self: A recordset containing matching records

        Examples:
            >>> users = await User.search([("age", ">", 18)])
            >>> for user in users:
            ...     print(user.name)
        """
        query = await cls._where_calc(domain or [])
        await cls._apply_ir_rules(query, "read")

        # Build query
        if order:
            query = query.order_by(order)
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)

        # Execute query and return recordset
        ids = await query.execute()
        return cls._browse(cls._env, cast(Sequence[int], ids), cast(Sequence[int], ids))

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
        logger.debug("Starting write validation for values: %s", vals)
        logger.debug("Current model IDs: %s", self._ids)

        try:
            if not self._ids:
                logger.error("No records to update - IDs are empty")
                raise ValueError("No records to update")

            # Check if records exist in database
            # Get actual ID values from model objects
            id_list = []
            for model_id in self._ids:
                if isinstance(model_id, str):
                    id_list.append(model_id)
                elif hasattr(model_id, "id"):
                    id_list.append(str(getattr(model_id, "id")))
                else:
                    id_list.append(str(model_id))

            logger.debug("Checking existence for IDs: %s", id_list)

            # Create query to check existence
            domain_tuple = cast(
                Tuple[str, Operator, ValueType],
                ("id", "in", id_list),
            )
            query = await self._where_calc([domain_tuple])
            logger.debug("Generated query: %s", query)

            # Count matching records
            count = await query.count()
            logger.debug("Found %d records matching IDs", count)

            if count != len(self._ids):
                logger.error(
                    "Record count mismatch - Expected: %d, Found: %d",
                    len(self._ids),
                    count,
                )
                raise ValueError("Some records do not exist")

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

    async def _create(self, vals: Dict[str, Any]) -> None:
        """Create record in database.

        Args:
            vals: Field values to create

        Raises:
            FieldValidationError: If validation fails
            DatabaseError: If database operation fails
        """
        # Validate values
        await self._validate_create(vals)

        # Convert values to database format
        db_vals: Dict[str, Any] = {}
        backend = self._env.adapter.backend_type

        # Convert user-provided values
        for name, value in vals.items():
            field = self.__fields__[name]
            if not field.readonly:  # Skip readonly fields
                db_vals[name] = await field.to_db(value, backend)

        # Add default values for missing required fields
        for name, field in self.__fields__.items():
            if name not in vals and field.required and not field.readonly:
                if field.default is not None:
                    default_value = (
                        field.default() if callable(field.default) else field.default
                    )
                    db_vals[name] = await field.to_db(default_value, backend)

        # Add system fields
        now = datetime.now(UTC)
        db_vals["created_at"] = now
        db_vals["updated_at"] = now

        # Insert record
        try:
            record_id = await self._env.adapter.insert_one(
                self._name, db_vals  # Collection name from model
            )
        except Exception as e:
            raise DatabaseError(
                message=f"Failed to create record: {e}", backend=backend
            ) from e

        # Update record ID
        self._ids = (record_id,)

    async def _write(self, vals: Dict[str, Any]) -> None:
        """Write values to database.

        Args:
            vals: Values to write
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
                logger.debug("Processing model with ID: %s", model_id)

                # Convert ID to ObjectId if string
                if isinstance(model_id, str):
                    _id = ObjectId(model_id)
                elif hasattr(model_id, "id"):
                    _id = ObjectId(str(getattr(model_id, "id")))
                else:
                    _id = model_id

                # Create update operation
                update_op = {"filter": {"_id": _id}, "update": {"$set": db_vals}}
                logger.debug("Created update operation: %s", update_op)

                updates.append(update_op)

            logger.debug("Attempting bulk update with %d operations", len(updates))
            result = await self._env.adapter.bulk_write(self._name, updates)
            logger.debug("Bulk update completed successfully: %s", result)

        except Exception as e:
            logger.error("Failed to update records: %s", str(e), exc_info=True)
            raise DatabaseError(
                backend=self._env.adapter.backend_type,
                message=f"Failed to update records: {str(e)}",
            ) from e

    async def _unlink(self) -> bool:
        """Delete records in recordset.

        Returns:
            bool: True if records were deleted successfully
        """
        if not self._ids:
            return False

        try:
            # Convert IDs to ObjectId if needed
            delete_ids = []
            for model_id in self._ids:
                if isinstance(model_id, str):
                    delete_ids.append(ObjectId(model_id))
                elif hasattr(model_id, "id"):
                    delete_ids.append(ObjectId(str(getattr(model_id, "id"))))
                else:
                    delete_ids.append(model_id)

            # Delete records
            collection = await self._env.adapter.get_collection(self._name)
            result = await collection.delete_many({"_id": {"$in": delete_ids}})

            # Clear recordset
            self._ids = ()
            self._prefetch_ids = ()

            return result.deleted_count > 0

        except Exception as e:
            logger.error("Failed to delete records: %s", str(e), exc_info=True)
            raise DatabaseError(
                message=f"Failed to delete records: {e}",
                backend=self._env.adapter.backend,
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
    async def aggregate(cls) -> AggregateQuery[DatabaseModel]:
        """Create aggregate query.

        This method creates an aggregate query builder for performing
        aggregation operations on the model's records.

        Returns:
            Aggregate query builder

        Examples:
            >>> # Count records by status
            >>> stats = await User.aggregate()\\
            ...     .group_by("status")\\
            ...     .count("total")\\
            ...     .execute()

            >>> # Calculate average age by country
            >>> avg_age = await User.aggregate()\\
            ...     .group_by("country")\\
            ...     .avg("age", "avg_age")\\
            ...     .having(total__gt=100)\\
            ...     .execute()

            >>> # Multiple aggregations
            >>> stats = await Order.aggregate()\\
            ...     .group_by("status", "category")\\
            ...     .count("total_orders")\\
            ...     .sum("amount", "total_amount")\\
            ...     .avg("amount", "avg_amount")\\
            ...     .min("amount", "min_amount")\\
            ...     .max("amount", "max_amount")\\
            ...     .having(total_orders__gt=10)\\
            ...     .execute()
        """
        logger.debug("Creating aggregate query for model: %s", cls._name)
        query = await cls._env.adapter.get_aggregate_query(cls)
        return query

    @classmethod
    async def join(
        cls,
        model: str,
        on: Dict[str, str],
        join_type: str = "inner",
    ) -> JoinQuery[DatabaseModel, Any]:
        """Create join query.

        This method creates a join query builder for performing
        join operations with other models.

        Args:
            model: Model to join with
            on: Join conditions {local_field: foreign_field}
            join_type: Join type (inner, left, right)

        Returns:
            Join query builder

        Examples:
            >>> # Simple join
            >>> users = await User.join(
            ...     "posts",
            ...     on={"id": "user_id"},
            ...     join_type="left"
            ... ).select(
            ...     "name",
            ...     "posts.title"
            ... ).execute()

            >>> # Multiple joins
            >>> users = await User.join(
            ...     "posts",
            ...     on={"id": "user_id"}
            ... ).join(
            ...     "comments",
            ...     on={"id": "user_id"}
            ... ).select(
            ...     "name",
            ...     "posts.title",
            ...     "comments.content"
            ... ).where(
            ...     posts__likes__gt=10,
            ...     comments__status="approved"
            ... ).execute()

            >>> # Join with aggregation
            >>> stats = await User.join(
            ...     "posts",
            ...     on={"id": "user_id"}
            ... ).group_by(
            ...     "name",
            ...     "email"
            ... ).count(
            ...     "posts.id",
            ...     "total_posts"
            ... ).having(
            ...     total_posts__gt=5
            ... ).execute()
        """
        logger.debug(
            "Creating join query for model %s with %s",
            cls._name,
            model,
        )
        query = await cls._env.adapter.get_join_query(cls)
        return query.join(model, on, join_type)

    @classmethod
    async def group(cls) -> AggregateQuery[DatabaseModel]:
        """Create group query.

        This method creates a group query builder for performing
        grouping operations on the model's records.

        Returns:
            Group query builder

        Examples:
            >>> # Simple grouping
            >>> stats = await Order.group()\\
            ...     .by("status")\\
            ...     .count("total")\\
            ...     .execute()

            >>> # Multiple grouping fields
            >>> stats = await Order.group()\\
            ...     .by("status", "category")\\
            ...     .count("total_orders")\\
            ...     .sum("amount", "total_amount")\\
            ...     .having(total_orders__gt=10)\\
            ...     .execute()

            >>> # Complex grouping
            >>> stats = await Order.group()\\
            ...     .by("customer.country", "product.category")\\
            ...     .count("total_orders")\\
            ...     .sum("amount", "total_amount")\\
            ...     .avg("amount", "avg_amount")\\
            ...     .having(
            ...         total_orders__gt=100,
            ...         total_amount__gt=10000
            ...     ).sort(
            ...         "-total_amount"
            ...     ).limit(10)\\
            ...     .execute()
        """
        logger.debug("Creating group query for model: %s", cls._name)
        query = await cls._env.adapter.get_group_query(cls)
        return query

    async def _check_unique_constraints(self, vals: Dict[str, Any]) -> None:
        """Check unique constraints.

        This method checks if any unique constraints would be violated
        by the given values.

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
            if await query.exists():
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

        This method converts all fields (both readonly and non-readonly) to their database format.

        Returns:
            Dictionary representation of model

        Examples:
            >>> user = User(name="John", age=30)
            >>> data = await user.to_dict()
            >>> print(data)  # {'name': 'John', 'age': 30, 'created_at': datetime(...)}
        """
        result: Dict[str, Any] = {}
        backend = self._env.adapter.backend_type
        for name, field in self.__fields__.items():
            value = getattr(self, name)
            result[name] = await field.to_db(value, backend)
        return result

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
    ) -> "AsyncContextManager[Transaction[ModelProtocol]]":
        """Get transaction context manager.

        Returns:
            Transaction context manager
        """
        return await self._env.adapter.transaction(model_type=type(self))

    @classmethod
    async def _get_env(cls) -> Environment:
        """Get environment instance from container.

        Returns:
            Environment: Environment instance from container

        Raises:
            RuntimeError: If environment is not found in container
        """
        container = Container()
        env = await container.get_env()
        if env is None:
            raise RuntimeError("Environment not found in container")
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
