"""Base model protocol."""

from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    Iterator,
    List,
    Optional,
    Protocol,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    runtime_checkable,
)

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo.cursor import Cursor

from earnorm.base.registry import Registry

# Type aliases
IndexDict = Dict[str, Any]
AclDict = Dict[str, Any]
RuleDict = Dict[str, Any]
EventDict = Dict[str, List[Any]]
AuditConfig = Dict[str, Any]
CacheConfig = Dict[str, Any]
MetricsConfig = Dict[str, Any]
JsonEncoders = Dict[type, Callable[[Any], str]]
DomainTuple = Tuple[str, str, Any]
DomainOperator = Union[str, DomainTuple]  # Can be '|', '&' or a condition tuple
Domain = Sequence[DomainOperator]  # Use Sequence instead of List for covariance
MongoQuery = Dict[str, Any]
SortSpec = List[Tuple[str, int]]
Collection = AsyncIOMotorCollection[Dict[str, Any]]
Database = AsyncIOMotorDatabase[Dict[str, Any]]
MongoCursor = Cursor[Dict[str, Any]]
SearchDomain = List[Tuple[str, str, Any]]

# Type variables
ModelT = TypeVar("ModelT", bound="BaseModel")

# Function types
ValidatorFunc = Callable[[ModelT], Coroutine[Any, Any, None]]
ConstraintFunc = Callable[[ModelT], Coroutine[Any, Any, None]]

# Registry instance
env = Registry()


@runtime_checkable
class BaseModel(Protocol):
    """Base model protocol.

    Attributes:
        _collection: MongoDB collection name
        _name: Odoo-style model name
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

    # Class attributes
    _collection: str
    _name: str  # Odoo-style model name
    _abstract: bool = False
    _data: Dict[str, Any]
    _indexes: Union[IndexDict, List[Dict[str, Any]]]
    _validators: List[ValidatorFunc[Any]]
    _constraints: List[ConstraintFunc[Any]]
    _acl: AclDict
    _rules: RuleDict
    _events: Dict[str, List[ValidatorFunc[Any]]]
    _audit: AuditConfig
    _cache: CacheConfig
    _metrics: MetricsConfig
    _json_encoders: JsonEncoders
    env: Registry

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

    @property
    def collection(self) -> str:
        """Get collection name."""
        return self._collection

    @property
    def ids(self) -> List[str]:
        """Get list of IDs."""
        return [str(record.id) for record in self]

    @property
    def data(self) -> Dict[str, Any]:
        """Get model data."""
        return self._data

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
            update_result = await collection.update_one(
                {"_id": ObjectId(self.id)}, {"$set": self._data}
            )
            if not update_result.modified_count:
                raise ValueError("Document not found")
        else:
            insert_result = await collection.insert_one(self._data)
            self._data["_id"] = insert_result.inserted_id

    async def delete(self) -> None:
        """Delete model from database."""
        if not self.id:
            return

        collection = await self._get_collection()
        result = await collection.delete_one({"_id": ObjectId(self.id)})
        if not result.deleted_count:
            raise ValueError("Document not found")

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
    def _domain_to_query(
        cls, domain: Sequence[Union[str, Tuple[str, str, Any]]]
    ) -> MongoQuery:
        """Convert domain to MongoDB query.

        Args:
            domain: Search domain

        Returns:
            MongoDB query dict
        """
        query: MongoQuery = {}

        for item in domain:
            if isinstance(item, str):
                continue  # Skip operators

            field, op, value = item  # type: ignore
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
                query[field] = {"$regex": str(value).replace("%", ".*")}
            elif op == "ilike":
                query[field] = {
                    "$regex": str(value).replace("%", ".*"),
                    "$options": "i",
                }

        return query

    @classmethod
    def _parse_order(cls, order: str) -> SortSpec:
        """Parse order string to MongoDB sort specification.

        Args:
            order: Order string (e.g. "name asc, date desc")

        Returns:
            List of (field, direction) tuples
        """
        sort: SortSpec = []
        for item in order.split(","):
            field, direction = item.strip().split(" ")
            sort.append((field, 1 if direction.lower() == "asc" else -1))
        return sort

    @classmethod
    def get_indexes(cls) -> List[Dict[str, Any]]:
        """Get model indexes.

        Returns:
            List of index specifications
        """
        if hasattr(cls, "_indexes"):
            indexes = cls._indexes
            if isinstance(indexes, dict):
                return [indexes]
            return list(indexes)  # Convert to list to ensure type compatibility
        return []

    @classmethod
    async def _get_collection(cls) -> Collection:
        """Get MongoDB collection.

        Returns:
            AsyncIOMotorCollection instance

        Raises:
            ValueError: If model is abstract
            RuntimeError: If database is not initialized
        """
        if cls._abstract:
            raise ValueError("Cannot access collection of abstract model")

        db = await cls._get_db()
        return db[cls._collection]

    @classmethod
    async def _get_db(cls) -> Database:
        """Get MongoDB database.

        Returns:
            AsyncIOMotorDatabase instance

        Raises:
            RuntimeError: If database is not initialized
        """
        if not hasattr(cls.env, "db") or cls.env.db is None:
            raise RuntimeError("Database not initialized")

        db = cls.env.db
        return db  # type: ignore

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
        domain: SearchDomain,
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
        options: Dict[str, Any] = {}
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
    async def search_count(cls, domain: SearchDomain) -> int:
        """Count records matching domain.

        Args:
            domain: Search domain

        Returns:
            Number of matching records
        """
        query = cls._domain_to_query(domain)
        collection = await cls._get_collection()
        return await collection.count_documents(query)

    @property
    def collection_name(self) -> str:
        """Get collection name."""
        return self._collection

    @classmethod
    def get_collection_name(cls) -> str:
        """Get collection name for model.

        Returns:
            Collection name
        """
        return cls._collection

    @property
    def is_abstract(self) -> bool:
        """Check if model is abstract."""
        return self._abstract

    @classmethod
    def is_abstract_model(cls) -> bool:
        """Check if model is abstract."""
        return cls._abstract

    @classmethod
    def get_name(cls) -> str:
        """Get model name (Odoo-style)."""
        return cls._name

    def __iter__(self) -> Iterator["BaseModel"]:
        """Make model iterable."""
        yield self
