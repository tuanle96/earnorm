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
    Callable,
    ClassVar,
    Dict,
    List,
    Optional,
    Self,
    Sequence,
    Tuple,
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
from earnorm.base.env import Environment
from earnorm.base.model.meta import MetaModel
from earnorm.exceptions import (
    DatabaseError,
    FieldValidationError,
    UniqueConstraintError,
)
from earnorm.fields import BaseField
from earnorm.types import DatabaseModel, ValueType

logger = logging.getLogger(__name__)


class BaseModel(DatabaseModel, metaclass=MetaModel):
    """Base class for all database models.

    Features:
    - Field validation and type conversion
    - CRUD operations
    - Multiple database support
    - Lazy loading
    - Built-in recordset functionality
    - Event system

    Examples:
        >>> class User(BaseModel):
        ...     name = StringField(required=True)
        ...     email = EmailField(unique=True)
        ...
        >>> user = User(name="John")
        >>> await user.save()
        >>> users = await User.filter([('name', 'like', 'J%')]).all()
    """

    __slots__ = ("_env", "_ids", "_prefetch_ids")

    # Class variables from ModelProtocol
    _store: ClassVar[bool] = True
    _name: ClassVar[str]  # Set by metaclass
    _description: ClassVar[Optional[str]] = None
    _table: ClassVar[Optional[str]] = None
    _sequence: ClassVar[Optional[str]] = None

    # Model fields
    _fields: Dict[str, BaseField[Any]]  # Set by metaclass
    id: int = 0  # Record ID with default value

    # Environment instance
    _env: Environment

    def __init__(
        self,
        env: Environment,
        ids: Optional[Sequence[int]] = None,
        prefetch_ids: Optional[Sequence[int]] = None,
    ) -> None:
        """Initialize recordset.

        Args:
            env: Environment instance
            ids: Record IDs
            prefetch_ids: IDs to prefetch
        """
        self._env = env
        self._ids = tuple(ids or ())  # Store as immutable tuple
        self._prefetch_ids = tuple(
            prefetch_ids or ids or ()
        )  # Store as immutable tuple

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
            New recordset instance
        """
        records = object.__new__(cls)
        records._env = env
        records._ids = tuple(ids)
        records._prefetch_ids = tuple(prefetch_ids or ids)  # Store as immutable tuple
        return records

    @classmethod
    async def browse(cls, ids: Optional[Union[int, Sequence[int]]] = None) -> Self:
        """Browse records by IDs.

        Args:
            ids: Record ID or list of record IDs

        Returns:
            Recordset containing records
        """
        if ids is None:
            ids = []
        elif isinstance(ids, (int, str)):
            ids = [ids]
        return cls._browse(cls._env, cast(Sequence[int], ids), cast(Sequence[int], ids))

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
            Recordset containing matching records
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

        # Execute query
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
            for name, field in self._fields.items():
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
                if name not in self._fields:
                    raise FieldValidationError(
                        message=f"Field '{name}' does not exist",
                        field_name=name,
                    )
                field = self._fields[name]
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
                if name not in self._fields:
                    raise FieldValidationError(
                        message=f"Field '{name}' does not exist",
                        field_name=name,
                    )
                field = self._fields[name]
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
            await self._validate_write_rules(vals)

        except Exception as e:
            logger.error("Validation failed: %s", str(e))
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
            field = self._fields[name]
            if not field.readonly:  # Skip readonly fields
                db_vals[name] = await field.to_db(value, backend)

        # Add default values for missing required fields
        for name, field in self._fields.items():
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
            field = self._fields[name]
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
            await self._env.adapter.update_many(cast(List[DatabaseModel], models))

        except Exception as e:
            raise DatabaseError(
                message=f"Failed to update records: {e}", backend=backend
            ) from e

    async def _unlink(self) -> None:
        """Delete record from database.

        Raises:
            FieldValidationError: If deletion is not allowed
            DatabaseError: If database operation fails
        """
        # Validate deletion
        await self._validate_unlink()

        try:
            # Convert to model objects
            models = [
                self._browse(self._env, [id], self._prefetch_ids) for id in self._ids
            ]

            # Bulk delete
            await self._env.adapter.delete_many(cast(List[DatabaseModel], models))

        except Exception as e:
            raise DatabaseError(
                message=f"Failed to delete records: {e}",
                backend=self._env.adapter.backend_type,
            ) from e

    async def write(self, values: Dict[str, Any]) -> Self:
        """Update records in recordset.

        Args:
            values: Field values to update

        Returns:
            Same recordset
        """
        await self._write(values)
        return self

    async def unlink(self) -> bool:
        """Delete records in recordset.

        Returns:
            True if records were deleted
        """
        await self._unlink()
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
            field = self._fields[func]
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
                field = self._fields[name]

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
            field = self._fields[name]
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
