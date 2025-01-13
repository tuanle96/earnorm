"""Base model implementation."""

from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo.cursor import Cursor

from earnorm.base.registry import Registry
from earnorm.di import container

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
env: Registry = container.get("registry")


class BaseModel:
    """Base model implementation.

    Attributes:
        _name: Model name, used as collection name if _collection not set
        _collection: Override MongoDB collection name (optional)
        _abstract: Whether this is an abstract model (optional)
        _data: Model data dictionary (optional)
        _indexes: Collection indexes configuration (optional)
        _validators: List of validator functions (optional)
        _constraints: List of constraint functions (optional)
        _acl: Access control configuration (optional)
        _rules: Record rules configuration (optional)
        _events: Event handlers configuration (optional)
        _audit: Audit logging configuration (optional)
        _cache: Caching configuration (optional)
        _metrics: Metrics configuration (optional)
        _json_encoders: Custom JSON encoders (optional)
    """

    # Required attributes
    _name: str = ""

    # Optional attributes with default values
    _collection: str = ""  # Override collection name
    _abstract: bool = False
    _data: Dict[str, Any] = {}
    _indexes: Union[IndexDict, List[Dict[str, Any]]] = []
    _validators: List[ValidatorFunc[Any]] = []
    _constraints: List[ConstraintFunc[Any]] = []
    _acl: AclDict = {}
    _rules: RuleDict = {}
    _events: Dict[str, List[ValidatorFunc[Any]]] = {}
    _audit: AuditConfig = {}
    _cache: CacheConfig = {}
    _metrics: MetricsConfig = {}
    _json_encoders: JsonEncoders = {}
    env: Registry = env

    def __init__(self, **data: Any) -> None:
        """Initialize model instance.

        Args:
            **data: Model data
        """
        self._data = data
        self._collection = getattr(self.__class__, "_collection", self._name)
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
        """Parse order string to MongoDB sort specification."""
        sort: List[Tuple[str, int]] = []
        for item in order.split(","):
            field, direction = item.strip().split(" ")
            sort.append((field, 1 if direction.lower() == "asc" else -1))
        return sort

    @classmethod
    async def _get_collection(cls) -> Collection:
        """Get MongoDB collection."""
        # Get registry from container to ensure we have the latest instance
        registry = container.get("registry")
        if registry.db is None:
            raise RuntimeError("Database not initialized")
        return registry.db[cls._collection]
