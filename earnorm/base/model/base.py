"""Base model implementation.

This module provides the base model class for all database models.
It includes:
- Field validation and type conversion
- CRUD operations
- Multiple database support
- Lazy loading
- Built-in recordset functionality
- Event system
"""

from datetime import UTC, datetime
from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Self,
    Set,
    Tuple,
    Type,
    Union,
    cast,
)

from earnorm.base.database.adapter import DatabaseAdapter
from earnorm.base.database.query.base.query import AsyncQuery
from earnorm.base.domain.expression import DomainExpression, LogicalOp, Operator
from earnorm.base.env import Environment
from earnorm.base.model.meta import MetaModel
from earnorm.fields import BaseField
from earnorm.types import DatabaseModel, JsonDict, M, ValueType


class FieldsDescriptor:
    """Descriptor for accessing model fields.

    This descriptor allows accessing fields through both class and instance:
        >>> User.__fields__  # Access through class
        >>> user.__fields__  # Access through instance
    """

    def __get__(
        self, obj: Optional["BaseModel"], objtype: Type["BaseModel"]
    ) -> Dict[str, BaseField[Any]]:
        """Get fields dictionary.

        Args:
            obj: Model instance or None if accessed through class
            objtype: Model class

        Returns:
            Dictionary mapping field names to Field instances
        """
        if obj is not None:
            objtype = type(obj)
        return getattr(objtype, "_fields", {})


