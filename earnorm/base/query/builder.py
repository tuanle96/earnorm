"""Query builder implementation."""

from typing import Any, Dict, List, Optional, Tuple, Union

from bson import ObjectId


class QueryBuilder:
    """MongoDB query builder.

    This class provides a fluent interface for building MongoDB queries:
    - Filter conditions
    - Sort options
    - Pagination
    - Field projection

    Examples:
        >>> builder = QueryBuilder()
        >>> query = (
        ...     builder
        ...     .filter(age=18)
        ...     .sort("created_at", -1)
        ...     .limit(10)
        ...     .offset(0)
        ...     .project(name=1, email=1)
        ... )
    """

    def __init__(self) -> None:
        """Initialize builder."""
        self._query: Dict[str, Any] = {}
        self._sort: List[Tuple[str, int]] = []
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None
        self._projection: Optional[Dict[str, int]] = None

    def filter(self, **kwargs: Any) -> "QueryBuilder":
        """Add filter conditions.

        Args:
            **kwargs: Field conditions to filter by

        Returns:
            Self for chaining

        Examples:
            >>> builder.filter(age=18, active=True)
            >>> builder.filter(role__in=["admin", "manager"])
        """
        for key, value in kwargs.items():
            if isinstance(value, dict):
                # Handle operators
                if key in self._query:
                    self._query[key].update(value)
                else:
                    self._query[key] = value
            else:
                self._query[key] = value
        return self

    def filter_by_id(self, id: Union[str, ObjectId]) -> "QueryBuilder":
        """Filter by ID.

        Args:
            id: Document ID (string or ObjectId)

        Returns:
            Self for chaining

        Examples:
            >>> builder.filter_by_id("507f1f77bcf86cd799439011")
        """
        self._query["_id"] = ObjectId(id) if isinstance(id, str) else id
        return self

    def sort(self, field: str, direction: int = 1) -> "QueryBuilder":
        """Add sort condition.

        Args:
            field: Field to sort by
            direction: Sort direction (1 for ascending, -1 for descending)

        Returns:
            Self for chaining

        Examples:
            >>> builder.sort("created_at", -1)  # newest first
        """
        self._sort.append((field, direction))
        return self

    def limit(self, limit: int) -> "QueryBuilder":
        """Set limit.

        Args:
            limit: Maximum number of documents to return

        Returns:
            Self for chaining

        Examples:
            >>> builder.limit(10)  # return at most 10 documents
        """
        self._limit = limit
        return self

    def offset(self, offset: int) -> "QueryBuilder":
        """Set offset.

        Args:
            offset: Number of documents to skip

        Returns:
            Self for chaining

        Examples:
            >>> builder.offset(10)  # skip first 10 documents
        """
        self._offset = offset
        return self

    def project(self, **kwargs: int) -> "QueryBuilder":
        """Set field projection.

        Args:
            **kwargs: Fields to include (1) or exclude (0)

        Returns:
            Self for chaining

        Examples:
            >>> builder.project(name=1, email=1)  # include only name and email
            >>> builder.project(_id=0)  # exclude _id field
        """
        if self._projection is None:
            self._projection = {}
        self._projection.update(kwargs)
        return self

    def build(self) -> Dict[str, Any]:
        """Build final query dict.

        Returns:
            Query dict with all components

        Examples:
            >>> builder.filter(age=18).sort("name", 1).build()
            {'filter': {'age': 18}, 'sort': [('name', 1)]}
        """
        query: Dict[str, Any] = {"filter": self._query}

        if self._sort:
            query["sort"] = self._sort

        if self._limit is not None:
            query["limit"] = self._limit

        if self._offset is not None:
            query["offset"] = self._offset

        if self._projection is not None:
            query["projection"] = self._projection

        return query

    def __str__(self) -> str:
        """Get string representation."""
        return str(self.build())
