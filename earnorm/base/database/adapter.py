"""Database adapter interface.

This module provides the base adapter interface for database operations.
It provides methods for querying, inserting, updating, and deleting data asynchronously.

Examples:
    >>> adapter = MongoAdapter(client)
    >>> # Basic query
    >>> users = await adapter.query(User).filter(
    ...     DomainBuilder()
    ...     .field("age").greater_than(18)
    ...     .and_()
    ...     .field("status").equals("active")
    ...     .build()
    ... ).all()
    >>> # Join query
    >>> users = await adapter.query(User, "join").join(Post).on(User.id == Post.user_id)
    >>> # Aggregate query
    >>> stats = await adapter.query(User, "aggregate").group_by(User.age).count()
"""

from abc import ABC, abstractmethod
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import (
    Any,
    Dict,
    Generic,
    List,
    Literal,
    Optional,
    Type,
    TypeVar,
    Union,
    get_args,
    get_origin,
    overload,
)

from earnorm.base.database.query.core.query import BaseQuery
from earnorm.base.database.query.interfaces.domain import DomainExpression
from earnorm.base.database.query.interfaces.operations.aggregate import (
    AggregateProtocol as AggregateQuery,
)
from earnorm.base.database.query.interfaces.operations.join import (
    JoinProtocol as JoinQuery,
)
from earnorm.base.database.transaction.base import TransactionManager
from earnorm.types import DatabaseModel

ModelT = TypeVar("ModelT", bound=DatabaseModel)
JoinT = TypeVar("JoinT", bound=DatabaseModel)
T = TypeVar("T")

# Define supported field types
FieldType = Literal[
    "string",
    "integer",
    "float",
    "decimal",
    "boolean",
    "datetime",
    "date",
    "enum",
    "json",
    "array",
    "object",
]

# Define type mapping
TYPE_MAPPING: Dict[FieldType, Type[Any]] = {
    "string": str,
    "integer": int,
    "float": float,
    "decimal": Decimal,
    "boolean": bool,
    "datetime": datetime,
    "date": date,
    "enum": Enum,
    "json": Dict[str, Any],
    "array": List[Any],
    "object": Dict[str, Any],
}