class EnvDescriptor:
    """Descriptor for accessing model environment.

    This descriptor allows accessing environment through both class and instance:
        >>> User.env  # Access through class
        >>> user.env  # Access through instance

    The environment is shared between all instances of the same model class.
    """

    def __get__(
        self, obj: Optional["BaseModel"], objtype: Type["BaseModel"]
    ) -> Environment:
        """Get model environment.

        Args:
            obj: Model instance or None if accessed through class
            objtype: Model class

        Returns:
            Model environment instance

        Raises:
            RuntimeError: If environment is not set
        """
        if obj is not None:
            objtype = type(obj)

        env = getattr(objtype, "_env", None)
        if env is None:
            raise RuntimeError(
                f"Environment not set for model {objtype.__name__}. "
                "Make sure the model is created through the environment"
            )
        return env

    def __set__(self, obj: "BaseModel", value: Environment) -> None:
        """Set model environment.

        Args:
            obj: Model instance
            value: Environment instance to set
        """
        setattr(type(obj), "_env", value)


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

    __slots__ = ()  # Defined by metaclass

    # Class variables from ModelProtocol
    _store: ClassVar[bool] = True
    _name: ClassVar[str]  # Set by metaclass
    _description: ClassVar[Optional[str]] = None
    _table: ClassVar[Optional[str]] = None
    _sequence: ClassVar[Optional[str]] = None

    # Model fields
    _fields: Dict[str, BaseField[Any]]  # Set by metaclass
    id: int = 0  # Record ID with default value

    # Use descriptors for fields and environment access
    __fields__ = FieldsDescriptor()
    env = EnvDescriptor()

    @property
    def adapter(self) -> DatabaseAdapter[DatabaseModel]:
        """Get database adapter.

        Returns:
            Database adapter for this model

        Raises:
            RuntimeError: If adapter not initialized
        """
        return self.env.adapter

    def __init__(self, **kwargs: Any) -> None:
        """Initialize model instance.

        Args:
            **kwargs: Initial field values
        """
        # Initialize record data
        self._data: Dict[str, Any] = {}
        self._changed: Set[str] = set()

        # Initialize recordset data
        self._domain: List[Union[Tuple[str, Operator, ValueType], LogicalOp]] = []
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None
        self._order: List[tuple[str, str]] = []
        self._group_by: List[str] = []
        self._having: List[Union[Tuple[str, Operator, ValueType], LogicalOp]] = []
        self._distinct: bool = False

        # Set initial values
        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_dict(self) -> JsonDict:
        """Convert model to dictionary.

        Returns:
            Dictionary representation of model
        """
        return {"id": self.id, **{name: getattr(self, name) for name in self._fields}}

    def from_dict(self, data: JsonDict) -> None:
        """Update model from dictionary.

        Args:
            data: Dictionary data to update from
        """
        for name, value in data.items():
            if name in self._fields:
                setattr(self, name, value)

    @classmethod
    async def browse(cls: Type[M], ids: Union[int, List[int]]) -> Union[M, List[M]]:
        """Browse records by IDs.

        Args:
            ids: Record ID or list of record IDs

        Returns:
            Single record or list of records
        """
        if isinstance(ids, int):
            instance = cls()
            instance.id = ids
            return instance

        instances: List[M] = []
        for _id in ids:
            instance = cls()
            instance.id = _id
            instances.append(instance)
        return instances

    @classmethod
    async def create(cls: Type[M], values: Dict[str, Any]) -> M:
        """Create a new record.

        Args:
            values: Field values

        Returns:
            Created record
        """
        instance = cls(**values)
        await cast(BaseModel, instance).save()
        return instance

    def __getattr__(self, name: str) -> Any:
        """Get field value.

        Args:
            name: Field name

        Returns:
            Field value

        Raises:
            AttributeError: If field not found
        """
        if name in self._fields:
            return self._fields[name].__get__(self, type(self))
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        """Set field value.

        Args:
            name: Field name
            value: Field value

        Raises:
            AttributeError: If field not found
            ValidationError: If validation fails
        """
        if name in getattr(self, "_fields", {}):
            field = self._fields[name]
            field.__set__(self, value)
            self._changed.add(name)
        else:
            super().__setattr__(name, value)

    # Recordset methods
    @classmethod
    def filter(
        cls: Type[M],
        domain: List[Union[Tuple[str, Operator, ValueType], LogicalOp]],
    ) -> M:
        """Add filter to record set.

        Args:
            domain: Filter domain

        Returns:
            Self for chaining
        """
        instance = cls()
        base_instance = cast(BaseModel, instance)
        if base_instance._domain:
            base_instance._domain.extend(["&"])
            base_instance._domain.extend(domain)
        else:
            base_instance._domain = domain
        return instance

    def limit(self: M, limit: int) -> M:
        """Set limit for record set.

        Args:
            limit: Maximum number of records

        Returns:
            Self for chaining
        """
        self._limit = limit
        return self

    def offset(self: M, offset: int) -> M:
        """Set offset for record set.

        Args:
            offset: Number of records to skip

        Returns:
            Self for chaining
        """
        self._offset = offset
        return self

    def group_by(self: M, *fields: str) -> M:
        """Set group by fields for record set.

        Args:
            *fields: Field names to group by

        Returns:
            Self for chaining
        """
        self._group_by.extend(fields)
        return self

    def having(
        self: M, domain: List[Union[Tuple[str, Operator, ValueType], LogicalOp]]
    ) -> M:
        """Add having clause to record set.

        Args:
            domain: Having domain

        Returns:
            Self for chaining
        """
        if self._having:
            self._having.extend(["&"])
            self._having.extend(domain)
        else:
            self._having = domain
        return self

    def distinct(self: M) -> M:
        """Make record set distinct.

        Returns:
            Self for chaining
        """
        self._distinct = True
        return self

    @property
    def _domain_expr(self) -> List[Union[Tuple[str, Operator, ValueType], LogicalOp]]:
        """Get domain expression.

        Returns:
            Domain expression
        """
        return self._domain

    @property
    def _limit_value(self) -> Optional[int]:
        """Get limit value.

        Returns:
            Limit value
        """
        return self._limit

    @property
    def _offset_value(self) -> Optional[int]:
        """Get offset value.

        Returns:
            Offset value
        """
        return self._offset

    @property
    def _order_by(self) -> List[Tuple[str, str]]:
        """Get order by expression.

        Returns:
            Order by expression
        """
        return self._order

    def order_by(self: M, field: str, direction: str = "asc") -> M:
        """Add ordering to record set.

        Args:
            field: Field to order by
            direction: Sort direction ('asc' or 'desc')

        Returns:
            Self for chaining
        """
        self._order.append((field, direction))
        return self

    # Query execution methods
    async def all(self) -> List[Self]:
        """Get all matching records.

        Returns:
            List of records
        """
        adapter = self.adapter
        query = await adapter.query(self.__class__)
        query = cast(AsyncQuery[Self], query)

        query = query.filter(DomainExpression(self._domain_expr))

        if self._limit_value is not None:
            query = query.limit(self._limit_value)

        if self._offset_value is not None:
            query = query.offset(self._offset_value)

        if self._order_by:
            query = query.sort(self._order_by[0][0], self._order_by[0][1] == "asc")
            for field, direction in self._order_by[1:]:
                query = query.sort(field, direction == "asc")

        result = await query.execute()
        return result

    async def first(self) -> Optional[Self]:
        """Get first matching record.

        Returns:
            First record or None
        """
        adapter = self.adapter
        query = await adapter.query(self.__class__)
        query = cast(AsyncQuery[Self], query)
        query = query.filter(DomainExpression(self._domain_expr))
        return await query.first()

    async def count(self) -> int:
        """Get number of matching records.

        Returns:
            Record count
        """
        adapter = self.adapter
        query = await adapter.query(self.__class__)
        query = cast(AsyncQuery[Self], query)
        query = query.filter(DomainExpression(self._domain_expr))
        return await query.count()

    # Batch operations
    async def update_all(self, values: Dict[str, Any]) -> int:
        """Update all matching records.

        Args:
            values: Values to update

        Returns:
            Number of updated records
        """
        # Update updated_at
        values["updated_at"] = datetime.now(UTC)

        adapter = self.adapter
        query = await adapter.query(self.__class__)
        query = cast(AsyncQuery[Self], query)
        query = query.filter(DomainExpression(self._domain_expr))
        return await query.update(values)

    async def delete_all(self) -> int:
        """Delete all matching records.

        Returns:
            Number of deleted records
        """
        adapter = self.adapter
        query = await adapter.query(self.__class__)
        query = cast(AsyncQuery[Self], query)
        query = query.filter(DomainExpression(self._domain_expr))
        return await query.delete()

    # Individual record operations
    async def save(self) -> None:
        """Save record to database."""
        # Validate all fields
        await self._validate()

        if self.id == 0:
            await self._create()
        else:
            await self._update()

    async def delete(self) -> None:
        """Delete record from database."""
        if self.id == 0:
            raise ValueError("Cannot delete unsaved record")

        await self.adapter.delete(self)
        self.id = 0

    async def _create(self) -> None:
        """Create new record."""
        # Set created_at and updated_at
        now = datetime.now(UTC)
        setattr(self, "created_at", now)
        setattr(self, "updated_at", now)

        # Convert values to database format and update instance
        db_values = await self._to_db()
        self.from_dict(db_values)

        # Insert into database
        result = await self.adapter.insert(self)

        # Update ID from result
        if isinstance(result, dict):
            result_dict: Dict[str, Any] = result
            id_value: Optional[int] = result_dict.get("_id", None)  # type: ignore
            if id_value is None:
                id_value = result_dict.get("id", None)  # type: ignore
            self.id = id_value if id_value is not None else 0
        else:
            self.id = 0

        # Clear changes
        self._changed.clear()

    async def _update(self) -> None:
        """Update existing record."""
        if not self._changed:
            return

        # Update updated_at
        setattr(self, "updated_at", datetime.now(UTC))

        # Convert changed values to database format
        db_values = await self._to_db(self._changed)
        self.from_dict(db_values)

        # Update database
        await self.adapter.update(self)

        # Clear changes
        self._changed.clear()

    async def _validate(self, fields: Optional[Set[str]] = None) -> None:
        """Validate fields.

        Args:
            fields: Fields to validate, or None for all fields

        Raises:
            ValidationError: If validation fails
        """
        fields_to_validate = fields or self._fields.keys()

        for name in fields_to_validate:
            field = self._fields[name]
            value = getattr(self, name)
            await field.validate(value)

    async def _to_db(self, fields: Optional[Set[str]] = None) -> Dict[str, Any]:
        """Convert fields to database format.

        Args:
            fields: Fields to convert, or None for all fields

        Returns:
            Database values
        """
        fields_to_convert = fields or self._fields.keys()
        values: Dict[str, Any] = {}

        for name in fields_to_convert:
            field = self._fields[name]
            value = getattr(self, name)
            values[name] = await field.to_db(value, self.adapter.backend_type)

        return values

    @property
    def fields(self) -> Dict[str, BaseField[Any]]:
        """Get model fields.

        Returns:
            Dictionary mapping field names to Field instances
        """
        return self._fields

    def __str__(self) -> str:
        """Return string representation."""
        return f"{self.__class__.__name__}(id={self.id})"

    def __repr__(self) -> str:
        """Return detailed string representation."""
        fields = [f"id={self.id!r}"]
        for name in self._fields:
            if name != "id":
                value = getattr(self, name)
                fields.append(f"{name}={value!r}")
        return f"{self.__class__.__name__}({', '.join(fields)})"
