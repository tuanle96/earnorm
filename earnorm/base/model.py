"""Base model protocol."""

from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    List,
    Optional,
    Protocol,
    Sequence,
    TypeVar,
    runtime_checkable,
)

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from earnorm.base.core.registry import env

# Type aliases
IndexDict = Dict[str, Any]
AclDict = Dict[str, Any]
RuleDict = Dict[str, Any]
EventDict = Dict[str, List[Any]]
AuditConfig = Dict[str, Any]
CacheConfig = Dict[str, Any]
MetricsConfig = Dict[str, Any]
JsonEncoders = Dict[type, Callable[[Any], str]]

# Type variables
ModelT = TypeVar("ModelT", bound="BaseModel")

# Function types
ValidatorFunc = Callable[[ModelT], Coroutine[Any, Any, None]]
ConstraintFunc = Callable[[ModelT], Coroutine[Any, Any, None]]


@runtime_checkable
class BaseModel(Protocol):
    """Base model protocol.

    Attributes:
        _collection: MongoDB collection name
        _abstract: Whether this is an abstract model
        _data: Model data dictionary
        _indexes: Collection indexes configuration
        _validators: List of validator functions
        _constraints: List of constraint functions
        _acl: Access control configuration
        _rules: Record rules configuration
        _events: Event handlers configuration
        _audit: Audit logging configuration
        _cache: Caching configuration
        _metrics: Metrics configuration
        _json_encoders: Custom JSON encoders
    """

    _collection: str
    _abstract: bool = False
    _data: Dict[str, Any]
    _indexes: IndexDict
    _validators: List[ValidatorFunc[Any]]
    _constraints: List[ConstraintFunc[Any]]
    _acl: AclDict
    _rules: RuleDict
    _events: Dict[str, List[ValidatorFunc[Any]]]
    _audit: AuditConfig
    _cache: CacheConfig
    _metrics: MetricsConfig
    _json_encoders: JsonEncoders

    def __init__(self, **data: Any) -> None:
        """Initialize model instance.

        Args:
            **data: Model data
        """
        self._data = data
        self._collection = self.__class__._collection
        self._abstract = getattr(self.__class__, "_abstract", False)

    @property
    def id(self) -> Optional[str]:
        """Get document ID."""
        return str(self._data.get("_id")) if self._data.get("_id") else None

    async def validate(self) -> None:
        """Validate model data.

        Raises:
            ValueError: If validation fails
        """
        # Run validators
        for validator in self._validators:
            await validator(self)

        # Run constraints
        for constraint in self._constraints:
            await constraint(self)

    async def save(self) -> None:
        """Save model to database.

        Raises:
            ValueError: If validation fails
        """
        # Validate data
        await self.validate()

        # Get collection
        collection = await self._get_collection()

        # Insert or update
        if self.id:
            await collection.update_one(
                {"_id": ObjectId(self.id)}, {"$set": self._data}
            )
        else:
            result = await collection.insert_one(self._data)
            self._data["_id"] = result.inserted_id

    async def delete(self) -> None:
        """Delete model from database."""
        if not self.id:
            return

        collection = await self._get_collection()
        await collection.delete_one({"_id": ObjectId(self.id)})

    @classmethod
    async def find_one(cls, filter_: Dict[str, Any]) -> Optional["BaseModel"]:
        """Find single document.

        Args:
            filter_: Query filter

        Returns:
            Model instance if found, None otherwise
        """
        collection = await cls._get_collection()
        data = await collection.find_one(filter_)
        if data:
            return cls(**data)
        return None

    @classmethod
    async def find(cls, filter_: Dict[str, Any]) -> Sequence["BaseModel"]:
        """Find multiple documents.

        Args:
            filter_: Query filter

        Returns:
            List of model instances
        """
        collection = await cls._get_collection()
        cursor = collection.find(filter_)
        return [cls(**data) async for data in cursor]

    @classmethod
    async def _get_collection(cls) -> AsyncIOMotorCollection:
        """Get MongoDB collection.

        Returns:
            AsyncIOMotorCollection instance
        """
        if cls._abstract:
            raise ValueError("Cannot access collection of abstract model")
        return await env.get_collection(cls._collection)

    async def write(self, values: Dict[str, Any]) -> None:
        """Update model with values.

        Args:
            values: Values to update
        """
        self._data.update(values)
        await self.save()

    async def unlink(self) -> None:
        """Delete model."""
        await self.delete()

    def read(self, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """Read model data.

        Args:
            fields: List of fields to read, None for all fields

        Returns:
            Model data dictionary
        """
        if fields is None:
            return dict(self._data)
        return {k: v for k, v in self._data.items() if k in fields}

    @classmethod
    async def search(
        cls,
        domain: List[tuple],
        offset: int = 0,
        limit: Optional[int] = None,
        order: Optional[str] = None,
    ) -> Sequence["BaseModel"]:
        """Search for records.

        Args:
            domain: Search domain
            offset: Number of records to skip
            limit: Maximum number of records to return
            order: Sort order

        Returns:
            List of model instances
        """
        # Convert domain to MongoDB query
        query = cls._domain_to_query(domain)

        # Build find options
        options = {}
        if offset:
            options["skip"] = offset
        if limit:
            options["limit"] = limit
        if order:
            options["sort"] = cls._parse_order(order)

        # Execute query
        collection = await cls._get_collection()
        cursor = collection.find(query, **options)
        return [cls(**data) async for data in cursor]

    @classmethod
    async def search_count(cls, domain: List[tuple]) -> int:
        """Count records matching domain.

        Args:
            domain: Search domain

        Returns:
            Number of matching records
        """
        query = cls._domain_to_query(domain)
        collection = await cls._get_collection()
        return await collection.count_documents(query)

    @classmethod
    def _domain_to_query(cls, domain: List[tuple]) -> Dict:
        """Convert domain to MongoDB query.

        Args:
            domain: Search domain

        Returns:
            MongoDB query dict
        """
        query = {}
        current_op = "$and"

        for item in domain:
            if item == "|":
                current_op = "$or"
                continue
            if item == "&":
                current_op = "$and"
                continue

            field, op, value = item
            if op == "=":
                query[field] = value
            elif op == "!=":
                query[field] = {"$ne": value}
            elif op == ">":
                query[field] = {"$gt": value}
            elif op == ">=":
                query[field] = {"$gte": value}
            elif op == "<":
                query[field] = {"$lt": value}
            elif op == "<=":
                query[field] = {"$lte": value}
            elif op == "in":
                query[field] = {"$in": value}
            elif op == "not in":
                query[field] = {"$nin": value}
            elif op == "like":
                query[field] = {"$regex": value.replace("%", ".*")}
            elif op == "ilike":
                query[field] = {"$regex": value.replace("%", ".*"), "$options": "i"}

        return query

    @classmethod
    def _parse_order(cls, order: str) -> List[tuple]:
        """Parse order string to MongoDB sort specification.

        Args:
            order: Order string (e.g. "name asc, date desc")

        Returns:
            List of (field, direction) tuples
        """
        sort = []
        for item in order.split(","):
            field, direction = item.strip().split(" ")
            sort.append((field, 1 if direction.lower() == "asc" else -1))
        return sort
