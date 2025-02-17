"""MongoDB adapter implementation.

This module provides MongoDB-specific implementation of the database adapter interface.
It handles all database operations including CRUD operations.

Examples:
    >>> adapter = MongoAdapter(pool=mongo_pool)
    >>> await adapter.init()
    >>> user_id = await adapter.create("users", {"name": "John"})
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

from earnorm.base.database.adapter import DatabaseAdapter
from earnorm.base.database.query.backends.mongo.converter import MongoConverter
from earnorm.exceptions import DatabaseError
from earnorm.pool.backends.mongo.connection import MongoConnection
from earnorm.pool.protocols.pool import AsyncPoolProtocol

logger = logging.getLogger(__name__)


class MongoAdapter(
    DatabaseAdapter[
        MongoConnection[AsyncIOMotorDatabase[Any], AsyncIOMotorCollection[Any]],
        AsyncIOMotorCollection[Any],
    ]
):
    """MongoDB adapter implementation.

    This class provides MongoDB-specific implementation of the database adapter interface.
    It handles all database operations including CRUD operations.

    Attributes:
        pool: MongoDB connection pool
        logger: Logger instance for this class
    """

    def __init__(
        self,
        pool: AsyncPoolProtocol[
            MongoConnection[AsyncIOMotorDatabase[Any], AsyncIOMotorCollection[Any]],
            AsyncIOMotorCollection[Any],
        ],
        *,
        env: Optional[Any] = None,
    ) -> None:
        """Initialize MongoDB adapter.

        Args:
            pool: MongoDB connection pool
            env: Environment instance
        """
        super().__init__(pool, env=env)

    @property
    def backend_type(self) -> str:
        """Get database backend type.

        Returns:
            str: Always returns 'mongodb'
        """
        return "mongodb"

    async def _init_adapter(self) -> None:
        """Initialize adapter-specific functionality.

        This method is called during initialization to set up any MongoDB-specific
        configuration or checks.

        Examples:
            >>> adapter = MongoAdapter(pool)
            >>> await adapter._init_adapter()  # Sets up MongoDB-specific config
        """
        try:
            async with await self.pool.connection() as db:
                await db.ping()
                self.logger.info(
                    "Successfully connected to MongoDB with pool: %s", self.pool
                )
        except Exception as e:
            raise DatabaseError(
                f"Failed to initialize MongoDB adapter: {e!s}", backend="mongodb"
            ) from e

    async def store_exists(self, name: str) -> bool:
        """Check if store exists.

        Args:
            name: Store name (collection in MongoDB)

        Returns:
            bool: True if store exists, False otherwise

        Examples:
            >>> exists = await adapter.store_exists("users")
            >>> print(exists)  # True if collection exists
        """
        try:
            async with await self.pool.connection() as db:
                collections = await db.execute("list_collection_names")
                return name in collections
        except Exception as e:
            raise DatabaseError(
                f"Failed to check if store {name} exists: {e!s}", backend="mongodb"
            ) from e

    async def init(self) -> None:
        """Initialize adapter.

        This method is called after adapter is created.
        It checks connection to database and performs any necessary setup.

        Raises:
            DatabaseError: If initialization fails
        """
        try:
            async with await self.pool.connection() as db:
                await db.ping()
        except Exception as e:
            raise DatabaseError(
                f"Failed to initialize MongoDB adapter: {e!s}", backend="mongodb"
            ) from e

    async def create(
        self,
        store: str,
        values: Union[Dict[str, Any], List[Dict[str, Any]]],
    ) -> Union[str, List[str]]:
        """Create one or more records in store.

        Args:
            store: Store name
            values: Record data or list of record data

        Returns:
            Record ID or list of record IDs

        Raises:
            DatabaseError: If creation fails
        """
        try:
            async with await self.pool.connection() as db:
                # Set store name for this operation
                db.set_store(store)

                if isinstance(values, list):
                    result = await db.execute("insert_many", documents=values)
                    return [str(id) for id in result.inserted_ids]
                result = await db.execute("insert_one", document=values)
                return str(result.inserted_id)
        except Exception as e:
            raise DatabaseError(
                f"Failed to create records in {store}: {e!s}", backend="mongodb"
            ) from e

    async def update(
        self,
        store: str,
        ids: List[str],
        values: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Update records in store.

        Args:
            store: Store name
            ids: List of record IDs to update
            values: Record data

        Returns:
            Number of updated records

        Raises:
            DatabaseError: If update fails
        """
        if not ids or not values:
            return 0
        try:
            async with await self.pool.connection() as db:
                db.set_store(store)
                # Convert string IDs to ObjectId and create filter
                object_ids = [ObjectId(id) for id in ids]
                filter = {"_id": {"$in": object_ids}}

                result = await db.execute(
                    "update_many",
                    filter=filter,
                    update={"$set": values},
                )
                return result.modified_count
        except Exception as e:
            raise DatabaseError(
                f"Failed to update records in {store}: {e!s}", backend="mongodb"
            ) from e

    async def delete(
        self,
        store: str,
        ids: List[str],
    ) -> Optional[int]:
        """Delete records from store.

        Args:
            store: Store name
            ids: List of record IDs to delete

        Returns:
            Number of deleted records

        Raises:
            DatabaseError: If deletion fails
        """
        if not ids:
            return None
        try:
            async with await self.pool.connection() as db:
                db.set_store(store)
                # Convert string IDs to ObjectId and create filter
                object_ids = [ObjectId(id) for id in ids]
                filter = {"_id": {"$in": object_ids}}
                result = await db.execute("delete_many", filter=filter)
                return result.deleted_count
        except Exception as e:
            raise DatabaseError(
                f"Failed to delete records from {store}: {e!s}", backend="mongodb"
            ) from e

    async def read(
        self,
        store: str,
        id_or_ids: Union[str, List[str]],
        fields: Optional[List[str]] = None,
    ) -> Union[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        """Read records from store.

        Args:
            store: Store name
            id_or_ids: Record ID(s)
            fields: Fields to return

        Returns:
            Record data or list of record data

        Raises:
            DatabaseError: If read fails
        """
        try:
            async with await self.pool.connection() as db:
                db.set_store(store)
                projection = {field: 1 for field in fields} if fields else None
                if isinstance(id_or_ids, str):
                    result = await db.execute(
                        "find_one",
                        filter={"_id": ObjectId(id_or_ids)},
                        projection=projection,
                    )
                    if not result:
                        return None
                    result.pop("_id", None)
                    return result

                cursor = await db.execute(
                    "find",
                    filter={"_id": {"$in": [ObjectId(id) for id in id_or_ids]}},
                    projection=projection,
                )
                results = await cursor.to_list(length=None)
                for result in results:
                    result.pop("_id", None)
                return results
        except Exception as e:
            raise DatabaseError(
                f"Failed to read records from {store}: {e!s}", backend="mongodb"
            ) from e

    async def create_store(self, name: str) -> None:
        """Create store.

        Args:
            name: Store name

        Raises:
            DatabaseError: If creation fails
        """
        try:
            async with await self.pool.connection() as db:
                await db.execute("create_collection", name=name)
        except Exception as e:
            raise DatabaseError(
                f"Failed to create store {name}: {e!s}", backend="mongodb"
            ) from e

    async def delete_store(self, name: str) -> None:
        """Delete store.

        Args:
            name: Store name

        Raises:
            DatabaseError: If deletion fails
        """
        try:
            async with await self.pool.connection() as db:
                await db.execute("drop_collection", name=name)
        except Exception as e:
            raise DatabaseError(
                f"Failed to delete store {name}: {e!s}", backend="mongodb"
            ) from e

    # Add drop_store alias for delete_store
    async def drop_store(self, name: str) -> None:
        """Drop a store (alias for delete_store).

        Args:
            name: Store name (collection in MongoDB)

        Raises:
            DatabaseError: If deletion fails

        Examples:
            >>> await adapter.drop_store("users")  # Drops users collection
        """
        await self.delete_store(name)

    async def list_stores(self) -> List[str]:
        """List all stores.

        Returns:
            List of store names

        Raises:
            DatabaseError: If listing fails
        """
        try:
            async with await self.pool.connection() as db:
                collections = await db.execute("list_collection_names")
                return collections
        except Exception as e:
            raise DatabaseError("Failed to list stores", backend="mongodb") from e

    async def search(
        self,
        store: str,
        filter: Optional[Dict[str, Any]] = None,
        fields: Optional[List[str]] = None,
        offset: int = 0,
        limit: Optional[int] = None,
        order: Optional[str] = None,
    ) -> List[str]:
        """Search records using MongoDB query.

        Args:
            store: Collection name
            filter: MongoDB query filter
            fields: Fields to project
            offset: Skip records
            limit: Limit records
            order: Sort order (field_name asc/desc)

        Returns:
            List of record IDs

        Examples:
            >>> # Find users age > 20
            >>> await adapter.search(
            ...     store="users",
            ...     filter={"age": {"$gt": 20}},
            ...     fields=["_id"],
            ...     limit=10
            ... )
            >>> # Sort by name descending
            >>> await adapter.search(
            ...     store="users",
            ...     order="name desc"
            ... )
        """
        try:
            async with await self.pool.connection() as db:
                # Set collection
                db.set_store(store)

                # Build projection if fields specified
                projection = {field: 1 for field in fields} if fields else None

                # Convert filter to MongoDB query using MongoConverter
                converter = MongoConverter()
                mongo_filter = converter.convert(filter) if filter else {}

                # Parse sort order
                sort = None
                if order:
                    field, *direction = order.strip().split()
                    direction_str = direction[0].lower() if direction else "asc"
                    sort = [(field, 1 if direction_str == "asc" else -1)]

                # Build find parameters
                find_params: Dict[str, Any] = {
                    "filter": mongo_filter,
                }
                if projection is not None:
                    find_params["projection"] = projection
                if offset:
                    find_params["skip"] = offset
                if limit is not None:
                    find_params["limit"] = limit
                if sort:
                    find_params["sort"] = sort

                # Execute find query and get cursor
                cursor = await db.execute("find", **find_params)

                # Get results from cursor and extract IDs
                results = await cursor.to_list(length=None)
                return [str(doc["_id"]) for doc in results]

        except Exception as e:
            raise DatabaseError(
                f"Failed to search records from {store}: {e!s}", backend="mongodb"
            ) from e