class DatabaseAdapter(Generic[ModelT], ABC):
    """Base class for all database adapters.

    This class defines the interface that all database-specific adapters must implement.
    It provides methods for querying, inserting, updating, and deleting data asynchronously.

    Args:
        ModelT: Type of model being queried
    """

    @abstractmethod
    async def init(self) -> None:
        """Initialize and connect to database.

        This method should be called before using the adapter.
        It should initialize resources and establish database connection.

        Raises:
            ConnectionError: If connection fails
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close database connection and cleanup resources.

        This method should be called when the adapter is no longer needed.
        """
        pass

    @abstractmethod
    async def get_connection(self) -> Any:
        """Get a connection from the adapter.

        Returns:
            Any: A connection object that can be used to interact with the database.
        """
        pass

    @abstractmethod
    @overload
    async def query(
        self, model_type: Type[ModelT], query_type: Literal["base"] = "base"
    ) -> BaseQuery[ModelT]:
        """Create basic query builder.

        Args:
            model_type: Type of model to query
            query_type: Type of query ("base")

        Returns:
            Basic query builder instance

        Examples:
            >>> # Basic query
            >>> users = await adapter.query(User).filter(
            ...     DomainBuilder()
            ...     .field("age").greater_than(18)
            ...     .and_()
            ...     .field("status").equals("active")
            ...     .build()
            ... ).all()
        """
        ...

    @abstractmethod
    @overload
    async def query(
        self, model_type: Type[ModelT], query_type: Literal["aggregate"]
    ) -> AggregateQuery[ModelT]:
        """Create aggregate query builder.

        Args:
            model_type: Type of model to query
            query_type: Type of query ("aggregate")

        Returns:
            Aggregate query builder instance

        Examples:
            >>> # Aggregate query
            >>> stats = await adapter.query(User, "aggregate")\\
            ...     .group_by("status")\\
            ...     .count("total")\\
            ...     .avg("age", "avg_age")\\
            ...     .having(total__gt=100)\\
            ...     .execute()
        """
        ...

    @abstractmethod
    @overload
    async def query(
        self, model_type: Type[ModelT], query_type: Literal["join"]
    ) -> JoinQuery[ModelT, Any]:
        """Create join query builder.

        Args:
            model_type: Type of model to query
            query_type: Type of query ("join")

        Returns:
            Join query builder instance

        Examples:
            >>> # Join query
            >>> users = await adapter.query(User, "join")\\
            ...     .join(Post)\\
            ...     .on(User.id == Post.user_id)\\
            ...     .select("name", "posts.title")\\
            ...     .execute()
        """
        ...

    @abstractmethod
    async def query(
        self,
        model_type: Type[ModelT],
        query_type: Literal["base", "aggregate", "join"] = "base",
    ) -> Union[BaseQuery[ModelT], AggregateQuery[ModelT], JoinQuery[ModelT, Any]]:
        """Create query builder of specified type.

        This method supports three types of queries:
        1. Basic query - For simple CRUD operations
        2. Aggregate query - For aggregation operations (count, sum, avg, etc.)
        3. Join query - For joining multiple collections/tables

        Args:
            model_type: Type of model to query
            query_type: Type of query to create ("base", "aggregate", "join")

        Returns:
            Query builder instance of requested type

        Raises:
            ValueError: If invalid query type specified

        Examples:
            >>> # Basic query
            >>> users = await adapter.query(User).filter(
            ...     DomainBuilder()
            ...     .field("age").greater_than(18)
            ...     .and_()
            ...     .field("status").equals("active")
            ...     .build()
            ... ).all()

            >>> # Aggregate query
            >>> stats = await adapter.query(User, "aggregate")\\
            ...     .group_by("status")\\
            ...     .count("total")\\
            ...     .avg("age", "avg_age")\\
            ...     .having(total__gt=100)\\
            ...     .execute()

            >>> # Join query
            >>> users = await adapter.query(User, "join")\\
            ...     .join(Post)\\
            ...     .on(User.id == Post.user_id)\\
            ...     .select("name", "posts.title")\\
            ...     .execute()
        """
        pass

    @abstractmethod
    async def get_aggregate_query(
        self, model_type: Type[ModelT]
    ) -> AggregateQuery[ModelT]:
        """Create aggregate query builder for model type.
        This includes group operations as they are a type of aggregation.

        Args:
            model_type: Type of model to query

        Returns:
            Aggregate query builder instance
        """
        pass

    @abstractmethod
    async def get_join_query(self, model_type: Type[ModelT]) -> JoinQuery[ModelT, Any]:
        """Create join query builder for model type.

        Args:
            model_type: Type of model to query

        Returns:
            Join query builder instance
        """
        pass

    @abstractmethod
    async def transaction(self, model_type: Type[ModelT]) -> TransactionManager[ModelT]:
        """Create new transaction.

        Args:
            model_type: Type of model to use in transaction

        Returns:
            Transaction context manager
        """
        pass

    @abstractmethod
    @overload
    async def create(self, model_type: Type[ModelT], values: Dict[str, Any]) -> str:
        """Create a single record.

        Args:
            model_type: Model type
            values: Field values

        Returns:
            Created record ID

        Raises:
            DatabaseError: If creation fails
        """
        ...

    @abstractmethod
    @overload
    async def create(
        self, model_type: Type[ModelT], values: List[Dict[str, Any]]
    ) -> List[str]:
        """Create multiple records.

        Args:
            model_type: Model type
            values: List of field values for multiple records

        Returns:
            List of created record IDs

        Raises:
            DatabaseError: If creation fails
        """
        ...

    @abstractmethod
    async def create(
        self,
        model_type: Type[ModelT],
        values: Union[Dict[str, Any], List[Dict[str, Any]]],
    ) -> Union[str, List[str]]:
        """Create one or multiple records.

        This method supports two modes:
        1. Create single record with dict of values
        2. Create multiple records with list of value dicts

        Args:
            model_type: Model type
            values: Field values for one record (dict) or multiple records (list of dicts)

        Returns:
            - Single record ID when creating one record
            - List of record IDs when creating multiple records

        Raises:
            DatabaseError: If creation fails
            ValueError: If invalid values provided

        Examples:
            >>> # Create single record
            >>> user_id = await adapter.create(User, {
            ...     "name": "John",
            ...     "email": "john@example.com"
            ... })

            >>> # Create multiple records
            >>> user_ids = await adapter.create(User, [
            ...     {"name": "John", "email": "john@example.com"},
            ...     {"name": "Jane", "email": "jane@example.com"}
            ... ])
        """
        pass

    @abstractmethod
    @overload
    async def update(self, model: ModelT) -> ModelT: ...

    @abstractmethod
    @overload
    async def update(
        self,
        model: Type[ModelT],
        filter_or_ops: Union[Dict[str, Any], DomainExpression],
        values: Dict[str, Any],
    ) -> int: ...

    @abstractmethod
    @overload
    async def update(
        self,
        model: Type[ModelT],
        filter_or_ops: List[Dict[str, Any]],
    ) -> Dict[str, int]: ...

    @abstractmethod
    async def update(
        self,
        model: Union[ModelT, Type[ModelT]],
        filter_or_ops: Optional[
            Union[Dict[str, Any], DomainExpression, List[Dict[str, Any]]]
        ] = None,
        values: Optional[Dict[str, Any]] = None,
    ) -> Union[ModelT, int, Dict[str, int]]:
        """Update one or multiple records.

        This method supports three modes:
        1. Update single record from model instance
        2. Update multiple records by filter or domain expression
        3. Bulk update multiple records with different operations

        Args:
            model: Model instance or model type
            filter_or_ops: One of:
                - None: When updating single model instance
                - Dict: Filter for updating multiple records
                - DomainExpression: Domain expression for filtering records
                - List[Dict]: List of bulk operations
            values: Values to update (only used with filter or domain expression)

        Returns:
            - Updated model instance when updating single record
            - Number of records updated when using filter/domain expression
            - Dict of operation counts when doing bulk update

        Raises:
            DatabaseError: If update fails
            ValueError: If model has no ID or invalid arguments

        Examples:
            >>> # Update single record
            >>> user = await User.browse("123")
            >>> user.name = "New Name"
            >>> updated_user = await adapter.update(user)

            >>> # Update multiple records by filter
            >>> updated = await adapter.update(
            ...     User,
            ...     {"status": "inactive"},
            ...     {"status": "active"}
            ... )
            >>> print(f"Updated {updated} records")

            >>> # Update multiple records by domain expression
            >>> domain = DomainExpression([
            ...     ("age", ">", 18),
            ...     "&",
            ...     ("status", "=", "active")
            ... ])
            >>> updated = await adapter.update(
            ...     User,
            ...     domain,
            ...     {"group": "adult"}
            ... )
            >>> print(f"Updated {updated} records")

            >>> # Bulk update operations
            >>> result = await adapter.update(User, [
            ...     {
            ...         "filter": {"status": "inactive"},
            ...         "values": {"status": "active"},
            ...         "operation": "update"
            ...     },
            ...     {
            ...         "filter": {"email": "old@example.com"},
            ...         "values": {"email": "new@example.com"},
            ...         "operation": "update"
            ...     },
            ...     {
            ...         "values": {"name": "New User", "email": "new@example.com"},
            ...         "operation": "insert"
            ...     },
            ...     {
            ...         "filter": {"status": "deleted"},
            ...         "operation": "delete"
            ...     }
            ... ])
            >>> print(f"Updated: {result['updated']}")
            >>> print(f"Inserted: {result['inserted']}")
            >>> print(f"Deleted: {result['deleted']}")
        """
        pass

    @abstractmethod
    @overload
    async def read(
        self, source: Type[ModelT], id_or_ids: str, fields: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Read a single record using model type.

        Args:
            source: Type of model to read
            id_or_ids: Record ID to read
            fields: Optional list of fields to read. If None, all fields are read.

        Returns:
            Dict containing record data if found, None otherwise

        Raises:
            DatabaseError: If read operation fails

        Examples:
            >>> # Read all fields
            >>> user = await adapter.read(User, "123")
            >>> # Read specific fields
            >>> user = await adapter.read(User, "123", ["name", "email"])
        """
        ...

    @abstractmethod
    @overload
    async def read(
        self, source: str, id_or_ids: str, fields: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Read a single record using collection name.

        Args:
            source: Collection/table name
            id_or_ids: Record ID to read
            fields: List of fields to read

        Returns:
            Dict containing record data if found, None otherwise

        Raises:
            DatabaseError: If read operation fails

        Examples:
            >>> user = await adapter.read("users", "123", ["name", "email"])
        """
        ...

    @abstractmethod
    @overload
    async def read(
        self,
        source: Type[ModelT],
        id_or_ids: List[str],
        fields: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Read multiple records using model type.

        Args:
            source: Type of model to read
            id_or_ids: List of record IDs to read
            fields: Optional list of fields to read. If None, all fields are read.

        Returns:
            List of records

        Raises:
            DatabaseError: If read operation fails

        Examples:
            >>> # Read all fields
            >>> users = await adapter.read(User, ["123", "456"])
            >>> # Read specific fields
            >>> users = await adapter.read(User, ["123", "456"], ["name", "email"])
        """
        ...

    @abstractmethod
    @overload
    async def read(
        self, source: str, id_or_ids: List[str], fields: List[str]
    ) -> List[Dict[str, Any]]:
        """Read multiple records using collection name.

        Args:
            source: Collection/table name
            id_or_ids: List of record IDs to read
            fields: List of fields to read

        Returns:
            List of records

        Raises:
            DatabaseError: If read operation fails

        Examples:
            >>> users = await adapter.read("users", ["123", "456"], ["name", "email"])
        """
        ...

    @abstractmethod
    async def read(
        self,
        source: Union[Type[ModelT], str],
        id_or_ids: Union[str, List[str]],
        fields: Optional[List[str]] = None,
    ) -> Union[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        """Read one or multiple records from database.

        This method supports four modes:
        1. Read single record using model type
        2. Read single record using collection name
        3. Read multiple records using model type
        4. Read multiple records using collection name

        Args:
            source: Model type or collection name
            id_or_ids: Single record ID or list of record IDs
            fields: Fields to read (optional for model type)

        Returns:
            - Dict or None when reading single record
            - List of dicts when reading multiple records

        Raises:
            DatabaseError: If read operation fails
            ValueError: If invalid arguments provided

        Examples:
            >>> # Single record with model type
            >>> user = await adapter.read(User, "123")
            >>> user = await adapter.read(User, "123", ["name", "email"])

            >>> # Single record with collection name
            >>> user = await adapter.read("users", "123", ["name", "email"])

            >>> # Multiple records with model type
            >>> users = await adapter.read(User, ["123", "456"])
            >>> users = await adapter.read(User, ["123", "456"], ["name", "email"])

            >>> # Multiple records with collection name
            >>> users = await adapter.read("users", ["123", "456"], ["name", "email"])
        """
        pass

    @abstractmethod
    @overload
    async def delete(self, model: ModelT) -> None:
        """Delete a single record.

        Args:
            model: Model instance to delete

        Raises:
            DatabaseError: If deletion fails
            ValueError: If model has no ID
        """
        ...

    @abstractmethod
    @overload
    async def delete(self, model: Type[ModelT], filter: Dict[str, Any]) -> int:
        """Delete multiple records by filter.

        Args:
            model: Model type
            filter: Filter to match records

        Returns:
            Number of records deleted

        Raises:
            DatabaseError: If deletion fails
        """
        ...

    @abstractmethod
    async def delete(
        self,
        model: Union[ModelT, Type[ModelT]],
        filter: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """Delete one or multiple records.

        This method supports two modes:
        1. Delete single record by model instance
        2. Delete multiple records by filter

        Args:
            model: Model instance or model type
            filter: Filter to match records (only used with model type)

        Returns:
            - None when deleting single record
            - Number of records deleted when using filter

        Raises:
            DatabaseError: If deletion fails
            ValueError: If model has no ID or invalid arguments

        Examples:
            >>> # Delete single record
            >>> user = await User.browse("123")
            >>> await adapter.delete(user)

            >>> # Delete multiple records
            >>> deleted = await adapter.delete(User, {"status": "inactive"})
            >>> print(f"Deleted {deleted} records")
        """
        pass

    @abstractmethod
    @overload
    async def convert_value(
        self,
        value: Any,
        field_type: Literal["string"],
        target_type: Type[str] = str,
    ) -> str:
        """Convert value to string."""
        ...

    @abstractmethod
    @overload
    async def convert_value(
        self,
        value: Any,
        field_type: Literal["integer"],
        target_type: Type[int] = int,
    ) -> int:
        """Convert value to integer."""
        ...

    @abstractmethod
    @overload
    async def convert_value(
        self,
        value: Any,
        field_type: Literal["float"],
        target_type: Type[float] = float,
    ) -> float:
        """Convert value to float."""
        ...

    @abstractmethod
    @overload
    async def convert_value(
        self,
        value: Any,
        field_type: Literal["decimal"],
        target_type: Type[Decimal] = Decimal,
    ) -> Decimal:
        """Convert value to decimal."""
        ...

    @abstractmethod
    @overload
    async def convert_value(
        self,
        value: Any,
        field_type: Literal["boolean"],
        target_type: Type[bool] = bool,
    ) -> bool:
        """Convert value to boolean."""
        ...

    @abstractmethod
    @overload
    async def convert_value(
        self,
        value: Any,
        field_type: Literal["datetime"],
        target_type: Type[datetime] = datetime,
    ) -> datetime:
        """Convert value to datetime."""
        ...

    @abstractmethod
    @overload
    async def convert_value(
        self,
        value: Any,
        field_type: Literal["date"],
        target_type: Type[date] = date,
    ) -> date:
        """Convert value to date."""
        ...

    @abstractmethod
    @overload
    async def convert_value(
        self,
        value: Any,
        field_type: Literal["enum"],
        target_type: Type[Enum],
    ) -> Enum:
        """Convert value to enum."""
        ...

    @abstractmethod
    @overload
    async def convert_value(
        self,
        value: Any,
        field_type: Literal["json"],
        target_type: Type[Dict[str, Any]] = dict,
    ) -> Dict[str, Any]:
        """Convert value to JSON object."""
        ...

    @abstractmethod
    @overload
    async def convert_value(
        self,
        value: Any,
        field_type: Literal["array"],
        target_type: Type[List[T]] = list,
    ) -> List[T]:
        """Convert value to array."""
        ...

    @abstractmethod
    async def convert_value(
        self,
        value: Any,
        field_type: FieldType,
        target_type: Optional[Type[T]] = None,
    ) -> T:
        """Convert value between database and Python format.

        This method handles conversion between database types and Python types.
        It supports all standard field types and custom type conversions.

        Args:
            value: Value to convert
            field_type: Type of field ("string", "integer", "float", etc.)
            target_type: Optional specific Python type to convert to

        Returns:
            Converted value with correct type

        Raises:
            ValueError: If conversion fails or type is not supported
            TypeError: If target_type is not compatible with field_type

        Examples:
            >>> # Basic type conversion
            >>> str_val = await adapter.convert_value(123, "string")
            >>> int_val = await adapter.convert_value("123", "integer")
            >>> float_val = await adapter.convert_value("123.45", "float")
            >>> decimal_val = await adapter.convert_value("123.45", "decimal")
            >>> bool_val = await adapter.convert_value(1, "boolean")
            >>> date_val = await adapter.convert_value("2024-01-01", "date")
            >>> datetime_val = await adapter.convert_value(
            ...     "2024-01-01T12:00:00",
            ...     "datetime"
            ... )

            >>> # Enum conversion
            >>> class Status(Enum):
            ...     ACTIVE = "active"
            ...     INACTIVE = "inactive"
            >>> enum_val = await adapter.convert_value(
            ...     "active",
            ...     "enum",
            ...     Status
            ... )

            >>> # Array conversion
            >>> array_val = await adapter.convert_value(
            ...     "[1, 2, 3]",
            ...     "array",
            ...     List[int]
            ... )

            >>> # JSON conversion
            >>> json_val = await adapter.convert_value(
            ...     '{"name": "John", "age": 30}',
            ...     "json"
            ... )
        """
        if target_type is None:
            target_type = TYPE_MAPPING.get(field_type, Any)  # type: ignore

        # Validate target_type compatibility with field_type
        expected_type = TYPE_MAPPING.get(field_type)
        if expected_type and not issubclass(get_origin(target_type) or target_type, expected_type):  # type: ignore
            raise TypeError(
                f"Target type {target_type} is not compatible with field type {field_type}"
            )

        # Handle null/None values
        if value is None:
            return None  # type: ignore

        try:
            # Convert value based on field type
            if field_type == "string":
                return str(value)  # type: ignore
            elif field_type == "integer":
                return int(value)  # type: ignore
            elif field_type == "float":
                return float(value)  # type: ignore
            elif field_type == "decimal":
                return Decimal(str(value))  # type: ignore
            elif field_type == "boolean":
                if isinstance(value, str):
                    return value.lower() in ("true", "1", "yes", "on")  # type: ignore
                return bool(value)  # type: ignore
            elif field_type == "datetime":
                if isinstance(value, str):
                    return datetime.fromisoformat(value)  # type: ignore
                return value  # type: ignore
            elif field_type == "date":
                if isinstance(value, str):
                    return date.fromisoformat(value)  # type: ignore
                elif isinstance(value, datetime):
                    return value.date()  # type: ignore
                return value  # type: ignore
            elif field_type == "enum" and target_type:
                if isinstance(value, target_type):
                    return value  # type: ignore
                return target_type(value)  # type: ignore
            elif field_type == "array":
                if isinstance(value, str):
                    import json

                    value = json.loads(value)
                if not isinstance(value, (list, tuple)):
                    raise ValueError(f"Cannot convert {value} to array")

                # Get item type from List[T]
                item_type = get_args(target_type)[0] if get_args(target_type) else None
                if item_type is None or item_type == Any:
                    return list(value)  # type: ignore

                # Convert each item using the specified type
                converted: List[Optional[T]] = [
                    item_type(item) if item is not None else None for item in value  # type: ignore
                ]
                return converted  # type: ignore
            elif field_type == "json":
                if isinstance(value, str):
                    import json

                    return json.loads(value)  # type: ignore
                return value  # type: ignore
            else:
                raise ValueError(f"Unsupported field type: {field_type}")

        except Exception as e:
            raise ValueError(
                f"Failed to convert value {value} to {field_type}: {str(e)}"
            ) from e

    @property
    @abstractmethod
    def backend_type(self) -> str:
        """Get backend type.

        Returns:
            Backend type (e.g. 'mongodb', 'postgresql', etc.)
        """
        pass

    def is_model_class(self, obj: Any) -> bool:
        """Check if object is a model class."""
        return isinstance(obj, type) and isinstance(obj, DatabaseModel)

    def is_model_instance(self, obj: Any) -> bool:
        """Check if object is a model instance."""
        return not isinstance(obj, type) and isinstance(obj, DatabaseModel)
