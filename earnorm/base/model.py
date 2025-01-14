"""Base model implementation."""

import logging
from typing import (
    Any,
    Callable,
    ClassVar,
    Coroutine,
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from pymongo.cursor import Cursor

from earnorm.base.domain import Domain, DomainParser
from earnorm.base.recordset import RecordSet
from earnorm.base.types import FieldProtocol, ModelProtocol, RecordSetProtocol

logger = logging.getLogger(__name__)

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


class BaseModel(ModelProtocol):
    """Base model implementation."""

    # Required attributes
    _name: str = ""
    _collection: str = ""
    _abstract: bool = False
    _data: Dict[str, Any] = {}
    _indexes: List[Dict[str, Any]] = []
    _container: ClassVar[Optional[Any]] = None

    @classmethod
    def get_container(cls) -> Any:
        """Get container instance.

        Returns:
            Container instance
        """
        if cls._container is None:
            from earnorm.di import container

            cls._container = container
        return cls._container

    @classmethod
    def get_env(cls) -> Any:
        """Get registry instance.

        Returns:
            Registry instance
        """
        return cls.get_container().registry

    def __init_subclass__(cls) -> None:
        """Initialize subclass annotations."""
        super().__init_subclass__()
        cls.__annotations__ = {}
        # Set field types in annotations
        for field_name, field in cls.__dict__.items():
            if isinstance(field, FieldProtocol):
                cls.__annotations__[field_name] = type(field.convert(None))

    def __init__(self, **data: Any) -> None:
        """Initialize model instance.

        Args:
            **data: Model data
        """
        self._data = data
        self._collection = getattr(self.__class__, "_collection", self._name)
        self._abstract = getattr(self.__class__, "_abstract", False)

    # Optional attributes with default values
    _validators: List[ValidatorFunc[Any]] = []
    _constraints: List[ConstraintFunc[Any]] = []
    _acl: AclDict = {}
    _rules: RuleDict = {}
    _events: Dict[str, List[ValidatorFunc[Any]]] = {}
    _audit: AuditConfig = {}
    _cache: CacheConfig = {}
    _metrics: MetricsConfig = {}
    _json_encoders: JsonEncoders = {}

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

        # Convert data to MongoDB format
        mongo_data: Dict[str, Any] = {}
        for field_name, field in self.__class__.__dict__.items():
            if isinstance(field, FieldProtocol):
                field.name = field_name  # Set field name
                value = getattr(self, field_name)
                if value is not None:  # Only save non-None values
                    mongo_data[field_name] = field.to_mongo(value)

        # Get connection from pool
        conn = await self.get_container().pool.acquire()
        try:
            # Insert or update
            if self.id:
                update_result = await collection.update_one(
                    {"_id": ObjectId(self.id)}, {"$set": mongo_data}
                )
                if not update_result.modified_count:
                    raise ValueError("Document not found")
                self._data.update(mongo_data)  # Update local data
            else:
                insert_result = await collection.insert_one(mongo_data)
                mongo_data["_id"] = insert_result.inserted_id
                self._data = mongo_data  # Update local data
        finally:
            await self.get_container().pool.release(conn)

    async def delete(self) -> None:
        """Delete model from database."""
        if not self.id:
            return

        # Get collection
        collection = await self._get_collection()

        # Get connection from pool
        conn = await self.get_container().pool.acquire()
        try:
            result = await collection.delete_one({"_id": ObjectId(self.id)})
            if not result.deleted_count:
                raise ValueError("Document not found")
        finally:
            await self.get_container().pool.release(conn)

    @classmethod
    async def find_one(
        cls: Type[ModelT], domain: Optional[List[Any]] = None, **kwargs: Any
    ) -> RecordSetProtocol[ModelT]:
        """Find single record and return as RecordSet."""
        query = DomainParser(domain).to_mongo_query()
        collection = await cls._get_collection()

        # Get connection from pool
        conn = await cls.get_container().pool.acquire()
        try:
            data = await collection.find_one(query, **kwargs)
            if data:
                return RecordSet(cls, [cls(**data)])
            return RecordSet(cls, [])
        finally:
            await cls.get_container().pool.release(conn)

    @classmethod
    async def find(
        cls, domain: Optional[Domain] = None, **kwargs: Any
    ) -> List[ModelProtocol]:
        """Find multiple documents.

        Args:
            domain: List of domain expressions
            **kwargs: Additional query options

        Returns:
            List of model instances
        """
        query = DomainParser(domain).to_mongo_query()
        collection = await cls._get_collection()

        # Get connection from pool
        conn = await cls.get_container().pool.acquire()
        try:
            cursor = collection.find(query, **kwargs)
            return [cls(**data) async for data in cursor]
        finally:
            await cls.get_container().pool.release(conn)

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
    async def _get_collection(cls) -> AsyncIOMotorCollection[Dict[str, Any]]:
        """Get MongoDB collection.

        Returns:
            Motor collection instance
        """
        # Get connection from pool
        conn = await cls.get_container().pool.acquire()
        try:
            db = conn.client[cls.get_container().registry.db.name]
            return db[cls.get_collection_name()]
        finally:
            await cls.get_container().pool.release(conn)

    @property
    def ids(self) -> List[Any]:
        """Get record IDs."""
        return [self.id] if self.id else []

    @property
    def collection_name(self) -> str:
        """Get collection name."""
        return self._collection

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        """Iterate over record fields."""
        return iter(self._data.items())

    @classmethod
    def get_collection_name(cls) -> str:
        """Get collection name."""
        return cls._collection or cls._name

    @classmethod
    def get_name(cls) -> str:
        """Get model name."""
        return cls._name

    @classmethod
    def get_indexes(cls) -> List[Dict[str, Any]]:
        """Get model indexes."""
        if isinstance(cls._indexes, dict):
            return [cls._indexes]
        return cls._indexes

    @classmethod
    async def search(
        cls: Type[ModelT], domain: Optional[List[Any]] = None, **kwargs: Any
    ) -> RecordSetProtocol[ModelT]:
        """Search records and return RecordSet."""
        query = DomainParser(domain).to_mongo_query()
        collection = await cls._get_collection()

        # Get connection from pool
        conn = await cls.get_container().pool.acquire()
        try:
            cursor = collection.find(query, **kwargs)
            records = [cls(**data) async for data in cursor]
            return RecordSet(cls, records)
        finally:
            await cls.get_container().pool.release(conn)

    @classmethod
    async def browse(cls: Type[ModelT], ids: List[str]) -> RecordSetProtocol[ModelT]:
        """Browse records by IDs."""
        domain = [("_id", "in", [ObjectId(id) for id in ids])]
        return await cls.search(domain)

    def __getattr__(self, name: str) -> Any:
        """Get dynamic attribute."""
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"'{self.__class__.__name__}' has no attribute '{name}'")
