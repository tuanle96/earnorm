"""Base query class.

This module provides the base class for database queries.
It includes query validation and builder integration.

Examples:
    ```python
    class MongoQuery(Query[AsyncIOMotorDatabase]):
        def __init__(self, collection: str, filter: Dict[str, Any]) -> None:
            self.collection = collection
            self.filter = filter

        def validate(self) -> None:
            if not self.collection:
                raise ValueError("Collection name is required")
    ```
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

DBType = TypeVar("DBType")


class Query(ABC, Generic[DBType]):
    """Base class for database queries.

    This class provides common functionality for all database queries.
    It includes query validation and builder integration.

    Type Parameters:
        DBType: Database type (e.g. AsyncIOMotorDatabase)

    Examples:
        ```python
        class MongoQuery(Query[AsyncIOMotorDatabase]):
            def __init__(self, collection: str, filter: Dict[str, Any]) -> None:
                self.collection = collection
                self.filter = filter

            def validate(self) -> None:
                if not self.collection:
                    raise ValueError("Collection name is required")
        ```
    """

    @abstractmethod
    def validate(self) -> None:
        """Validate query.

        This method should validate that the query is well-formed
        and contains all required fields.

        Raises:
            ValueError: If query is invalid

        Examples:
            ```python
            query = MongoQuery("users", {"age": {"$gt": 18}})
            query.validate()  # Raises if invalid
            ```
        """
        pass

    @abstractmethod
    def clone(self) -> "Query[DBType]":
        """Create copy of query.

        This method should create a deep copy of the query.

        Returns:
            New query instance with same parameters

        Examples:
            ```python
            query = MongoQuery("users", {"age": {"$gt": 18}})
            copy = query.clone()
            ```
        """
        pass
