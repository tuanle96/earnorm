"""Base model for EarnORM.

This module provides the base model class that all ORM models inherit from.
It handles record management, field access, and database operations.

Examples:
    >>> from earnorm.base.model import BaseModel
    >>> from earnorm.fields import StringField, IntegerField
    >>>
    >>> class Partner(BaseModel):
    ...     _name = 'res.partner'
    ...     _description = 'Partners'
    ...
    ...     name = StringField(required=True)
    ...     age = IntegerField()
    ...
    ...     async def send_email(self):
    ...         # Send email to partner
    ...         pass
"""

from typing import (
    Any,
    AsyncIterator,
    ClassVar,
    Dict,
    Iterator,
    List,
    Optional,
    Set,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

from earnorm.base.database.query.backends.mongo.builder import MongoQueryBuilder
from earnorm.base.database.query.backends.mongo.executor import MongoQueryExecutor
from earnorm.base.domain.converter import MongoConverter
from earnorm.base.domain.expression import DomainExpression
from earnorm.base.env import Environment
from earnorm.base.model.meta import MetaModel, RecordSetType
from earnorm.di import container
from earnorm.fields.base import Field
from earnorm.types import JsonDict
from earnorm.validators.base import ValidationError

# Type variable for self-referencing
Self = TypeVar("Self", bound="BaseModel")

T = TypeVar("T", bound="BaseModel")

# Domain expression types
DomainItem = Union[List[Any], str]


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


class BaseModel(metaclass=MetaModel):
    """Base class for all ORM models.

    This class provides core functionality for:
    - Record management (create, read, write, delete)
    - Field access and validation
    - Database operations
    - Record sets and iteration
    - Prefetching and caching

    A model instance can represent either a single record or multiple records.
    When representing multiple records, it behaves like both a model instance
    and a collection, supporting:
    - Iteration over records
    - Length and containment checks
    - Indexing and slicing
    - Lazy loading of fields
    - Prefetching of related records

    Attributes:
        _name: Technical name of the model (e.g. 'res.partner')
        _description: User-friendly description
        _table: Database table name
        _sequence: Sequence for ID generation
        _inherit: Parent model(s) to inherit from
        _inherits: Parent models to delegate to
        _order: Default ordering
        _rec_name: Field to use for record name
        _auto: Whether to create database table
        _register: Whether to register in registry
        _abstract: Whether model is abstract
        _transient: Whether records are temporary
    """

    __slots__ = ["_instance_env", "_ids", "_prefetch"]

    # Model metadata
    _name: ClassVar[str]
    _description: ClassVar[Optional[str]] = None
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
            raise ValidationError("No environment provided")

        self._ids: List[int] = []
        self._prefetch: Dict[str, Set[int]] = {}

        if ids is not None:
            self._ids = self._normalize_ids(ids)

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
        recordset = await instance._browse(ids)
        return cast(Self, recordset)

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
        env = await cls.env
        instance = cls(env=env)
        recordset = await instance._create(values)
        return cast(Self, recordset)

    @classmethod
    async def search(cls: Type[T], domain: List[Any] | None = None) -> T:
        """Search for records matching domain.

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
        query = instance._domain_to_query(domain or [])
        ids = await instance._search(query)
        recordset = await instance._browse(ids)
        return cast(T, recordset)

    def _normalize_ids(self, ids: Optional[Union[int, List[int]]]) -> List[int]:
        """Normalize record IDs to a list of integers.

        Args:
            ids: Single ID or list of IDs to normalize

        Returns:
            List of normalized integer IDs

        Examples:
            >>> model._normalize_ids(1)
            [1]
            >>> model._normalize_ids([1, 2, 3])
            [1, 2, 3]
        """
        if ids is None:
            return []
        if isinstance(ids, int):
            return [ids]
        return [int(x) for x in ids]

    async def _browse(
        self, ids: Optional[Union[int, List[int]]] = None
    ) -> "RecordSetType":
        """Internal method to create recordset.

        This is an internal method that returns RecordSetType.
        Public methods should use browse() instead which returns the model type.
        """
        recordset = self._RecordSet(env=await self.env)
        if ids is not None:
            recordset._ids = self._normalize_ids(ids)
            self._add_to_prefetch(self._name, set(recordset._ids))
        return recordset

    def _add_to_prefetch(self, model: str, ids: Set[int]) -> None:
        """Add IDs to prefetch cache.

        Args:
            model: Model name
            ids: Record IDs to prefetch

        Raises:
            ValidationError: If model name is empty or ids is empty

        Examples:
            >>> model._add_to_prefetch("res.partner", {1, 2, 3})
        """
        if not model:
            raise ValidationError("Model name cannot be empty")
        if not ids:
            raise ValidationError("IDs cannot be empty")

        if model not in self._prefetch:
            self._prefetch[model] = set()
        self._prefetch[model].update(ids)

    def __len__(self) -> int:
        """Get number of records in this instance."""
        return len(self._ids)

    def __bool__(self) -> bool:
        """Return True if this instance contains any records."""
        return bool(self._ids)

    @overload
    def __getitem__(self: Self, index: int) -> Self: ...

    @overload
    def __getitem__(self: Self, index: slice) -> Self: ...

    def __getitem__(self: Self, index: Union[int, slice]) -> Self:
        """Get record(s) at index.

        Args:
            index: Integer index or slice

        Returns:
            Single record instance for integer index
            Multiple record instance for slice

        Examples:
            >>> users = await User.search([])
            >>> first_user = users[0]  # Returns User
            >>> some_users = users[1:3]  # Returns User
        """
        if isinstance(index, slice):
            instance = self.__class__(env=self._instance_env)
            instance._ids = self._ids[index]
            return instance
        else:
            instance = self.__class__(env=self._instance_env)
            instance._ids = [self._ids[index]]
            return instance

    def __iter__(self: Self) -> Iterator[Self]:
        """Iterate over records in this instance.

        Each iteration returns a new instance containing a single record.

        Examples:
            >>> users = await User.search([])  # Multiple records
            >>> for user in users:  # Each user is User instance
            ...     print(user.name)  # Lazy loads name for each record
        """
        for record_id in self._ids:
            # Create new instance with single ID
            instance = self.__class__(env=self._instance_env)
            instance._ids = [record_id]
            yield instance

    async def ensure_one(self: Self) -> Self:
        """Ensure this instance contains exactly one record.

        Returns:
            Self if instance contains one record

        Raises:
            ValidationError: If instance is empty or contains multiple records

        Examples:
            >>> user = await users.ensure_one()  # Raises if not exactly one record
            >>> print(user.name)  # Safe to use as single record
        """
        if not self._ids:
            raise ValidationError(f"No {self._name} record found")
        if len(self._ids) > 1:
            raise ValidationError(
                f"Expected single {self._name} record, got {len(self._ids)}"
            )
        return self

    @property
    def ids(self) -> List[int]:
        """Get IDs of records in this instance.

        Returns:
            List of record IDs

        Examples:
            >>> users = await User.search([])
            >>> print(users.ids)  # [1, 2, 3]
        """
        return self._ids.copy()

    async def __aiter__(self) -> AsyncIterator["BaseModel"]:
        """Async iterator over records in this recordset.

        Yields:
            Individual record instances

        Examples:
            >>> async for user in users:
            ...     print(user.name)
        """
        for record_id in self._ids:
            yield await self._browse(record_id)

    async def _validate_values(self, values: Dict[str, Any]) -> None:
        """Validate field values before create/write.

        Args:
            values: Field values to validate

        Raises:
            ValidationError: If validation fails

        Examples:
            >>> await model._validate_values({
            ...     'name': 'John',
            ...     'age': 30
            ... })
        """
        # Get field definitions
        fields = self.__class__.__fields__

        # Check required fields
        for field_name, field in fields.items():
            if field.required and field_name not in values:
                raise ValidationError(f"Field {field_name} is required")

        # Validate field values
        for field_name, value in values.items():
            if field_name not in fields:
                raise ValidationError(f"Unknown field {field_name}")

            field = fields[field_name]
            try:
                await field.validate(value)
            except ValidationError as e:
                raise ValidationError(
                    f"Invalid value for {field_name}: {str(e)}"
                ) from e

    async def write(self: Self, values: Dict[str, Any]) -> Self:
        """Update record values.

        Args:
            values: Field values to update

        Returns:
            Model instance containing the updated record

        Examples:
            >>> user = await user.write({"name": "Jane"})  # Returns User instance
            >>> print(user.name)
        """
        recordset = await self._write(values)
        return cast(Self, recordset)

    async def unlink(self) -> bool:
        """Delete records.

        Returns:
            True if successful

        Raises:
            ValidationError: If validation fails

        Examples:
            >>> success = await user.unlink()
        """
        # get valid ids
        ids = self._ids
        if not ids:
            raise ValidationError("No records to unlink")

        return await self._unlink(ids)

    async def _search(self, query: JsonDict) -> List[int]:
        """Search for records matching query.

        Args:
            query: Database query dict

        Returns:
            List of matching record IDs

        Examples:
            >>> ids = await model._search({"age": {"$gt": 18}})
            >>> print(ids)  # [1, 2, 3]
        """
        # Get database connection from environment
        if not self._instance_env:
            raise ValidationError("No environment available")

        # Build and execute query
        backend_type = self._instance_env.backend_type
        if backend_type == "mongodb":
            # Build MongoDB query
            builder = MongoQueryBuilder(self._name)
            builder.filter(query).project({"_id": 1})
            query = await builder.build()

            # Execute query
            executor = MongoQueryExecutor(self._instance_env)
            result = await executor.execute(query)

            # Extract IDs from result
            return [doc["_id"] for doc in result.get("documents", [])]
        else:
            raise NotImplementedError(f"Backend {backend_type} not supported yet")

    def __str__(self) -> str:
        """String representation showing model name and record IDs.

        Examples:
            >>> str(users)  # 'User(1,2,3)'
            >>> str(users[0])  # 'User(1)'
        """
        model_name = self.__class__.__name__
        ids = ",".join(str(id) for id in self._ids)
        return f"{model_name}({ids})"

    # Private methods for record operations
    async def _create(self, values: Dict[str, Any]) -> "RecordSetType":
        """Create record in database.

        Args:
            values: Field values for new record

        Returns:
            RecordSet containing the new record

        Raises:
            ValidationError: If validation fails
        """
        # 1. Validate values
        await self._validate_values(values)

        # 2. Get database connection from environment
        if not self._instance_env:
            raise ValidationError("No environment available")

        # 3. Build and execute query
        backend_type = self._instance_env.backend_type
        if backend_type == "mongodb":
            # Build MongoDB query
            builder = MongoQueryBuilder(self._name)
            builder.insert_one(values)
            query = await builder.build()

            # Execute query in transaction
            async with self._instance_env.transaction() as tx:
                # Pre-create hooks
                await self._before_create(values)

                # Execute create
                executor = MongoQueryExecutor(tx)
                result = await executor.execute(query)

                # Get created record ID
                record_id = result.get("inserted_id")
                if not record_id:
                    raise ValidationError("Failed to create record: No ID returned")

                # Post-create hooks
                record = await self._browse([record_id])
                await self._after_create(record)

                return record
        else:
            raise NotImplementedError(f"Backend {backend_type} not supported yet")

    async def _write(self, values: Dict[str, Any]) -> "RecordSetType":
        """Update record in database.

        Args:
            values: Field values to update

        Returns:
            RecordSet containing the updated record

        Raises:
            ValidationError: If validation fails or no records to update
        """
        # 1. Check records exist
        if not self._ids:
            raise ValidationError("No records to update")

        # 2. Validate values
        await self._validate_values(values)

        # 3. Get database connection from environment
        if not self._instance_env:
            raise ValidationError("No environment available")

        # 4. Build and execute query
        backend_type = self._instance_env.backend_type
        if backend_type == "mongodb":
            # Build MongoDB query
            builder = MongoQueryBuilder(self._name)
            builder.filter({"_id": {"$in": self._ids}}).update({"$set": values})
            query = await builder.build()

            # Execute query in transaction
            async with self._instance_env.transaction() as tx:
                # Pre-write hooks
                await self._before_write(values)

                # Execute update
                executor = MongoQueryExecutor(tx)
                result = await executor.execute(query)

                # Check update success
                if not result.get("modified_count"):
                    raise ValidationError("Failed to update records")

                # Post-write hooks
                record = await self._browse(self._ids)
                await self._after_write(record)

                return record
        else:
            raise NotImplementedError(f"Backend {backend_type} not supported yet")

    async def _unlink(self, ids: List[int]) -> bool:
        """Delete records from database.

        Args:
            ids: List of record IDs to delete

        Returns:
            True if successful

        Raises:
            ValidationError: If validation fails or no records to delete

        Examples:
            >>> success = await model._unlink([1, 2, 3])
            >>> print(success)  # True
        """
        # 1. Check records exist
        if not ids:
            raise ValidationError("No records to delete")

        # 2. Get database connection from environment
        if not self._instance_env:
            raise ValidationError("No environment available")

        # 3. Build and execute query
        backend_type = self._instance_env.backend_type
        if backend_type == "mongodb":
            # Build MongoDB query
            builder = MongoQueryBuilder(self._name)
            builder.filter({"_id": {"$in": ids}}).delete()
            query = await builder.build()

            # Execute query in transaction
            async with self._instance_env.transaction() as tx:
                # Pre-unlink hooks
                await self._before_unlink(ids)

                # Execute delete
                executor = MongoQueryExecutor(tx)
                result = await executor.execute(query)

                # Check delete success
                if not result.get("deleted_count"):
                    raise ValidationError("Failed to delete records")

                # Post-unlink hooks
                await self._after_unlink(ids)

                return True
        else:
            raise NotImplementedError(f"Backend {backend_type} not supported yet")

    def _domain_to_query(self, domain: List[Any]) -> JsonDict:
        """Convert domain expression to database query.

        Args:
            domain: Domain expression list

        Returns:
            Database query dict

        Examples:
            >>> model._domain_to_query([["age", ">", 18], "AND", ["status", "=", "active"]])
            {"$and": [{"age": {"$gt": 18}}, {"status": "active"}]}
        """
        # Create domain expression
        expr = DomainExpression(domain)

        # Convert to database query based on backend type
        backend_type = self._instance_env.backend_type
        if backend_type == "mongodb":
            converter = MongoConverter()
        else:
            raise NotImplementedError(f"Backend {backend_type} not supported yet")

        return converter.convert(expr)

    async def _before_create(self, values: Dict[str, Any]) -> None:
        """Hook called before creating record.

        Args:
            values: Field values for new record
        """
        pass

    async def _after_create(self, record: "RecordSetType") -> None:
        """Hook called after creating record.

        Args:
            record: Created record
        """
        pass

    async def _before_write(self, values: Dict[str, Any]) -> None:
        """Hook called before writing record.

        Args:
            values: Field values to update
        """
        pass

    async def _after_write(self, record: "RecordSetType") -> None:
        """Hook called after writing record.

        Args:
            record: Updated record
        """
        pass

    async def _before_unlink(self, ids: List[int]) -> None:
        """Hook called before deleting records.

        Args:
            ids: List of record IDs to delete
        """
        pass

    async def _after_unlink(self, ids: List[int]) -> None:
        """Hook called after deleting records.

        Args:
            ids: List of record IDs deleted
        """
        pass
