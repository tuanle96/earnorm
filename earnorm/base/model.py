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
from motor.motor_asyncio import (
    AsyncIOMotorCollection,
    AsyncIOMotorCursor,
    AsyncIOMotorDatabase,
)
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

    # Cache configuration
    _cache_enabled: bool = True  # Enable/disable caching for this model
    _cache_ttl: int = 3600  # Default TTL in seconds
    _cache_prefix: Optional[str] = None  # Custom prefix for this model

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

    @classmethod
    def get_cache_manager(cls) -> Optional[Any]:
        """Get cache manager instance.

        Returns:
            Cache manager instance if available
        """
        try:
            return cls.get_container().get("cache_manager")
        except Exception as e:
            logger.error(f"Error getting cache manager: {str(e)}")
            return None

    @classmethod
    def get_cache_key(cls, key: str) -> str:
        """Get cache key with model prefix.

        Args:
            key: Base key

        Returns:
            Full cache key
        """
        prefix = cls._cache_prefix or f"{cls._name}:"
        return f"{prefix}{key}"

    @classmethod
    def get_query_cache_key(cls, query: Dict[str, Any], **kwargs: Any) -> str:
        """Generate cache key for a query.

        Args:
            query: MongoDB query
            **kwargs: Additional query options

        Returns:
            Cache key
        """
        # Sort query and kwargs to ensure consistent keys
        sorted_query = {k: query[k] for k in sorted(query.keys())}
        sorted_kwargs = {k: kwargs[k] for k in sorted(kwargs.keys())}

        # Create unique key based on query and options
        key_parts = [str(sorted_query), str(sorted_kwargs)]
        return cls.get_cache_key(":".join(key_parts))

    @classmethod
    def get_record_cache_key(cls, record_id: str) -> str:
        """Get cache key for a specific record.

        Args:
            record_id: Record ID

        Returns:
            Cache key for the record
        """
        return cls.get_cache_key(f"record:{record_id}")

    async def invalidate_cache(self) -> None:
        """Invalidate all cache entries for this record."""
        cache = self.get_cache_manager()
        if cache and self._cache_enabled:
            # Clear all cache entries for this record
            pattern = self.get_cache_key(f"*{self.id}*")
            await cache.clear(pattern)

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

    async def verify_exists(self) -> bool:
        """Verify record exists in database."""
        if not self.id:
            return False

        collection = await self._get_collection()
        result = await collection.find_one({"_id": ObjectId(self.id)})

        # If record doesn't exist, invalidate cache
        if not result:
            cache = self.get_cache_manager()
            if cache and self._cache_enabled:
                # Invalidate both record cache and query cache
                key = self.get_record_cache_key(self.id)
                await cache.delete(key)
                await cache.delete_pattern(f"{self.__class__._name}:query:*")

                # Also check if key exists in cache and delete pattern if it does
                if await cache.exists(key):
                    logger.warning(
                        f"Found orphaned cache entry for deleted record {self.id}"
                    )
                    await cache.delete_pattern(f"*{self.id}*")

        return bool(result)

    async def save(self) -> None:
        """Save model to database."""
        import logging

        logger = logging.getLogger(self.__class__.__name__)

        # Get cache manager
        cache = self.get_cache_manager()

        try:
            # Get distributed lock if cache enabled
            if cache and self._cache_enabled:
                async with await cache.with_lock(
                    f"save:{self.__class__._name}:{self.id or 'new'}"
                ):
                    # Validate data
                    logger.debug("Validating data")
                    await self.validate()

                    # For existing records, verify existence in DB
                    if self.id:
                        exists = await self.verify_exists()
                        if not exists:
                            raise ValueError(
                                f"Record {self.id} does not exist or has been deleted"
                            )

                    # Get collection
                    collection = await self._get_collection()
                    logger.debug(f"Using collection: {collection.name}")

                    # Convert data to MongoDB format
                    mongo_data: Dict[str, Any] = {}

                    # Include all data from _data
                    logger.debug(f"Current data: {self._data}")
                    mongo_data.update(self._data)
                    logger.debug(f"After including _data: {mongo_data}")

                    # Convert fields to MongoDB format
                    for field_name, field in self.__class__.__dict__.items():
                        if isinstance(field, FieldProtocol):
                            field.name = field_name  # Set field name
                            value = getattr(self, field_name)
                            if value is not None:  # Only save non-None values
                                mongo_data[field_name] = field.to_mongo(value)
                    logger.debug(f"Final mongo data: {mongo_data}")

                    # Get connection from pool
                    conn = await self.get_container().pool.acquire()
                    try:
                        # Insert or update
                        if self.id:
                            # Remove _id from update data
                            update_data = {
                                k: v for k, v in mongo_data.items() if k != "_id"
                            }
                            logger.debug(
                                f"Updating document {self.id} with data: {update_data}"
                            )
                            update_result = await collection.update_one(
                                {"_id": ObjectId(self.id)}, {"$set": update_data}
                            )
                            logger.debug(
                                f"Update result: matched={update_result.matched_count}, modified={update_result.modified_count}"
                            )
                            if not update_result.matched_count:
                                raise ValueError("Document not found")
                            self._data.update(update_data)  # Update local data
                            logger.debug(f"Updated local data: {self._data}")
                        else:
                            logger.debug(
                                f"Inserting new document with data: {mongo_data}"
                            )
                            insert_result = await collection.insert_one(mongo_data)
                            mongo_data["_id"] = insert_result.inserted_id
                            self._data = mongo_data  # Update local data
                            logger.debug(
                                f"Inserted document with ID: {insert_result.inserted_id}"
                            )

                        # Batch invalidate cache
                        if cache and self._cache_enabled:
                            batch = cache.batch()
                            # Add record cache key
                            await batch.add_key(self.get_record_cache_key(str(self.id)))
                            # Add query cache pattern
                            await batch.add_pattern(f"{self.__class__._name}:query:*")
                            # Invalidate batch
                            await cache.invalidate_batch()

                    finally:
                        await self.get_container().pool.release(conn)
            else:
                # No cache, just save
                await self._save_without_lock()

        except Exception as e:
            logger.error(f"Failed to save record: {str(e)}")
            raise

    async def _save_without_lock(self) -> None:
        """Save without distributed lock."""
        # Original save implementation without lock
        await self.validate()

        if self.id:
            exists = await self.verify_exists()
            if not exists:
                raise ValueError(f"Record {self.id} does not exist or has been deleted")

        # Rest of the original save implementation...

    async def delete(self) -> None:
        """Delete model from database."""
        if not self.id:
            return

        # Get collection
        collection = await self._get_collection()

        # Get cache manager
        cache = self.get_cache_manager()

        # Get connection from pool
        conn = await self.get_container().pool.acquire()
        try:
            # Get distributed lock if cache enabled
            if cache and self._cache_enabled:
                async with await cache.with_lock(f"delete:{self.id}"):
                    # Delete from DB
                    result = await collection.delete_one({"_id": ObjectId(self.id)})
                    if not result.deleted_count:
                        raise ValueError("Document not found")

                    # Invalidate all related cache
                    batch = cache.batch()
                    # Add record cache
                    await batch.add_key(self.get_record_cache_key(self.id))
                    # Add query cache patterns
                    await batch.add_pattern(f"{self.__class__._name}:query:*")
                    # Add any pattern containing this ID
                    await batch.add_pattern(f"*{self.id}*")
                    # Invalidate batch
                    await cache.invalidate_batch()
            else:
                # No cache, just delete from DB
                result = await collection.delete_one({"_id": ObjectId(self.id)})
                if not result.deleted_count:
                    raise ValueError("Document not found")

        finally:
            await self.get_container().pool.release(conn)

    async def unlink(self) -> None:
        """Delete record from database."""
        if not self.id:
            return

        collection = await self._get_collection()
        await collection.delete_one({"_id": ObjectId(self.id)})

        # Invalidate cache
        if self._cache_enabled:
            cache = self.get_cache_manager()
            if cache:
                # Invalidate both record cache and query cache
                key = self.get_record_cache_key(self.id)
                await cache.delete(key)
                await cache.delete_pattern(f"{self.__class__._name}:query:*")

    @classmethod
    async def find_one(
        cls: Type[ModelT], domain: Optional[List[Any]] = None, **kwargs: Any
    ) -> RecordSetProtocol[ModelT]:
        """Find single record and return as RecordSet."""
        import logging

        logger = logging.getLogger(cls.__name__)

        query = DomainParser(domain).to_mongo_query()
        cache_key = cls.get_query_cache_key(query, limit=1, **kwargs)
        logger.debug(f"Finding document with query: {query}, cache_key: {cache_key}")

        # Try to get from cache
        cache = cls.get_cache_manager()
        if cache and cls._cache_enabled:
            logger.debug("Cache enabled, trying to get from cache")
            cached_data = await cache.get(cache_key)
            if cached_data is not None:
                logger.debug(f"Found in cache: {cached_data}")
                if cached_data:  # If data exists
                    # Verify cached record exists in DB
                    collection = await cls._get_collection()
                    record_id = cached_data[0].get("_id")
                    if record_id:
                        exists = await collection.find_one({"_id": ObjectId(record_id)})
                        if exists:
                            return RecordSet(cls, [cls(**cached_data[0])])
                        else:
                            # Record doesn't exist in DB, invalidate cache
                            logger.warning(
                                f"Cached record {record_id} not found in DB, invalidating cache"
                            )
                            await cache.delete(cache_key)
                            # Also invalidate any query cache that might contain this record
                            await cache.delete_pattern(f"{cls._name}:query:*")
                return RecordSet(cls, [])
            logger.debug("Not found in cache")

        # Get from database
        collection = await cls._get_collection()
        conn = await cls.get_container().pool.acquire()
        try:
            logger.debug("Querying database")
            data = await collection.find_one(query, **kwargs)
            logger.debug(f"Database result: {data}")
            result = [data] if data else []

            # Cache the result
            if cache and cls._cache_enabled:
                logger.debug(f"Caching result: {result}")
                await cache.set(cache_key, result, cls._cache_ttl)

            if result:
                logger.debug("Returning record from database")
                return RecordSet(cls, [cls(**result[0])])
            logger.debug("No record found in database")
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
        cache_key = cls.get_query_cache_key(query, **kwargs)

        # Try to get from cache
        cache = cls.get_cache_manager()
        if cache and cls._cache_enabled:
            cached_data = await cache.get(cache_key)
            if cached_data is not None:
                return [cls(**data) for data in cached_data]

        # Get from database
        collection = await cls._get_collection()
        conn = await cls.get_container().pool.acquire()
        try:
            cursor = collection.find(query, **kwargs)
            result = [data async for data in cursor]

            # Cache the result
            if cache and cls._cache_enabled:
                await cache.set(cache_key, result, cls._cache_ttl)

            return [cls(**data) for data in result]
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
        """Search records and return as RecordSet."""
        import logging

        logger = logging.getLogger(cls.__name__)

        query = DomainParser(domain).to_mongo_query()
        cache_key = cls.get_query_cache_key(query, **kwargs)
        logger.debug(f"Searching documents with query: {query}, cache_key: {cache_key}")

        # Try to get from cache
        cache = cls.get_cache_manager()
        if cache and cls._cache_enabled:
            logger.debug("Cache enabled, trying to get from cache")
            cached_data = await cache.get(cache_key)
            if cached_data is not None:
                logger.debug(f"Found in cache: {cached_data}")
                if cached_data:  # If data exists
                    # Verify all cached records exist in DB
                    collection = await cls._get_collection()
                    all_exist = True
                    invalid_ids: List[str] = []

                    for record in cached_data:
                        record_id = record.get("_id")
                        if record_id:
                            exists = await collection.find_one(
                                {"_id": ObjectId(record_id)}
                            )
                            if not exists:
                                all_exist = False
                                invalid_ids.append(record_id)

                    if all_exist:
                        return RecordSet(cls, [cls(**data) for data in cached_data])
                    else:
                        # Some records don't exist in DB, invalidate cache
                        logger.warning(
                            f"Cached records {invalid_ids} not found in DB, invalidating cache"
                        )
                        await cache.delete(cache_key)
                        # Also invalidate any query cache that might contain these records
                        await cache.delete_pattern(f"{cls._name}:query:*")
                return RecordSet(cls, [])
            logger.debug("Not found in cache")

        # Get from database
        collection = await cls._get_collection()
        conn = await cls.get_container().pool.acquire()
        try:
            logger.debug("Querying database")
            cursor: AsyncIOMotorCursor[Dict[str, Any]] = collection.find(
                query, **kwargs
            )
            data: List[Dict[str, Any]] = await cursor.to_list(length=None)  # type: ignore[assignment]
            logger.debug(f"Database result: {data}")

            # Cache the result
            if cache and cls._cache_enabled:
                logger.debug(f"Caching result: {data}")
                await cache.set(cache_key, data, cls._cache_ttl)

            return RecordSet(cls, [cls(**doc) for doc in data])
        finally:
            await cls.get_container().pool.release(conn)

    @classmethod
    async def browse(cls: Type[ModelT], ids: List[str]) -> RecordSetProtocol[ModelT]:
        """Browse records by IDs."""
        # Try to get from cache first
        cache = cls.get_cache_manager()
        if cache and cls._cache_enabled:
            # Try to get each record from cache
            cached_records: List[ModelT] = []
            missing_ids: List[str] = []

            for id in ids:
                cache_key = cls.get_cache_key(f"id:{id}")
                cached_data = await cache.get(cache_key)
                if cached_data is not None:
                    cached_records.append(cls(**cached_data))
                else:
                    missing_ids.append(id)

            # If all records were cached, return them
            if not missing_ids:
                return RecordSet(cls, cached_records)

            # Otherwise, fetch missing records
            domain = [("_id", "in", [ObjectId(id) for id in missing_ids])]
            missing_records = await cls.search(domain)

            # Cache the missing records
            for record in missing_records:
                cache_key = cls.get_cache_key(f"id:{record.id}")
                await cache.set(cache_key, record.data, cls._cache_ttl)

            # Combine cached and missing records
            all_records = cached_records + list(missing_records)

            # Sort records to match original ID order
            id_map = {str(record.id): record for record in all_records}
            sorted_records = [id_map[id] for id in ids if id in id_map]

            return RecordSet(cls, sorted_records)

        # If cache is disabled, just search by IDs
        domain = [("_id", "in", [ObjectId(id) for id in ids])]
        return await cls.search(domain)

    def __getattr__(self, name: str) -> Any:
        """Get dynamic attribute."""
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"'{self.__class__.__name__}' has no attribute '{name}'")

    async def get_collection(self) -> Collection:
        """Get collection for this model.

        Returns:
            AsyncIOMotorCollection instance
        """
        return await self._get_collection()

    async def write(self, values: Dict[str, Any]) -> bool:
        """Update record with values.

        Args:
            values: Dictionary of field values to update

        Returns:
            True if update successful

        Raises:
            ValueError: If validation fails
        """
        import logging

        logger = logging.getLogger(self.__class__.__name__)

        logger.debug(f"Writing values to record: {values}")

        # Update attributes and data
        for key, value in values.items():
            logger.debug(f"Setting {key}={value}")
            setattr(self, key, value)
            self._data[key] = value

        # Save updated record
        logger.debug("Saving record")
        await self.save()
        logger.debug("Record saved successfully")

        return True

    @classmethod
    async def cleanup_orphaned_cache(cls) -> None:
        """Cleanup orphaned cache entries.

        This method scans all record cache entries and removes those
        whose corresponding records no longer exist in the database.
        """
        logger.info(f"Starting orphaned cache cleanup for {cls._name}")

        if not cls._cache_enabled:
            logger.debug("Cache is disabled, skipping cleanup")
            return

        cache = cls.get_cache_manager()
        if not cache:
            logger.warning("Cache manager not available")
            return

        try:
            # Get all record cache keys
            pattern = cls.get_cache_key("record:*")
            keys = await cache.keys(pattern)

            if not keys:
                logger.debug(f"No cache entries found matching pattern: {pattern}")
                return

            logger.info(f"Found {len(keys)} cache entries to check")

            # Get collection for existence check
            collection = await cls._get_collection()

            # Track statistics
            total = len(keys)
            removed = 0

            # Check each cached record
            for key in keys:
                try:
                    # Extract ID from key (last part after "record:")
                    record_id = key.split("record:")[-1]

                    # Check if record exists in DB
                    exists = await collection.find_one({"_id": ObjectId(record_id)})

                    if not exists:
                        logger.debug(
                            f"Record {record_id} not found in DB, cleaning up cache"
                        )
                        # Delete all related cache entries
                        batch = cache.batch()
                        await batch.add_key(key)  # Record cache
                        await batch.add_pattern(f"{cls._name}:query:*")  # Query cache
                        await batch.add_pattern(f"*{record_id}*")  # Any related cache
                        await cache.invalidate_batch()
                        removed += 1

                except Exception as e:
                    logger.error(f"Error cleaning up cache for key {key}: {str(e)}")
                    continue

            logger.info(
                f"Cleanup complete - Checked: {total}, Removed: {removed}, "
                f"Remaining: {total - removed}"
            )

        except Exception as e:
            logger.error(f"Failed to cleanup orphaned cache: {str(e)}")

    @property
    def event_bus(self) -> Any:
        """Get event bus instance.

        Returns:
            Event bus instance from container
        """
        return self.get_container().event_bus
